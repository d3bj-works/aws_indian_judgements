import os
import sys
import time
import json
import argparse
import shutil
from rich.console import Console
from rich.panel import Panel

from config import PipelineConfig
from pipeline.storage import StorageManager
from batch_runner import BatchScheduler
from pipeline.parquet_exporter import ParquetExporter

def main():
    parser = argparse.ArgumentParser(description="Google Colab Ingestion Runner for AWS Indian Judgments Pipeline")
    parser.add_argument("--drive-dir", type=str, required=True, help="Google Drive persistent output directory (e.g. /content/drive/MyDrive/aws_indian_judgements)")
    parser.add_argument("--scratch-dir", type=str, default="/tmp/colab_scratch", help="Local VM scratch directory (default: /tmp/colab_scratch)")
    parser.add_argument("--s3-keys-file", type=str, default=None, help="Path to text or JSON file containing S3 keys to process")
    parser.add_argument("--limit", type=int, default=1000, help="Maximum number of PDFs to process in this run (default: 1000)")
    parser.add_argument("--batch-size", type=int, default=50, help="Batch size per execution sweep (default: 50)")
    parser.add_argument("--max-workers", type=int, default=16, help="Thread worker count for high concurrency (default: 16)")
    parser.add_argument("--run-id", type=str, default="colab-hc-001", help="Execution run identifier")
    parser.add_argument("--keep-artifacts", action="store_true", help="Set flag to keep individual TXT/JSON files in scratch instead of purging")

    args = parser.parse_args()
    console = Console()

    # Ensure directories
    os.makedirs(args.drive_dir, exist_ok=True)
    os.makedirs(args.scratch_dir, exist_ok=True)

    console.print(Panel.fit(
        f"[bold green]Google Colab Ingestion & Optimization Runner[/bold green]\n"
        f"Drive Persistent Dir: [yellow]{args.drive_dir}[/yellow]\n"
        f"Local Scratch Dir: [yellow]{args.scratch_dir}[/yellow]\n"
        f"Workers: [yellow]{args.max_workers}[/yellow] | Batch Size: [yellow]{args.batch_size}[/yellow] | Limit: [yellow]{args.limit}[/yellow]"
    ))

    # Construct S3 keys list
    s3_keys = []
    if args.s3_keys_file and os.path.exists(args.s3_keys_file):
        with open(args.s3_keys_file, "r") as f:
            if args.s3_keys_file.endswith(".json"):
                s3_keys = json.load(f)
            else:
                s3_keys = [line.strip() for line in f if line.strip()]
    else:
        # Fallback to sample key JSONs or live S3 bucket listing
        for kfile in ["./data/hc_keys_sample.json", "./data/sc_keys_sample.json"]:
            if os.path.exists(kfile):
                with open(kfile, "r") as f:
                    s3_keys = json.load(f)
                break
        
        if not s3_keys:
            console.print("[yellow]Fetching real S3 keys from AWS Open Data endpoint...[/yellow]")
            import requests, xml.etree.ElementTree as ET
            try:
                r = requests.get("https://indian-supreme-court-judgments.s3.amazonaws.com/?max-keys=1000", timeout=10)
                root = ET.fromstring(r.text)
                ns = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}
                s3_keys = [elem.find("s3:Key", ns).text for elem in root.findall("s3:Contents", ns) if elem.find("s3:Key", ns).text.endswith(".pdf")]
            except Exception as e:
                console.print(f"[bold red]Failed to list bucket keys: {e}[/bold red]")

    # Initialize Pipeline Storage & Checkpoint to filter out already processed document IDs
    config = PipelineConfig(
        run_id=args.run_id,
        base_output_dir=args.scratch_dir,
        drive_output_dir=args.drive_dir,
        local_scratch_dir=args.scratch_dir,
        batch_size=args.batch_size,
        max_workers=args.max_workers,
        keep_pdf_files=False,
        keep_intermediate_artifacts=args.keep_artifacts,
        resume_enabled=True
    )
    storage = StorageManager(config)

    # Deduplication & Resume Check: Exclude documents already processed in prior runs
    ckpt = storage.load_checkpoint()
    completed_doc_ids = set(ckpt.get("completed_doc_ids", []))
    if not completed_doc_ids:
        completed_doc_ids = storage.get_completed_doc_ids()

    from pipeline.cleaner import TextCleaner

    unprocessed_keys = []
    for k in s3_keys:
        doc_id = os.path.basename(k).replace(".pdf", "")
        if TextCleaner.is_english_key(k) and doc_id not in completed_doc_ids and not storage.is_document_processed(doc_id):
            unprocessed_keys.append(k)

    console.print(f"[bold cyan]Found {len(s3_keys):,} total keys | {len(completed_doc_ids):,} already completed | {len(unprocessed_keys):,} English unprocessed keys remaining.[/bold cyan]")


    # Default to 1000 unprocessed PDFs target (unless overridden by --limit)
    s3_keys = unprocessed_keys[:args.limit]

    scheduler = BatchScheduler(config, storage)


    console.print(f"[bold cyan]Launching pipeline execution over {len(s3_keys):,} documents...[/bold cyan]")
    start_time = time.time()
    
    summary = scheduler.run_batch_pipeline(s3_keys)
    
    elapsed = time.time() - start_time
    console.print(f"\n[bold green]Batch processing finished in {elapsed:.2f}s![/bold green]")
    console.print(f"Overall Throughput: [bold magenta]{summary['throughput_pdfs_per_sec']:.2f} PDFs/sec[/bold magenta] ({summary['throughput_pages_per_sec']:.2f} pages/sec)")

    # Automatic Parquet Consolidation to Drive if intermediate artifacts exist in scratch
    if args.keep_artifacts and os.path.exists(config.entities_dir):
        console.print("[bold cyan]Compiling Parquet files to Google Drive...[/bold cyan]")
        exporter = ParquetExporter(output_dir=args.scratch_dir)
        parquet_res = exporter.export_all(batch_chunk_size=1000)
        
        # Copy compiled Parquet files to Drive Parquet folder
        os.makedirs(config.parquet_dir, exist_ok=True)
        for pfile in ["metadata.parquet", "entities.parquet", "documents_text.parquet"]:
            src = os.path.join(exporter.parquet_dir, pfile)
            dst = os.path.join(config.parquet_dir, pfile)
            if os.path.exists(src):
                shutil.copy2(src, dst)
                console.print(f"  • Synced to Google Drive: [bold green]{dst}[/bold green]")

    console.print(Panel.fit(
        f"[bold green]Google Colab Ingestion Completed Successfully![/bold green]\n"
        f"Parquet & Checkpoint Directory on Drive: [yellow]{config.parquet_dir}[/yellow]"
    ))

if __name__ == "__main__":
    main()
