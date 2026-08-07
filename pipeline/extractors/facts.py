import re
from typing import List, Dict, Any

class FactExtractor:
    """
    Extractor for Fact & Chronology Entities (Event Dates, Monetary Values, Annexure Markings, Coram/Judges).
    """

    DATE_PATTERNS = [
        r"\b\d{1,2}(?:st|nd|rd|th)?\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*,?\s*\d{4}\b",
        r"\b\d{1,2}[/\.-]\d{1,2}[/\.-]\d{2,4}\b",
    ]

    MONEY_PATTERN = r"\b(?:Rs\.?|INR)\s*[\d,]+(?:\.\d{2})?(?:\s*(?:lakhs?|lacs?|crores?|million|billion))?\b"
    ANNEXURE_PATTERN = r"\b(?:Annexure|Exhibit)\s+[A-Z0-9\-_]+\b"
    JUDGE_PATTERN = r"\b(?:Justice|Hon'ble(?:\s+Mr\.|\s+Mrs\.)?\s+Justice)\s+([A-Z][A-Za-z\.\s]+)\b"

    def extract(self, text: str, paragraphs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        extracted = []
        seen = set()

        for p in paragraphs:
            p_text = p["text"]
            p_idx = p["index"]
            p_start = p["start"]

            # 1. Event Dates
            for pattern in self.DATE_PATTERNS:
                for match in re.finditer(pattern, p_text, re.IGNORECASE):
                    matched_str = match.group(0).strip()
                    key = (matched_str, p_idx, p_start + match.start())
                    if key in seen:
                        continue
                    seen.add(key)

                    extracted.append({
                        "type": "date",
                        "canonical": matched_str,
                        "matched": matched_str,
                        "normalized": matched_str.replace("\n", " "),
                        "statute": None,
                        "paragraph": p_idx,
                        "start": p_start + match.start(),
                        "end": p_start + match.end(),
                        "confidence": 0.90
                    })

            # 2. Monetary Values
            for match in re.finditer(self.MONEY_PATTERN, p_text, re.IGNORECASE):
                matched_str = match.group(0).strip()
                key = (matched_str, p_idx, p_start + match.start())
                if key in seen:
                    continue
                seen.add(key)

                extracted.append({
                    "type": "monetary_value",
                    "canonical": matched_str,
                    "matched": matched_str,
                    "normalized": matched_str,
                    "statute": None,
                    "paragraph": p_idx,
                    "start": p_start + match.start(),
                    "end": p_start + match.end(),
                    "confidence": 0.85
                })

            # 3. Annexure Markings
            for match in re.finditer(self.ANNEXURE_PATTERN, p_text, re.IGNORECASE):
                matched_str = match.group(0).strip()
                key = (matched_str, p_idx, p_start + match.start())
                if key in seen:
                    continue
                seen.add(key)

                extracted.append({
                    "type": "annexure",
                    "canonical": matched_str,
                    "matched": matched_str,
                    "normalized": matched_str,
                    "statute": None,
                    "paragraph": p_idx,
                    "start": p_start + match.start(),
                    "end": p_start + match.end(),
                    "confidence": 0.90
                })

            # 4. Judges / Coram
            for match in re.finditer(self.JUDGE_PATTERN, p_text):
                matched_str = match.group(0).strip()
                judge_name = match.group(1).strip()
                if len(judge_name) < 3 or judge_name.lower() in ["and", "the", "court"]:
                    continue

                key = (matched_str, p_idx, p_start + match.start())
                if key in seen:
                    continue
                seen.add(key)

                extracted.append({
                    "type": "coram",
                    "canonical": f"Hon'ble Justice {judge_name}",
                    "matched": matched_str,
                    "normalized": judge_name,
                    "statute": None,
                    "paragraph": p_idx,
                    "start": p_start + match.start(),
                    "end": p_start + match.end(),
                    "confidence": 0.90
                })

        return extracted
