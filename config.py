# config.py
import os
from dotenv import load_dotenv
load_dotenv()

# ── LLM Config ──────────────────────────────────────────────
OPENROUTER_MODEL = "meta-llama/llama-3-8b-instruct"

# ── AWS Config ───────────────────────────────────────────────
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
S3_BUCKET = os.getenv("S3_BUCKET_NAME")

# ── Vector DB Config ─────────────────────────────────────────
CHROMA_DB_PATH = "./chroma_db"
COLLECTION_NAME = "medical_knowledge"
TOP_K_RESULTS = 3

def get_llm():
    """Uses OpenRouter — works locally and on cloud."""
    from langchain_openai import ChatOpenAI
    
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY not found in .env!")
    
    print(f"[LLM] Using OpenRouter: {OPENROUTER_MODEL}")
    return ChatOpenAI(
        model=OPENROUTER_MODEL,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        temperature=0
    )