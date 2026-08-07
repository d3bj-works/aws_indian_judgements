import re
from typing import Dict, Any

class MetadataExtractor:
    """
    Deterministic metadata extractor for Indian Supreme Court judgments.
    """
    
    def extract_metadata(self, text: str, page_count: int, doc_id: str = "") -> Dict[str, Any]:
        header_text = text[:3000] if text else ""
        
        # 1. Court Name
        court = "Supreme Court of India"
        if re.search(r"IN THE SUPREME COURT OF INDIA", header_text, re.IGNORECASE):
            court = "Supreme Court of India"
        elif re.search(r"HIGH COURT", header_text, re.IGNORECASE):
            match = re.search(r"HIGH COURT OF [A-Z\s]+", header_text, re.IGNORECASE)
            if match:
                court = match.group(0).strip()

        # 2. Citation
        citation = None
        cit_match = re.search(r"(?:CITATION|Citations?):\s*([^\n]+)", header_text, re.IGNORECASE)
        if not cit_match:
            cit_match = re.search(r"\b(\d{4}\s+AIR\s+\d+|\d{4}\s+SCC\s+\d+|\d{4}\s+INSC\s+\d+)\b", header_text, re.IGNORECASE)
        if cit_match:
            citation = cit_match.group(1).strip()

        # 3. Date of Judgment
        date_str = None
        date_match = re.search(r"(?:DATE OF JUDGMENT|DECIDED ON|DATED):\s*([^\n]+)", header_text, re.IGNORECASE)
        if not date_match:
            date_match = re.search(r"\b(\d{1,2}(?:st|nd|rd|th)?\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s*,\s*\d{4})\b", header_text, re.IGNORECASE)
        if date_match:
            date_str = date_match.group(1).strip()

        # 4. Bench / Judges
        bench = []
        bench_match = re.search(r"(?:BENCH|BEFORE|CORAM):\s*([^\n]+(?:\n[^\n]+){0,3})", header_text, re.IGNORECASE)
        if bench_match:
            raw_bench = bench_match.group(1)
            # Split by commas or 'AND' or newlines
            bench = [j.strip() for j in re.split(r'[,;\n]| AND ', raw_bench) if j.strip() and len(j.strip()) > 2]
            
        # 5. Parties (Petitioner vs Respondent)
        petitioner = None
        respondent = None
        
        vs_match = re.search(r"([A-Z0-9\s.,&()'\"-]+)\s+(?:v/s|vs\.?|VERSUS)\s+([A-Z0-9\s.,&()'\"-]+)", header_text, re.IGNORECASE)
        if vs_match:
            petitioner = vs_match.group(1).strip().replace("\n", " ")
            respondent = vs_match.group(2).strip().replace("\n", " ")
            
        case_title = f"{petitioner} vs {respondent}" if (petitioner and respondent) else doc_id

        return {
            "document_id": doc_id,
            "case_title": case_title,
            "court": court,
            "citation": citation,
            "date": date_str,
            "bench": bench,
            "petitioner": petitioner,
            "respondent": respondent,
            "page_count": page_count,
            "word_count": len(text.split()) if text else 0,
            "char_count": len(text) if text else 0
        }
