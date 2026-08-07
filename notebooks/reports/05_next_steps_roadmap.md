# Strategic Expansion Roadmap: Statutory Knowledge Graph vs High Court Corpus Expansion

**Corpus Scope**: 38,235 Supreme Court Judgments (1950–2026)  
**Processed Datasets**: [`acts_and_sections.csv`](file:///home/duttadev/projects/aws_indian_judgements/notebooks/reports/assets/acts_and_sections.csv) (300k rows), [`acts.csv`](file:///home/duttadev/projects/aws_indian_judgements/notebooks/reports/assets/acts.csv) (91k canonical enactments)  
**Primary Focus**: Detailed comparison between **Option A (Statutory Knowledge Graph)** and **Option B (High Court Corpus Expansion)** to determine optimal sequence and execution order.

---

## Executive Summary

Following baseline corpus profiling ([`01_corpus_baseline_profiling.md`](file:///home/duttadev/projects/aws_indian_judgements/notebooks/reports/01_corpus_baseline_profiling.md)), statutory Pareto analysis ([`02_entity_pareto_concentration.md`](file:///home/duttadev/projects/aws_indian_judgements/notebooks/reports/02_entity_pareto_concentration.md)), new criminal codes transition tracking ([`03_statute_deep_dive_bns_spotlight.md`](file:///home/duttadev/projects/aws_indian_judgements/notebooks/reports/03_statute_deep_dive_bns_spotlight.md)), and canonical Central vs State tagging ([`04_canonical_statutes_central_vs_state.md`](file:///home/duttadev/projects/aws_indian_judgements/notebooks/reports/04_canonical_statutes_central_vs_state.md)), the project stands at a key strategic fork:

- **Option A: Statutory Co-Occurrence Citation Knowledge Graph**  
  Build network graphs, community detection clusters, PageRank metrics, and GraphRAG exports on the existing Supreme Court corpus.
- **Option B: High Court Judgments Corpus Expansion**  
  Ingest, extract, normalize, and structure High Court decision datasets to mirror the Supreme Court data pipeline.

---

## Side-by-Side Comparison Matrix

| Technical Dimension | Option A: Statutory Knowledge Graph | Option B: High Court Corpus Expansion |
| :--- | :--- | :--- |
| **Prerequisites & Data Readiness** | **100% Ready**. Operates on existing 38.2k SC dataset & enriched `acts.csv`. | **0% Ingested**. Requires setting up High Court PDF/text sources & pipeline execution. |
| **Time to Execution & Results** | **Immediate (1–2 Days)**. Pure analytical & graph computation. | **Multi-Stage (1–2 Weeks)**. Requires ingestion, text cleaning, entity NLP, & parquet export. |
| **Primary Output** | GraphRAG node/edge datasets, Louvain domain clusters, PageRank, PyVis 3D visual graph. | `data/high_court/parquet/` datasets, High Court entity extractions, state-level legal corpus. |
| **Technical Complexity** | Graph algorithms, network science (`networkx`, `community-louvain`, `pyvis`). | Data engineering, parallel ingestion, batch scheduling, metadata parsing (`batch_runner.py`). |
| **Risk & Bottlenecks** | Very Low (Internal data processing). | Moderate (Data format variability, OCR requirements, large file volumes). |
| **Downstream Synergy** | Defines standard graph schema for multi-court integration. | Expands geographical coverage to regional state High Courts. |

---

## Detailed Breakdown of Options

### Option A: Statutory Co-Occurrence Citation Knowledge Graph

#### Scope & Deliverables
Transform flat statute citation pairs into a weighted **Network Graph $G = (V, E)$**:
- **Co-Occurrence Matrix**: DuckDB pairwise aggregation of co-cited enactments and provisions per judgment.
- **Community Detection**: Run Louvain & Infomap algorithms to partition law into 7+ domain clusters (*Criminal*, *Civil*, *Tax*, *Commercial*, *Land*, *Labor*, *Constitutional*).
- **Centrality Metrics**: Calculate PageRank and Betweenness Centrality to uncover key anchor statutes and "bridge laws".
- **Exports**: `statute_cooccurrence_edges.csv`, `statute_network_nodes.csv`, `statute_knowledge_graph.html` (interactive HTML graph visualization), and Jupyter Notebook [`notebooks/statute_knowledge_graph.ipynb`](file:///home/duttadev/projects/aws_indian_judgements/notebooks/statute_knowledge_graph.ipynb).

---

### Option B: High Court Judgments Corpus Expansion

#### Scope & Deliverables
Extend the ingestion and entity extraction pipeline to High Court decisions (Allahabad HC, Bombay HC, Delhi HC, Madras HC, Calcutta HC, etc.):
- **Pipeline Setup**: Establish `data/high_court/` directory hierarchy (`raw_text/`, `entities/`, `parquet/`).
- **Entity Extraction & Canonical Tagging**: Run statute and section extractor over High Court judgments, generating `high_court_acts_and_sections.csv` and `high_court_acts.csv`.
- **SC vs HC Comparative Profiling**: Analyze how state laws are invoked in High Courts vs Supreme Court appellate review.

---

## Strategic Recommendation: Which One to Do First?

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                        RECOMMENDED SEQUENCE & EXECUTION ORDER                          │
├────────────────────────────────────────────────────────────────────────────────────────┤
│                                                                                        │
│   STEP 1: Option A — Statutory Knowledge Graph Engine (Supreme Court)                  │
│   ├── Leverage 100% prepared SC dataset (acts.csv, acts_and_sections.csv)               │
│   ├── Build co-occurrence network, PageRank centrality & Louvain domain clusters       │
│   └── Establish GraphRAG node/edge schema & PyVis interactive visualizers               │
│                                                                                        │
│                                           │                                            │
│                                           ▼                                            │
│                                                                                        │
│   STEP 2: Option B — High Court Judgments Corpus Expansion                              │
│   ├── Ingest & extract High Court decisions into data/high_court/parquet/               │
│   ├── Canonicalize state legislation citations against central registry                │
│   └── Merge High Court graph into pre-built Knowledge Graph schema (Unified Graph)     │
│                                                                                        │
└────────────────────────────────────────────────────────────────────────────────────────┘
```

### Why Do **Option A (Statutory Knowledge Graph)** First?

1. **Zero Data Friction**: The Supreme Court dataset (38,235 judgments, 300k act-section pairs, 91k canonical titles) is **already fully extracted, canonicalized, and enriched**. Option A yields immediate, high-value visual and algorithmic results without waiting for new ingestion pipelines.
2. **Defines the Multi-Court Graph Schema**: Building the Knowledge Graph engine now establishes the node/edge metadata schema, centrality scoring, and visualizer tools on Supreme Court jurisprudence. 
3. **Seamless High Court Integration**: When High Court judgments are subsequently ingested in Option B, their co-occurrence edges can be merged directly into the pre-established Graph schema to create a unified **Indian Judicial Citation Knowledge Graph (Supreme Court + High Courts)**!

---

## Summary Decision Matrix

> **Do Option A First IF**:
> - You want immediate, publication-quality graph analytics, PageRank rankings, domain community clusters, and interactive 3D visualizers.
> - You want to establish the GraphRAG framework on clean, pre-existing Supreme Court data.

> **Do Option B Second IF**:
> - You are ready to launch long-running data ingestion and entity extraction pipelines for multi-court datasets across state High Courts.

---

## Active Execution Decision: Option B (High Court Corpus Expansion)

**Status**: **SELECTED FOR IMMEDIATE EXECUTION**  
**Prerequisite Identified**: **Pipeline Optimization & Bottleneck Remediation**

Following user confirmation, the project is proceeding directly with **Option B: High Court Corpus Expansion**.

### Empirical Log Review & Optimization Requirements
Before initiating large-scale High Court ingestion, an audit of the Supreme Court baseline log (`metrics_RUN-2026-50000.jsonl` — 37,235 judgments, 585,988 pages) identified critical performance bottlenecks:

1. **HTTP/S3 Download Bottleneck (81.2% of Total Latency)**:
   - Average document processing time: `1,620.40 ms`.
   - Download phase (`download_ms`): **`1,315.25 ms`** per document due to unpooled single-use HTTP connections.
2. **Concurrency & Throughput Target**:
   - Current baseline throughput: **2.13 PDFs/sec** (33.53 pages/sec).
   - Targeted post-optimization throughput: **> 8–12 PDFs/sec** via `requests.Session()` HTTP keep-alive connection pooling and worker pool tuning (`max_workers`).

Next action item: Apply connection pooling optimizations in [`pipeline/downloader.py`](file:///home/duttadev/projects/aws_indian_judgements/pipeline/downloader.py) and configuration scaling in [`config.py`](file:///home/duttadev/projects/aws_indian_judgements/config.py) prior to launching High Court batch ingestion.

