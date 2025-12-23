import os
import sys
import shutil
import time
import importlib.util

def detect_grade(filename: str) -> str:
    """
    Auto-detects grade level from filename.
    Returns: '小学', '初中', '高中', '大学', "硕士", "博士" or '通用'
    """
    fname = filename.lower()
    if any(k in fname for k in ["小学", "一年级", "二年级", "三年级", "四年级", "五年级", "六年级"]):
        return "小学"
    if any(k in fname for k in ["初中", "七年级", "八年级", "九年级"]):
        return "初中"
    if any(k in fname for k in ["高中", "高一", "高二", "高三"]):
        return "高中"
    if any(k in fname for k in ["大学", "本科"]):
        return "大学"
    if any(k in fname for k in ["研究生", "硕士"]):
        return "硕士"
    if any(k in fname for k in ["博士", "博士后"]):
        return "博士"
    
    return "通用"  # Default fallback

def build_knowledge_base():
    print("\n" + "="*50)
    print("🚀 STARTING DATABASE BUILD (With Metadata Tagging)")
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
        
        # Load DocxService
        docx_spec = importlib.util.spec_from_file_location("docx_service", "backend/app/services/docx_service.py")
        docx_module = importlib.util.module_from_spec(docx_spec)
        docx_spec.loader.exec_module(docx_module)
        DocxService = docx_module.DocxService

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

    files = [f for f in os.listdir(data_dir) if f.lower().endswith((".pdf", ".docx"))]
    print(f"\n📂 [Step 3] Scanning '{data_dir}': Found {len(files)} files.")
    
    success_count = 0
    
    for i, filename in enumerate(files):
        print(f"\n--- Processing File {i+1}/{len(files)}: {filename} ---")
        file_path = os.path.join(data_dir, filename)
        absolute_path = os.path.abspath(file_path)
        
        # [CRITICAL] Detect Grade
        grade_tag = detect_grade(filename)
        print(f"   🏷️  Detected Grade: [{grade_tag}]")
        
        try:
            print("   [1/3] Extracting text...", end=" ", flush=True)
            if filename.lower().endswith(".pdf"):
                text = PDFService.extract_text(absolute_path)
            elif filename.lower().endswith(".docx"):
                text = DocxService.extract_text(absolute_path)
            print("Done.")

            if not text:
                print("   ⚠️ [WARN] Extracted text is empty. Skipping.")
                continue
            
            total_chars = len(text)
            print(f"   [2/3] Total Length: {total_chars} characters.")
            
            print(f"   [3/3] Sending to ChromaDB in batches...")
            
            batch_size = 1000 
            chunks = [text[i:i+batch_size] for i in range(0, len(text), batch_size)]
            total_batches = len(chunks)

            for b_idx, chunk in enumerate(chunks):
                percent = ((b_idx + 1) / total_batches) * 100
                print(f"\r        Batch {b_idx+1}/{total_batches} [{percent:.1f}%] ...", end="", flush=True)
                
                # [CRITICAL] Inject Grade Metadata Here
                rag.add_documents(chunk, metadata={
                    "source": filename,
                    "grade": grade_tag  # <--- This saves the tag to the DB
                })
                
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