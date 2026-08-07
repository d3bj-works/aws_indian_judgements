import pymupdf as fitz
from pipeline.extractors.base import BaseTextExtractor, ExtractionResult

class PyMuPDFTextExtractor(BaseTextExtractor):
    """
    Searchable PDF text extractor using PyMuPDF (fitz).
    High performance C-backed PDF parsing.
    """
    
    def extract_text(self, pdf_path: str) -> ExtractionResult:
        doc = fitz.open(pdf_path)
        page_count = len(doc)
        text_pages = []
        
        for page in doc:
            text_pages.append(page.get_text())

        full_text = "\n\n".join(text_pages)
        doc_metadata = doc.metadata or {}
        doc.close()
        
        words = full_text.split()
        
        return ExtractionResult(
            raw_text=full_text,
            page_count=page_count,
            char_count=len(full_text),
            word_count=len(words),
            metadata=doc_metadata
        )
