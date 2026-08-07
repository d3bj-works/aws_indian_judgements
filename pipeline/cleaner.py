import re
import unicodedata
from typing import List, Dict, Any

class TextCleaner:
    """
    Cleans raw extracted text from court judgments with NFKC normalization,
    ligature repair, page noise stripping, and paragraph offset preservation.
    """
    
    LIGATURE_MAP = {
        "ﬁ": "fi",
        "ﬂ": "fl",
        "æ": "ae",
        "Æ": "AE",
        "œ": "oe",
        "Œ": "OE",
        "ﬀ": "ff",
        "ﬃ": "ffi",
        "ﬄ": "ffl",
    }
    
    @staticmethod
    def clean_text(raw_text: str) -> str:
        if not raw_text:
            return ""
            
        # 1. Unicode NFKC Normalization
        text = unicodedata.normalize("NFKC", raw_text)
        
        # 2. Ligature Replacement
        for lig, rep in TextCleaner.LIGATURE_MAP.items():
            text = text.replace(lig, rep)
        
        # 3. Normalize line endings
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        
        # 4. Remove null bytes and non-printable control characters (except newline, tab)
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
        
        # 5. Remove Page Header/Footer noise patterns (e.g., "SUPREME COURT REPORTS [2023] 4 S.C.R.")
        text = re.sub(r'(?i)^\s*(?:SUPREME COURT REPORTS|INDIAN LAW REPORTS|ALL INDIA REPORTER)\s*(?:\[\d{4}\].*|\d+.*)?$', '', text, flags=re.MULTILINE)
        text = re.sub(r'^\s*\[\d{4}\]\s+\d+\s+S\.C\.R\.\s*$', '', text, flags=re.MULTILINE)
        
        # 6. Fix hyphenated words broken across lines e.g. "judg-\nment" -> "judgment"
        text = re.sub(r'(\w+)-\n(\w+)', r'\1\2', text)
        
        # 7. Replace 3+ consecutive newlines with 2 newlines (preserve paragraph spacing)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # 8. Trim trailing whitespace per line
        lines = [line.rstrip() for line in text.split('\n')]
        
        return "\n".join(lines).strip()

    @staticmethod
    def is_english_key(s3_key: str) -> bool:
        """
        Returns True if S3 key represents an English judgment PDF.
        Excludes vernacular translation tags (e.g. _HI, _BN, _TA, _TE, _MR, _KN, _ML, _OR, _GU, _PA).
        """
        key_lower = s3_key.lower()
        non_english_suffixes = ("_hi.pdf", "_bn.pdf", "_ta.pdf", "_te.pdf", "_mr.pdf", "_kn.pdf", "_ml.pdf", "_or.pdf", "_gu.pdf", "_pa.pdf", "_ur.pdf")
        if any(key_lower.endswith(s) for s in non_english_suffixes):
            return False
        if "/hindi/" in key_lower or "/bengali/" in key_lower or "/marathi/" in key_lower or "/tamil/" in key_lower:
            return False
        return True

    @staticmethod
    def is_english_text(text: str, min_ascii_ratio: float = 0.80) -> bool:
        """
        Verifies if extracted text is primarily English (latin ASCII script).
        Returns False for non-English translated judgments.
        """
        if not text or len(text) < 50:
            return True
        ascii_chars = sum(1 for c in text[:2000] if ord(c) < 128)
        ratio = ascii_chars / min(2000, len(text))
        return ratio >= min_ascii_ratio

    @staticmethod
    def extract_paragraphs(cleaned_text: str) -> List[Dict[str, Any]]:

        """
        Splits cleaned text into paragraphs, computing character start/end offsets.
        """
        paragraphs = []
        if not cleaned_text:
            return paragraphs

        blocks = cleaned_text.split("\n\n")
        current_offset = 0

        for idx, block in enumerate(blocks):
            block_len = len(block)
            start_offset = cleaned_text.find(block, current_offset)
            if start_offset == -1:
                start_offset = current_offset
            end_offset = start_offset + block_len

            paragraphs.append({
                "index": idx,
                "text": block,
                "start": start_offset,
                "end": end_offset
            })
            current_offset = end_offset + 2

        return paragraphs

