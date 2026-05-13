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
        self.provider = settings.LLM_PROVIDER or "groq"
        self.groq_api_key = settings.GROQ_API_KEY
        self.model = settings.LLM_MODEL or "llama-3.1-8b-instant"
        self.base_url = settings.LLM_BASE_URL or "https://api.groq.com/openai/v1"

        # Verify configuration
        if not self.groq_api_key:
            logger.error("❌ GROQ_API_KEY is not set in environment variables. LLMService will not work.")
        if not self.provider:
            logger.error("❌ LLM_PROVIDER is not set in environment variables. Defaulting to 'groq'.")

    # Create groq as primary LLM provider, with abstraction for future providers
    async def chat(self, messages: List[Dict[str, str]], temperature: float = 0.7) -> str:
        """Generate chat response from LLM"""
    # Validate all messages have required fields before making API call
        for i, msg in enumerate(messages):
            if "role" not in msg or not msg["role"]:
                raise ValueError(f"Message {i} is missing 'role' field.")
            if "content" not in msg or not msg["content"] or not msg["content"].strip():
                raise ValueError(f"Message {i} has empty 'content' field.")
            if msg["role"] not in ["user", "assistant", "system"]:
                raise ValueError(f"Message {i} has invalid 'role': {msg['role']}.")
        logger.info(f"✅ Validated {len(messages)} messages for LLM chat request.")

        if not self.provider or self.provider == "groq":
            return await self._groq_chat(messages=messages, temperature=temperature)
        else:
            raise NotImplementedError(f"LLM provider {self.provider} not implemented.")
        
    async def _groq_chat(self, messages: List[Dict[str, str]], temperature: float) -> str:
        """Call Groq API with error handling."""
        try:
            if not self.groq_api_key:
                raise ValueError("GROQ_API_KEY is not configured.")
            if not messages:
                raise ValueError("Messages cannot be empty.")
            
            logger.info(f"📥 Sending request to Groq API with model: {self.model}")
            logger.debug(f"Messages: {messages}")
    
            async with httpx.AsyncClient(timeout=60) as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": max(0, min(temperature, 2)),  # Ensure temperature is between 0 and 2
                        "max_tokens": 400,
                    },
                    follow_redirects=True
                )
                logger.info(f"📤 Received response from Groq API with status code: {response.status_code}")

                if response.status_code != 200:
                    error_text = response.text
                    logger.error(f"❌ Groq API error: {response.status_code}: {error_text}")
                    raise httpx.HTTPStatusError(
                        f"Groq API returned {response.status_code}: {error_text}",
                        request=response.request,
                        response=response
                    )
                result = response.json()
                content = result["choices"][0]["message"]["content"]
                logger.info(f"✅ Successfully got response from Groq API.")
                return content
            
        except httpx.HTTPStatusError as e:
            logger.error(f"❌ HTTP error calling Groq API: {str(e)}")
            raise
        except Exception as e:
            logger.error(f"❌ Error during Groq chat: {type(e).__name__}: {str(e)}")
            raise
                
        
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