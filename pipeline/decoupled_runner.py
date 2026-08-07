import time
import os
import queue
import threading
import gc
import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Tuple

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live

from config import PipelineConfig
from pipeline.storage import StorageManager
from pipeline.downloader import PDFDownloader
from pipeline.extractors.searchable import PyMuPDFTextExtractor
from pipeline.cleaner import TextCleaner
from pipeline.metadata import MetadataExtractor
from pipeline.entities import EntityExtractor
from pipeline.tracker import DocumentMetrics, MachineResourceMonitor

class DecoupledPipelineScheduler:
    """
    Producer-Consumer Pipeline Scheduler:
    - Dedicated Producer Thread: Continuously streams PDF downloads from S3, saturating network bandwidth.
    - Bounded Download Queue (maxsize=8): Ensures at most 8 unprocessed PDFs exist on disk/RAM at any moment.
    - Consumer Worker Pool: Parallel CPU threads for text extraction, regex/NER entity parsing, and storage.
    - Immediate File Purge: Raw PDFs are deleted from disk immediately after text extraction.
    """

    def __init__(self, config: PipelineConfig, storage: StorageManager, max_queue_size: int = 8):
        self.config = config
        self.storage = storage
        self.max_queue_size = max_queue_size
        self.download_queue = queue.Queue(maxsize=max_queue_size)
        self.downloader = PDFDownloader(s3_base_url=config.s3_base_url, pool_maxsize=16)
        self.monitor = MachineResourceMonitor()
        self.console = Console()

        # Shared Extractor Instances for Consumer Workers
        self.text_extractor = PyMuPDFTextExtractor()
        self.cleaner = TextCleaner()
        self.metadata_extractor = MetadataExtractor()
        self.entity_extractor = EntityExtractor()

    def run_decoupled_pipeline(self, s3_keys: List[str]) -> Dict[str, Any]:
        total_pdfs = len(s3_keys)
        completed_count = 0
        skipped_count = 0
        failed_count = 0
        failed_keys = []

        total_pages_processed = 0
        total_download_ms = 0.0
        total_extract_ms = 0.0
        total_entity_ms = 0.0
        total_doc_ms = 0.0

        start_time = time.time()

        # Load checkpoint
        ckpt = self.storage.load_checkpoint() if self.config.resume_enabled else {}
        completed_doc_ids = set(ckpt.get("completed_doc_ids", []))
        if not completed_doc_ids:
            completed_doc_ids = self.storage.get_completed_doc_ids()

        num_consumers = max(1, self.config.max_workers)
        sentinel = None

        self.console.print(Panel.fit(
            f"[bold green]Starting Decoupled Producer-Consumer Pipeline Engine[/bold green]\n"
            f"Run ID: [yellow]{self.config.run_id}[/yellow] | Total PDFs: [yellow]{total_pdfs}[/yellow] | "
            f"Download Queue Safety Ceiling: [bold magenta]{self.max_queue_size} PDFs[/bold magenta] | "
            f"CPU Consumer Threads: [yellow]{num_consumers}[/yellow]"
        ))

        # --- Producer Thread Function ---
        def download_producer():
            for key in s3_keys:
                doc_id = os.path.basename(key).replace(".pdf", "")
                
                # Fast Resume Check
                if self.config.resume_enabled and (doc_id in completed_doc_ids or self.storage.is_document_processed(doc_id)):
                    self.download_queue.put(("SKIPPED", key, doc_id, None, 0.0))
                    continue

                t0 = time.perf_counter()
                dest_pdf_path = self.storage.get_pdf_path(doc_id)
                success, msg, file_bytes = self.downloader.download_pdf(key, dest_pdf_path)
                download_ms = (time.perf_counter() - t0) * 1000.0

                if success:
                    # Blocks automatically if download_queue reaches max_queue_size (8)
                    self.download_queue.put(("DOWNLOADED", key, doc_id, dest_pdf_path, download_ms, file_bytes))
                else:
                    self.download_queue.put(("FAILED", key, doc_id, None, download_ms, 0))


            # Push sentinels to signal consumers to terminate
            for _ in range(num_consumers):
                self.download_queue.put(sentinel)

        # Launch Producer Thread
        producer_thread = threading.Thread(target=download_producer, daemon=True)
        producer_thread.start()

        # --- Consumer Worker Processing ---
        def process_item(item: Any) -> Tuple[DocumentMetrics, Dict[str, Any]]:
            if len(item) == 6:
                status_tag, key, doc_id, pdf_path, download_ms, file_bytes = item
            else:
                status_tag, key, doc_id, pdf_path, download_ms = item[:5]
                file_bytes = 0

            metrics = DocumentMetrics(document_id=doc_id)
            metrics.download_ms = download_ms
            output_artifacts = {"file_bytes": file_bytes}
            start_total = time.perf_counter()


            if status_tag == "SKIPPED":
                metrics.status = "skipped"
                metrics.total_ms = (time.perf_counter() - start_total) * 1000.0
                return metrics, output_artifacts

            if status_tag == "FAILED":
                metrics.status = "download_failed"
                metrics.total_ms = (time.perf_counter() - start_total) * 1000.0
                return metrics, output_artifacts

            try:
                # Stage 1: Validate PDF
                t0 = time.perf_counter()
                val_ok, val_msg = self.downloader.validate_pdf(pdf_path)
                metrics.validation_ms = (time.perf_counter() - t0) * 1000.0
                if not val_ok:
                    metrics.status = "validation_failed"
                    self.storage.delete_pdf(doc_id)
                    return metrics, output_artifacts

                # Stage 2: Extract Text
                t0 = time.perf_counter()
                ext_res = self.text_extractor.extract_text(pdf_path)
                metrics.extract_ms = (time.perf_counter() - t0) * 1000.0
                metrics.pages = ext_res.page_count
                metrics.word_count = ext_res.word_count

                # CRITICAL SAFETY: Immediate PDF File Purge from disk right after text extraction!
                if not self.config.keep_pdf_files:
                    self.storage.delete_pdf(doc_id)

                raw_text_path = self.storage.save_raw_text(doc_id, ext_res.raw_text)
                output_artifacts["raw_text_path"] = raw_text_path

                # Stage 3: Clean Text
                t0 = time.perf_counter()
                clean_text = self.cleaner.clean_text(ext_res.raw_text)
                metrics.clean_ms = (time.perf_counter() - t0) * 1000.0
                clean_text_path = self.storage.save_clean_text(doc_id, clean_text)
                output_artifacts["clean_text_path"] = clean_text_path

                # Stage 4: Metadata Extraction
                t0 = time.perf_counter()
                meta = self.metadata_extractor.extract_metadata(clean_text, page_count=ext_res.page_count, doc_id=doc_id)
                metrics.metadata_ms = (time.perf_counter() - t0) * 1000.0
                meta_path = self.storage.save_metadata(doc_id, meta)
                output_artifacts["metadata_path"] = meta_path
                output_artifacts["metadata"] = meta

                # Stage 5: Entity Extraction
                t0 = time.perf_counter()
                entities = self.entity_extractor.extract_entities(clean_text, metadata=meta, doc_id=doc_id)
                metrics.entity_ms = (time.perf_counter() - t0) * 1000.0
                entities_path = self.storage.save_entities(doc_id, entities)
                output_artifacts["entities_path"] = entities_path
                output_artifacts["entities"] = entities

                metrics.status = "success"
                metrics.total_ms = (time.perf_counter() - start_total) * 1000.0 + download_ms
                self.storage.save_document_metrics(metrics)
                return metrics, output_artifacts

            except Exception as e:
                metrics.status = "exception_failed"
                metrics.error_message = str(e)
                metrics.total_ms = (time.perf_counter() - start_total) * 1000.0
                self.storage.delete_pdf(doc_id)
                self.storage.save_document_metrics(metrics)
                return metrics, output_artifacts

        last_drive_sync = time.time()
        sync_interval_sec = 180  # Save progress to Google Drive every 3 minutes (180 seconds)

        # Live Dashboard Loop
        with Live(self._generate_dashboard(0, total_pdfs, 0, 0, total_pdfs, 0, 0, 0, 0, 0, 0, 0, 0), refresh_per_second=4) as live:
            with ThreadPoolExecutor(max_workers=num_consumers) as executor:
                active_futures = set()


                while True:
                    # Pop next item from Producer Queue
                    item = self.download_queue.get()
                    if item is sentinel:
                        self.download_queue.task_done()
                        break

                    # Dispatch item to Consumer Thread Pool
                    future = executor.submit(process_item, item)
                    active_futures.add(future)
                    self.download_queue.task_done()

                    # Harvest completed futures
                    completed_futures = {f for f in active_futures if f.done()}
                    for f in completed_futures:
                        active_futures.remove(f)
                        try:
                            metrics, _ = f.result()
                            total_pages_processed += metrics.pages
                            total_download_ms += metrics.download_ms
                            total_extract_ms += metrics.extract_ms
                            total_entity_ms += metrics.entity_ms
                            total_doc_ms += metrics.total_ms

                            if metrics.status == "success":
                                completed_count += 1
                                completed_doc_ids.add(metrics.document_id)
                            elif metrics.status == "skipped":
                                skipped_count += 1
                            else:
                                failed_count += 1
                        except Exception:
                            failed_count += 1

                    # 3-Minute Periodic Drive Checkpoint Sync (Every 180 seconds)
                    now_time = time.time()
                    if now_time - last_drive_sync >= sync_interval_sec:
                        last_drive_sync = now_time
                        self.storage.save_checkpoint({
                            "run_id": self.config.run_id,
                            "processed_count": completed_count + skipped_count + failed_count,
                            "successful_count": completed_count,
                            "skipped_count": skipped_count,
                            "failed_count": failed_count,
                            "total_pages": total_pages_processed,
                            "completed_doc_ids": list(completed_doc_ids),
                            "timestamp": now_time
                        })

                    # Live Stats Update
                    processed_so_far = completed_count + skipped_count + failed_count
                    elapsed = now_time - start_time
                    avg_sec = elapsed / max(1, processed_so_far)
                    pdf_throughput = processed_so_far / max(0.001, elapsed)
                    pages_throughput = total_pages_processed / max(0.001, elapsed)
                    eta_sec = (total_pdfs - processed_so_far) * avg_sec

                    q_size = self.download_queue.qsize()
                    live.update(self._generate_dashboard(
                        processed_so_far, total_pdfs, completed_count, skipped_count, total_pdfs,
                        total_pages_processed, q_size, failed_count, pdf_throughput,
                        pages_throughput, eta_sec, total_download_ms, total_entity_ms, total_doc_ms
                    ))


                # Drain remaining consumer futures
                for f in active_futures:
                    try:
                        metrics, _ = f.result()
                        total_pages_processed += metrics.pages
                        total_download_ms += metrics.download_ms
                        total_extract_ms += metrics.extract_ms
                        total_entity_ms += metrics.entity_ms
                        total_doc_ms += metrics.total_ms

                        if metrics.status == "success":
                            completed_count += 1
                            completed_doc_ids.add(metrics.document_id)
                        elif metrics.status == "skipped":
                            skipped_count += 1
                        else:
                            failed_count += 1
                    except Exception:
                        failed_count += 1

        producer_thread.join()

        # Save Checkpoint with completed IDs
        self.storage.save_checkpoint({
            "run_id": self.config.run_id,
            "processed_count": completed_count + skipped_count + failed_count,
            "successful_count": completed_count,
            "skipped_count": skipped_count,
            "failed_count": failed_count,
            "total_pages": total_pages_processed,
            "completed_doc_ids": list(completed_doc_ids),
            "timestamp": time.time()
        })

        total_duration = time.time() - start_time
        processed_total = completed_count + skipped_count
        return {
            "run_id": self.config.run_id,
            "total_pdfs": total_pdfs,
            "total_pages": total_pages_processed,
            "newly_processed": completed_count,
            "skipped_existing": skipped_count,
            "failed": failed_count,
            "total_duration_sec": round(total_duration, 2),
            "throughput_pages_per_sec": round(total_pages_processed / max(0.001, total_duration), 2),
            "throughput_pdfs_per_sec": round(processed_total / max(0.001, total_duration), 2),
            "peak_ram_mb": self.monitor.get_snapshot()["ram_peak_mb"]
        }

    def _generate_dashboard(self, processed: int, total: int, completed: int, skipped: int, 
                            total_target: int, total_pages: int, q_size: int, failed: int, 
                            pdf_throughput: float, pages_throughput: float, eta_sec: float,
                            acc_download_ms: float = 0, acc_entity_ms: float = 0, acc_total_ms: float = 0) -> Panel:
        res = self.monitor.get_snapshot()
        processed_count = max(1, completed + skipped + failed)
        
        avg_download = acc_download_ms / processed_count
        avg_entity = acc_entity_ms / processed_count
        avg_total = acc_total_ms / processed_count

        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="bold white")

        table.add_row("Run ID", self.config.run_id)
        table.add_row("Progress", f"{processed} / {total} PDFs")
        table.add_row("Newly Processed PDFs", f"[bold green]{completed}[/bold green]")
        table.add_row("Skipped (Existing)", f"[yellow]{skipped}[/yellow]")
        table.add_row("Failed PDFs", f"[red]{failed}[/red]" if failed > 0 else f"{failed}")
        table.add_row("Download Queue Fill Level", f"[bold magenta]{q_size} / {self.max_queue_size} PDFs[/bold magenta]")
        table.add_row("Total Pages Processed", f"[bold green]{total_pages:,}[/bold green] pages")

        table.add_row("Pages Throughput Rate", f"[bold magenta]{pages_throughput:.2f} pages/sec[/bold magenta]")
        table.add_row("Document Throughput Rate", f"[bold cyan]{pdf_throughput:.2f} PDFs/sec[/bold cyan]")
        table.add_row("Avg Download Latency", f"{avg_download:.1f} ms / PDF")
        table.add_row("Avg Entity Latency", f"{avg_entity:.1f} ms / PDF")
        table.add_row("RAM Used RSS", f"{res['ram_used_mb']} MB")

        return Panel(table, title="[bold green]Producer-Consumer Streaming Dashboard[/bold green]", expand=False)

