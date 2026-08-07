import time
import os
from typing import Dict, Any, Tuple

from config import PipelineConfig
from pipeline.downloader import PDFDownloader
from pipeline.extractors.searchable import PyMuPDFTextExtractor
from pipeline.cleaner import TextCleaner
from pipeline.metadata import MetadataExtractor
from pipeline.entities import EntityExtractor
from pipeline.storage import StorageManager
from pipeline.tracker import DocumentMetrics, StageTimer, MachineResourceMonitor

class DocumentProcessor:
    """
    Independent worker that processes exactly one PDF end-to-end through all pipeline stages:
    Download -> Validate -> Extract Text -> Clean Text -> Metadata -> Entity -> Persist -> Benchmark.
    """
    
    def __init__(self, config: PipelineConfig, storage: StorageManager, downloader: Optional[PDFDownloader] = None):
        self.config = config
        self.storage = storage
        self.downloader = downloader if downloader else PDFDownloader(s3_base_url=config.s3_base_url, pool_maxsize=config.max_workers * 2)
        self.text_extractor = PyMuPDFTextExtractor()  # Phase 1 Searchable Extractor
        self.cleaner = TextCleaner()
        self.metadata_extractor = MetadataExtractor()
        self.entity_extractor = EntityExtractor()


    def process_single_pdf(self, s3_key: str, doc_id: str = "") -> Tuple[DocumentMetrics, Dict[str, Any]]:
        if not doc_id:
            doc_id = os.path.basename(s3_key).replace(".pdf", "")
            
        metrics = DocumentMetrics(document_id=doc_id)
        start_total = time.perf_counter()
        output_artifacts = {}

        # Resumability Check: Skip if already processed and resume enabled
        if self.config.resume_enabled and self.storage.is_document_processed(doc_id):
            metrics.status = "skipped"
            metrics.total_ms = (time.perf_counter() - start_total) * 1000.0
            return metrics, output_artifacts

        try:
            # Stage 1: Download
            t0 = time.perf_counter()
            dest_pdf_path = self.storage.get_pdf_path(doc_id)
            success, msg = self.downloader.download_pdf(s3_key, dest_pdf_path)
            metrics.download_ms = (time.perf_counter() - t0) * 1000.0
            
            if not success:
                metrics.status = "download_failed"
                metrics.error_message = msg
                return metrics, output_artifacts

            # Stage 2: Validate
            t0 = time.perf_counter()
            val_ok, val_msg = self.downloader.validate_pdf(dest_pdf_path)
            metrics.validation_ms = (time.perf_counter() - t0) * 1000.0
            
            if not val_ok:
                metrics.status = "validation_failed"
                metrics.error_message = val_msg
                return metrics, output_artifacts

            # Stage 3: Extract Text
            t0 = time.perf_counter()
            ext_res = self.text_extractor.extract_text(dest_pdf_path)
            metrics.extract_ms = (time.perf_counter() - t0) * 1000.0
            metrics.pages = ext_res.page_count
            metrics.word_count = ext_res.word_count
            raw_text_path = self.storage.save_raw_text(doc_id, ext_res.raw_text)
            output_artifacts["raw_text_path"] = raw_text_path

            # Optional PDF Cleanup (Purge PDF file after text extraction)
            if not self.config.keep_pdf_files:
                self.storage.delete_pdf(doc_id)

            # Stage 4: Clean Text
            t0 = time.perf_counter()
            clean_text = self.cleaner.clean_text(ext_res.raw_text)
            metrics.clean_ms = (time.perf_counter() - t0) * 1000.0
            clean_text_path = self.storage.save_clean_text(doc_id, clean_text)
            output_artifacts["clean_text_path"] = clean_text_path

            # Stage 5: Metadata Extraction
            t0 = time.perf_counter()
            meta = self.metadata_extractor.extract_metadata(clean_text, page_count=ext_res.page_count, doc_id=doc_id)
            metrics.metadata_ms = (time.perf_counter() - t0) * 1000.0
            meta_path = self.storage.save_metadata(doc_id, meta)
            output_artifacts["metadata_path"] = meta_path
            output_artifacts["metadata"] = meta

            # Stage 6: Entity Extraction
            t0 = time.perf_counter()
            entities = self.entity_extractor.extract_entities(clean_text, metadata=meta, doc_id=doc_id)
            metrics.entity_ms = (time.perf_counter() - t0) * 1000.0
            entities_path = self.storage.save_entities(doc_id, entities)
            output_artifacts["entities_path"] = entities_path
            output_artifacts["entities"] = entities

            # Stage 7: Persist Metrics & Log Event
            t0 = time.perf_counter()
            metrics.status = "success"
            metrics.total_ms = (time.perf_counter() - start_total) * 1000.0
            metrics.save_ms = (time.perf_counter() - t0) * 1000.0
            
            self.storage.save_document_metrics(metrics)
            self.storage.log_jsonl_event({
                "timestamp": time.time(),
                "document_id": doc_id,
                "stage": "complete",
                "duration_ms": round(metrics.total_ms, 2),
                "status": "success"
            })
            
            return metrics, output_artifacts

        except Exception as e:
            metrics.status = "exception_failed"
            metrics.error_message = str(e)
            metrics.total_ms = (time.perf_counter() - start_total) * 1000.0
            self.storage.save_document_metrics(metrics)
            return metrics, output_artifacts
