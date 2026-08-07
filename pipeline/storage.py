import os
import json
from typing import Dict, Any
from config import PipelineConfig
from pipeline.tracker import DocumentMetrics

class StorageManager:
    """
    Thread-safe persistent storage manager for intermediate pipeline outputs.
    Ensures outputs are saved cleanly without overwriting prior pipeline steps.
    """
    
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.config.ensure_directories()
        
    def get_pdf_path(self, doc_id: str) -> str:
        safe_id = self._safe_filename(doc_id)
        return os.path.join(self.config.pdf_dir, f"{safe_id}.pdf")

    def save_raw_text(self, doc_id: str, text: str) -> str:
        safe_id = self._safe_filename(doc_id)
        path = os.path.join(self.config.raw_text_dir, f"{safe_id}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def save_clean_text(self, doc_id: str, text: str) -> str:
        safe_id = self._safe_filename(doc_id)
        path = os.path.join(self.config.clean_text_dir, f"{safe_id}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
        return path

    def save_metadata(self, doc_id: str, metadata: Dict[str, Any]) -> str:
        safe_id = self._safe_filename(doc_id)
        path = os.path.join(self.config.metadata_dir, f"{safe_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        return path

    def save_entities(self, doc_id: str, entities: Dict[str, Any]) -> str:
        safe_id = self._safe_filename(doc_id)
        path = os.path.join(self.config.entities_dir, f"{safe_id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(entities, f, indent=2, ensure_ascii=False)
        return path

    def log_jsonl_event(self, event_data: Dict[str, Any]):
        """Appends an event object to the JSONL log file."""
        log_path = os.path.join(self.config.logs_dir, f"events_{self.config.run_id}.jsonl")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(event_data, ensure_ascii=False) + "\n")

    def save_document_metrics(self, metrics: DocumentMetrics):
        """Appends document metrics to the main structured metrics log."""
        metrics_path = os.path.join(self.config.benchmarks_dir, f"metrics_{self.config.run_id}.jsonl")
        with open(metrics_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(metrics.to_dict(), ensure_ascii=False) + "\n")

    def save_checkpoint(self, checkpoint_data: Dict[str, Any]):
        """Atomic write of pipeline progress checkpoint."""
        ckpt_path = os.path.join(self.config.checkpoints_dir, "checkpoint.json")
        tmp_path = ckpt_path + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(checkpoint_data, f, indent=2)
        os.replace(tmp_path, ckpt_path)

    def load_checkpoint(self) -> Dict[str, Any]:
        """Loads execution checkpoint if present."""
        ckpt_path = os.path.join(self.config.checkpoints_dir, "checkpoint.json")
        if os.path.exists(ckpt_path):
            try:
                with open(ckpt_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def is_document_processed(self, doc_id: str) -> bool:
        """
        Checks whether a document has already been successfully processed
        by checking for valid presence of output entity and clean text files.
        """
        safe_id = self._safe_filename(doc_id)
        ent_path = os.path.join(self.config.entities_dir, f"{safe_id}.json")
        clean_path = os.path.join(self.config.clean_text_dir, f"{safe_id}.txt")
        return (
            os.path.exists(ent_path) and os.path.getsize(ent_path) > 10 and
            os.path.exists(clean_path) and os.path.getsize(clean_path) > 10
        )

    def get_completed_doc_ids(self) -> set:
        """Returns a set of doc_ids that have completed processing."""
        if not os.path.exists(self.config.entities_dir):
            return set()
        completed = set()
        for f in os.listdir(self.config.entities_dir):
            if f.endswith(".json"):
                doc_id = f[:-5]
                clean_path = os.path.join(self.config.clean_text_dir, f"{doc_id}.txt")
                if os.path.exists(clean_path) and os.path.getsize(clean_path) > 10:
                    completed.add(doc_id)
        return completed

    def delete_pdf(self, doc_id: str) -> bool:
        """Deletes raw PDF from disk after text extraction if configured."""
        pdf_path = self.get_pdf_path(doc_id)
        if os.path.exists(pdf_path):
            try:
                os.remove(pdf_path)
                return True
            except OSError:
                pass
        return False

    def export_to_parquet(self) -> Dict[str, Any]:
        """Converts output directory into metadata.parquet, entities.parquet, and documents_text.parquet."""
        from pipeline.parquet_exporter import ParquetExporter
        exporter = ParquetExporter(self.config.base_output_dir)
        return exporter.export_all()

    @staticmethod
    def _safe_filename(doc_id: str) -> str:
        """Sanitizes doc_id for filesystem use."""
        return doc_id.replace("/", "_").replace("\\", "_").replace(" ", "_").replace("=", "_")


