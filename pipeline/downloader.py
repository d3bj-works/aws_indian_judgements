import os
import requests
from typing import Tuple

class PDFDownloader:
    """
    Downloads PDFs from AWS Open Data S3 endpoint and validates PDF integrity.
    """
    
    def __init__(self, s3_base_url: str = "https://indian-supreme-court-judgments.s3.amazonaws.com"):
        self.s3_base_url = s3_base_url.rstrip("/")

    def download_pdf(self, s3_key: str, dest_path: str, timeout: int = 15) -> Tuple[bool, str]:
        """
        Downloads a PDF from S3 key to dest_path.
        Returns (success: bool, message: str)
        """
        if s3_key.startswith("http://") or s3_key.startswith("https://"):
            url = s3_key
        else:
            url = f"{self.s3_base_url}/{s3_key.lstrip('/')}"
            
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        try:
            response = requests.get(url, stream=True, timeout=timeout)
            if response.status_code != 200:
                return False, f"HTTP Error {response.status_code} fetching {url}"
            
            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        
            return True, "Download successful"
        except Exception as e:
            return False, f"Download failed: {str(e)}"

    def validate_pdf(self, file_path: str) -> Tuple[bool, str]:
        """
        Validates whether file exists, is non-empty, and has valid PDF magic header.
        """
        if not os.path.exists(file_path):
            return False, "File does not exist"
            
        file_size = os.path.getsize(file_path)
        if file_size < 100:  # Valid PDFs are almost always > 100 bytes
            return False, f"PDF file too small ({file_size} bytes)"
            
        try:
            with open(file_path, "rb") as f:
                header = f.read(5)
                if not header.startswith(b"%PDF-"):
                    return False, f"Invalid PDF header: {header!r}"
            return True, "Valid PDF"
        except Exception as e:
            return False, f"PDF validation error: {str(e)}"
