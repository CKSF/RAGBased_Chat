import os
import uuid
import json
from typing import List, Optional
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
# Bypassing complex storage imports by using simple file-based JSON storage for now or recreating logic
# actually, let's use a simple file-based approach for parent docs.

class SimpleFileStore:
    """A simple persistent key-value store for parent documents."""
    def __init__(self, directory: str):
        self.directory = directory
        if not os.path.exists(directory):
            os.makedirs(directory)
    
    def mset(self, key_value_pairs: List[tuple[str, Document]]):
        for key, doc in key_value_pairs:
            # Serialize document to JSON
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
        return docs

class RAGService:
    def __init__(self, persist_directory: str = "chroma_db", parent_store_directory: str = "doc_store"):
        # 1. Embedding Model
        self.embeddings = HuggingFaceEmbeddings(
            model_name="shibing624/text2vec-base-chinese"
        )
        
        # 2. Splitters
        self.parent_splitter = RecursiveCharacterTextSplitter(chunk_size=2000, chunk_overlap=200)
        self.child_splitter = RecursiveCharacterTextSplitter(chunk_size=400, chunk_overlap=50)
        
        # 3. Vector Store (Child Chunks)
        self.vector_store = Chroma(
            collection_name="split_parents",
            embedding_function=self.embeddings,
            persist_directory=persist_directory
        )
        
        # 4. Doc Store (Parent Chunks)
        self.doc_store = SimpleFileStore(parent_store_directory)

    def add_documents(self, text: str, metadata: dict = None):
        """
        Manually implement 'Parent Document' indexing.
        1. Split text into large Parents.
        2. Assign ID to Parent.
        3. Save Parent.
        4. Split Parent into small Children.
        5. Link Child -> Parent via ID.
        6. Index Children.
        """
        if metadata is None:
            metadata = {}
            
        # 1. Create Parent Documents
        parent_docs = self.parent_splitter.create_documents([text], metadatas=[metadata])
        
        parents_to_save = []
        children_to_index = []
        
        for p_doc in parent_docs:
            # 2. Assign ID
            p_id = str(uuid.uuid4())
            
            # 3. Prepare to save Parent
            parents_to_save.append((p_id, p_doc))
            
            # 4. Split into Children
            child_docs = self.child_splitter.split_documents([p_doc])
            
            # 5. Link Child -> Parent
            for c_doc in child_docs:
                c_doc.metadata["parent_id"] = p_id
                children_to_index.append(c_doc)
        
        # Execute Save
        self.doc_store.mset(parents_to_save)
        
        # Execute Index
        # Batch add to avoid hitting limits if any
        if children_to_index:
            self.vector_store.add_documents(children_to_index)
            # self.vector_store.persist() # Auto-persists in new versions

    def query(self, question: str, k: int = 5) -> List[Document]:
        """
        Query logic:
        1. Search VectorStore for top k children.
        2. Extract parent_ids.
        3. Retrieve unique Parents from DocStore.
        """
        # 1. Search Children
        if not self.vector_store:
            # Should be initialized in init, but safety check
            return []
            
        child_docs = self.vector_store.similarity_search(question, k=k)
        
        # 2. Get Parent IDs (deduplicated, preserve order)
        parent_ids = []
        seen = set()
        for doc in child_docs:
            p_id = doc.metadata.get("parent_id")
            if p_id and p_id not in seen:
                parent_ids.append(p_id)
                seen.add(p_id)
        
        # 3. Retrieve Parents
        if not parent_ids:
            return []
            
        return self.doc_store.mget(parent_ids)
