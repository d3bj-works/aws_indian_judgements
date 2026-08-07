import os
import sys
import time
import argparse
import logging
from rich.logging import RichHandler
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from pipeline.parquet_exporter import ParquetExporter

def setup_logging(verbose: bool = False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(rich_tracebacks=True, show_path=False)]
    )

def get_directory_size(path: str) -> int:
    """Calculates total size in bytes of a directory."""
    total_bytes = 0
    if not os.path.exists(path):
        return 0
    for root, _, files in os.walk(path):
        for f in files:
            try:
                total_bytes += os.path.getsize(os.path.join(root, f))
            except OSError:
                pass
    return total_bytes

def format_bytes(bytes_val: int) -> str:
    """Formats raw bytes into human-readable representation."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if abs(bytes_val) < 1024.0:
            return f"{bytes_val:3.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} PB"

def main():
    parser = argparse.ArgumentParser(description="Export Pre-existing Supreme Court Judgments Output to Apache Parquet")
    parser.add_argument("--input-dir", type=str, default="./output_1000", help="Directory containing pre-existing metadata, entities, raw_text, clean_text (default: ./output_1000)")
    parser.add_argument("--compression", type=str, default="zstd", choices=["zstd", "snappy", "gzip"], help="Parquet compression algorithm (default: zstd)")
    parser.add_argument("--batch-chunk-size", type=int, default=5000, help="Number of files to process per in-memory Arrow batch (default: 5000)")
    parser.add_argument("--verbose", "-v", action="store_true", help="Enable verbose debug logging")
    
    args = parser.parse_args()
    setup_logging(args.verbose)
    console = Console()

    input_dir = os.path.abspath(args.input_dir)
    if not os.path.exists(input_dir):
        console.print(f"[bold red]Error: Input directory '{input_dir}' does not exist![/bold red]")
        sys.exit(1)

    console.print(Panel.fit(
        f"[bold blue]Pre-existing Dataset Parquet Compiler[/bold blue]\n"
        f"Target Directory: [yellow]{input_dir}[/yellow]\n"
        f"Compression: [yellow]{args.compression.upper()}[/yellow] | Batch Chunk Size: [yellow]{args.batch_chunk_size}[/yellow]"
    ))

    start_time = time.time()
    
    # Calculate original folder size
    console.print("[bold cyan]Calculating original dataset size...[/bold cyan]")
    orig_size_bytes = get_directory_size(input_dir)
    console.print(f"Original directory size: [bold white]{format_bytes(orig_size_bytes)}[/bold white]")

    # Run Parquet Exporter
    exporter = ParquetExporter(output_dir=input_dir, compression=args.compression)
    res = exporter.export_all(batch_chunk_size=args.batch_chunk_size)
    
    duration = time.time() - start_time
    
    parquet_dir = res["parquet_dir"]
    parquet_size_bytes = get_directory_size(parquet_dir)
    
    reduction_pct = ((orig_size_bytes - parquet_size_bytes) / max(1, orig_size_bytes)) * 100.0

    # Summary Table
    table = Table(title="[bold green]Parquet Export & Compression Summary[/bold green]")
    table.add_column("Output File", style="cyan")
    table.add_column("Record Count", style="bold white")
    table.add_column("Parquet Size", style="bold green")

    meta_info = res["metadata"]
    ent_info = res["entities"]
    text_info = res["documents_text"]

    table.add_row("metadata.parquet", f"{meta_info['count']:,} documents", format_bytes(meta_info['size_bytes']))
    table.add_row("entities.parquet", f"{ent_info['count']:,} entities", format_bytes(ent_info['size_bytes']))
    table.add_row("documents_text.parquet", f"{text_info['count']:,} document texts", format_bytes(text_info['size_bytes']))

    console.print(table)

    summary_panel = Panel.fit(
        f"[bold green]Parquet Compilation Completed Successfully![/bold green]\n"
        f"Output Path: [yellow]{parquet_dir}[/yellow]\n"
        f"Original Size: [yellow]{format_bytes(orig_size_bytes)}[/yellow] ➔ Parquet Size: [bold green]{format_bytes(parquet_size_bytes)}[/bold green]\n"
        f"Total Footprint Reduction: [bold magenta]{reduction_pct:.2f}%[/bold magenta]\n"
        f"Time Elapsed: [yellow]{duration:.2f} seconds[/yellow]"
    )
    console.print(summary_panel)

if __name__ == "__main__":
    main()
