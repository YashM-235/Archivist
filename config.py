import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "data", "uploads")
INDEX_DIR = os.path.join(BASE_DIR, "data", "vector_store")

os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(INDEX_DIR, exist_ok=True)

# --- Chunking ---
CHUNK_SIZE = 900          # target characters per chunk
CHUNK_OVERLAP = 150       # character overlap between consecutive chunks

# --- Embeddings / Vector store ---
EMBEDDING_MODEL = "all-MiniLM-L6-v2"   # local, free, runs on CPU
TOP_K = 5                              # chunks retrieved per query

# --- Groq LLM ---
# Groq deprecated llama-3.3-70b-versatile / llama-3.1-8b-instant in mid-2026.
# These are the current recommended replacements (verify at console.groq.com/docs/models
# if this project is picked up again later, since Groq's lineup changes often).
GROQ_MODEL = "openai/gpt-oss-120b"
AVAILABLE_MODELS = [
    {"id": "openai/gpt-oss-120b", "label": "GPT-OSS 120B (best quality)"},
    {"id": "openai/gpt-oss-20b", "label": "GPT-OSS 20B (fastest)"},
    {"id": "qwen/qwen3.6-27b", "label": "Qwen3.6 27B (strong reasoning)"},
]
GROQ_API_KEY_ENV = "GROQ_API_KEY"
