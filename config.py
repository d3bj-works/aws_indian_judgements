import os
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class PipelineConfig:
    run_id: str = "20260807-001"
    base_output_dir: str = "./output"
    drive_output_dir: Optional[str] = None  # Google Drive persistent output path (for Parquet & Checkpoint)
    local_scratch_dir: Optional[str] = None  # Local NVMe/SSD scratch directory for Colab
    batch_size: int = 50
    max_workers: int = 16
    retry_limit: int = 3
    benchmark_pdf_limit: int = 1000
    s3_base_url: str = "https://indian-supreme-court-judgments.s3.amazonaws.com"
    resume_enabled: bool = True
    keep_pdf_files: bool = False  # Purge raw PDF after extraction to optimize disk & RAM
    keep_intermediate_artifacts: bool = True  # Set False in Colab to avoid writing thousands of small TXT/JSON files
    max_ram_threshold_mb: int = 8192  # Target maximum process RAM safety limit
    
    # Subdirectories
    pdf_dir: str = field(init=False)
    raw_text_dir: str = field(init=False)
    clean_text_dir: str = field(init=False)
    metadata_dir: str = field(init=False)
    entities_dir: str = field(init=False)
    logs_dir: str = field(init=False)
    benchmarks_dir: str = field(init=False)
    checkpoints_dir: str = field(init=False)
    parquet_dir: str = field(init=False)
    auto_export_parquet: bool = False

    def __post_init__(self):
        # Staging directory for intermediate files (uses local scratch if provided)
        staging_dir = self.local_scratch_dir if self.local_scratch_dir else self.base_output_dir
        # Drive output directory for persistent outputs (Parquet, checkpoints, logs)
        persistent_dir = self.drive_output_dir if self.drive_output_dir else self.base_output_dir

        self.pdf_dir = os.path.join(staging_dir, "pdf")
        self.raw_text_dir = os.path.join(staging_dir, "raw_text")
        self.clean_text_dir = os.path.join(staging_dir, "clean_text")
        self.metadata_dir = os.path.join(staging_dir, "metadata")
        self.entities_dir = os.path.join(staging_dir, "entities")
        
        self.logs_dir = os.path.join(persistent_dir, "logs")
        self.benchmarks_dir = os.path.join(persistent_dir, "benchmarks")
        self.checkpoints_dir = os.path.join(persistent_dir, "checkpoints")
        self.parquet_dir = os.path.join(persistent_dir, "parquet")


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
            self.parquet_dir,
        ]:
            os.makedirs(d, exist_ok=True)
