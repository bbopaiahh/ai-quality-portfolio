import os
from pathlib import Path

from dotenv import load_dotenv


def _positive_int(name: str, default: int) -> int:
    try:
        return max(1, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------
# Project Root
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------
# Environment Variables
# ---------------------------------------------------------

ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE)


# ---------------------------------------------------------
# LLM Configuration
# ---------------------------------------------------------

# Primary provider: Gemini
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/openai/"
GEMINI_MODEL = "gemini-3.7-flash"

# Fallback provider: Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_MODEL = "openai/gpt-oss-120b"


# ---------------------------------------------------------
# Document Processing Configuration
# ---------------------------------------------------------

CHUNK_SIZE = 7000

CHUNK_OVERLAP = 600

# Upload and OCR limits are environment-configurable so deployments can
# tune them for their hardware and Streamlit hosting limits.
RARE_MAX_UPLOAD_FILES = _positive_int("RARE_MAX_UPLOAD_FILES", 20)
RARE_MAX_UPLOAD_FILE_MB = _positive_int("RARE_MAX_UPLOAD_FILE_MB", 100)
RARE_MAX_UPLOAD_BATCH_MB = _positive_int("RARE_MAX_UPLOAD_BATCH_MB", 250)
RARE_OCR_LANGUAGE = os.getenv("RARE_OCR_LANGUAGE", "eng")
RARE_OCR_MIN_PAGE_CHARS = _positive_int("RARE_OCR_MIN_PAGE_CHARS", 24)
RARE_TESSERACT_CMD = os.getenv("RARE_TESSERACT_CMD")


# ---------------------------------------------------------
# Application Configuration
# ---------------------------------------------------------

APP_NAME = "RARE - AI Test Engineering Assistant"

SUPPORTED_DOCUMENT_TYPES = [
    ".pdf",
    ".docx",
    ".png",
    ".jpg",
    ".jpeg",
    ".tif",
    ".tiff",
    ".bmp",
    ".webp",
]
