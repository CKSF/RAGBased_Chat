import os
import sys
import shutil

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from backend.app.services.rag_service import RAGService
from backend.app.services.pdf_service import PDFService
from backend.app.services.chunking_service import ChunkingService

def build_knowledge_base():
    # 1. CLEANUP: Remove old DB to ensure fresh start
    print("🧹 Cleaning up old database...")
    if os.path.exists("chroma_db"):
        shutil.rmtree("chroma_db", ignore_errors=True)
    if os.path.exists("doc_store"):
        shutil.rmtree("doc_store", ignore_errors=True)

    # 2. INIT
    print("🚀 Initializing RAG Service (Parent Document Retriever)...")
    # Use the production DB folder name 'chroma_db'
    rag = RAGService(persist_directory="chroma_db", parent_store_directory="doc_store")
    
    # Define data source
    data_dir = "data"
    
    # 3. SCAN & INDEX
    print(f"📂 Scanning directory: {data_dir}")
    total_files = 0
    
    for filename in os.listdir(data_dir):
        if filename.lower().endswith(".pdf"):
            total_files += 1
            file_path = os.path.join(data_dir, filename)
            absolute_path = os.path.abspath(file_path)
            
            print(f"   Processing: {filename}...")
            
            try:
                # Extract
                text = PDFService.extract_text(absolute_path)
                if not text:
                    print("   [WARN] No text extracted. Skipping.")
                    continue
                    
                # Index (Pass the full text, RAGService handles splitting)
                print(f"     -> Indexing full text ({len(text)} chars)...")
                rag.add_documents(text, metadata={"source": filename})
                print("     -> Indexed successfully.")
                
            except Exception as e:
                print(f"   [ERROR] Failed to process file: {e}")

    print("\n" + "="*50)
    print(f"🎉 Build Complete!")
    print(f"Files Processed: {total_files}")
    print("Database saved to: ./chroma_db & ./doc_store")
    print("="*50)

if __name__ == "__main__":
    build_knowledge_base()
