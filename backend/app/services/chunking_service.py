try:
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
from typing import List

class ChunkingService:
    def __init__(self, chunk_size: int = 500, chunk_overlap: int = 50):
        """
        Initialize the ChunkingService.
        
        Args:
            chunk_size (int): The maximum size of each chunk.
            chunk_overlap (int): The amount of overlap between chunks.
        """
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", "。", "！", "？", " ", ""]
        )

    def split_text(self, text: str) -> List[str]:
        """
        Split text into chunks.
        
        Args:
            text (str): The input text to split.
            
        Returns:
            List[str]: A list of text chunks.
        """
        if not text:
            return []
        return self.text_splitter.split_text(text)
