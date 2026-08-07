import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class PipelineConfig:
    run_id: str = "20260807-001"
    base_output_dir: str = "./output"
    batch_size: int = 5
    max_workers: int = 4
    retry_limit: int = 3
    benchmark_pdf_limit: int = 1000
    s3_base_url: str = "https://indian-supreme-court-judgments.s3.amazonaws.com"
    resume_enabled: bool = True
    keep_pdf_files: bool = False  # Purge raw PDF after extraction to optimize disk & RAM
    max_ram_threshold_mb: int = 4096  # Target maximum process RAM safety limit
    
    # Subdirectories
    pdf_dir: str = field(init=False)
    raw_text_dir: str = field(init=False)
    clean_text_dir: str = field(init=False)
    metadata_dir: str = field(init=False)
    entities_dir: str = field(init=False)
    logs_dir: str = field(init=False)
    benchmarks_dir: str = field(init=False)
    checkpoints_dir: str = field(init=False)

    def __post_init__(self):
        self.pdf_dir = os.path.join(self.base_output_dir, "pdf")
        self.raw_text_dir = os.path.join(self.base_output_dir, "raw_text")
        self.clean_text_dir = os.path.join(self.base_output_dir, "clean_text")
        self.metadata_dir = os.path.join(self.base_output_dir, "metadata")
        self.entities_dir = os.path.join(self.base_output_dir, "entities")
        self.logs_dir = os.path.join(self.base_output_dir, "logs")
        self.benchmarks_dir = os.path.join(self.base_output_dir, "benchmarks")
        self.checkpoints_dir = os.path.join(self.base_output_dir, "checkpoints")

    def ensure_directories(self):
        """Creates all intermediate storage directories if they do not exist."""
        for d in [
            self.pdf_dir,
            self.raw_text_dir,
            self.clean_text_dir,
            self.metadata_dir,
            self.entities_dir,
            self.logs_dir,
            self.benchmarks_dir,
            self.checkpoints_dir,
        ]:
            os.makedirs(d, exist_ok=True)
