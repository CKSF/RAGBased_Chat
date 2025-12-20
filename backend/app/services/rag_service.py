import os
import uuid
import json
from typing import List, Optional
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.retrievers import BM25Retriever
from backend.config import Config

class EnsembleRetriever:
    """
    Custom implementation of EnsembleRetriever with RRF (Reciprocal Rank Fusion).
    Bypasses 'langchain.retrievers' dependency issues.
    """
    def __init__(self, retrievers: List, weights: List[float], c: int = 60):
        self.retrievers = retrievers
        self.weights = weights
        self.c = c

    def invoke(self, query: str) -> List[Document]:
        # 1. Gather results from all retrievers
        all_results = []
        for retriever in self.retrievers:
            if hasattr(retriever, 'invoke'):
                docs = retriever.invoke(query)
            elif hasattr(retriever, 'get_relevant_documents'):
                docs = retriever.get_relevant_documents(query)
            else:
                docs = []
            all_results.append(docs)
        
        # 2. RRF Fusion
        # Content -> {doc, score}
        doc_map = {}
        
        for i, docs in enumerate(all_results):
            weight = self.weights[i]
            for rank, doc in enumerate(docs):
                # Use page_content as unique key (or parent_id if available, but content is safer for dedup)
                # Here we use page_content to deduplicate same chunks from different retrievers
                key = doc.page_content
                if key not in doc_map:
                    doc_map[key] = {"doc": doc, "score": 0.0}
                
                # RRF Formula: score += w * (1 / (rank + c))
                doc_map[key]["score"] += weight * (1 / (rank + self.c))
        
        # 3. Sort by new score
        # Convert map back to list
        fused_docs = sorted(doc_map.values(), key=lambda x: x["score"], reverse=True)
        
        # Return only the Document objects
        return [item["doc"] for item in fused_docs]


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
        print(f"\n🟢 [RAG Init] Initializing RAG Service (Hybrid Search)...")
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

        # 4. Doc Store (Parent Chunks)
        self.doc_store = SimpleFileStore(parent_store_directory)
        
        # 5. Initialize Hybrid Search (BM25 + Chroma)
        self._init_hybrid_retriever()

    def _init_hybrid_retriever(self):
        """Initialize LangChain's EnsembleRetriever (BM25 + Vector)."""
        try:
            # We need to fetch all documents to build the BM25 index in memory
            print("   [RAG Init] Building In-Memory BM25 Index...")
            
            # Using get() without IDs returns all docs (limit is None by default usually, but let's be safe)
            # Warning: For very large datasets, this needs pagination.
            all_docs_data = self.vector_store.get()
            
            # Reconstruct Document objects
            all_docs = []
            if all_docs_data and 'documents' in all_docs_data:
                ids = all_docs_data['ids']
                texts = all_docs_data['documents']
                metadatas = all_docs_data['metadatas']
                
                for i in range(len(ids)):
                    if texts[i]: # Skip empty chunks
                        doc = Document(page_content=texts[i], metadata=metadatas[i] if metadatas else {})
                        all_docs.append(doc)
            
            doc_count = len(all_docs)
            print(f"   [RAG Init] Loaded {doc_count} chunks for BM25.")

            if doc_count > 0:
                # A. BM25 Receiver
                self.bm25_retriever = BM25Retriever.from_documents(all_docs)
                # Standardize 'k' later in query, but set a default
                self.bm25_retriever.k = 5 
                
                # B. Chroma Receiver
                self.chroma_retriever = self.vector_store.as_retriever(
                    search_type="similarity", 
                    search_kwargs={"k": 5}
                )
                
                # C. Ensemble
                weights = [Config.RAG_BM25_WEIGHT, Config.RAG_VECTOR_WEIGHT]
                print(f"   [RAG Init] Ensemble Weights -> BM25: {weights[0]}, Vector: {weights[1]}")
                
                self.ensemble_retriever = EnsembleRetriever(
                    retrievers=[self.bm25_retriever, self.chroma_retriever],
                    weights=weights
                )
                print("   [RAG Init] ✅ EnsembleRetriever (Hybrid) is ready.")
            else:
                print("   [RAG Init] ⚠️ No documents found. Hybrid search will fallback or fail.")
                self.ensemble_retriever = None

        except Exception as e:
            print(f"   [RAG Init] ❌ Failed to init Hybrid Search: {e}")
            import traceback
            traceback.print_exc()
            self.ensemble_retriever = None

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
            
            # Re-init hybrid retriever to include new docs
            # Note: In production, you might optimize this to incremental update
            self._init_hybrid_retriever()

    def query(self, question: str, k: int = 5) -> List[Document]:
        print(f"\n🔎 [RAG Query (Hybrid)] Question: '{question}'")
        
        if not self.ensemble_retriever:
            print("❌ [RAG Query] Retriever is not initialized. (DB Empty?)")
            return []

        # 1. Search Ensemble
        # Adjust 'k' for both retrievers dynamically
        self.bm25_retriever.k = k
        self.chroma_retriever.search_kwargs["k"] = k
        
        print(f"   [RAG Query] Searching top {k} (x2 sources)...")
        
        # Invoke Ensemble
        # Note: input must be a string for invoke
        child_docs = self.ensemble_retriever.invoke(question)
        
        if not child_docs:
            print("❌ [RAG Query] No results found.")
            return []
            
        print(f"   [RAG Query] Found {len(child_docs)} results (merged).")
        
        # Log preview
        for i, doc in enumerate(child_docs[:3]):
            print(f"     [{i}] ID: {doc.metadata.get('parent_id')} | Content: {doc.page_content[:20]}...")
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
            return child_docs 

        final_docs = self.doc_store.mget(parent_ids)
        print(f"✅ [RAG Query] Retrieved {len(final_docs)} full parent documents.")
        
        return final_docs