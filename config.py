import os
from dotenv import load_dotenv
load_dotenv()

# ── LLM Config ──────────────────────────────────────────────
USE_OLLAMA = True       # True = Ollama (free, local, dev)
                        # False = OpenAI (paid, fast, demo day)
USE_BEDROCK = False     # True = AWS Bedrock (Week 3 onwards)

OLLAMA_MODEL = "qwen2.5:7b"
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")

OPENAI_MODEL = "gpt-4o"
BEDROCK_MODEL = "anthropic.claude-3-sonnet-20240229-v1:0"

# ── AWS Config (use from Day 1) ──────────────────────────────
USE_AWS_TEXTRACT = True   # Always True for AWS hackathon
AWS_REGION = os.getenv("AWS_REGION", "us-east-2")
S3_BUCKET = os.getenv("S3_BUCKET_NAME")

# ── Vector DB Config ─────────────────────────────────────────
CHROMA_DB_PATH = "./chroma_db"
COLLECTION_NAME = "medical_knowledge"
TOP_K_RESULTS = 3

def get_llm():
    """
    Returns correct LLM based on config.
    Week 1-2: Ollama (free)
    Week 3:   Bedrock (cloud native)
    Week 4:   OpenAI (best quality for demo)
    """
    if USE_OLLAMA:
        from langchain_ollama import ChatOllama
        print(f"[LLM] Using Ollama: {OLLAMA_MODEL}")
        return ChatOllama(
            model=OLLAMA_MODEL,
            base_url=OLLAMA_BASE_URL,
            temperature=0
        )
    elif USE_BEDROCK:
        from langchain_aws import ChatBedrock
        print(f"[LLM] Using AWS Bedrock: {BEDROCK_MODEL}")
        return ChatBedrock(
            model_id=BEDROCK_MODEL,
            region_name="us-east-1"
        )
    else:
        from langchain_openai import ChatOpenAI
        print(f"[LLM] Using OpenAI: {OPENAI_MODEL}")
        return ChatOpenAI(
            model=OPENAI_MODEL,
            api_key=os.getenv("OPENAI_API_KEY"),
            temperature=0
        )