import os
import json
import sys
from collections import Counter
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax

from config import PipelineConfig
from pipeline.storage import StorageManager
from orchestrator import DocumentProcessor
from pipeline.tracker import MachineResourceMonitor

def main():
    console = Console()
    console.print(Panel.fit("[bold blue]Supreme Court PDF Pipeline - Single PDF Execution Test (Verbose Logging)[/bold blue]"))
    
    # 1. Setup Config & Storage
    config = PipelineConfig(run_id="TEST-SINGLE-001", base_output_dir="./output_test")
    storage = StorageManager(config)
    
    # 2. Pick sample S3 PDF Key
    s3_key = "data/pdf/year=1950/english/1950_1_1008_1018_EN.pdf"
    doc_id = "1950_1_1008_1018_EN"
    
    console.print(f"[bold yellow]Processing Target S3 PDF Key:[/bold yellow] [cyan]{s3_key}[/cyan]")
    console.print(f"[bold yellow]Document ID:[/bold yellow] [cyan]{doc_id}[/cyan]")
    
    # 3. Monitor initial resources
    monitor = MachineResourceMonitor()
    initial_res = monitor.get_snapshot()
    
    # 4. Execute Pipeline
    console.print("\n[bold green]>>> Starting Stage-by-Stage Processing...[/bold green]")
    processor = DocumentProcessor(config, storage)
    metrics, artifacts = processor.process_single_pdf(s3_key, doc_id=doc_id)
    final_res = monitor.get_snapshot()
    
    # 5. Display Timings & Metrics Table
    table = Table(title="[bold green]Pipeline Stage Execution Benchmarks[/bold green]")
    table.add_column("Pipeline Stage", style="cyan")
    table.add_column("Time (ms)", style="magenta", justify="right")
    table.add_column("Status / Notes", style="green")
    
    table.add_row("1. Download PDF", f"{metrics.download_ms:.2f}", "HTTP 200 OK")
    table.add_row("2. Validate PDF Header", f"{metrics.validation_ms:.2f}", "%PDF magic header OK")
    table.add_row("3. Extract Text (PyMuPDF)", f"{metrics.extract_ms:.2f}", f"{metrics.pages} pages, {metrics.word_count} words")
    table.add_row("4. Clean Text (NFKC & Ligatures)", f"{metrics.clean_ms:.2f}", "Normalized & Noise Stripped")
    table.add_row("5. Extract Metadata", f"{metrics.metadata_ms:.2f}", "Case Title, Court, Bench, Date")
    table.add_row("6. Extract Legal Entities (Entity_Extraction.md)", f"{metrics.entity_ms:.2f}", f"Extracted {artifacts.get('entities', {}).get('entities_count', 0)} entities")
    table.add_row("7. Persist Outputs", f"{metrics.save_ms:.2f}", "Saved to structured output folders")
    table.add_row("[bold]TOTAL PIPELINE TIME[/bold]", f"[bold]{metrics.total_ms:.2f}[/bold]", f"[bold]{metrics.status.upper()}[/bold]")
    
    console.print(table)
    
    # 6. Display Extracted Metadata
    if "metadata" in artifacts:
        meta_json = json.dumps(artifacts["metadata"], indent=2, ensure_ascii=False)
        console.print(Panel(Syntax(meta_json, "json", theme="monokai", line_numbers=True), title="[bold]Extracted Metadata[/bold]"))

    # 7. Display Extracted Legal Entities (Breakdown & Schema Validation)
    if "entities" in artifacts:
        entities_payload = artifacts["entities"]
        entities_list = entities_payload.get("entities", [])
        
        # Breakdown Table by Type
        type_counts = Counter([e.get("type") for e in entities_list])
        breakdown_table = Table(title="[bold yellow]Extracted Entity Categorization Breakdown[/bold yellow]")
        breakdown_table.add_column("Entity Type", style="cyan")
        breakdown_table.add_column("Count", style="bold magenta", justify="right")
        breakdown_table.add_column("Sample Entities Extracted", style="white")

        for ent_type, count in type_counts.items():
            samples = [e.get("canonical") or e.get("matched") for e in entities_list if e.get("type") == ent_type][:3]
            sample_str = ", ".join(f"'{s}'" for s in samples if s)
            breakdown_table.add_row(ent_type, str(count), sample_str)

        console.print(breakdown_table)

        # Full Payload Syntax Display
        ent_json = json.dumps(entities_payload, indent=2, ensure_ascii=False)
        console.print(Panel(Syntax(ent_json, "json", theme="monokai", line_numbers=True), title="[bold]Benchmark Payload (Entity_Extraction.md Schema)[/bold]"))

    # 8. Display Resource Usage
    res_table = Table(title="[bold yellow]System Resource Usage During Test[/bold yellow]")
    res_table.add_column("Metric", style="cyan")
    res_table.add_column("Value", style="bold white")
    res_table.add_row("CPU Percent", f"{final_res['cpu_percent']}%")
    res_table.add_row("RAM Used (Process)", f"{final_res['ram_used_mb']} MB")
    res_table.add_row("RAM Available (System)", f"{final_res['system_ram_available_mb']} MB")
    
    console.print(res_table)
    
    # 9. Verify generated artifact files exist
    console.print("\n[bold green]Saved Output Files:[/bold green]")
    for k, v in artifacts.items():
        if isinstance(v, str) and os.path.exists(v):
            console.print(f"  • [cyan]{k}[/cyan]: [file://{os.path.abspath(v)}]{os.path.abspath(v)}[/file://{os.path.abspath(v)}]")

if __name__ == "__main__":
    main()
