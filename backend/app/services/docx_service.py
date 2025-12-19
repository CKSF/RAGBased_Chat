import os
import docx  # from python-docx

class DocxService:
    @staticmethod
    def extract_text(file_path: str) -> str:
        """
        Extract text from a DOCX file.
        
        Args:
            file_path (str): Absolute path to the DOCX file.
            
        Returns:
            str: Extracted text content.
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"DOCX file not found at: {file_path}")
            
        text_content = []
        try:
            doc = docx.Document(file_path)
            
            # 1. Extract text from paragraphs
            for para in doc.paragraphs:
                if para.text.strip():
                    text_content.append(para.text.strip())
            
            # 2. (Optional) Extract text from tables if your docs have them
            for table in doc.tables:
                for row in table.rows:
                    row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                    if row_text:
                        text_content.append(" | ".join(row_text))

            return "\n\n".join(text_content)
            
        except Exception as e:
            raise ValueError(f"Failed to read DOCX: {str(e)}")