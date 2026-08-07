import re
from typing import Dict, List, Any, Optional

from pipeline.cleaner import TextCleaner
from pipeline.extractors.citations import CitationExtractor
from pipeline.extractors.statutes import StatutoryExtractor
from pipeline.extractors.facts import FactExtractor

class EntityExtractor:
    """
    Legal Entity Extractor for Indian Court Judgments compliant with Entity_Extraction.md specification.
    """

    def __init__(self):
        self.citation_extractor = CitationExtractor()
        self.statutory_extractor = StatutoryExtractor()
        self.fact_extractor = FactExtractor()

    def extract_entities(self, text: str, metadata: Optional[Dict[str, Any]] = None, doc_id: str = "", row_index: int = 0) -> Dict[str, Any]:
        if not text:
            return self._build_payload([], metadata, doc_id, row_index)

        # 1. Extract paragraph offsets
        paragraphs = TextCleaner.extract_paragraphs(text)

        # 2. Extract entities across submodules
        citation_entities = self.citation_extractor.extract(text, paragraphs)
        statutory_entities = self.statutory_extractor.extract(text, paragraphs)
        fact_entities = self.fact_extractor.extract(text, paragraphs)

        all_entities = citation_entities + statutory_entities + fact_entities

        # 3. Deduplicate & sort entities by paragraph and start character index
        deduped = []
        seen_keys = set()
        for ent in all_entities:
            key = (ent["type"], ent["matched"], ent["paragraph"], ent["start"])
            if key not in seen_keys:
                seen_keys.add(key)
                deduped.append(ent)

        deduped.sort(key=lambda x: (x["paragraph"], x["start"]))

        return self._build_payload(deduped, metadata, doc_id, row_index)

    def _build_payload(self, entities: List[Dict[str, Any]], metadata: Optional[Dict[str, Any]], doc_id: str, row_index: int) -> Dict[str, Any]:
        metadata = metadata or {}

        case_id = metadata.get("document_id") or doc_id
        title = metadata.get("case_title") or doc_id
        citation = metadata.get("citation") or ""
        court = metadata.get("court") or "Supreme Court of India"

        # Determine year from date, citation, or doc_id
        year = ""
        date_str = metadata.get("date") or ""
        year_match = re.search(r"\b(19\d{2}|20\d{2})\b", date_str or citation or doc_id)
        if year_match:
            year = year_match.group(1)

        return {
            "row_index": row_index,
            "case_id": case_id,
            "title": title,
            "citation": citation,
            "year": year,
            "court": court,
            "entities_count": len(entities),
            "entities": entities
        }
