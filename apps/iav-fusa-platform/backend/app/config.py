"""Application configuration."""
import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).parent.parent
load_dotenv(BASE_DIR / ".env")

# LLM
MODEL = os.getenv("DEEPAGENTS_MODEL", "anthropic:claude-sonnet-4-6")

# OpenAI 兼容端点（MiniMax / 其他代理）
OPENAI_API_BASE = os.getenv("OPENAI_API_BASE", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Dify RAG
DIFY_API_URL = os.getenv("DIFY_API_URL", "http://localhost:5001")
DIFY_API_KEY = os.getenv("DIFY_API_KEY", "")

COLLECTION_MAP = {
    "iso26262_hara": os.getenv("DIFY_DATASET_HARA", ""),
    "iso26262_fmea": os.getenv("DIFY_DATASET_FMEA", ""),
    "iso26262_fta": os.getenv("DIFY_DATASET_FTA", ""),
    "failure_modes": os.getenv("DIFY_DATASET_FAILURE_MODES", ""),
    "historical_cases": os.getenv("DIFY_DATASET_HISTORICAL", ""),
    "company_standards": os.getenv("DIFY_DATASET_COMPANY", ""),
}

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/fusa")

# Redis
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# MinIO
MINIO_ENDPOINT = os.getenv("MINIO_ENDPOINT", "localhost:9000")
MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "minioadmin")

# LangSmith
LANGSMITH_TRACING = os.getenv("LANGSMITH_TRACING", "false").lower() == "true"
LANGSMITH_API_KEY = os.getenv("LANGSMITH_API_KEY", "")
LANGSMITH_PROJECT = os.getenv("LANGSMITH_PROJECT", "iav-fusa-platform")

# Skills directories
SKILLS_COMMON_DIR = str(BASE_DIR / "skills" / "common")
SKILLS_HARA_DIR = str(BASE_DIR / "skills" / "hara")
SKILLS_FMEA_DIR = str(BASE_DIR / "skills" / "fmea")
SKILLS_FTA_DIR = str(BASE_DIR / "skills" / "fta")

# Memory
AGENTS_MD_PATH = str(BASE_DIR / "AGENTS.md")

# RPN threshold for human review
RPN_THRESHOLD = int(os.getenv("RPN_THRESHOLD", "100"))
