import json
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime
import httpx
from app.core.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    """LLM service for chatbot, route recommendation, and natural language booking services."""

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.groq_api_key = settings.GROQ_API_KEY
        self.model = settings.LLM_MODEL
        self.base_url = settings.LLM_BASE_URL or "https://api.groq.com/openai/v1"

    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """Generic chat method to interact with the LLM."""
        if self.provider == "groq":
            return await self._groq_chat(messages, temperature)
        else:
            return await self._local_chat(messages, temperature)
        
    async def _groq_chat(self, messages: List[Dict[str, str]], temperature: float) -> str:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization":f"Bearer {self.groq_api_key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": 600,
                }
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"]
        
        async def _local_chat(self, messages: List[Dict[str, str]], temperature: float) -> str:
            return "Local LLM not implemented yet."
        
        async def recommend_routes(self, user_query: str, context: Dict = None) -> Dict:
            """Recommend routes based on natural language query."""
            system_prompt = """You are a taxi route recommendation engine assistant.
            Based on the user's query, suggest the best pickup and drop locations,
            vehicle type, and any tips. Return JSON with fields:
            pickup, drop, vehicle_type, reason, estimated_time, estimated_price.
            If query is vague, ask clarifying questions."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_query}
            ]
            response = await self.chat(messages, temperature=0.4)
            # Try to parse JSON
            try:
                return json.loads(response)
            except:
                return {"error": "Could not parse recommendation", "raw": response}
            
        async def answer_route_question(self, question: str, route_context: Dict = None) -> str:
            """Answer user question about a specific route or map."""
            context_str = json.dumps(route_context) if route_context else "No specific context provided."
            system_prompt = f"""You are a helpful assistant for a taxi app.
            Current route/context: {context_str}
            Answer the user's question about routes, traffic, estimated time, or places of interest.
            Keep answers concise and friendly."""

            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question}
            ]
            return await self.chat(messages, temperature=0.7)