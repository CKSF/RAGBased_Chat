import os
import sys
import shutil
import time
import importlib.util

def build_knowledge_base():
    print("\n" + "="*50)
    print("🚀 STARTING DATABASE BUILD (Progress Bar Mode)")
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

    # 2. INIT
    print("\n🚀 [Step 2] Initializing RAG Service...")
    try:
        # Load PDFService manually
        pdf_spec = importlib.util.spec_from_file_location("pdf_service", "backend/app/services/pdf_service.py")
        pdf_module = importlib.util.module_from_spec(pdf_spec)
        pdf_spec.loader.exec_module(pdf_module)
        PDFService = pdf_module.PDFService

        # Load RAGService manually
        rag_spec = importlib.util.spec_from_file_location("rag_service", "backend/app/services/rag_service.py")
        rag_module = importlib.util.module_from_spec(rag_spec)
        rag_spec.loader.exec_module(rag_module)
        RAGService = rag_module.RAGService
        
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
            text = PDFService.extract_text(absolute_path)
            print("Done.")

            if not text:
                print("   ⚠️ [WARN] Extracted text is empty. Skipping.")
                continue
            
            total_chars = len(text)
            print(f"   [2/3] Total Length: {total_chars} characters.")
            
            # --- THE NEW BATCHING LOGIC ---
            print(f"   [3/3] Sending to ChromaDB in batches (to prevent freeze)...")
            
            # We split text into chunks of ~1000 chars to show progress
            # RAGService usually handles splitting, but this feed-in loop 
            # ensures we see progress and don't kill the CPU.
            batch_size = 1000 
            chunks = [text[i:i+batch_size] for i in range(0, len(text), batch_size)]
            total_batches = len(chunks)

            for b_idx, chunk in enumerate(chunks):
                # Print progress bar
                percent = ((b_idx + 1) / total_batches) * 100
                print(f"\r        Batch {b_idx+1}/{total_batches} [{percent:.1f}%] ...", end="", flush=True)
                
                # Send this small piece
                rag.add_documents(chunk, metadata={"source": filename})
                
                # Tiny sleep to let your CPU breathe (Prevents SSH freeze)
                time.sleep(0.05) 

            print("\n        ✅ File Completed.")
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