import re
from typing import List, Dict, Any

class CitationExtractor:
    """
    Extractor for Neutral Citations, Reporter Citations, and eCourts CNR Numbers.
    """

    NEUTRAL_PATTERNS = [
        (r"\b((?:19|20)\d{2})\s+INSC\s+(\d+)\b", "INSC Neutral Citation"),
        (r"\b((?:19|20)\d{2}):([A-Z]{2,4}):(\d+)\b", "High Court Neutral Citation"),
    ]

    REPORTER_PATTERNS = [
        r"\b\[(\d{4})\]\s+(\d+)\s+S\.C\.R\.\s+(\d+)\b",
        r"\b\((\d{4})\)\s+(\d+)\s+SCC\s+(\d+)\b",
        r"\bAIR\s+(\d{4})\s+SC\s+(\d+)\b",
        r"\b(\d{4})\s+(\d+)\s+(?:SCC|AIR|SCR|SCALE|CrLJ|MLJ|GLR)\s+(\d+)\b",
    ]

    CNR_PATTERN = r"\b[A-Z]{4}\d{12}\b"

    def extract(self, text: str, paragraphs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        extracted = []
        seen = set()

        for p in paragraphs:
            p_text = p["text"]
            p_idx = p["index"]
            p_start = p["start"]

            # 1. Neutral Citations
            for pattern, c_type in self.NEUTRAL_PATTERNS:
                for match in re.finditer(pattern, p_text):
                    matched_str = match.group(0)
                    key = (matched_str, p_idx, p_start + match.start())
                    if key in seen:
                        continue
                    seen.add(key)

                    extracted.append({
                        "type": "neutral_citation",
                        "canonical": matched_str,
                        "matched": matched_str,
                        "normalized": matched_str,
                        "statute": None,
                        "paragraph": p_idx,
                        "start": p_start + match.start(),
                        "end": p_start + match.end(),
                        "confidence": 1.0
                    })

            # 2. Reporter Citations
            for pattern in self.REPORTER_PATTERNS:
                for match in re.finditer(pattern, p_text):
                    matched_str = match.group(0)
                    key = (matched_str, p_idx, p_start + match.start())
                    if key in seen:
                        continue
                    seen.add(key)

                    extracted.append({
                        "type": "reporter_citation",
                        "canonical": matched_str,
                        "matched": matched_str,
                        "normalized": matched_str.replace("S.C.R.", "SCR"),
                        "statute": None,
                        "paragraph": p_idx,
                        "start": p_start + match.start(),
                        "end": p_start + match.end(),
                        "confidence": 0.95
                    })

            # 3. CNR Number
            for match in re.finditer(self.CNR_PATTERN, p_text):
                matched_str = match.group(0)
                key = (matched_str, p_idx, p_start + match.start())
                if key in seen:
                    continue
                seen.add(key)

                extracted.append({
                    "type": "cnr",
                    "canonical": matched_str,
                    "matched": matched_str,
                    "normalized": matched_str,
                    "statute": None,
                    "paragraph": p_idx,
                    "start": p_start + match.start(),
                    "end": p_start + match.end(),
                    "confidence": 1.0
                })

        return extracted
