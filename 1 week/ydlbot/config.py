"""Конфигурация проекта. Все значения берутся из .env (см. .env.example)."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

load_dotenv(BASE_DIR / ".env")

# ---- Telegram ----
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")

# ---- LLM (чат) ----
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://llm.alem.ai/v1").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "gemma4")

# ---- Embeddings ----
EMBED_BASE_URL = os.getenv("EMBED_BASE_URL", "https://llm.alem.ai/v1").rstrip("/")
EMBED_API_KEY = os.getenv("EMBED_API_KEY", "")
EMBED_MODEL = os.getenv("EMBED_MODEL", "text-1024")

# ---- Скрейпинг ----
SCRAPE_BASE_URL = os.getenv("SCRAPE_BASE_URL", "https://yessenovfoundation.org/")
SCRAPE_MAX_PAGES = int(os.getenv("SCRAPE_MAX_PAGES", "250"))
SCRAPE_DELAY = float(os.getenv("SCRAPE_DELAY", "0.4"))

# ---- RAG ----
CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "900"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "150"))
TOP_K = int(os.getenv("TOP_K", "7"))
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.25"))

# ---- Файлы хранения ----
FAISS_INDEX_PATH = DATA_DIR / "faiss.index"
CHUNKS_PATH = DATA_DIR / "chunks.pkl"
KB_META_PATH = DATA_DIR / "kb_meta.json"
DB_PATH = DATA_DIR / "logs.db"

# Дословный ответ, когда информации нет в базе знаний.
NOT_FOUND_MESSAGE = "Я не нашёл этой информации в материалах фонда."
