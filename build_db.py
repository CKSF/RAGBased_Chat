import os
import sys
import shutil
import time
import importlib.util

def build_knowledge_base():
    print("\n" + "="*50)
    print("🚀 STARTING DATABASE BUILD (Ghost-Free Mode)")
    print("="*50)

    # 1. CLEANUP
    print("🧹 [Step 1] Cleaning up old database...")
    if os.path.exists("chroma_db"):
        try:
            shutil.rmtree("chroma_db")
            print("   -> Removed chroma_db")
        except OSError as e:
            print(f"   ⚠️ Could not delete chroma_db: {e}")
            
    if os.path.exists("doc_store"):
        shutil.rmtree("doc_store", ignore_errors=True)
        print("   -> Removed doc_store")

    # 2. INIT (The "Sniper" Import)
    print("\n🚀 [Step 2] Initializing RAG Service...")
    try:
        # Load PDFService manually
        pdf_spec = importlib.util.spec_from_file_location("pdf_service", "backend/app/services/pdf_service.py")
        pdf_module = importlib.util.module_from_spec(pdf_spec)
        pdf_spec.loader.exec_module(pdf_module)
        PDFService = pdf_module.PDFService

        # Load RAGService manually (Bypassing package __init__!)
        rag_spec = importlib.util.spec_from_file_location("rag_service", "backend/app/services/rag_service.py")
        rag_module = importlib.util.module_from_spec(rag_spec)
        rag_spec.loader.exec_module(rag_module)
        RAGService = rag_module.RAGService
        
        # Now instantiate
        rag = RAGService(persist_directory="chroma_db", parent_store_directory="doc_store")
        
    except Exception as e:
        print(f"❌ CRITICAL ERROR initializing RAG: {e}")
        import traceback
        traceback.print_exc()
        return

    # 3. SCAN & INDEX
    data_dir = "data"
    if not os.path.exists(data_dir):
        print(f"❌ Error: Data directory '{data_dir}' not found.")
        return

    files = [f for f in os.listdir(data_dir) if f.lower().endswith(".pdf")]
    print(f"\n📂 [Step 3] Scanning '{data_dir}': Found {len(files)} PDFs.")
    
    success_count = 0
    
    for i, filename in enumerate(files):
        print(f"\n--- Processing File {i+1}/{len(files)}: {filename} ---")
        file_path = os.path.join(data_dir, filename)
        absolute_path = os.path.abspath(file_path)
        
        try:
            print("   [1/3] Extracting text...", end=" ", flush=True)
            start_time = time.time()
            text = PDFService.extract_text(absolute_path)
            duration = time.time() - start_time
            print(f"Done ({duration:.2f}s)")

            if not text:
                print("   ⚠️ [WARN] Extracted text is empty. Skipping.")
                continue
            
            print(f"   [2/3] Got {len(text)} characters.")
            print("   [3/3] Sending to ChromaDB...", end=" ", flush=True)
            
            rag.add_documents(text, metadata={"source": filename})
            print("Done.")
            success_count += 1
            
        except Exception as e:
            print(f"\n   ❌ [ERROR] Failed processing {filename}")
            print(f"   Error details: {e}")

    # 4. FINAL VERIFICATION
    print("\n" + "="*50)
    print(f"🎉 Build Finished! Successfully processed {success_count}/{len(files)} files.")
    
    if os.path.exists("chroma_db/chroma.sqlite3"):
        print("   ✅ chroma.sqlite3 found.")
    else:
        print("   ❌ chroma.sqlite3 NOT found. Persistence failed.")
    print("="*50)

if __name__ == "__main__":
    build_knowledge_base()