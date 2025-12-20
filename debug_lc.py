import langchain
import os
print(f"LangChain Version: {langchain.__version__}")
print(f"LangChain File: {langchain.__file__}")

try:
    from langchain.retrievers import EnsembleRetriever
    print("SUCCESS: import from langchain.retrievers")
except ImportError as e:
    print(f"FAIL: import from langchain.retrievers ({e})")

try:
    from langchain.retrievers.ensemble import EnsembleRetriever
    print("SUCCESS: import from langchain.retrievers.ensemble")
except ImportError as e:
    print(f"FAIL: import from langchain.retrievers.ensemble ({e})")

try:
    import langchain.retrievers
    print(f"langchain.retrievers dir: {dir(langchain.retrievers)}")
except ImportError as e:
    print(f"FAIL: import langchain.retrievers ({e})")
