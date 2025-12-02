import os
from dotenv import load_dotenv

load_dotenv()

# LLM API 설정
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")

# Consensus 분석 설정
CONSENSUS_ENABLED = os.getenv("CONSENSUS_ENABLED", "False").lower() == "true"
CONSENSUS_PROVIDERS = os.getenv("CONSENSUS_PROVIDERS", "gemini,openai").split(",")

# Flask 서버 설정
FLASK_HOST = os.getenv("FLASK_HOST", "0.0.0.0")
FLASK_PORT = int(os.getenv("FLASK_PORT", "5000"))
FLASK_DEBUG = os.getenv("FLASK_DEBUG", "True").lower() == "true"

# 기타 설정
REQUEST_TIMEOUT = int(os.getenv("REQUEST_TIMEOUT", "40"))
MAX_RETRIES = int(os.getenv("MAX_RETRIES", "2"))

# Simple helpers
def ensure_dir(path: str):
    import os
    os.makedirs(os.path.dirname(path), exist_ok=True)
