import os
import json
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from config import PipelineConfig
from pipeline.storage import StorageManager
from batch_runner import BatchScheduler

def main():
    console = Console()
    console.print(Panel.fit("[bold blue]Supreme Court PDF Pipeline - Batch Processing Execution & Resumability Test[/bold blue]"))

    config = PipelineConfig(
        run_id="TEST-BATCH-SCALE-001",
        base_output_dir="./output_batch_test",
        batch_size=2,
        max_workers=2,
        keep_pdf_files=False,
        resume_enabled=True
    )
    storage = StorageManager(config)

    sample_s3_keys = [
        "data/pdf/year=1950/english/1950_1_1008_1018_EN.pdf",
        "data/pdf/year=1950/english/1950_1_15_25_EN.pdf",
        "data/pdf/year=1950/english/1950_1_25_29_EN.pdf",
        "data/pdf/year=1950/english/1950_1_30_63_EN.pdf",
        "data/pdf/year=1950/english/1950_1_335_390_EN.pdf"
    ]

    console.print(f"\n[bold yellow]Pass 1: Executing Batch Processing Run with {len(sample_s3_keys)} Documents...[/bold yellow]")
    scheduler = BatchScheduler(config, storage)
    results_pass1 = scheduler.run_batch_pipeline(sample_s3_keys)

    table1 = Table(title="[bold green]Pass 1 Summary (Fresh Processing)[/bold green]")
    table1.add_column("Metric", style="cyan")
    table1.add_column("Value", style="bold white")
    for k, v in results_pass1.items():
        table1.add_row(k, str(v))
    console.print(table1)

    console.print(f"\n[bold yellow]Pass 2: Re-executing Batch Run (Testing Resumability & Document Skipping)...[/bold yellow]")
    results_pass2 = scheduler.run_batch_pipeline(sample_s3_keys)

    table2 = Table(title="[bold green]Pass 2 Summary (Resume / Skip Existing)[/bold green]")
    table2.add_column("Metric", style="cyan")
    table2.add_column("Value", style="bold white")
    for k, v in results_pass2.items():
        table2.add_row(k, str(v))
    console.print(table2)

    # Check generated entity files count & details
    entities_dir = config.entities_dir
    if os.path.exists(entities_dir):
        entity_files = [f for f in os.listdir(entities_dir) if f.endswith('.json')]
        console.print(f"\n[bold green]Generated Entity JSON Files ({len(entity_files)}):[/bold green]")

        ent_summary_table = Table(title="[bold yellow]Extracted Entities per Document[/bold yellow]")
        ent_summary_table.add_column("Document ID", style="cyan")
        ent_summary_table.add_column("Entities Count", style="bold magenta", justify="right")
        ent_summary_table.add_column("Case Title / Citation", style="white")

        for f in sorted(entity_files)[:5]:
            filepath = os.path.join(entities_dir, f)
            with open(filepath, 'r') as fp:
                data = json.load(fp)
                ent_summary_table.add_row(
                    data.get("case_id", f),
                    str(data.get("entities_count", 0)),
                    f"{data.get('title', '')[:40]} | {data.get('citation', '')}"
                )
        console.print(ent_summary_table)

if __name__ == "__main__":
    main()

