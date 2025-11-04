import os
from dotenv import load_dotenv

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "40"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))

# Simple helpers
def ensure_dir(path: str):
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
