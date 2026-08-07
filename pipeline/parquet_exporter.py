import os
import json
import glob
import logging
import time
import psutil
from typing import Dict, Any, List, Optional

import pyarrow as pa
import pyarrow.parquet as pq
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn

logger = logging.getLogger("parquet_exporter")

class ParquetExporter:
    """
    Utility for consolidating individual intermediate JSON and TXT output files
    into 3 optimized ZSTD-compressed Parquet files:
    1. metadata.parquet
    2. entities.parquet
    3. documents_text.parquet
    """

    def __init__(self, output_dir: str, compression: str = "zstd"):
        self.output_dir = output_dir
        self.compression = compression
        
        self.metadata_dir = os.path.join(output_dir, "metadata")
        self.entities_dir = os.path.join(output_dir, "entities")
        self.raw_text_dir = os.path.join(output_dir, "raw_text")
        self.clean_text_dir = os.path.join(output_dir, "clean_text")
        self.parquet_dir = os.path.join(output_dir, "parquet")
        
        os.makedirs(self.parquet_dir, exist_ok=True)
        self.process = psutil.Process(os.getpid())

    def _get_ram_mb(self) -> float:
        return round(self.process.memory_info().rss / (1024 * 1024), 2)

    def export_all(self, batch_chunk_size: int = 5000) -> Dict[str, Any]:
        """
        Converts all JSON metadata, entities, and raw/clean text files in output_dir
        into 3 Parquet files. Processed in memory-efficient chunks.
        """
        logger.info(f"Starting complete Parquet export for directory: {self.output_dir}")
        meta_stats = self.export_metadata(chunk_size=batch_chunk_size)
        ent_stats = self.export_entities(chunk_size=batch_chunk_size)
        text_stats = self.export_documents_text(chunk_size=1000)
        
        return {
            "metadata": meta_stats,
            "entities": ent_stats,
            "documents_text": text_stats,
            "parquet_dir": self.parquet_dir
        }

    def export_metadata(self, chunk_size: int = 5000) -> Dict[str, Any]:
        out_file = os.path.join(self.parquet_dir, "metadata.parquet")
        meta_files = sorted(glob.glob(os.path.join(self.metadata_dir, "*.json")))
        if not meta_files:
            logger.warning("No metadata JSON files found to export.")
            return {"file": out_file, "count": 0, "size_bytes": 0}

        logger.info(f"[1/3] Exporting {len(meta_files):,} metadata files -> metadata.parquet (RAM: {self._get_ram_mb()} MB)...")
        schema = pa.schema([
            ("document_id", pa.string()),
            ("case_title", pa.string()),
            ("court", pa.string()),
            ("citation", pa.string()),
            ("date", pa.string()),
            ("bench", pa.list_(pa.string())),
            ("petitioner", pa.string()),
            ("respondent", pa.string()),
            ("page_count", pa.int32()),
            ("word_count", pa.int32()),
            ("char_count", pa.int32()),
        ])

        writer = pq.ParquetWriter(out_file, schema, compression=self.compression)
        total_rows = 0
        t0 = time.time()

        with Progress(SpinnerColumn(), TextColumn("[bold cyan]Compiling metadata.parquet..."), BarColumn(), TaskProgressColumn()) as progress:
            task = progress.add_task("metadata", total=len(meta_files))
            
            for i in range(0, len(meta_files), chunk_size):
                chunk = meta_files[i:i + chunk_size]
                records = []
                for fpath in chunk:
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        bench_val = data.get("bench")
                        if isinstance(bench_val, str):
                            bench_val = [bench_val]
                        elif not isinstance(bench_val, list):
                            bench_val = []

                        records.append({
                            "document_id": str(data.get("document_id") or ""),
                            "case_title": str(data.get("case_title") or ""),
                            "court": str(data.get("court") or ""),
                            "citation": str(data.get("citation") or "") if data.get("citation") else None,
                            "date": str(data.get("date") or "") if data.get("date") else None,
                            "bench": [str(b) for b in bench_val if b],
                            "petitioner": str(data.get("petitioner") or "") if data.get("petitioner") else None,
                            "respondent": str(data.get("respondent") or "") if data.get("respondent") else None,
                            "page_count": int(data.get("page_count") or 0),
                            "word_count": int(data.get("word_count") or 0),
                            "char_count": int(data.get("char_count") or 0),
                        })
                    except Exception:
                        continue
                
                if records:
                    table = pa.Table.from_pylist(records, schema=schema)
                    writer.write_table(table)
                    total_rows += len(records)
                
                progress.update(task, advance=len(chunk))
                logger.info(f"  • metadata.parquet: Chunk {i//chunk_size + 1} processed ({total_rows:,}/{len(meta_files):,} records) | RAM: {self._get_ram_mb()} MB")

        writer.close()
        size_bytes = os.path.getsize(out_file) if os.path.exists(out_file) else 0
        elapsed = time.time() - t0
        logger.info(f"✓ Completed metadata.parquet: {total_rows:,} records | {size_bytes / (1024*1024):.2f} MB | {elapsed:.2f}s")
        return {"file": out_file, "count": total_rows, "size_bytes": size_bytes}

    def export_entities(self, chunk_size: int = 5000) -> Dict[str, Any]:
        out_file = os.path.join(self.parquet_dir, "entities.parquet")
        entity_files = sorted(glob.glob(os.path.join(self.entities_dir, "*.json")))
        if not entity_files:
            logger.warning("No entity JSON files found to export.")
            return {"file": out_file, "count": 0, "size_bytes": 0}

        logger.info(f"[2/3] Exporting {len(entity_files):,} entity files -> entities.parquet (RAM: {self._get_ram_mb()} MB)...")
        schema = pa.schema([
            ("case_id", pa.string()),
            ("type", pa.string()),
            ("canonical", pa.string()),
            ("matched", pa.string()),
            ("normalized", pa.string()),
            ("statute", pa.string()),
            ("paragraph", pa.int32()),
            ("start", pa.int32()),
            ("end", pa.int32()),
            ("confidence", pa.float32()),
        ])

        writer = pq.ParquetWriter(out_file, schema, compression=self.compression)
        total_entities = 0
        t0 = time.time()

        with Progress(SpinnerColumn(), TextColumn("[bold green]Compiling entities.parquet..."), BarColumn(), TaskProgressColumn()) as progress:
            task = progress.add_task("entities", total=len(entity_files))
            
            for i in range(0, len(entity_files), chunk_size):
                chunk = entity_files[i:i + chunk_size]
                records = []
                for fpath in chunk:
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        case_id = str(data.get("case_id") or os.path.splitext(os.path.basename(fpath))[0])
                        
                        entities_list = data.get("entities", [])
                        for ent in entities_list:
                            records.append({
                                "case_id": case_id,
                                "type": str(ent.get("type") or ""),
                                "canonical": str(ent.get("canonical") or ""),
                                "matched": str(ent.get("matched") or ""),
                                "normalized": str(ent.get("normalized") or "") if ent.get("normalized") else None,
                                "statute": str(ent.get("statute") or "") if ent.get("statute") else None,
                                "paragraph": int(ent.get("paragraph") or 0),
                                "start": int(ent.get("start") or 0),
                                "end": int(ent.get("end") or 0),
                                "confidence": float(ent.get("confidence") or 1.0),
                            })
                    except Exception:
                        continue
                
                if records:
                    table = pa.Table.from_pylist(records, schema=schema)
                    writer.write_table(table)
                    total_entities += len(records)
                
                progress.update(task, advance=len(chunk))
                logger.info(f"  • entities.parquet: Chunk {i//chunk_size + 1} processed ({total_entities:,} total entities extracted from {i + len(chunk):,}/{len(entity_files):,} files) | RAM: {self._get_ram_mb()} MB")

        writer.close()
        size_bytes = os.path.getsize(out_file) if os.path.exists(out_file) else 0
        elapsed = time.time() - t0
        logger.info(f"✓ Completed entities.parquet: {total_entities:,} entities | {size_bytes / (1024*1024):.2f} MB | {elapsed:.2f}s")
        return {"file": out_file, "count": total_entities, "size_bytes": size_bytes}

    def export_documents_text(self, chunk_size: int = 1000) -> Dict[str, Any]:
        out_file = os.path.join(self.parquet_dir, "documents_text.parquet")
        clean_files = sorted(glob.glob(os.path.join(self.clean_text_dir, "*.txt")))
        if not clean_files:
            logger.warning("No clean text TXT files found to export.")
            return {"file": out_file, "count": 0, "size_bytes": 0}

        logger.info(f"[3/3] Exporting {len(clean_files):,} text files -> documents_text.parquet (RAM: {self._get_ram_mb()} MB)...")
        schema = pa.schema([
            ("document_id", pa.string()),
            ("raw_text", pa.string()),
            ("clean_text", pa.string()),
        ])

        writer = pq.ParquetWriter(out_file, schema, compression=self.compression)
        total_docs = 0
        t0 = time.time()

        with Progress(SpinnerColumn(), TextColumn("[bold yellow]Compiling documents_text.parquet..."), BarColumn(), TaskProgressColumn()) as progress:
            task = progress.add_task("text", total=len(clean_files))
            
            for i in range(0, len(clean_files), chunk_size):
                chunk = clean_files[i:i + chunk_size]
                records = []
                for clean_path in chunk:
                    try:
                        doc_id = os.path.splitext(os.path.basename(clean_path))[0]
                        raw_path = os.path.join(self.raw_text_dir, f"{doc_id}.txt")
                        
                        clean_text = ""
                        raw_text = ""
                        
                        with open(clean_path, "r", encoding="utf-8") as f:
                            clean_text = f.read()
                            
                        if os.path.exists(raw_path):
                            with open(raw_path, "r", encoding="utf-8") as f:
                                raw_text = f.read()
                        else:
                            raw_text = clean_text

                        records.append({
                            "document_id": doc_id,
                            "raw_text": raw_text,
                            "clean_text": clean_text,
                        })
                    except Exception:
                        continue
                
                if records:
                    table = pa.Table.from_pylist(records, schema=schema)
                    writer.write_table(table)
                    total_docs += len(records)
                
                progress.update(task, advance=len(chunk))
                logger.info(f"  • documents_text.parquet: Chunk {i//chunk_size + 1} processed ({total_docs:,}/{len(clean_files):,} document texts) | RAM: {self._get_ram_mb()} MB")

        writer.close()
        size_bytes = os.path.getsize(out_file) if os.path.exists(out_file) else 0
        elapsed = time.time() - t0
        logger.info(f"✓ Completed documents_text.parquet: {total_docs:,} document texts | {size_bytes / (1024*1024):.2f} MB | {elapsed:.2f}s")
        return {"file": out_file, "count": total_docs, "size_bytes": size_bytes}
