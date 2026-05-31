import os
from pathlib import Path
from dotenv import load_dotenv
import logging

logger = logging.getLogger(__name__)

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
logging.info(f"✅ Loaded environtment variables from: {ENV_PATH}")

if not ENV_PATH.exists():
    ENV_PATH = BASE_DIR.parent / '.env'
    logging.warning(f"⚠️ .env file not found at {ENV_PATH}, trying fallback location: {ENV_PATH}")
else:
    logging.info(f"✅ .env file found at {ENV_PATH}")