import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    """Base configuration."""
    # Volcengine / DeepSeek Configuration
    VOLC_API_KEY = os.getenv('VOLC_API_KEY')
    VOLC_BASE_URL = os.getenv('VOLC_BASE_URL', 'https://ark.cn-beijing.volces.com/api/v3')
    VOLC_MODEL = os.getenv('VOLC_MODEL', 'deepseek-r1-250528')
    
    # Lightweight model for fast tasks (query rewriting)
    VOLC_LITE_MODEL = os.getenv('VOLC_LITE_MODEL', 'deepseek-r1-250528')

    # RAG Hybrid Search Weights
    RAG_BM25_WEIGHT = float(os.getenv('RAG_BM25_WEIGHT', '0.5'))
    RAG_VECTOR_WEIGHT = float(os.getenv('RAG_VECTOR_WEIGHT', '0.5'))

    @classmethod
    def validate(cls):
        """Validate critical configuration."""
        if not cls.VOLC_API_KEY:
            raise ValueError("VOLC_API_KEY not found in environment variables or .env file.")

# Simple usage example (can be removed in production)
if __name__ == "__main__":
    try:
        Config.validate()
        print("Configuration valid.")
        print(f"Model: {Config.VOLC_MODEL}")
    except ValueError as e:
        print(f"Configuration Error: {e}")
