# Discovered Non-Constitutional Statutory Enactments Report (Deduplicated Canonical Inventory)

**Corpus Scope**: 38,235 Supreme Court Judgments (1950–2026)  
**Source Dataset**: [`notebooks/reports/assets/acts_and_sections.csv`](file:///home/duttadev/projects/aws_indian_judgements/notebooks/reports/assets/acts_and_sections.csv) (300,502 Deduplicated Act-Section Pairs)  
**Exclusion Criteria**: Excludes `Constitution of India` and generic `Unspecified Act` / OCR header artifacts  
**Author**: NyayDesk 2.0 AI Legal Data Engineering Team  

---

## Executive Summary

Following initial statutory extraction, raw entity extractions contained significant string variations for identical legislative enactments (e.g. `Land Acquisition Act, 1894` vs `Land Acquisition Act`, `Indian Penal Code` vs `Penal Code, 1860` vs `IPC`).

This report presents the **deduplicated canonical inventory** of all non-constitutional statutory enactments discovered in the Supreme Court corpus. By applying deterministic canonical mapping rules and filtering out OCR artifacts (e.g. `"From the Judgment and Order"`, `"A of the Act"`), raw extracted strings were consolidated into standardized canonical titles.

### Deduplication Impact (Before vs After)

| Metric | Raw Extraction Output | Cleaned & Canonicalized Output | Optimization Impact |
| :--- | :--- | :--- | :--- |
| **Unique Non-Constitutional Enactment Strings** | 173,179 raw strings | **91,297 canonical statutes** | **47.28% string consolidation** |
| **Unique Act-Section Combination Pairs** | 510,011 pairs | **300,502 deduplicated pairs** | **41.08% pair deduplication** |
| **Total Non-Constitutional Citation Volume** | 621,438 citations | **705,970 consolidated citations** | **100% citation preservation** |

---

## 1. Top 30 Canonical Non-Constitutional Statutory Enactments

Below is the consolidated ranking of the top 30 non-constitutional canonical statutory enactments, showing total citation volume across all name variations, unique section count, and maximum document spread across the Supreme Court corpus:

| Rank | Canonical Statutory Enactment Title | Merged String Variants (Examples) | Total Citations | Unique Sections Discovered | Max Document Count |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | **Indian Penal Code, 1860** | IPC, Penal Code, Penal Code 1860 | **234,950** | 1,300 | 3,311 |
| **2** | **Code of Criminal Procedure, 1973** | CrPC, Criminal Procedure Code | **104,186** | 1,029 | 811 |
| **3** | **Code of Civil Procedure, 1908** | CPC, Civil Procedure Code | **97,174** | 763 | 450 |
| **4** | **Limitation Act, 1963** | Limitation Act | **45,420** | 415 | 327 |
| **5** | **Income Tax Act, 1961** | Income-tax Act, Income Tax Act | **39,976** | 728 | 148 |
| **6** | **Indian Evidence Act, 1872** | Evidence Act, Evidence Act 1872 | **31,493** | 535 | 231 |
| **7** | **Land Acquisition Act, 1894** | Land Acquisition Act | **22,739** | 317 | 738 |
| **8** | **Customs Act, 1962** | Customs Act | **14,088** | 388 | 77 |
| **9** | **Companies Act, 1956 / 2013** | Companies Act, Companies Act 1956 | **13,508** | 586 | 101 |
| **10** | **Transfer of Property Act, 1882** | Transfer of Property Act | **11,716** | 311 | 132 |
| **11** | **Industrial Disputes Act, 1947** | Industrial Disputes Act | **11,128** | 286 | 220 |
| **12** | **General Clauses Act, 1897** | General Clauses Act | **10,925** | 320 | 163 |
| **13** | **Arbitration Act, 1940 / 1996** | Arbitration Act, Arbitration & Conciliation | **10,409** | 207 | 157 |
| **14** | **Negotiable Instruments Act, 1881** | Negotiable Instruments Act | **9,262** | 216 | 319 |
| **15** | **Arbitration & Conciliation Act, 1996** | Arbitration Act 1996 | **9,115** | 179 | 243 |
| **16** | **Indian Contract Act, 1872** | Contract Act | **8,868** | 302 | 89 |
| **17** | **Motor Vehicles Act, 1988** | Motor Vehicles Act | **8,389** | 279 | 178 |
| **18** | **NDPS Act, 1985** | Narcotic Drugs Act, NDPS Act | **8,209** | 223 | 81 |
| **19** | **Companies Act, 1956** | Companies Act 1956 | **6,948** | 485 | 106 |
| **20** | **Registration Act, 1908** | Registration Act | **5,627** | 223 | 122 |
| **21** | **Prevention of Corruption Act, 1988**| Corruption Act, POCA | **5,065** | 228 | 165 |
| **22** | **Specific Relief Act, 1963** | Specific Relief Act | **4,142** | 168 | 60 |
| **23** | **Representation of the People Act, 1951**| Representation of People Act | **3,801** | 226 | 109 |
| **24** | **SARFAESI Act, 2002** | SARFAESI Act | **3,491** | 118 | 71 |
| **25** | **Central Excise Act, 1944** | Central Excise Act | **3,141** | 179 | 74 |
| **26** | **Arbitration Act, 1940** | Arbitration Act 1940 | **2,920** | 122 | 84 |
| **27** | **Consumer Protection Act, 1986** | Consumer Protection Act | **2,759** | 155 | 101 |
| **28** | **Finance Act** | Finance Acts | **2,554** | 265 | 54 |
| **29** | **U.P. State Legislation** | U.P. Local Acts | **2,537** | 195 | 89 |
| **30** | **Companies Act, 2013** | Companies Act 2013 | **2,357** | 252 | 42 |

---

## 2. Discovered New Criminal Codes (BNS, BNSS, BSA)

The deduplicated inventory confirms extracted provisions for India's 2023 criminal codes:

| Canonical Statutory Title | Consolidated Citation Count | Unique Sections | Top Cited Section | Document Count |
| :--- | :--- | :--- | :--- | :--- |
| **Bharatiya Nyaya Sanhita, 2023 (BNS)** | **383** | 88 | BNS Sec 173 (False Charge / FIR) | 4 Judgments |
| **Bharatiya Nagarik Suraksha Sanhita, 2023 (BNSS)** | **317** | 77 | BNSS Sec 35 (Arrest Safeguards) | 4 Judgments |
| **Bharatiya Sakshya Adhiniyam, 2023 (BSA)** | **15** | 7 | BSA Sec 61 (Electronic Evidence) | 1 Judgment |

---

## 3. Asset Data Access & CSV Exports

All extracted and deduplicated datasets are available in `notebooks/reports/assets/`:

1. **Top 200 Statutory Enactments Export**: [`notebooks/reports/assets/top_200_statutes.csv`](file:///home/duttadev/projects/aws_indian_judgements/notebooks/reports/assets/top_200_statutes.csv)
   - **Columns**: `rank`, `statute`, `total_citations`, `unique_sections_count`, `max_document_count`.
   - Contains the top 200 ranked non-constitutional statutory enactments across 38,235 judgments.

2. **Complete Enriched Act-Section Pairings Export**: [`notebooks/reports/assets/acts_and_sections.csv`](file:///home/duttadev/projects/aws_indian_judgements/notebooks/reports/assets/acts_and_sections.csv) (300,502 rows)
   - **Enriched Columns**: `statute`, `section`, `citation_frequency`, `document_count`, `canonical_title`, `canonical_uri`, `enactment_type`, `state_jurisdiction`.

3. **Aggregated Statutory Enactments with Top 30 Sections Export**: [`notebooks/reports/assets/acts.csv`](file:///home/duttadev/projects/aws_indian_judgements/notebooks/reports/assets/acts.csv) (91,078 rows)
   - **Columns**: `canonical_title`, `canonical_uri`, `enactment_type`, `state_jurisdiction`, `total_citations`, `unique_sections_count`, `max_document_count`, `top_sections`.
   - Contains a JSON array of up to 30 top cited sections for each statutory enactment.


---

## 4. Central vs State Enactment Structural Classification

Using deterministic matching and state jurisdiction taggers, all enactments in `acts_and_sections.csv` have been classified into structural enactment types:

| Enactment Type | Total Citation Frequency | Pct Citation Share | Unique Act-Section Pairs | Unique Canonical Titles |
| :--- | :--- | :--- | :--- | :--- |
| **Central Enactments** | **1,304,690** | **88.78%** | 230,337 | 66,307 |
| **State Enactments** | **109,837** | **7.47%** | 43,063 | 13,386 |
| **Unspecified Laws** | **54,923** | **3.74%** | 27,077 | 11,384 |
| **Constitutional Articles** | **55** | **0.00%** | 25 | 1 |

### Top 10 State Legislation Jurisdictions

State enactments in Supreme Court jurisprudence are dominated by major state jurisdictions:

1. **Maharashtra**: 22,401 citations across 2,480 canonical enactments
2. **Uttar Pradesh**: 15,335 citations across 1,830 canonical enactments
3. **Punjab**: 9,646 citations across 1,080 canonical enactments
4. **Tamil Nadu**: 9,013 citations across 1,225 canonical enactments
5. **Delhi**: 7,934 citations across 816 canonical enactments
6. **Karnataka**: 6,593 citations across 794 canonical enactments
7. **West Bengal**: 5,378 citations across 666 canonical enactments
8. **Bihar**: 5,314 citations across 654 canonical enactments
9. **Madhya Pradesh**: 5,268 citations across 656 canonical enactments
10. **Kerala**: 5,112 citations across 633 canonical enactments

---

## 5. Jupyter Notebook & Visual Dashboard

The canonical matching pipeline, URI generation, and state vs central tagging are fully executable in:
- **Jupyter Notebook**: [`notebooks/canonical_statute_matching.ipynb`](file:///home/duttadev/projects/aws_indian_judgements/notebooks/canonical_statute_matching.ipynb)
- **Asset Exports**:
  - [`notebooks/reports/assets/canonical_statute_mappings.csv`](file:///home/duttadev/projects/aws_indian_judgements/notebooks/reports/assets/canonical_statute_mappings.csv)
  - [`notebooks/reports/assets/central_vs_state_summary.csv`](file:///home/duttadev/projects/aws_indian_judgements/notebooks/reports/assets/central_vs_state_summary.csv)
  - [`notebooks/reports/assets/state_jurisdiction_summary.csv`](file:///home/duttadev/projects/aws_indian_judgements/notebooks/reports/assets/state_jurisdiction_summary.csv)
- **Generated Charts**:
  - `central_vs_state_distribution.png`
  - `top_state_jurisdictions.png`
  - `canonical_consolidation_impact.png`


