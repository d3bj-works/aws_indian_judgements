# High Court Ingestion & Pipeline Optimization Strategy

**Corpus Baseline Audit**: 37,235 Supreme Court Judgments (1950–2026)  
**Metrics File Analyzed**: [`metrics_RUN-2026-50000.jsonl`](file:///home/duttadev/projects/aws_indian_judgements/output_1000/benchmarks/metrics_RUN-2026-50000.jsonl)  
**Primary Focus**: Empirical log analysis and optimization architecture for High Court Corpus Ingestion (Option B).

---

## 1. Empirical Log Analysis Summary

An analysis of the full 37,235-document Supreme Court baseline dataset run yielded the following performance metrics:

| Metric | Value |
| :--- | :--- |
| **Total Processed Documents** | 37,235 |
| **Total Processed Pages** | 585,988 |
| **Total Word Count** | 224,761,433 (~224.7M words) |
| **Total Elapsed Execution Time** | 17,478.04 seconds (~4.85 hours) |
| **Overall PDF Throughput** | **2.13 PDFs / second** (127.8 PDFs / minute) |
| **Overall Page Throughput** | **33.53 pages / second** |

---

## 2. Pipeline Latency Breakdown & Bottleneck Identification

| Pipeline Stage | Avg Duration (ms) | Percentage Share | Resource Dependency | Assessment |
| :--- | :--- | :--- | :--- | :--- |
| **Download (`download_ms`)** | **1,315.25 ms** | **81.2%** | Network RTT / HTTP | **PRIMARY BOTTLENECK** |
| **Text Extraction (`extract_ms`)** | 118.69 ms | 7.3% | CPU (PyMuPDF) | Normal |
| **Entity Extraction (`entity_ms`)** | 85.14 ms | 5.3% | CPU (Regex / Spacy) | Normal |
| **Metadata Extraction (`metadata_ms`)** | 51.09 ms | 3.2% | CPU | Fast |
| **Text Cleaning (`clean_ms`)** | 9.54 ms | 0.6% | CPU | Fast |
| **Validation (`validation_ms`)** | 4.68 ms | 0.3% | Disk I/O | Fast |
| **Total Per Document** | **1,620.40 ms** | **100.0%** | — | — |

---

## 3. Key Findings & Root Cause Diagnostics

1. **81.2% Time Spent on Unpooled Network Downloads**:
   - `PDFDownloader.download_pdf` executes a non-persistent `requests.get()` request for every judgment.
   - Re-establishing TCP connections and performing TLS handshakes for each document adds ~800–1200ms latency overhead per file.
2. **Sub-optimal Concurrency Limit**:
   - `max_workers` in [`config.py`](file:///home/duttadev/projects/aws_indian_judgements/config.py) defaults to `4`.
   - With network downloads bottlenecked by HTTP RTT, 4 workers are insufficient to saturate network throughput.

---

## 4. Optimization Plan for High Court Ingestion

To scale the pipeline efficiently for High Court datasets (which will exceed 100k–500k documents across state High Courts), the following optimizations are planned:

1. **HTTP Connection Pooling & Session Reuse**:
   - Update [`PDFDownloader`](file:///home/duttadev/projects/aws_indian_judgements/pipeline/downloader.py) to manage a shared `requests.Session()` with HTTP Keep-Alive connection pooling (`urllib3.HTTPAdapter`).
2. **Worker & Batch Scaling**:
   - Increase `max_workers` from 4 to 16/24 for I/O tasks.
   - Adjust `batch_size` from 5 to 50/100 to reduce batch loop and dashboard refresh overhead.
3. **Directory & Partitioning Readiness**:
   - Establish `data/high_court/` directory hierarchy (`raw_text/`, `clean_text/`, `metadata/`, `entities/`, `parquet/`).

---

## 5. Verification Metrics Target

- **Download Latency Target**: Reduce `download_ms` from ~1,315 ms to < 200 ms per file.
- **Target Ingestion Throughput**: Increase throughput from **2.13 PDFs/sec** to **> 8–12 PDFs/sec**.
