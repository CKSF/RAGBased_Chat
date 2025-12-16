import os
from pypdf import PdfReader

class PDFService:
    @staticmethod
    def extract_text(file_path: str) -> str:
        """
        Extract text from a PDF file.
        
        Args:
            file_path (str): Absolute path to the PDF file.
            
        Returns:
            str: Extracted text content.
            
        Raises:
            FileNotFoundError: If file does not exist.
            ValueError: If file is not a valid PDF or is encrypted.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"PDF file not found at: {file_path}")
            
        text_content = []
        try:
            reader = PdfReader(file_path)
            for i, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    # Basic cleaning: Remove excessive whitespace
                    clean_text = page_text.strip()
                    text_content.append(clean_text)
                    
            return "\n\n".join(text_content)
            
        except Exception as e:
            raise ValueError(f"Failed to read PDF: {str(e)}")
