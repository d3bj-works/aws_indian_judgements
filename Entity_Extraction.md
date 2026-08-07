---
status: stable
owner: Debjyoti
updated: 2026-08-07
tags:
  - domain
  - entity-extraction
  - nlp
  - knowledge-graph
  - pdf-pipeline
  - hub-note
---

# Legal Entity Extraction & Authority Verification Specification

## Executive Summary
This document provides the consolidated, single-source-of-truth technical specification for **Legal Entity Extraction** in NyayDesk 2.0. Entity extraction converts unstructured legal text (court judgments, petitions, paper books, statutory notices, and interim orders) into structured domain entities. These extracted entities drive **Zero-Hallucination Citation Verification**, **Cross-Matter Knowledge Graphs**, **Chronology & Timeline Automation**, and **Private Chamber RAG**.

---

## 1. Domain Topology & Target Entity Taxonomy

Entity extraction targets 4 core domain tiers across Indian jurisprudence:

```
┌────────────────────────────────────────────────────────────────────────┐
│                        LEGAL ENTITY TAXONOMY                           │
│                                                                        │
│ ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────┐ │
│ │ Judicial / Metadata  │  │ Statutory / Provisions│  │ Fact & Time  │ │
│ │  • Neutral Citations │  │  • Bare Acts (BNS/IPC│  │  • Dates     │ │
│ │  • Reporter Citations│  │  • Sections/Subsects │  │  • Events    │ │
│ │  • Case Title / Coram│  │  • Const. Articles   │  │  • Annexures │ │
│ │  • CNR & Bench       │  │  • Procedural Rules  │  │  • Amounts   │ │
│ └──────────┬───────────┘  └──────────┬───────────┘  └──────┬───────┘ │
└────────────┼─────────────────────────┼─────────────────────┼─────────┘
             │                         │                     │
             ▼                         ▼                     ▼
┌────────────────────────────────────────────────────────────────────────┐
│                         KNOWLEDGE GRAPH NODES                          │
│     (Statute) ◄─[BELONGS_TO]── (Section) ◄─[INTERPRETS]── (Judgment)   │
│     (Judgment) ──[CITED_IN]─► (Case)  (Bench) ◄─[AUTHORED_BY]─ (Judge)  │
└────────────────────────────────────────────────────────────────────────┘
```

### 1.1 Judicial & Case Identifiers
| Entity Type | Definition / Format | Regular Expression / Extraction Pattern | Primary Standard / Example |
| :--- | :--- | :--- | :--- |
| **Neutral Citation** | e-SCR & High Court official neutral IDs | `\b(19\d{2}\|20\d{2})\s+INSC\s+(\d+)\b` / `\b(20\d{2})\s+:[A-Z]{2,4}:\d+\b` | `2023 INSC 920` / `2024:DHC:1420` |
| **Reporter Citations** | Standard commercial & official law reports | `\b(\d{4})\s+(\d+)\s+(SCC\|AIR\|SCR\|SCALE\|CrLJ\|MLJ\|GLR)\s+(\d+)\b` | `(2021) 4 SCC 123` / `AIR 2020 SC 45` |
| **CNR Number** | 16-character alphanumeric eCourts unique case record ID | `\b[A-Z]{4}\d{12}\b` | `DLHC010012342023` |
| **Case Title** | Petitioner/Appellant vs. Respondent/Defendant string | `^([\w\s\.,\(\)]+?)\s+\b(v\.|vs\.|versus\|VS\.)\b\s+([\w\s\.,\(\)]+)$` | *Kesavananda Bharati v. State of Kerala* |
| **Judges / Coram** | Bench composition & authoring judge | `\b(BEFORE\|CORAM):\s*([\w\s,\.\(\)Hon'ble Justice]+)` | *Hon'ble Mr. Justice D.Y. Chandrachud* |
| **Court & Forum** | Court level and bench location | `\b(Supreme Court of India\|High Court of [\w\s]+)\|District Court\b` | *High Court of Judicature at Bombay* |

### 1.2 Statutory & Legislative Provisions
| Entity Type | Scope & Normalization Rules | Target Pattern / Rules | Example |
| :--- | :--- | :--- | :--- |
| **Bare Act / Statute** | IPC, CrPC, IEA vs BNS, BNSS, BSB (2023) & Special Acts | `\b(Bharatiya Nyaya Sanhita\|BNS\|Indian Penal Code\|IPC\|Limitation Act\|NI Act)\b` | *Bharatiya Nyaya Sanhita, 2023* |
| **Section** | Numerical / alpha-numeric statutory provision | `\b(Section\|Sec\.|S\.)\s*(\d+[A-Z]?(\(\d+\))*)\b` | *Section 303(2)* / *Section 138* |
| **Article** | Constitutional provisions | `\b(Article\|Art\.)\s*(\d+[A-Z]?(\(\d+\))*)\b` | *Article 21* / *Article 226* |
| **Order & Rule** | Procedural Code (CPC) specific provisions | `\bOrder\s+([I\|V\|X\|L\|C]+|\d+)\s+Rule\s+(\d+)\b` | *Order XXXIX Rule 1 & 2 CPC* |

### 1.3 Fact & Procedural Chronology Entities
| Entity Type | Extract Boundary | Domain Utility | Target Consumer |
| :--- | :--- | :--- | :--- |
| **Event Dates** | `DD/MM/YYYY`, `DDth Month YYYY` | Populates [[Timeline]] & [[LimitationPeriod]] | Junior Associate Priya (Chronology) |
| **Interim Orders** | Operative directions, stay orders, bail grants | Creates `Order` domain entity | Senior Advocate Arindam (Briefing) |
| **Monetary Values** | Recovery amount, cheque bounce value, penalty | Financial assessment & court fee validation | Chamber Litigation Binder |
| **Annexure Markings** | `Annexure P-1`, `Exhibit D-4` | Evidentiary binding & paper book indexing | Clerk Rakesh (Registry Filing) |

---

## 2. Extraction Output Payload Schema (Benchmark Ground Truth)

Based on empirical extraction outputs in `research/judgements/extracted_entities.json`, the extraction pipeline emits a standardized JSON payload structure:

```json
{
  "row_index": 0,
  "case_id": "1950 INSC 25",
  "title": "SRI RANGA NILAYAM RAMA KRISHNA RAO versus KANDOKOLU CHELLA Y AMMA ALIAS MANGAMMA AND ANOTHER",
  "citation": "[1950] 1 S.C.R. 806",
  "year": "1950",
  "court": "Supreme Court of India",
  "entities_count": 6,
  "entities": [
    {
      "type": "statute",
      "canonical": "Madras Agriculturists' Relief Act",
      "matched": "Madras Agriculturists' Relief Act",
      "normalized": "Madras Agriculturists' Relief Act",
      "statute": "Madras Agriculturists' Relief Act",
      "paragraph": 0,
      "start": 257,
      "end": 290,
      "confidence": 0.95
    },
    {
      "type": "order_rule",
      "canonical": "Order XXI Rule 90",
      "matched": "O.XXI, r. 90",
      "normalized": "O.XXI R.90",
      "statute": "Code of Civil Procedure, 1908",
      "paragraph": 0,
      "start": 403,
      "end": 415,
      "confidence": 0.90
    },
    {
      "type": "section",
      "canonical": "Section 3 (D)",
      "matched": "ss. 3 (D), 8, 10, 19",
      "normalized": "3 (D)",
      "statute": "Madras Agriculturists' Relief Act",
      "paragraph": 0,
      "start": 305,
      "end": 325,
      "confidence": 0.90
    },
    {
      "type": "article",
      "canonical": "Article 136",
      "matched": "article 136",
      "normalized": "136",
      "statute": "Constitution of India",
      "paragraph": 0,
      "start": 207,
      "end": 218,
      "confidence": 0.95
    }
  ]
}
```

---

## 3. Extraction Pipeline Architecture

The end-to-end extraction pipeline consists of 5 deterministic processing layers:

```text
[ Input PDF / Text ]
         │
         ▼
 ┌──────────────────────────────────────────────────────────┐
 │ Layer 1: Multi-Engine PDF Extraction                     │
 │  • Digital (2020-Present): PyMuPDF (fitz) @ ~18 ms/page  │
 │  • Mixed (2000-2019): PyMuPDF + pdfplumber layout engine │
 │  • Legacy (1950-1999): Tesseract / Cloud Vision OCR      │
 └─────────────────────────┬────────────────────────────────┘
                           │
                           ▼
 ┌──────────────────────────────────────────────────────────┐
 │ Layer 2: Text Normalization & Layout Cleaning            │
 │  • Unicode NFKC Normalization                            │
 │  • Ligature Repair (ﬁ → fi, ﬂ → fl, æ → ae)             │
 │  • Page Marker & Header/Footer Noise Stripping           │
 └─────────────────────────┬────────────────────────────────┘
                           │
                           ▼
 ┌──────────────────────────────────────────────────────────┐
 │ Layer 3: Extractor Engine (Deterministic + LLM Hybrid)   │
 │  • Regex Submodules: citations.py, statutes.py, etc.    │
 │  • LLM Fact Extractor: JSON schema chronology parser    │
 └─────────────────────────┬────────────────────────────────┘
                           │
                           ▼
 ┌──────────────────────────────────────────────────────────┐
 │ Layer 4: Normalization & Canonical Linkage               │
 │  • Title/Coram Noise Stripping (removing v., State of)   │
 │  • Neutral Citation Linkage (100% Match Priority)       │
 └─────────────────────────┬────────────────────────────────┘
                           │
                           ▼
 ┌──────────────────────────────────────────────────────────┐
 │ Layer 5: Knowledge Graph & Citation Guardrails           │
 │  • Authority Resolver (overruled bench validation)       │
 │  • Multi-Tier RAG Context Indexing                       │
 └─────────────────────────┴────────────────────────────────┘
```

---

## 4. Pre-Extraction Normalization & Layout Cleaning

Direct entity extraction on raw extracted text fails due to OCR noise, ligatures, and running titles. Standardized preprocessing rules:

1. **Unicode NFKC Normalization**: Converts non-standard code points into canonical form.
2. **Ligature Substitution**: Replaces combined characters (`ﬁ` $\rightarrow$ `fi`, `ﬂ` $\rightarrow$ `fl`, `æ` $\rightarrow$ `ae`).
3. **Noise Stripping**:
   * Page header/footer titles (e.g., *"SUPREME COURT REPORTS [2023] 4 S.C.R."*).
   * Page numbers floating at paragraph edges.
4. **Paragraph Integrity**: Preserves double-newline block structure (`paragraphs[]`) for section chunking and embedding generation.

---

## 5. Deterministic Linkage & Priority Hierarchy

Matching extracted judgment titles and citations against the full legal corpus (2.4Cr+ records) follows a strict deterministic fallback hierarchy:

```
  ┌────────────────────────────────────────────────────────────┐
  │ Priority 1: Neutral Citation Match                         │
  │ • Pattern: 2023 INSC 920 / 2024:DHC:1420                   │
  │ • Confidence: 100% (Direct canonical database link)        │
  └─────────────────────────────┬──────────────────────────────┘
                                │ (If missing)
                                ▼
  ┌────────────────────────────────────────────────────────────┐
  │ Priority 2: Official Reporter Citation Match               │
  │ • Pattern: (2021) 4 SCC 123 / AIR 2020 SC 45               │
  │ • Confidence: ~95–99% (Matched against volume/page index) │
  └─────────────────────────────┬──────────────────────────────┘
                                │ (If missing)
                                ▼
  ┌────────────────────────────────────────────────────────────┐
  │ Priority 3: Title + Coram String Distance Match             │
  │ • Step A: Strip noise ("v.", "vs.", "The State of", "UOI") │
  │ • Step B: Compute Levenshtein / Jaro-Winkler distance      │
  │ • Confidence: Threshold >= 0.85 (Fuzzy match evaluation)   │
  └────────────────────────────────────────────────────────────┘
```

---

## 6. Code Structure & Pipeline File Layout

The entity extraction codebase is organized in `nyaydesk_backend` and research pipelines as follows:

```text
pipeline/
├── 01_profile_pdfs.py         # Stratified PDF corpus sampling (1950s–2020s)
├── 02_extract_text.py          # PyMuPDF/pdfplumber multi-engine text extractor
├── 03_normalize_text.py        # NFKC normalization & header/footer stripper
├── 04_quality_score.py        # Extraction quality & OCR necessity scoring
├── 05_extract_entities.py      # Core entity extraction orchestrator
├── 06_link_entities.py         # Knowledge graph node/edge builder
└── config.py                   # Regex patterns & statutory dictionaries

extractors/
├── pdf/
│   ├── pymupdf.py              # Primary fast extractor (~18 ms/page)
│   ├── pdfplumber.py           # Tabular & layout heavy fallback
│   └── fallback.py             # OCR gateway (Tesseract / Cloud Vision)
├── normalize.py                # Unicode & ligature cleanup utilities
├── statutes.py                 # Bare act & BNS/IPC transition parser
├── sections.py                 # Statutory section & subsection extractor
├── articles.py                 # Constitutional article parser
├── citations.py                # Neutral & reporter citation resolver
└── judges.py                   # Bench & coram parser
```

---

## 7. Downstream System Integrations

Extracted entities directly hydrate core NyayDesk sub-systems:

1. **[[Knowledge Graph]]**: Establishes `CITED_IN`, `INTERPRETS`, `OVERRULES`, and `AUTHORED_BY` edges.
2. **[[AI Pipeline]] (Zero-Hallucination Guardrail)**: Intercepts generated LLM citations and validates volume/reporter/page existence against extracted canonical records.
3. **[[Timeline]] & [[LimitationPeriod]]**: Converts extracted filing dates, order dates, and statutory sections into automated limitation countdown timers.
4. **[[Document]] (Case Binder Assembly)**: Links extracted annexure IDs to physical paper books and client uploaded PDFs.

---

## 8. Benchmarks & Empirical Performance Metrics

* **Ground Truth Sample**: Tested against benchmark outputs in `research/judgements/extracted_entities.json`.
* **Extraction Throughput**: Target $\le$ **25 ms per page** for digital PDFs using PyMuPDF (`fitz`).
* **Citation Resolution Precision**: **100% precision** mandatory for public law citations before model output streaming.
* **BNS / BNSS Mapping Accuracy**: 100% accuracy on statutory cross-mapping between legacy codes (IPC/CrPC) and new criminal codes (BNS/BNSS).
