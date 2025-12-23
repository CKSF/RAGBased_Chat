import os
import uuid
import json
import traceback
from typing import List, Optional, Dict, Any
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.retrievers import BM25Retriever
from backend.config import Config

# ==========================================
# 1. Custom Ensemble Retriever (RRF Fusion)
# ==========================================
class EnsembleRetriever:
    """
    Custom implementation of EnsembleRetriever with RRF (Reciprocal Rank Fusion).
    """
    def __init__(self, retrievers: List, weights: List[float], c: int = 60):
        self.retrievers = retrievers
        self.weights = weights
        self.c = c

    def invoke(self, query: str) -> List[Document]:
        # 1. Gather results from all retrievers
        all_results = []
        for retriever in self.retrievers:
            try:
                if hasattr(retriever, 'invoke'):
                    docs = retriever.invoke(query)
                elif hasattr(retriever, 'get_relevant_documents'):
                    docs = retriever.get_relevant_documents(query)
                else:
                    docs = []
                all_results.append(docs)
            except Exception as e:
                print(f"   ⚠️ Retriever error: {e}")
                all_results.append([])
        
        # 2. RRF Fusion
        doc_map = {}
        for i, docs in enumerate(all_results):
            weight = self.weights[i]
            for rank, doc in enumerate(docs):
                # Use page_content as unique key to deduplicate
                key = doc.page_content
                if key not in doc_map:
                    doc_map[key] = {"doc": doc, "score": 0.0}
                
                # RRF Formula: score += w * (1 / (rank + c))
                doc_map[key]["score"] += weight * (1 / (rank + self.c))
        
        # 3. Sort by fused score
        fused_docs = sorted(doc_map.values(), key=lambda x: x["score"], reverse=True)
        return [item["doc"] for item in fused_docs]


# ==========================================
# 2. Simple File Store (Parent Document Storage)
# ==========================================
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
                # Silently skip missing keys (cleaning up old refs)
                pass
        return docs


# ==========================================
# 3. Main RAG Service
# ==========================================
class RAGService:
    def __init__(self, persist_directory: str = "chroma_db", parent_store_directory: str = "doc_store"):
        print(f"\n🟢 [RAG Init] Initializing RAG Service...")
        print(f"   [RAG Init] DB Directory: {os.path.abspath(persist_directory)}")
        
        # 1. Embedding Model
        # Using a standard Chinese embedding model
        self.embeddings = HuggingFaceEmbeddings(
            model_name="shibing624/text2vec-base-chinese"
        )
        
        # 2. Splitters
        # Parent: Large context for LLM
        self.parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
        # Child: Small chunks for accurate retrieval
        self.child_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
        
        # 3. Vector Store (Child Chunks)
        self.vector_store = Chroma(
            collection_name="split_parents", 
            embedding_function=self.embeddings,
            persist_directory=persist_directory
        )

        # 4. Doc Store (Parent Chunks)
        self.doc_store = SimpleFileStore(parent_store_directory)
        
        # 5. Initialize Hybrid Search
        self._init_hybrid_retriever()

    def _init_hybrid_retriever(self):
        """Initialize EnsembleRetriever (BM25 + Vector)."""
        try:
            print("   [RAG Init] Loading documents for BM25...")
            # Fetch all docs to build BM25 index
            all_docs_data = self.vector_store.get()
            
            all_docs = []
            if all_docs_data and 'documents' in all_docs_data:
                texts = all_docs_data['documents']
                metadatas = all_docs_data['metadatas']
                
                for i in range(len(texts)):
                    if texts[i]:
                        doc = Document(
                            page_content=texts[i], 
                            metadata=metadatas[i] if metadatas else {}
                        )
                        all_docs.append(doc)
            
            doc_count = len(all_docs)
            print(f"   [RAG Init] Loaded {doc_count} chunks for BM25.")

            if doc_count > 0:
                # A. BM25
                self.bm25_retriever = BM25Retriever.from_documents(all_docs)
                self.bm25_retriever.k = 5 
                
                # B. Chroma
                self.chroma_retriever = self.vector_store.as_retriever(
                    search_type="similarity", 
                    search_kwargs={"k": 5}
                )
                
                # C. Ensemble
                weights = [Config.RAG_BM25_WEIGHT, Config.RAG_VECTOR_WEIGHT]
                self.ensemble_retriever = EnsembleRetriever(
                    retrievers=[self.bm25_retriever, self.chroma_retriever],
                    weights=weights
                )
                print("   [RAG Init] ✅ Hybrid Search Ready.")
            else:
                print("   [RAG Init] ⚠️ DB Empty. Hybrid search disabled.")
                self.ensemble_retriever = None

        except Exception as e:
            print(f"   [RAG Init] ❌ Error init Hybrid Search: {e}")
            self.ensemble_retriever = None

    def add_documents(self, text: str, metadata: dict = None):
        """
        Process text, split into parent/child, and index with metadata.
        """
        if metadata is None:
            metadata = {}
            
        # 1. Create Parent Docs
        parent_docs = self.parent_splitter.create_documents([text], metadatas=[metadata])
        
        parents_to_save = []
        children_to_index = []
        
        for p_doc in parent_docs:
            p_id = str(uuid.uuid4())
            parents_to_save.append((p_id, p_doc))
            
            # 2. Create Child Docs
            child_docs = self.child_splitter.split_documents([p_doc])
            
            for c_doc in child_docs:
                c_doc.metadata["parent_id"] = p_id
                
                # [CRITICAL] Propagate specific metadata (like 'grade') to children
                # This ensures the Vector Store filters can see the grade
                for key in ["source", "grade", "topic"]: 
                    if key in metadata:
                        c_doc.metadata[key] = metadata[key]
                        
                children_to_index.append(c_doc)
        
        # 3. Save to Stores
        self.doc_store.mset(parents_to_save)
        
        if children_to_index:
            self.vector_store.add_documents(children_to_index)
            # Re-init BM25 to include new docs (simple approach)
            # In high-load prod, you'd want to do this async or less frequently
            # self._init_hybrid_retriever()

    def query(self, question: str, k: int = 5, filters: Optional[Dict[str, Any]] = None) -> List[Document]:
        """
        Execute Hybrid Search with strict filtering.
        
        Args:
            question: User query
            k: Number of parent docs to return
            filters: Dict like {"grade": "小学"}
        """
        print(f"\n🔎 [RAG Query] '{question}' | Filters: {filters}")
        
        if not self.ensemble_retriever:
            return []

        # --- Step 1: Configure Chroma Native Filters ---
        # This optimizes the Vector Search part
        # if filters:
        #     # Chroma expects filter dict: {"metadata_field": "value"}
        #     self.chroma_retriever.search_kwargs["filter"] = filters
        # else:
        #     # Clear previous filters if any
        #     if "filter" in self.chroma_retriever.search_kwargs:
        #         del self.chroma_retriever.search_kwargs["filter"]
        
        # Set K for retrievers (fetching more initially to allow for post-filtering of BM25 results)
        fetch_k = k * 3  
        self.bm25_retriever.k = fetch_k
        self.chroma_retriever.search_kwargs["k"] = fetch_k
        
        # --- Step 2: Execute Retrieval ---
        try:
            # This returns a merged list from BM25 + Vector
            raw_docs = self.ensemble_retriever.invoke(question)
        except Exception as e:
            print(f"❌ Retrieval Error: {e}")
            traceback.print_exc()
            return []

        # --- Step 3: Strict Post-Retrieval Filtering ---
        # Necessary because BM25 results ignore the Chroma native filter
        filtered_docs = []
        
        target_grade = filters.get("grade") if filters else None
        
        for doc in raw_docs:
            doc_grade = doc.metadata.get("grade", "通用")
            
            # Logic: If a grade filter is set, ONLY accept that grade OR '通用'
            if target_grade:
                if doc_grade != target_grade and doc_grade != "通用":
                    # Skip mismatch (e.g. skip "大学" when looking for "小学")
                    continue
            
            filtered_docs.append(doc)
            
        print(f"   [Filter] {len(raw_docs)} raw -> {len(filtered_docs)} valid docs (Target: {target_grade})")

        # --- Step 4: Map to Parent Documents ---
        parent_ids = []
        seen = set()
        
        # Only process enough children to fill 'k' parents
        for doc in filtered_docs:
            p_id = doc.metadata.get("parent_id")
            if p_id and p_id not in seen:
                parent_ids.append(p_id)
                seen.add(p_id)
                if len(parent_ids) >= k:
                    break
        
        if not parent_ids:
            return [] # Logic: return empty if no parents found

        final_docs = self.doc_store.mget(parent_ids)
        print(f"✅ [Result] Retrieved {len(final_docs)} parent documents.")
        
        return final_docs