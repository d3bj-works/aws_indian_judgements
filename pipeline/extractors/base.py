from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class ExtractionResult:
    raw_text: str
    page_count: int
    char_count: int
    word_count: int
    metadata: Dict[str, Any]

class BaseTextExtractor(ABC):
    """
    Abstract base class for PDF text extraction.
    Phase 1 implements PyMuPDF for searchable PDFs.
    Phase 2 will implement OCR / layout analysis engines extending this same interface.
    """
    
    @abstractmethod
    def extract_text(self, pdf_path: str) -> ExtractionResult:
        """Extract text and basic structural metadata from a PDF file."""
        pass
