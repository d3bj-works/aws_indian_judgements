# Requirements: Supreme Court PDF Ingestion & Benchmarking Pipeline (Phase 1)

## Objective

Build a robust, resumable, and benchmarked ingestion pipeline for approximately **40,000 searchable Supreme Court PDFs** from the AWS Open Data dataset.

**Important:** This phase assumes **all PDFs are searchable**. OCR is **out of scope** for this phase.

The pipeline must be designed so that OCR can later replace the text extraction stage without requiring changes to downstream processing.

---

# Primary Goals

* Download PDFs in batches
* Extract searchable text
* Clean extracted text
* Extract metadata
* Extract legal entities
* Store intermediate outputs
* Measure performance of every stage
* Support resumable execution
* Produce detailed logs and benchmarks

---

# High-Level Pipeline

```
Manifest
    ↓
Batch Scheduler
    ↓
Download PDF
    ↓
Validate PDF
    ↓
Extract Text
    ↓
Clean Text
    ↓
Metadata Extraction
    ↓
Entity Extraction
    ↓
Persist Output
    ↓
Update Progress
```

Each PDF should be processed independently.

---

# Concurrency Model

Use Python's

```
concurrent.futures.ThreadPoolExecutor
```

for Phase 1.

The implementation should support configurable worker counts.

---

# Batching Strategy

Do **not** schedule all 40,000 PDFs simultaneously.

Instead:

* Read the manifest sequentially.
* Process PDFs in configurable batches.
* Wait until the batch completes.
* Persist progress.
* Start the next batch.

---

## Initial Benchmark Strategy

The first **1,000 PDFs** are for benchmarking.

Start conservatively.

Example progression:

| PDFs Processed |                        Batch Size |
| -------------- | --------------------------------: |
| 1–100          |                                 5 |
| 101–250        |                                10 |
| 251–500        |                                15 |
| 501–750        |                                20 |
| 751–1000       | Increase only if resources permit |

The batch size should be configurable.

Future enhancement: adaptive batch sizing based on observed RAM usage.

---

# Processing Steps

Each worker processes exactly one PDF.

```
Download

↓

Validate

↓

Extract Text

↓

Clean Text

↓

Metadata Extraction

↓

Entity Extraction

↓

Persist

↓

Return Metrics
```

Workers must be independent.

---

# Intermediate Storage

Never overwrite previous stages.

Store:

```
/pdf/

/raw_text/

/clean_text/

/metadata/

/entities/

/logs/

/benchmarks/

/checkpoints/
```

This avoids repeating expensive operations later.

---

# Metadata Extraction

Extract wherever available:

* Case title
* Court
* Citation
* Date
* Bench
* Judges
* Parties
* Page count

---

# Entity Extraction

Initial deterministic extraction only.

Examples:

* Acts
* Sections
* Articles
* Case citations
* Judges
* Party names
* Dates

Semantic extraction is not required in Phase 1.

---

# Benchmarking Requirements

Every stage must be timed independently.

Record:

| Stage             |
| ----------------- |
| Download          |
| Validation        |
| Text Extraction   |
| Cleaning          |
| Metadata          |
| Entity Extraction |
| Save Output       |
| Database Write    |
| Total Time        |

---

# Machine Resource Monitoring

For every completed batch record:

* CPU %
* Peak RAM
* Disk Read
* Disk Write
* Batch Duration
* PDFs/sec
* Average Time/PDF

These metrics will be used to determine optimal concurrency.

---

# Live Progress

Provide a continuously updating progress display.

Example:

```
Run ID: 20260807-001

Batch: 18 / 80

Completed:
4,320 / 40,000

Running:
5

Failed:
2

Average:
1.42 sec/PDF

Throughput:
8.7 PDFs/sec

ETA:
1h 52m
```

Progress should refresh automatically.

---

# Persistent Logging

Maintain a structured processing log.

Each processed PDF should include:

```
document_id

batch_number

status

download_ms

validation_ms

extract_ms

clean_ms

metadata_ms

entity_ms

save_ms

database_ms

total_ms

pages

word_count

error_message

timestamp
```

---

# JSONL Event Log

Additionally maintain an append-only JSONL log.

Example:

```json
{
  "timestamp":"...",
  "document_id":"...",
  "stage":"extract",
  "duration_ms":418,
  "status":"success"
}
```

This will be used for debugging.

---

# Checkpointing

After every completed batch save:

```
checkpoint.json
```

Example:

```json
{
    "run_id":"20260807-001",
    "last_completed_batch":14,
    "processed":3500
}
```

If interrupted, the pipeline should resume automatically from the next batch.

---

# Failure Handling

Do not repeatedly retry failed PDFs during the main run.

Instead:

* Log failure
* Continue processing
* Store failed document IDs

After all batches complete:

* Retry failed PDFs
* Maximum three attempts
* Remaining failures written to

```
failed_final.csv
```

---

# Run Tracking

Each ingestion execution should have a unique Run ID.

Example:

```
Run ID:
20260807-001
```

All outputs should reference this Run ID.

This enables benchmarking across multiple executions and future pipeline versions.

---

# Configuration

All runtime settings should be configurable.

Examples:

```
batch_size

max_workers

output_directory

retry_limit

benchmark_pdf_limit

logging_level
```

No hardcoded values.

---

# Deliverables

The completed implementation should provide:

* Resumable ingestion pipeline
* ThreadPoolExecutor-based concurrent processing
* Configurable batch scheduling
* Live progress monitoring
* Persistent checkpointing
* Structured logging
* Stage-wise benchmarking
* Machine resource monitoring
* Intermediate artifacts preserved
* Deterministic metadata extraction
* Deterministic legal entity extraction
* Comprehensive error handling and retry mechanism

The codebase should be modular so that, in Phase 2, the text extraction stage can be replaced by an OCR and layout-analysis pipeline without requiring changes to downstream metadata extraction, entity extraction, storage, benchmarking, or progress tracking.
