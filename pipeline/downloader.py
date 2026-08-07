import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Tuple, Optional

class PDFDownloader:
    """
    Downloads PDFs from AWS Open Data S3 endpoint and validates PDF integrity.
    Uses persistent connection pooling (HTTP Keep-Alive) and retries for maximum network throughput.
    """
    
    def __init__(
        self, 
        s3_base_url: str = "https://indian-supreme-court-judgments.s3.amazonaws.com",
        session: Optional[requests.Session] = None,
        pool_maxsize: int = 32
    ):
        self.s3_base_url = s3_base_url.rstrip("/")
        if session is not None:
            self.session = session
        else:
            self.session = requests.Session()
            adapter = HTTPAdapter(
                pool_connections=pool_maxsize,
                pool_maxsize=pool_maxsize,
                max_retries=Retry(
                    total=3,
                    backoff_factor=0.5,
                    status_forcelist=[500, 502, 503, 504],
                    raise_on_status=False
                )
            )
            self.session.mount("https://", adapter)
            self.session.mount("http://", adapter)

    def download_pdf(self, s3_key: str, dest_path: str, timeout: int = 15) -> Tuple[bool, str, int]:
        """
        Downloads a PDF from S3 key to dest_path using persistent connection pool.
        Returns (success: bool, message: str, file_size_bytes: int)
        """
        if s3_key.startswith("http://") or s3_key.startswith("https://"):
            url = s3_key
        else:
            url = f"{self.s3_base_url}/{s3_key.lstrip('/')}"
            
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        
        try:
            response = self.session.get(url, stream=True, timeout=timeout)
            if response.status_code != 200:
                return False, f"HTTP Error {response.status_code} fetching {url}", 0
            
            file_size = 0
            with open(dest_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=65536):
                    if chunk:
                        f.write(chunk)
                        file_size += len(chunk)
                        
            return True, "Download successful", file_size
        except Exception as e:
            return False, f"Download failed: {str(e)}", 0



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
