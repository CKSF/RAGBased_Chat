from backend.app.services.pdf_service import PDFService
from backend.app.services.chunking_service import ChunkingService
from backend.app.services.rag_service import RAGService
from backend.app.services.llm_service import LLMService

# Global Service Instances (Singletons)
# RAGService loads models, so we only want one instance.
print("🔄 Initializing RAG Service implementation...")
rag_service = RAGService(persist_directory="chroma_db", parent_store_directory="doc_store")

print("🔄 Initializing LLM Service...")
llm_service = LLMService()

# Export classes and instances
__all__ = [
    "PDFService",
    "ChunkingService",
    "RAGService", "rag_service",
    "LLMService", "llm_service"
]
