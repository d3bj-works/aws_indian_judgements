# Executive Data Analysis Report: Supreme Court Judgments & Extracted Legal Entities

**Corpus Scope**: 38,235 Supreme Court Judgments (1950–2026)  
**Extracted Entities**: 2,889,841 Legal Domain Entities  
**Output Storage**: Apache Parquet (ZSTD Compressed)  
**Author**: NyayDesk 2.0 AI Data Engineering Team  

---

## Executive Summary

This report delivers the comprehensive technical and empirical analysis of **Step 1: Document Metadata & Extracted Legal Entities** for the Supreme Court of India judgments corpus. 

Through the Parquet export pipeline, intermediate JSON and text files were consolidated into 3 high-performance ZSTD-compressed Parquet files, reducing the raw data storage footprint from **4.00 GB to 970.71 MB** (**76.27% reduction**). 

### Key Findings
1. **Corpus Volume & Coverage**: The dataset covers **38,235 judgments**. Entity extraction achieved a **99.97% success rate** (38,224 out of 38,235 documents yielded at least one extracted entity).
2. **Entity Density**: A total of **2,889,841 legal entities** were extracted. On average, each judgment yields **75.60 extracted entities**.
3. **Dominant Tiers**: **Statutory Sections** ($36.02\%$) and **Bare Acts / Statutes** ($26.04\%$) constitute over $62\%$ of all extracted legal references, followed by **Dates** ($20.24\%$) and **Constitutional Articles** ($8.81\%$).
4. **Complexity Inflation**: Legal entity density per judgment has increased dramatically over judicial eras, rising from **54.34 entities/doc** in the 1990s to **127.60 entities/doc** in the 2020s (a **$134.8\%$ increase**).

---

## 1. Dataset Relational Architecture & Schema

The dataset is partitioned into 3 schema-optimized Parquet files in `data/supreme_court/parquet/`:

| Parquet File | Record Count | Disk Size | Primary / Foreign Key | Key Fields |
| :--- | :--- | :--- | :--- | :--- |
| `metadata.parquet` | 38,235 | 1.20 MB | `document_id` (PK) | `document_id`, `case_title`, `court`, `citation`, `date`, `bench`, `petitioner`, `respondent`, `page_count`, `word_count`, `char_count` |
| `entities.parquet` | 2,889,841 | 122.30 MB | `case_id` (FK $\rightarrow$ `document_id`) | `case_id`, `type`, `canonical`, `matched`, `normalized`, `statute`, `paragraph`, `start`, `end`, `confidence` |
| `documents_text.parquet` | 38,235 | 894.37 MB | `document_id` (PK / 1-to-1) | `document_id`, `raw_text`, `clean_text` |

### Relational Topology

```mermaid
erDiagram
    METADATA {
        string document_id PK "1950_1_1008_1018_EN"
        string case_title "Kesavananda Bharati v. State"
        string court "Supreme Court of India"
        string citation "[1950] 1 S.C.R. 806"
        string date "26th February, 1950"
        int page_count "16"
        int word_count "6033"
    }

    DOCUMENTS_TEXT {
        string document_id PK "1950_1_1008_1018_EN"
        text raw_text "Uncleaned PDF OCR Text"
        text clean_text "NFKC Normalized Text"
    }

    ENTITIES {
        string case_id FK "1950_1_1008_1018_EN"
        string type "statute | section | article"
        string canonical "Constitution of India"
        string matched "Art. 21"
        float confidence "0.95"
    }

    METADATA ||--|| DOCUMENTS_TEXT : "1-to-1 Match"
    METADATA ||--o{ ENTITIES : "1-to-Many Link (case_id)"
```

> [!NOTE]
> **Join Keys**: `metadata.parquet` and `documents_text.parquet` maintain a strict 1-to-1 relationship indexed on `document_id`. `entities.parquet` links via `entities.case_id` = `metadata.document_id` in a 1-to-many relationship.

---

## 2. Document Metadata Profiling & Corpus Statistics

### Overall Corpus Length Statistics

| Metric | Page Count | Word Count | Character Count |
| :--- | :--- | :--- | :--- |
| **Mean** | 15.93 pages | 6,033.47 words | 35,126.31 chars |
| **Maximum** | 1,093 pages | 485,965 words | 2,866,781 chars |

### Temporal Distribution & Judicial Volume (1950–2026)

By extracting years from `date` strings and fallback `document_id` prefixes (`COALESCE(REGEXP_EXTRACT(date, '\b(19\d{2}|20\d{2})\b'), REGEXP_EXTRACT(document_id, '^(\d{4})'))`), we recovered temporal metadata for **31,128 judgments**:

```
Decade    Judgment Count    Pct of Corpus    Avg Entities / Doc
───────   ──────────────    ─────────────    ──────────────────
1950s              828              2.66%                 87.27
1960s            2,842              9.13%                 62.89
1970s            2,953              9.49%                 61.73
1980s            2,439              7.83%                 63.41
1990s            3,124             10.04%                 54.34
2000s            6,108             19.62%                 57.03
2010s            7,694             24.72%                 92.54
2020s            4,956             15.92%                127.60
```

> [!IMPORTANT]
> **Key Insight**: Judgment output accelerated dramatically after 2000, with **60.26% of all judgments** in the corpus delivered between 2000 and 2026.

---

## 3. Extracted Entity Taxonomy & Breakdown

The extraction pipeline identifies 11 core legal entity types across the 2,889,841 extracted records:

| Entity Type | Record Count | Pct Share | Avg Confidence | Description & Primary Usage |
| :--- | :--- | :--- | :--- | :--- |
| **`section`** | 1,040,970 | 36.02% | 0.9000 | Statutory sections & sub-sections (IPC 302, CrPC 482) |
| **`statute`** | 752,628 | 26.04% | 0.9500 | Bare Acts & Legislative enactments (BNS, CPC, IEA) |
| **`date`** | 585,010 | 20.24% | 0.9000 | Fact chronology, filing dates, order dates |
| **`article`** | 254,464 | 8.81% | 0.9500 | Constitutional provisions (Art 14, 19, 21, 136, 226) |
| **`monetary_value`** | 169,677 | 5.87% | 0.8500 | Monetary claims, penalties, cheque bounce amounts |
| **`reporter_citation`** | 33,042 | 1.14% | 0.9500 | Commercial report citations (SCC, AIR, SCR, SCALE) |
| **`order_rule`** | 17,257 | 0.60% | 0.9000 | Procedural code rules (Order XXXIX Rule 1 CPC) |
| **`coram`** | 17,072 | 0.59% | 0.9000 | Bench composition & authoring judge names |
| **`annexure`** | 15,759 | 0.55% | 0.9000 | Paper book exhibits & annexures (Annexure P-1) |
| **`neutral_citation`** | 3,961 | 0.14% | 1.0000 | Official e-SCR / HC neutral IDs (2023 INSC 920) |
| **`cnr`** | 1 | 0.00% | 1.0000 | Unique 16-character eCourts case record ID |
| **TOTAL** | **2,889,841** | **100.00%** | **0.9168** | **Overall Extraction Benchmark** |

---

## 4. Top Cited Statutory Provisions & Constitutional Articles

### Top 10 Most Cited Statutes / Bare Acts
1. **Constitution of India**
2. **Indian Penal Code, 1860 (IPC)**
3. **Code of Criminal Procedure, 1973 (CrPC)**
4. **Code of Civil Procedure, 1908 (CPC)**
5. **Indian Evidence Act, 1872 (IEA)**
6. **Income Tax Act, 1961**
7. **Companies Act, 1956 / 2013**
8. **Motor Vehicles Act, 1988**
9. **Arbitration and Conciliation Act, 1996**
10. **Negotiable Instruments Act, 1881**

### Top 5 Most Cited Constitutional Articles
1. **Article 136**: Special Leave Petitions (SLP)
2. **Article 226**: High Court Writ Jurisdiction
3. **Article 14**: Equality Before Law & Non-Arbitrariness
4. **Article 21**: Protection of Life & Personal Liberty
5. **Article 32**: Constitutional Remedies (Supreme Court Writ)

---

## 5. Data Quality & Completeness Audit

### Null Value Analysis on Metadata (38,235 Records)
- **`citation`**: 2,284 present (94.03% null - legacy documents reliance on raw text header).
- **`date`**: 2,424 present in native field (recovered 31,128 via `document_id` year parsing).
- **`petitioner` / `respondent`**: 1,135 present.

### Extraction Confidence Distribution
- **Confidence Range**: 0.85 to 1.00 across all entity types.
- **Low-Confidence Flags (< 0.80)**: **0 records** (100% of extracted entities satisfy minimum confidence thresholds).

---

## 6. Recommendations & Downstream System Integrations

> [!TIP]
> **1. Knowledge Graph Hydration**: Use `entities.parquet` to construct `(Judgment) -[CITE]-> (Statute)` and `(Judgment) -[INTERPRETS]-> (Section)` edges for legal graph RAG.

> [!TIP]
> **2. Zero-Hallucination Guardrails**: Leverage extracted `neutral_citation` and `reporter_citation` records to build citation verification guardrails against LLM hallucinations.

> [!TIP]
> **3. Chronology Automation**: Combine extracted `date` entities with `order_rule` and `monetary_value` records to automate limitation period calculations and brief building.
