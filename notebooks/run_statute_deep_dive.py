import os
import re
import json
import duckdb
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Set style for publication-ready plots
plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
plt.rcParams['font.family'] = 'DejaVu Sans'
plt.rcParams['font.size'] = 10
plt.rcParams['axes.titlesize'] = 13
plt.rcParams['axes.titleweight'] = 'bold'
plt.rcParams['axes.labelsize'] = 11
plt.rcParams['axes.labelweight'] = 'bold'
plt.rcParams['xtick.labelsize'] = 10
plt.rcParams['ytick.labelsize'] = 10
plt.rcParams['figure.titlesize'] = 14

DATA_DIR = "data/supreme_court/parquet"
REPORTS_DIR = "notebooks/reports"
ASSETS_DIR = "notebooks/reports/assets"
os.makedirs(ASSETS_DIR, exist_ok=True)

con = duckdb.connect()

print("1. Querying Overall Statute Volume & Pareto Distribution...")
statute_summary = con.execute(f"""
    SELECT 
        COALESCE(canonical, matched) as statute_name,
        COUNT(*) as citation_count,
        COUNT(DISTINCT case_id) as doc_count
    FROM '{DATA_DIR}/entities.parquet'
    WHERE type = 'statute' OR type = 'article'
    GROUP BY statute_name
    ORDER BY citation_count DESC
""").df()

# Compute Pareto totals
total_citations = statute_summary['citation_count'].sum()
statute_summary['cum_citations'] = statute_summary['citation_count'].cumsum()
statute_summary['cum_pct'] = (statute_summary['cum_citations'] / total_citations) * 100

print(f"Total Statute/Article Citations: {total_citations:,}")
print(f"Total Unique Statute Enactments: {len(statute_summary):,}")

# --- 2. Legal Domain Categorization ---
print("2. Categorizing Legal Domains...")
def categorize_statute(name):
    if not isinstance(name, str):
        return "Other Special Laws"
    n = name.lower()
    if 'constitution' in n or 'article' in n:
        return "Constitutional & Administrative Law"
    elif any(k in n for k in ['penal', 'ipc', 'criminal', 'crpc', 'evidence', 'nyaya', 'nagarik', 'sakshya', 'bns', 'bnss', 'bsa', 'ndps', 'corruption', 'pocso', 'pmla', 'police', 'terrorist', 'tada', 'pota', 'sc/st', 'scheduled caste']):
        return "Criminal & Penal Jurisprudence"
    elif any(k in n for k in ['civil procedure', 'cpc', 'limitation', 'specific relief', 'court fees', 'arbitration']):
        return "Civil Procedure & Dispute Resolution"
    elif any(k in n for k in ['income tax', 'excise', 'customs', 'wealth tax', 'gst', 'tax', 'sales tax', 'vat', 'stamp']):
        return "Taxation & Revenue Law"
    elif any(k in n for k in ['company', 'companies', 'insolvency', 'bankruptcy', 'ibc', 'negotiable', 'cheque', 'contract', 'sarfaesi', 'banking', 'sebi', 'consumer']):
        return "Commercial, Corporate & Banking"
    elif any(k in n for k in ['industrial', 'labour', 'labor', 'workmen', 'workman', 'factories', 'service', 'administrative tribunal', 'pension', 'provident']):
        return "Labor, Employment & Service Law"
    elif any(k in n for k in ['land acquisition', 'rent', 'forest', 'environment', 'motor vehicles', 'electricity', 'property', 'transfer of property', 'town planning']):
        return "Property, Land & Environmental Laws"
    else:
        return "Other Special Laws"

statute_summary['domain'] = statute_summary['statute_name'].apply(categorize_statute)

domain_df = statute_summary.groupby('domain').agg(
    citation_count=('citation_count', 'sum'),
    unique_statutes=('statute_name', 'count')
).reset_index().sort_values('citation_count', ascending=False)

domain_df['pct_share'] = (domain_df['citation_count'] / total_citations) * 100
domain_df.to_csv(f"{ASSETS_DIR}/statute_domain_distribution.csv", index=False)
print("Domain Breakdown:\n", domain_df.to_string())

# --- 3. Top 25 Statutes & Top 10 Sections Hierarchy ---
print("3. Profiling Top 25 Statutes & Top 10 Sections Each...")
top_25_statutes = statute_summary.head(25)['statute_name'].tolist()

top_sections_list = []
for stat in top_25_statutes:
    # Escape single quotes in statute name for SQL
    stat_clean = stat.replace("'", "''")
    sec_df = con.execute(f"""
        SELECT 
            normalized as section_name,
            matched as raw_matched,
            COUNT(*) as sec_citations
        FROM '{DATA_DIR}/entities.parquet'
        WHERE type = 'section'
          AND (statute = '{stat_clean}' OR canonical = '{stat_clean}')
          AND normalized IS NOT NULL AND normalized != ''
        GROUP BY normalized, raw_matched
        ORDER BY sec_citations DESC
        LIMIT 10
    """).df()
    
    stat_total = statute_summary[statute_summary['statute_name'] == stat]['citation_count'].values[0]
    
    for idx, row in sec_df.iterrows():
        top_sections_list.append({
            'statute': stat,
            'statute_total_citations': stat_total,
            'sec_rank': idx + 1,
            'section': row['section_name'],
            'matched_text': row['raw_matched'],
            'section_citations': row['sec_citations'],
            'pct_of_statute': round((row['sec_citations'] / stat_total) * 100, 2)
        })

hierarchy_df = pd.DataFrame(top_sections_list)
hierarchy_df.to_csv(f"{ASSETS_DIR}/top_25_statutes_hierarchy.csv", index=False)
print(f"Top 25 Statutes Hierarchy generated: {len(hierarchy_df)} section records.")

# --- 4. Detailed New Criminal Codes Spotlight (BNS, BNSS, BSA vs IPC, CrPC, IEA) ---
print("4. Conducting Spotlight Analysis on BNS, BNSS, BSA vs IPC, CrPC, IEA...")

new_codes_query = f"""
    SELECT 
        e.case_id,
        e.type,
        e.canonical,
        e.matched,
        e.normalized,
        e.statute,
        m.date,
        COALESCE(REGEXP_EXTRACT(m.date, '\\b(19\\d{{2}}|20\\d{{2}})\\b'), REGEXP_EXTRACT(m.document_id, '^(\\d{{4}})')) as year
    FROM '{DATA_DIR}/entities.parquet' e
    JOIN '{DATA_DIR}/metadata.parquet' m ON e.case_id = m.document_id
    WHERE LOWER(e.canonical) LIKE '%nyaya%'
       OR LOWER(e.canonical) LIKE '%nagarik%'
       OR LOWER(e.canonical) LIKE '%sakshya%'
       OR LOWER(e.canonical) LIKE '%bns%'
       OR LOWER(e.canonical) LIKE '%bnss%'
       OR LOWER(e.canonical) LIKE '%bsa%'
       OR LOWER(e.statute) LIKE '%nyaya%'
       OR LOWER(e.statute) LIKE '%nagarik%'
       OR LOWER(e.statute) LIKE '%sakshya%'
       OR LOWER(e.statute) LIKE '%bns%'
       OR LOWER(e.statute) LIKE '%bnss%'
       OR LOWER(e.statute) LIKE '%bsa%'
"""
new_codes_df = con.execute(new_codes_query).df()
new_codes_df.to_csv(f"{ASSETS_DIR}/bns_bnss_bsa_mentions.csv", index=False)

# Cross-Mapping Matrix: BNS vs IPC
bns_sections = con.execute(f"""
    SELECT 
        normalized as bns_section,
        matched as raw_text,
        COUNT(*) as citation_count
    FROM '{DATA_DIR}/entities.parquet'
    WHERE type = 'section'
      AND (LOWER(statute) LIKE '%nyaya%' OR LOWER(canonical) LIKE '%nyaya%')
    GROUP BY bns_section, raw_text
    ORDER BY citation_count DESC
""").df()

# Mapping dict for BNS -> IPC key offences
ipc_map = {
    '103': '302 (Murder)',
    '105': '304 (Culpable Homicide)',
    '109': '307 (Attempt to Murder)',
    '111': 'Organized Crime (New)',
    '112': 'Petty Organized Crime (New)',
    '113': 'Terrorist Act (New)',
    '64': '376 (Rape)',
    '318': '420 (Cheating)',
    '306': '379 (Theft)',
    '191': '147/149 (Rioting/Unlawful Assembly)',
    '356': '499/500 (Defamation)',
    '69': 'Deceitful Sexual Intercourse (New)',
    '173': 'Info to Police / FIR (BNSS 173 / CrPC 154)',
    '35': 'Arrest without Warrant (BNSS 35 / CrPC 41)',
    '223': 'Cognizance of Offence (BNSS 223 / CrPC 190)',
    '156': 'Police Investigation (BNSS 156 / CrPC 156)'
}

bns_sections['ipc_equivalent'] = bns_sections['bns_section'].astype(str).map(ipc_map).fillna('Legacy Mapping / Special Provision')
bns_sections.to_csv(f"{ASSETS_DIR}/bns_ipc_cross_mapping.csv", index=False)

# Compare Citation Volume Post-2023
criminal_transition = con.execute(f"""
    SELECT 
        COALESCE(REGEXP_EXTRACT(m.date, '\\b(202[3-6])\\b'), REGEXP_EXTRACT(m.document_id, '^(202[3-6])')) as year,
        CASE 
            WHEN LOWER(e.canonical) LIKE '%penal%' OR LOWER(e.canonical) LIKE '%ipc%' THEN 'IPC (1860)'
            WHEN LOWER(e.canonical) LIKE '%nyaya%' OR LOWER(e.canonical) LIKE '%bns%' THEN 'BNS (2023)'
            WHEN LOWER(e.canonical) LIKE '%criminal%' OR LOWER(e.canonical) LIKE '%crpc%' THEN 'CrPC (1973)'
            WHEN LOWER(e.canonical) LIKE '%nagarik%' OR LOWER(e.canonical) LIKE '%bnss%' THEN 'BNSS (2023)'
            WHEN LOWER(e.canonical) LIKE '%evidence%' OR LOWER(e.canonical) LIKE '%iea%' THEN 'IEA (1872)'
            WHEN LOWER(e.canonical) LIKE '%sakshya%' OR LOWER(e.canonical) LIKE '%bsa%' THEN 'BSA (2023)'
            ELSE 'Other'
        END as code_family,
        COUNT(*) as citations
    FROM '{DATA_DIR}/entities.parquet' e
    JOIN '{DATA_DIR}/metadata.parquet' m ON e.case_id = m.document_id
    WHERE year IS NOT NULL AND year != ''
    GROUP BY year, code_family
    HAVING code_family != 'Other'
    ORDER BY year, code_family
""").df()

criminal_transition.to_csv(f"{ASSETS_DIR}/criminal_code_transition_matrix.csv", index=False)

# --- 5. Inter-Statute Co-Occurrence Adjacency Matrix ---
print("5. Computing Inter-Statute Co-Occurrence Adjacency Matrix...")

cooc_query = f"""
    WITH case_statutes AS (
        SELECT DISTINCT 
            case_id, 
            CASE 
                WHEN LOWER(canonical) LIKE '%constitution%' THEN 'Constitution of India'
                WHEN LOWER(canonical) LIKE '%penal%' THEN 'Indian Penal Code, 1860'
                WHEN LOWER(canonical) LIKE '%civil procedure%' THEN 'Code of Civil Procedure, 1908'
                WHEN LOWER(canonical) LIKE '%criminal procedure%' THEN 'Code of Criminal Procedure, 1973'
                WHEN LOWER(canonical) LIKE '%evidence%' THEN 'Indian Evidence Act, 1872'
                WHEN LOWER(canonical) LIKE '%income tax%' THEN 'Income Tax Act, 1961'
                WHEN LOWER(canonical) LIKE '%arbitration%' THEN 'Arbitration and Conciliation Act, 1996'
                WHEN LOWER(canonical) LIKE '%company%' OR LOWER(canonical) LIKE '%companies%' THEN 'Companies Act, 1956'
                WHEN LOWER(canonical) LIKE '%limitation%' THEN 'Limitation Act, 1963'
                WHEN LOWER(canonical) LIKE '%negotiable%' THEN 'Negotiable Instruments Act, 1881'
                WHEN LOWER(canonical) LIKE '%nyaya%' THEN 'Bharatiya Nyaya Sanhita'
                WHEN LOWER(canonical) LIKE '%nagarik%' THEN 'Bharatiya Nagarik Suraksha Sanhita'
                ELSE NULL
            END as stat_group
        FROM '{DATA_DIR}/entities.parquet'
        WHERE type = 'statute' OR type = 'article'
    )
    SELECT 
        a.stat_group as statute_a,
        b.stat_group as statute_b,
        COUNT(DISTINCT a.case_id) as shared_cases
    FROM case_statutes a
    JOIN case_statutes b ON a.case_id = b.case_id AND a.stat_group != b.stat_group
    WHERE a.stat_group IS NOT NULL AND b.stat_group IS NOT NULL
    GROUP BY statute_a, statute_b
    ORDER BY shared_cases DESC
"""
cooc_df = con.execute(cooc_query).df()
cooc_df.to_csv(f"{ASSETS_DIR}/statute_cooccurrence_matrix.csv", index=False)

# --- 6. Decadal Evolution Trends ---
print("6. Computing Decadal Evolution Trends...")
decadal_df = con.execute(f"""
    SELECT 
        CASE 
            WHEN year BETWEEN '1950' AND '1959' THEN '1950s'
            WHEN year BETWEEN '1960' AND '1969' THEN '1960s'
            WHEN year BETWEEN '1970' AND '1979' THEN '1970s'
            WHEN year BETWEEN '1980' AND '1989' THEN '1980s'
            WHEN year BETWEEN '1990' AND '1999' THEN '1990s'
            WHEN year BETWEEN '2000' AND '2009' THEN '2000s'
            WHEN year BETWEEN '2010' AND '2019' THEN '2010s'
            WHEN year >= '2020' THEN '2020s'
            ELSE 'Unknown'
        END as decade,
        CASE 
            WHEN LOWER(canonical) LIKE '%constitution%' THEN 'Constitution of India'
            WHEN LOWER(canonical) LIKE '%penal%' THEN 'IPC / BNS'
            WHEN LOWER(canonical) LIKE '%civil procedure%' THEN 'CPC'
            WHEN LOWER(canonical) LIKE '%criminal procedure%' THEN 'CrPC / BNSS'
            WHEN LOWER(canonical) LIKE '%evidence%' THEN 'IEA / BSA'
            WHEN LOWER(canonical) LIKE '%income tax%' THEN 'Income Tax Act'
            WHEN LOWER(canonical) LIKE '%arbitration%' THEN 'Arbitration Act'
            ELSE 'Other Acts'
        END as statute_group,
        COUNT(*) as citations
    FROM (
        SELECT 
            e.canonical,
            COALESCE(REGEXP_EXTRACT(m.date, '\\b(19\\d{{2}}|20\\d{{2}})\\b'), REGEXP_EXTRACT(m.document_id, '^(\\d{{4}})')) as year
        FROM '{DATA_DIR}/entities.parquet' e
        JOIN '{DATA_DIR}/metadata.parquet' m ON e.case_id = m.document_id
        WHERE e.type = 'statute' OR e.type = 'article'
    ) sub
    WHERE decade != 'Unknown'
    GROUP BY decade, statute_group
    ORDER BY decade, citations DESC
""").df()

decadal_df.to_csv(f"{ASSETS_DIR}/statute_decadal_trends.csv", index=False)

# --- 7. Coram & Complexity Analysis ---
print("7. Computing Coram & Complexity Attributes by Statute Domain...")
complexity_df = con.execute(f"""
    WITH case_domains AS (
        SELECT DISTINCT 
            m.document_id,
            m.page_count,
            m.word_count,
            LEN(m.bench) as bench_size,
            CASE 
                WHEN LOWER(e.canonical) LIKE '%constitution%' THEN 'Constitutional Law'
                WHEN LOWER(e.canonical) LIKE '%penal%' OR LOWER(e.canonical) LIKE '%criminal%' OR LOWER(e.canonical) LIKE '%nyaya%' THEN 'Criminal Law'
                WHEN LOWER(e.canonical) LIKE '%civil procedure%' OR LOWER(e.canonical) LIKE '%limitation%' THEN 'Civil & Procedural Law'
                WHEN LOWER(e.canonical) LIKE '%company%' OR LOWER(e.canonical) LIKE '%arbitration%' OR LOWER(e.canonical) LIKE '%income tax%' THEN 'Commercial & Tax Law'
                ELSE 'Special Laws'
            END as primary_domain
        FROM '{DATA_DIR}/metadata.parquet' m
        JOIN '{DATA_DIR}/entities.parquet' e ON m.document_id = e.case_id
    )
    SELECT 
        primary_domain,
        COUNT(DISTINCT document_id) as total_judgments,
        ROUND(AVG(page_count), 2) as avg_pages,
        ROUND(AVG(word_count), 2) as avg_words,
        ROUND(AVG(bench_size), 2) as avg_bench_size,
        COUNT(CASE WHEN bench_size >= 5 THEN 1 END) as constitution_benches
    FROM case_domains
    GROUP BY primary_domain
    ORDER BY total_judgments DESC
""").df()

complexity_df.to_csv(f"{ASSETS_DIR}/statute_coram_complexity.csv", index=False)

# --- 8. Generate Publication-Quality Visualizations ---
print("8. Generating High-Resolution Charts...")

# Chart 1: Domain Distribution
fig, ax = plt.subplots(figsize=(10, 5))
sns.barplot(data=domain_df, x='pct_share', y='domain', palette='viridis', ax=ax)
ax.set_title("Supreme Court Statutory Citations by Legal Domain")
ax.set_xlabel("Percentage Share of Total Citations (%)")
ax.set_ylabel("")
for i, v in enumerate(domain_df['pct_share']):
    ax.text(v + 0.5, i, f"{v:.1f}% ({domain_df['citation_count'].iloc[i]:,})", va='center', fontweight='bold', fontsize=9)
plt.tight_layout()
plt.savefig(f"{ASSETS_DIR}/statute_domain_distribution.png", dpi=300)
plt.close()

# Chart 2: Top 15 Statutes Chart
top_15 = statute_summary.head(15)
fig, ax = plt.subplots(figsize=(10, 6))
sns.barplot(data=top_15, x='citation_count', y='statute_name', palette='crest', ax=ax)
ax.set_title("Top 15 Most Cited Statutory Enactments & Constitutional Provisions")
ax.set_xlabel("Total Extracted Citations")
ax.set_ylabel("")
for i, v in enumerate(top_15['citation_count']):
    ax.text(v + 2000, i, f"{v:,}", va='center', fontweight='bold', fontsize=9)
plt.tight_layout()
plt.savefig(f"{ASSETS_DIR}/top_25_statutes_chart.png", dpi=300)
plt.close()

# Chart 3: New Criminal Codes Spotlight Transition
fig, ax = plt.subplots(figsize=(9, 5))
new_codes_summary = new_codes_df.groupby(['canonical', 'type']).size().reset_index(name='count').sort_values('count', ascending=False).head(10)
sns.barplot(data=new_codes_summary, x='count', y='canonical', hue='type', palette='rocket', ax=ax)
ax.set_title("Bharatiya Nyaya Sanhita (BNS) & Nagarik Suraksha Sanhita (BNSS) Mentions")
ax.set_xlabel("Extraction Frequency in Supreme Court Judgments")
ax.set_ylabel("")
plt.tight_layout()
plt.savefig(f"{ASSETS_DIR}/bns_bnss_bsa_transition.png", dpi=300)
plt.close()

# Chart 4: BNS Top Sections
top_bns_sec = bns_sections.head(10)
fig, ax = plt.subplots(figsize=(9, 5))
sns.barplot(data=top_bns_sec, x='citation_count', y='bns_section', palette='mako', ax=ax)
ax.set_title("Top Cited Sections in Bharatiya Nyaya Sanhita / Nagarik Suraksha Sanhita")
ax.set_xlabel("Citation Frequency")
ax.set_ylabel("Section Number")
for i, row in top_bns_sec.iterrows():
    ax.text(row['citation_count'] + 0.3, i, f"Sec {row['bns_section']}: {row['ipc_equivalent']}", va='center', fontsize=9)
plt.tight_layout()
plt.savefig(f"{ASSETS_DIR}/bns_ipc_top_sections.png", dpi=300)
plt.close()

# Chart 5: Co-Occurrence Heatmap
pivot_cooc = cooc_df.pivot(index='statute_a', columns='statute_b', values='shared_cases').fillna(0)
fig, ax = plt.subplots(figsize=(10, 8))
sns.heatmap(pivot_cooc, annot=True, fmt=',.0f', cmap='YlGnBu', cbar=True, ax=ax)
ax.set_title("Statutory Co-Occurrence Matrix (Shared Case Count)")
plt.xticks(rotation=45, ha='right')
plt.tight_layout()
plt.savefig(f"{ASSETS_DIR}/statute_cooccurrence_heatmap.png", dpi=300)
plt.close()

# Chart 6: Decadal Trends
decadal_pivot = decadal_df.pivot(index='decade', columns='statute_group', values='citations').fillna(0)
fig, ax = plt.subplots(figsize=(11, 6))
decadal_pivot.plot(kind='line', marker='o', linewidth=2, ax=ax)
ax.set_title("Decadal Evolution of Major Statutory Citation Volume (1950s–2020s)")
ax.set_xlabel("Decade")
ax.set_ylabel("Total Citations")
ax.legend(title="Statute Group", bbox_to_anchor=(1.05, 1), loc='upper left')
plt.tight_layout()
plt.savefig(f"{ASSETS_DIR}/statute_decadal_trends.png", dpi=300)
plt.close()

print("Charts successfully saved in notebooks/reports/assets/!")

# --- 9. Generate Executable Jupyter Notebook (`notebooks/statute_deep_dive.ipynb`) ---
print("9. Creating notebooks/statute_deep_dive.ipynb...")
nb_cells = [
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "# Step 3: Comprehensive Statute Deep Dive & New Criminal Codes Spotlight\n",
            "**Corpus Scope**: 38,235 Supreme Court Judgments (1950–2026)  \n",
            "**Statutory Citations Analyzed**: 2,065,319 Legal Enactments & Provisions  \n",
            "**Primary Focus**: Full Statutory Spectrum & Spotlight Transition to **BNS, BNSS, BSA**"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "import os\n",
            "import duckdb\n",
            "import pandas as pd\n",
            "import numpy as np\n",
            "import matplotlib.pyplot as plt\n",
            "import seaborn as sns\n",
            "\n",
            "con = duckdb.connect()\n",
            "DATA_DIR = '../data/supreme_court/parquet'\n",
            "ASSETS_DIR = 'reports/assets'\n",
            "print('DuckDB connected. Parquet dataset ready.')"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 1. Legal Domain Categorization & Citation Shares"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "domain_df = pd.read_csv(f'{ASSETS_DIR}/statute_domain_distribution.csv')\n",
            "domain_df"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 2. Top 25 Statutes & Section Hierarchies"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "hierarchy_df = pd.read_csv(f'{ASSETS_DIR}/top_25_statutes_hierarchy.csv')\n",
            "hierarchy_df.head(20)"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 3. Dedicated Spotlight: Bharatiya Nyaya Sanhita (BNS), BNSS & BSA Transition"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "bns_cross = pd.read_csv(f'{ASSETS_DIR}/bns_ipc_cross_mapping.csv')\n",
            "bns_cross.head(15)"
        ]
    },
    {
        "cell_type": "markdown",
        "metadata": {},
        "source": [
            "## 4. Statutory Co-Occurrence Matrix"
        ]
    },
    {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {},
        "outputs": [],
        "source": [
            "cooc_df = pd.read_csv(f'{ASSETS_DIR}/statute_cooccurrence_matrix.csv')\n",
            "cooc_df.head(15)"
        ]
    }
]

notebook_json = {
    "cells": nb_cells,
    "metadata": {
        "language_info": {"name": "python"},
        "orig_nbformat": 4
    },
    "nbformat": 4,
    "nbformat_minor": 2
}

with open("notebooks/statute_deep_dive.ipynb", "w") as f:
    json.dump(notebook_json, f, indent=2)

print("notebooks/statute_deep_dive.ipynb created.")

print("All calculations and asset generation completed successfully!")
