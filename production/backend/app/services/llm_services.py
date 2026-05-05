import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    """LLM service for chatbot, route recommendation, and natural language booking services."""

    def __init__(self)
        self.provider = settings.LLM_PROVIDER
        self.groq_api_key = settings.GROQ_API_KEY
        self.model = settings.LLM_MODEL
        self.base_url = settings.LLM_BASE_URL or "https://api.groq.com/openai/v1"