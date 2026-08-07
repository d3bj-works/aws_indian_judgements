import time
import os
import json
import gc
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.live import Live

from config import PipelineConfig
from pipeline.storage import StorageManager
from orchestrator import DocumentProcessor
from pipeline.tracker import MachineResourceMonitor

from pipeline.downloader import PDFDownloader

from pipeline.decoupled_runner import DecoupledPipelineScheduler

class BatchScheduler:
    """
    Schedules and executes PDF processing using a Decoupled Producer-Consumer Architecture.
    - Producer thread streams PDF downloads continuously to saturate network bandwidth.
    - Bounded Download Queue (max 8 PDFs) prevents disk/RAM explosion.
    - Consumer thread pool processes CPU text & entity extraction concurrently.
    - Immediate file purge deletes raw PDFs from disk immediately after text extraction.
    """
    
    def __init__(self, config: PipelineConfig, storage: StorageManager, max_queue_size: int = 8):
        self.config = config
        self.storage = storage
        self.decoupled_scheduler = DecoupledPipelineScheduler(config, storage, max_queue_size=max_queue_size)
        self.console = Console()

    def run_batch_pipeline(self, s3_keys: List[str]) -> Dict[str, Any]:
        return self.decoupled_scheduler.run_decoupled_pipeline(s3_keys)

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
        
        batch_size = self.config.batch_size
        max_workers = self.config.max_workers
        
        start_pipeline_time = time.time()
        
        # Load checkpoint info if available
        ckpt = self.storage.load_checkpoint() if self.config.resume_enabled else {}
        last_completed_batch = ckpt.get("last_completed_batch", 0)
        
        # Restore stats from checkpoint if available
        if last_completed_batch > 0:
            skipped_count = ckpt.get("processed_count", last_completed_batch * batch_size)
            total_pages_processed = ckpt.get("total_pages", 0)
        
        # Partition keys into batches
        batches = [s3_keys[i:i + batch_size] for i in range(0, total_pdfs, batch_size)]
        total_batches = len(batches)
        
        self.console.print(Panel.fit(
            f"[bold blue]Starting Batch Execution Engine[/bold blue]\n"
            f"Run ID: [yellow]{self.config.run_id}[/yellow] | Total PDFs: [yellow]{total_pdfs}[/yellow] | "
            f"Workers: [yellow]{max_workers}[/yellow] | Batch Size: [yellow]{batch_size}[/yellow] | "
            f"Resume: [green]{self.config.resume_enabled}[/green] (Resuming from batch {last_completed_batch+1}/{total_batches})"
        ))

        with Live(self._generate_dashboard(max(1, last_completed_batch), total_batches, completed_count, skipped_count, total_pdfs, total_pages_processed, 0, failed_count, 0, 0, 0, 0, 0, 0), refresh_per_second=4) as live:
            for b_idx, batch in enumerate(batches, start=1):
                # Fast Checkpoint Resume: Skip entire batch if already completed in checkpoint
                if self.config.resume_enabled and b_idx <= last_completed_batch:
                    continue

                batch_start = time.time()
                
                with ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_key = {
                        executor.submit(self.processor.process_single_pdf, key): key for key in batch
                    }
                    
                    for future in as_completed(future_to_key):
                        key = future_to_key[future]
                        try:
                            metrics, _ = future.result()
                            total_pages_processed += metrics.pages
                            total_download_ms += metrics.download_ms
                            total_extract_ms += metrics.extract_ms
                            total_entity_ms += metrics.entity_ms
                            total_doc_ms += metrics.total_ms
                            
                            if metrics.status == "success":
                                completed_count += 1
                            elif metrics.status == "skipped":
                                skipped_count += 1
                            else:
                                failed_count += 1
                                failed_keys.append(key)
                        except Exception as e:
                            failed_count += 1
                            failed_keys.append(key)
                            
                        # Live Stats Update
                        processed_so_far = completed_count + skipped_count + failed_count
                        elapsed = time.time() - start_pipeline_time
                        avg_sec = elapsed / max(1, processed_so_far)
                        pdf_throughput = processed_so_far / max(0.001, elapsed)
                        pages_throughput = total_pages_processed / max(0.001, elapsed)
                        eta_sec = (total_pdfs - processed_so_far) * avg_sec
                        
                        live.update(self._generate_dashboard(
                            b_idx, total_batches, completed_count, skipped_count, total_pdfs, 
                            total_pages_processed, len(batch), failed_count, pdf_throughput, 
                            pages_throughput, eta_sec, total_download_ms, total_entity_ms, total_doc_ms
                        ))

                # Batch completed - RAM Garbage Collection & Safety Check
                gc.collect()
                if self.monitor.is_memory_exceeded(self.config.max_ram_threshold_mb):
                    self.console.print(f"[bold red]WARNING: Memory threshold ({self.config.max_ram_threshold_mb} MB) reached. Forcing deep GC sweep...[/bold red]")
                    gc.collect()

                # Batch completed - Save Checkpoint
                self.storage.save_checkpoint({
                    "run_id": self.config.run_id,
                    "last_completed_batch": b_idx,
                    "total_batches": total_batches,
                    "processed_count": completed_count + skipped_count + failed_count,
                    "successful_count": completed_count,
                    "skipped_count": skipped_count,
                    "failed_count": failed_count,
                    "total_pages": total_pages_processed,
                    "timestamp": time.time()
                })

        # 2-Pass Retry Protocol for Failed PDFs
        final_failed_keys = []
        if failed_keys:
            self.console.print(f"\n[bold yellow]Initiating Retry Pass for {len(failed_keys)} failed documents...[/bold yellow]")
            for key in failed_keys:
                retry_success = False
                for attempt in range(1, self.config.retry_limit + 1):
                    metrics, _ = self.processor.process_single_pdf(key)
                    if metrics.status == "success":
                        completed_count += 1
                        failed_count -= 1
                        total_pages_processed += metrics.pages
                        retry_success = True
                        break
                    elif metrics.status == "skipped":
                        skipped_count += 1
                        failed_count -= 1
                        retry_success = True
                        break
                if not retry_success:
                    final_failed_keys.append(key)

        # Output final failed CSV if any remain
        if final_failed_keys:
            failed_csv_path = os.path.join(self.config.base_output_dir, "failed_final.csv")
            with open(failed_csv_path, "w") as f:
                f.write("s3_key\n")
                for fk in final_failed_keys:
                    f.write(f"{fk}\n")
            self.console.print(f"[bold red]Final unresolved failures logged to: {failed_csv_path}[/bold red]")

        total_duration = time.time() - start_pipeline_time
        processed_total = completed_count + skipped_count
        run_summary = {
            "run_id": self.config.run_id,
            "total_pdfs": total_pdfs,
            "total_pages": total_pages_processed,
            "newly_processed": completed_count,
            "skipped_existing": skipped_count,
            "failed": len(final_failed_keys),
            "total_duration_sec": round(total_duration, 2),
            "throughput_pages_per_sec": round(total_pages_processed / max(0.001, total_duration), 2),
            "throughput_pdfs_per_sec": round(processed_total / max(0.001, total_duration), 2),
            "peak_ram_mb": self.monitor.get_snapshot()["ram_peak_mb"]
        }

        # Export Benchmark Run Summary JSON
        summary_path = os.path.join(self.config.benchmarks_dir, f"summary_{self.config.run_id}.json")
        with open(summary_path, "w", encoding="utf-8") as f:
            json.dump(run_summary, f, indent=2)

        return run_summary

    def _generate_dashboard(self, batch_num: int, total_batches: int, completed: int, skipped: int, 
                            total: int, total_pages: int, running: int, failed: int, 
                            pdf_throughput: float, pages_throughput: float, eta_sec: float,
                            acc_download_ms: float = 0, acc_entity_ms: float = 0, acc_total_ms: float = 0) -> Panel:
        res = self.monitor.get_snapshot()
        processed_count = max(1, completed + skipped + failed)
        
        avg_download = acc_download_ms / processed_count
        avg_entity = acc_entity_ms / processed_count
        avg_total = acc_total_ms / processed_count
        
        # Bottleneck calculation
        download_pct = (avg_download / max(0.001, avg_total)) * 100
        if download_pct > 50:
            bottleneck_str = f"[bold red]S3 Network Download I/O ({download_pct:.1f}% share)[/bold red]"
        else:
            bottleneck_str = f"[bold yellow]CPU Processing / Entity Extraction ({100-download_pct:.1f}% share)[/bold yellow]"
        
        table = Table(show_header=False, box=None)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="bold white")
        
        table.add_row("Run ID", self.config.run_id)
        table.add_row("Batch Progress", f"{batch_num} / {total_batches}")
        table.add_row("Total PDFs Target", f"{total}")
        table.add_row("Newly Processed PDFs", f"{completed}")
        table.add_row("Skipped (Existing)", f"[yellow]{skipped}[/yellow]")
        table.add_row("Failed PDFs", f"[red]{failed}[/red]" if failed > 0 else f"{failed}")
        table.add_row("Total Pages Processed", f"[bold green]{total_pages:,}[/bold green] pages")
        
        # Primary Throughput in Pages / Sec
        table.add_row("Pages Throughput Rate", f"[bold magenta]{pages_throughput:.2f} pages/sec[/bold magenta] ({pages_throughput * 60:.1f} pages/min)")
        table.add_row("Document Throughput Rate", f"{pdf_throughput:.2f} PDFs/sec ({pdf_throughput * 60:.1f} PDFs/min)")
        
        # Bottleneck & Latency Tracking
        table.add_row("Active Bottleneck", bottleneck_str)
        table.add_row("Avg S3 Download Latency", f"{avg_download:.1f} ms / PDF")
        table.add_row("Avg Entity Extract Latency", f"{avg_entity:.1f} ms / PDF")
        table.add_row("Avg Total Document Latency", f"{avg_total:.1f} ms / PDF")
        
        # Resource & Memory Tracking
        table.add_row("Estimated Remaining Time", f"{int(eta_sec // 60)}m {int(eta_sec % 60)}s")
        table.add_row("CPU Usage", f"{res['cpu_percent']}%")
        table.add_row("RAM Used (Current RSS)", f"{res['ram_used_mb']} MB")
        table.add_row("RAM Peak RSS", f"{res['ram_peak_mb']} MB")
        table.add_row("RAM Safety Ceiling", f"{self.config.max_ram_threshold_mb} MB")
        table.add_row("System Memory Available", f"{res['system_ram_available_mb']} MB")
        
        return Panel(table, title=f"[bold green]Live Pipeline Execution & Bottleneck Dashboard[/bold green]", expand=False)


