import time
import psutil
from dataclasses import dataclass, field
from typing import Dict, Any

@dataclass
class DocumentMetrics:
    document_id: str
    status: str = "pending"
    download_ms: float = 0.0
    validation_ms: float = 0.0
    extract_ms: float = 0.0
    clean_ms: float = 0.0
    metadata_ms: float = 0.0
    entity_ms: float = 0.0
    save_ms: float = 0.0
    database_ms: float = 0.0
    total_ms: float = 0.0
    pages: int = 0
    word_count: int = 0
    error_message: str = ""
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "document_id": self.document_id,
            "status": self.status,
            "download_ms": round(self.download_ms, 2),
            "validation_ms": round(self.validation_ms, 2),
            "extract_ms": round(self.extract_ms, 2),
            "clean_ms": round(self.clean_ms, 2),
            "metadata_ms": round(self.metadata_ms, 2),
            "entity_ms": round(self.entity_ms, 2),
            "save_ms": round(self.save_ms, 2),
            "database_ms": round(self.database_ms, 2),
            "total_ms": round(self.total_ms, 2),
            "pages": self.pages,
            "word_count": self.word_count,
            "error_message": self.error_message,
            "timestamp": self.timestamp
        }

class StageTimer:
    def __init__(self):
        self.start_time = 0.0

    def __enter__(self):
        self.start_time = time.perf_counter()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    @property
    def elapsed_ms(self) -> float:
        return (time.perf_counter() - self.start_time) * 1000.0

class MachineResourceMonitor:
    def __init__(self):
        self.process = psutil.Process()
        self.peak_rss_mb = 0.0
        
    def get_snapshot(self) -> Dict[str, Any]:
        mem_info = self.process.memory_info()
        disk_io = psutil.disk_io_counters()
        ram_used_mb = round(mem_info.rss / (1024 * 1024), 2)
        if ram_used_mb > self.peak_rss_mb:
            self.peak_rss_mb = ram_used_mb
        
        return {
            "cpu_percent": psutil.cpu_percent(interval=None),
            "ram_used_mb": ram_used_mb,
            "ram_peak_mb": round(self.peak_rss_mb, 2),
            "system_ram_available_mb": round(psutil.virtual_memory().available / (1024 * 1024), 2),
            "disk_read_bytes": disk_io.read_bytes if disk_io else 0,
            "disk_write_bytes": disk_io.write_bytes if disk_io else 0,
        }

    def is_memory_exceeded(self, limit_mb: float = 4096.0) -> bool:
        """Returns True if current process RSS exceeds the threshold."""
        current_mb = self.process.memory_info().rss / (1024 * 1024)
        return current_mb > limit_mb

