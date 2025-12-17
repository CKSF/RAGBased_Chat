import os
import uuid
import json
from typing import List, Optional
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter

class SimpleFileStore:
    """A simple persistent key-value store for parent documents."""
    def __init__(self, directory: str):
        self.directory = directory
        if not os.path.exists(directory):
            os.makedirs(directory)
    
    def mset(self, key_value_pairs: List[tuple[str, Document]]):
        for key, doc in key_value_pairs:
            data = {
                "page_content": doc.page_content,
                "metadata": doc.metadata
            }
            with open(os.path.join(self.directory, f"{key}.json"), "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False)
                
    def mget(self, keys: List[str]) -> List[Document]:
        docs = []
        for key in keys:
            path = os.path.join(self.directory, f"{key}.json")
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    docs.append(Document(page_content=data["page_content"], metadata=data["metadata"]))
            else:
                print(f"   [FileStore] ⚠️ Missing file for key: {key}")
        return docs

class RAGService:
    def __init__(self, persist_directory: str = "chroma_db", parent_store_directory: str = "doc_store"):
        print(f"\n🟢 [RAG Init] Initializing RAG Service...")
        print(f"   [RAG Init] DB Directory: {os.path.abspath(persist_directory)}")
        
        # 1. Embedding Model
        print(f"   [RAG Init] Loading Embedding Model: shibing624/text2vec-base-chinese...")
        self.embeddings = HuggingFaceEmbeddings(
            model_name="shibing624/text2vec-base-chinese"
        )
        
        # 2. Splitters
        self.parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
        self.child_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
        
        # 3. Vector Store (Child Chunks)
        self.vector_store = Chroma(
            collection_name="split_parents", # CRITICAL: Must match build_db.py
            embedding_function=self.embeddings,
            persist_directory=persist_directory
        )
        
        # DEBUG: Check DB Health on Init
        try:
            # Note: This accesses internal Chroma API, strictly for debugging
            coll = self.vector_store._collection
            count = coll.count()
            print(f"   [RAG Init] ✅ Connected to ChromaDB. Collection '{coll.name}' has {count} chunks.")
            if count == 0:
                print("   [RAG Init] ⚠️ WARNING: Collection is EMPTY. Did build_db.py run correctly?")
        except Exception as e:
            print(f"   [RAG Init] ⚠️ Could not verify chunk count: {e}")

        # 4. Doc Store (Parent Chunks)
        self.doc_store = SimpleFileStore(parent_store_directory)

    def add_documents(self, text: str, metadata: dict = None):
        if metadata is None:
            metadata = {}
            
        parent_docs = self.parent_splitter.create_documents([text], metadatas=[metadata])
        
        parents_to_save = []
        children_to_index = []
        
        for p_doc in parent_docs:
            p_id = str(uuid.uuid4())
            parents_to_save.append((p_id, p_doc))
            
            child_docs = self.child_splitter.split_documents([p_doc])
            
            for c_doc in child_docs:
                c_doc.metadata["parent_id"] = p_id
                children_to_index.append(c_doc)
        
        # Save & Index
        self.doc_store.mset(parents_to_save)
        
        if children_to_index:
            print(f"   [Index] Adding {len(children_to_index)} child chunks...")
            self.vector_store.add_documents(children_to_index)
            # FORCE PERSIST
            try:
                if hasattr(self.vector_store, 'persist'):
                    self.vector_store.persist()
                    print("   [Index] Persisted to disk.")
            except: 
                pass

    def query(self, question: str, k: int = 5) -> List[Document]:
        print(f"\n🔎 [RAG Query] Question: '{question}'")
        
        if not self.vector_store:
            print("❌ [RAG Query] Vector Store is not initialized.")
            return []

        # 1. Search Vector Store
        print(f"   [RAG Query] Searching for top {k} chunks...")
        
        # Use search_with_score to see the distance
        results_with_scores = self.vector_store.similarity_search_with_score(question, k=k)
        
        if not results_with_scores:
            print("❌ [RAG Query] similarity_search returned 0 results.")
            print("   -> Tip: Check if embedding model matches build_db.py exactly.")
            return []
            
        print(f"   [RAG Query] Found {len(results_with_scores)} raw matches.")
        
        child_docs = []
        for i, (doc, score) in enumerate(results_with_scores):
            # Lower score is usually better in Chroma (Distance)
            print(f"     [{i}] Score: {score:.4f} | ID: {doc.metadata.get('parent_id')} | Content: {doc.page_content[:20]}...")
            child_docs.append(doc)
            
        # 2. Get Parent IDs
        parent_ids = []
        seen = set()
        for doc in child_docs:
            p_id = doc.metadata.get("parent_id")
            if p_id and p_id not in seen:
                parent_ids.append(p_id)
                seen.add(p_id)
        
        print(f"   [RAG Query] Extracted {len(parent_ids)} unique Parent IDs: {parent_ids}")
        
        # 3. Retrieve Parents
        if not parent_ids:
            print("⚠️ [RAG Query] No parent IDs found in metadata. Returning child docs only.")
            return child_docs # Fallback to children if parents fail

        final_docs = self.doc_store.mget(parent_ids)
        print(f"✅ [RAG Query] Retrieved {len(final_docs)} full parent documents.")
        
        return final_docs