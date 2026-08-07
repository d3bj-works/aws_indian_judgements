import re
from typing import List, Dict, Any, Optional

class StatutoryExtractor:
    """
    Extractor for Bare Acts, Statutory Sections, Articles, and Order/Rules.
    """

    KNOWN_ACTS = [
        ("Indian Penal Code", ["IPC", "Indian Penal Code, 1860", "Indian Penal Code"]),
        ("Code of Criminal Procedure", ["CrPC", "Code of Criminal Procedure, 1973", "Code of Criminal Procedure"]),
        ("Code of Civil Procedure", ["CPC", "Code of Civil Procedure, 1908", "Code of Civil Procedure"]),
        ("Indian Evidence Act", ["IEA", "Indian Evidence Act, 1872", "Indian Evidence Act"]),
        ("Bharatiya Nyaya Sanhita", ["BNS", "Bharatiya Nyaya Sanhita, 2023", "Bharatiya Nyaya Sanhita"]),
        ("Bharatiya Nagarik Suraksha Sanhita", ["BNSS", "Bharatiya Nagarik Suraksha Sanhita, 2023", "Bharatiya Nagarik Suraksha Sanhita"]),
        ("Bharatiya Sakshya Adhiniyam", ["BSB", "Bharatiya Sakshya Adhiniyam, 2023", "Bharatiya Sakshya Adhiniyam"]),
        ("Limitation Act", ["Limitation Act, 1963", "Limitation Act"]),
        ("Negotiable Instruments Act", ["NI Act", "Negotiable Instruments Act, 1881", "Negotiable Instruments Act"]),
        ("Constitution of India", ["Constitution of India", "Constitution"]),
    ]

    GENERIC_ACT_PATTERN = r"\b([A-Z][A-Za-z\s'\.,\-]+(?:Act|Code|Rules|Regulations|Order)(?:,\s*\d{4})?)\b"

    SECTION_PATTERN = r"\b(?:Sections?|Sec\.|ss\.|s\.)\s*(\d+[A-Z]?(?:\s*\([A-Z0-9]+\))*)(\s*,\s*\d+[A-Z]?(?:\s*\([A-Z0-9]+\))*)*\b"
    ARTICLE_PATTERN = r"\b(?:Articles?|Art\.)\s*(\d+[A-Z]?(?:\s*\([A-Z0-9]+\))*)\b"
    ORDER_RULE_PATTERN = r"\b(?:Order|O\.)\s*([I|V|X|L|C]+|\d+)\s*,?\s*(?:Rule|r\.)\s*(\d+)\b"

    def extract(self, text: str, paragraphs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        extracted = []
        seen = set()

        for p in paragraphs:
            p_text = p["text"]
            p_idx = p["index"]
            p_start = p["start"]

            # 1. Bare Act Extraction
            active_statute = self._find_active_statute(p_text)

            # Extract explicit Acts in paragraph
            for match in re.finditer(self.GENERIC_ACT_PATTERN, p_text):
                matched_str = match.group(0).strip()
                # Clean up noise lines
                if len(matched_str) < 5 or matched_str.startswith("The Act") or matched_str.startswith("This Act") or matched_str.startswith("under the Act"):
                    continue
                if "\n" in matched_str:
                    matched_str = " ".join(matched_str.split())

                canonical = self._canonicalize_act(matched_str)
                key = (matched_str, p_idx, p_start + match.start())
                if key in seen:
                    continue
                seen.add(key)

                extracted.append({
                    "type": "statute",
                    "canonical": canonical,
                    "matched": match.group(0),
                    "normalized": canonical,
                    "statute": canonical,
                    "paragraph": p_idx,
                    "start": p_start + match.start(),
                    "end": p_start + match.end(),
                    "confidence": 0.95
                })

            # 2. Section Extraction
            for match in re.finditer(self.SECTION_PATTERN, p_text, re.IGNORECASE):
                matched_str = match.group(0)
                sec_val = match.group(1).strip()
                canonical = f"Section {sec_val}"
                key = (matched_str, p_idx, p_start + match.start())
                if key in seen:
                    continue
                seen.add(key)

                extracted.append({
                    "type": "section",
                    "canonical": canonical,
                    "matched": matched_str,
                    "normalized": sec_val,
                    "statute": active_statute,
                    "paragraph": p_idx,
                    "start": p_start + match.start(),
                    "end": p_start + match.end(),
                    "confidence": 0.90
                })

            # 3. Article Extraction
            for match in re.finditer(self.ARTICLE_PATTERN, p_text, re.IGNORECASE):
                matched_str = match.group(0)
                art_val = match.group(1).strip()
                canonical = f"Article {art_val}"
                key = (matched_str, p_idx, p_start + match.start())
                if key in seen:
                    continue
                seen.add(key)

                extracted.append({
                    "type": "article",
                    "canonical": canonical,
                    "matched": matched_str,
                    "normalized": art_val,
                    "statute": "Constitution of India",
                    "paragraph": p_idx,
                    "start": p_start + match.start(),
                    "end": p_start + match.end(),
                    "confidence": 0.95
                })

            # 4. Order & Rule Extraction
            for match in re.finditer(self.ORDER_RULE_PATTERN, p_text, re.IGNORECASE):
                matched_str = match.group(0)
                order_num = match.group(1).strip()
                rule_num = match.group(2).strip()
                canonical = f"Order {order_num} Rule {rule_num}"
                norm = f"O.{order_num} R.{rule_num}"
                key = (matched_str, p_idx, p_start + match.start())
                if key in seen:
                    continue
                seen.add(key)

                extracted.append({
                    "type": "order_rule",
                    "canonical": canonical,
                    "matched": matched_str,
                    "normalized": norm,
                    "statute": active_statute or "Code of Civil Procedure, 1908",
                    "paragraph": p_idx,
                    "start": p_start + match.start(),
                    "end": p_start + match.end(),
                    "confidence": 0.90
                })

        return extracted

    def _canonicalize_act(self, act_str: str) -> str:
        for canonical, aliases in self.KNOWN_ACTS:
            for alias in aliases:
                if alias.lower() in act_str.lower():
                    return canonical
        return act_str

    def _find_active_statute(self, text: str) -> Optional[str]:
        for canonical, aliases in self.KNOWN_ACTS:
            for alias in aliases:
                if re.search(r"\b" + re.escape(alias) + r"\b", text, re.IGNORECASE):
                    return canonical
        return None
