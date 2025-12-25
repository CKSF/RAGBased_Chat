from typing import List, Dict, Any
import os
from pypdf import PdfReader

class PDFService:
    @staticmethod
    def extract_text(file_path: str) -> List[Dict[str, Any]]:
        """
        Extract text from a PDF file with page metadata.
        
        Args:
            file_path (str): Absolute path to the PDF file.
            
        Returns:
            List[Dict]: A list of dicts, each containing:
                - 'page_content': str
                - 'metadata': {'page': int}
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at: {file_path}")
            
        docs = []
        try:
            reader = PdfReader(file_path)
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text and page_text.strip():
                    docs.append({
                        "page_content": page_text.strip(),
                        "metadata": {"page": i + 1}
                    })
                    
            return docs
            
        except Exception as e:
            raise ValueError(f"Failed to read PDF: {str(e)}")
