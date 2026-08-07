import os
import sys
import json
import argparse
import requests
import xml.etree.ElementTree as ET
from typing import List

from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from config import PipelineConfig
from pipeline.storage import StorageManager
from batch_runner import BatchScheduler

def fetch_s3_keys_backwards(start_year: int = 2025, max_keys: int = 1000, s3_base_url: str = "https://indian-supreme-court-judgments.s3.amazonaws.com") -> List[str]:
    """
    Fetches up to max_keys S3 PDF document keys from AWS Open Data,
    starting from start_year and querying backwards year by year.
    """
    console = Console()
    console.print(f"[bold cyan]Fetching S3 document keys starting from year {start_year} downwards (Target: {max_keys} PDFs)...[/bold cyan]")
    
    keys = []
    current_year = start_year
    ns = {'s3': 'http://s3.amazonaws.com/doc/2006-03-01/'}
    
    base_endpoint = s3_base_url.rstrip("/")
    
    while len(keys) < max_keys and current_year >= 1950:
        prefix = f"data/pdf/year={current_year}/english/"
        continuation_token = None
        year_keys_count = 0
        
        while len(keys) < max_keys:
            url = f"{base_endpoint}/?list-type=2&prefix={prefix}"
            if continuation_token:
                url += f"&continuation-token={continuation_token}"
                
            try:
                resp = requests.get(url, timeout=15)
                if resp.status_code != 200:
                    console.print(f"[bold yellow]Warning: HTTP {resp.status_code} when listing year {current_year}[/bold yellow]")
                    break
                    
                root = ET.fromstring(resp.content)
                batch_keys = [elem.text for elem in root.findall('.//s3:Key', ns) if elem.text and elem.text.endswith('.pdf')]
                
                needed = max_keys - len(keys)
                keys.extend(batch_keys[:needed])
                year_keys_count += len(batch_keys[:needed])
                
                is_truncated = root.find('.//s3:IsTruncated', ns)
                if is_truncated is not None and is_truncated.text == 'true':
                    next_token_elem = root.find('.//s3:NextContinuationToken', ns)
                    if next_token_elem is not None and next_token_elem.text:
                        continuation_token = requests.utils.quote(next_token_elem.text)
                    else:
                        break
                else:
                    break
            except Exception as e:
                console.print(f"[bold red]Error fetching keys for year {current_year}: {e}[/bold red]")
                break
                
        console.print(f"  • Year {current_year}: fetched {year_keys_count} keys (Total accumulated: [bold white]{len(keys)}[/bold white])")
        current_year -= 1
        
    return keys[:max_keys]

def main():
    parser = argparse.ArgumentParser(description="Indian Supreme Court PDF Processing Pipeline Runner")
    parser.add_argument("--limit", type=int, default=1000, help="Total number of PDFs to process (default: 1000)")
    parser.add_argument("--start-year", type=int, default=2025, help="Starting year to fetch judgments (default: 2025)")
    parser.add_argument("--batch-size", type=int, default=10, help="Batch size for parallel processing (default: 10)")
    parser.add_argument("--workers", type=int, default=4, help="Number of ThreadPoolExecutor worker threads (default: 4)")
    parser.add_argument("--output-dir", type=str, default="./output_1000", help="Base output directory (default: ./output_1000)")
    parser.add_argument("--keep-pdfs", action="store_true", help="Keep raw PDF files on disk after extraction (default: False)")
    parser.add_argument("--no-resume", action="store_true", help="Disable skipping already processed documents")
    parser.add_argument("--export-parquet", action="store_true", help="Automatically export outputs to Parquet tables after processing")
    
    args = parser.parse_args()
    
    console = Console()
    console.print(Panel.fit(
        f"[bold blue]Supreme Court PDF Pipeline - Processing Runner[/bold blue]\n"
        f"Target: [yellow]{args.limit} PDFs[/yellow] | Start Year: [yellow]{args.start_year}[/yellow] | "
        f"Workers: [yellow]{args.workers}[/yellow] | Batch Size: [yellow]{args.batch_size}[/yellow] | "
        f"Auto-Parquet: [green]{args.export_parquet}[/green]"
    ))

    # Configure Pipeline
    config = PipelineConfig(
        run_id=f"RUN-{args.start_year}-{args.limit}",
        base_output_dir=args.output_dir,
        batch_size=args.batch_size,
        max_workers=args.workers,
        keep_pdf_files=args.keep_pdfs,
        resume_enabled=not args.no_resume,
        auto_export_parquet=args.export_parquet
    )
    storage = StorageManager(config)

    # Manifest file path
    manifest_path = os.path.join(config.benchmarks_dir, f"manifest_{config.run_id}.json")
    
    # Check if manifest exists or fetch fresh keys
    if os.path.exists(manifest_path) and not args.no_resume:
        console.print(f"[bold green]Loading cached document manifest from: {manifest_path}[/bold green]")
        with open(manifest_path, "r", encoding="utf-8") as f:
            s3_keys = json.load(f)
    else:
        s3_keys = fetch_s3_keys_backwards(start_year=args.start_year, max_keys=args.limit, s3_base_url=config.s3_base_url)
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(s3_keys, f, indent=2)
        console.print(f"[bold green]Saved target document manifest to: {manifest_path}[/bold green]")

    if not s3_keys:
        console.print("[bold red]No S3 document keys found to process. Exiting.[/bold red]")
        sys.exit(1)

    console.print(f"\n[bold yellow]Launching Batch Execution Engine for {len(s3_keys)} Documents...[/bold yellow]")
    scheduler = BatchScheduler(config, storage)
    summary = scheduler.run_batch_pipeline(s3_keys)

    # Auto Parquet Export if requested
    if args.export_parquet:
        console.print("\n[bold cyan]Exporting outputs to Apache Parquet...[/bold cyan]")
        parquet_summary = storage.export_to_parquet()
        summary["parquet_dir"] = parquet_summary["parquet_dir"]

    # Print Final Summary Table
    summary_table = Table(title="[bold green]Final Pipeline Execution Summary[/bold green]")
    summary_table.add_column("Metric", style="cyan")
    summary_table.add_column("Value", style="bold white")
    for k, v in summary.items():
        summary_table.add_row(k, str(v))
    console.print(summary_table)

if __name__ == "__main__":
    main()
