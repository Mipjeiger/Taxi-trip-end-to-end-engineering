import logging
import time
import uuid
import json
import re
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.postgres_db import get_postgres_db
from app.core.qdrant_client import qdrant_vector_db
from app.core.evidently_monitor import evidently_monitor
from app.services.llm_services import llm_service, LLMService
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from app.services.ml_predictor import MLPredictor
from app.api.dependencies import get_ml_predictor
from app.services.trip_retriever import TripRetriever


router = APIRouter()
logger = logging.getLogger(__name__)

# ================================================================
# Lazy-loaded embedding model (loads once, reused across requests)
# ================================================================
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        try:
            from fastembed import TextEmbedding
            _embedding_model = TextEmbedding(model_name="BAAI/bge-small-en-v1.5")
            logger.info("✅ Loaded embedding model: BAAI/bge-small-en-v1.5")
        except Exception as e:
            logger.error(f"❌ Failed to load embedding model: {e}")
            _embedding_model = None
    return _embedding_model

def embed_text(text: str) -> Optional[List[float]]:
    """Generate embedding vector from text. Returns None on failure."""
    try:
        model = get_embedding_model()
        if model is None:
            return None
        vectors = list(model.embed([text])) # returns generator, convert to list
        return vectors[0].tolist()
    except Exception as e:
        logger.error(f"❌ Embedding generation failed for text: {text[:50]}... Error: {e}")
        return None

# ================================================================
# Request Models
# ================================================================

class Message(BaseModel):
    role: str = Field(..., pattern="^(system|user|assistant)$")
    content: str = Field(..., min_length=1)

class ChatRequest(BaseModel):
    user_id: str
    session_id: Optional[str] = None
    messages: List[Message] = List[Message]
    temperature: float = Field(default=0.7, ge=0, le=2)
    context: Optional[Dict] = None # Optional context for the LLM to consider in the conversation

class RouteRecommendRequest(BaseModel):
    query: str
    context: Optional[Dict] = None

class RouteQuestionRequest(BaseModel):
    question: str
    route_context: Optional[Dict] = None

class PriceQuestionRequest(BaseModel):
    question: str
    price_context: Optional[float] = None

# ===============================================================
# Chat Endpoint
# ===============================================================

@router.post("/chat")
async def chat_endpoint(request: ChatRequest , db: AsyncSession = Depends(get_postgres_db)):
    """Generate Chat endpoint with LLM, Qdrant vector search, and Evidently monitoring."""
    start_time = time.time()
    session_id = request.session_id or str(uuid.uuid4())

    try:
        user_message = request.messages[-1].content if request.messages else ""

        # Step 1: Embed user message for context search
        query_vector = embed_text(user_message)

        # Step 2: Search Qdrant for similar conversation history if context is provided
        context_results = []
        if query_vector:
            try:
                qdrant_vector_db.create_collection(
                    "chat_history",
                    vector_size=384 # BAAI/bge-small-en-v1.5 vector size
                )
                context_results = qdrant_vector_db.search_vector(
                    collection_name="chat_history",
                    query_vector=query_vector,
                    limit=3
                )
                logger.info(f"🔍 Retrieved {len(context_results)} context results from Qdrant for user: {request.user_id}")
            except Exception as e:
                logger.error(f"❌ Error occurred while searching Qdrant: {e}")

        # Step 3: Build message for LLM with optional context ijnection
        messages = [msg.model_dump() for msg in request.messages]

        if context_results:
            past_context = "\n".join([f"- {r['metadata'].get('prompt', '?')} -> {r['metadata'].get('response', '?')[:100]}"]
                                     for r in context_results)
            context_system_msg = {
                "role": "system",
                "content": f"Relevant past interactions:\n{past_context}\nUse this information to provide a better response."
            }
            messages = [context_system_msg] + messages

        # Inject request.context dict if provided
        if request.context:
            messages = [{
                "role": "system",
                "content": f"Current context:\n{json.dumps(request.context, indent=2)}"
            }] + messages

        # Step 4: Call LLm
        logger.info(f"💬 LLM Request: {user_message}")
        response = await llm_service.chat(messages=messages, 
                                          temperature=request.temperature,
                                          user_id=request.user_id,
                                          session_id=session_id)

        # Step 5: Calculate metrics
        response_time_ms = int((time.time() - start_time) * 1000)
        tokens_estimate = len(user_message.split()) + len(response.split())
        cost_estimate = (tokens_estimate / 1000) * 0.0001

        # Step 6: Store in Qdrant
        if query_vector:
            try:
                point_id = abs(hash(session_id + user_message)) % (10**9)  # Simple hash for point ID
                qdrant_vector_db.add_point(
                    collection_name="chat_history",
                    point_id=str(point_id),
                    vector=query_vector,
                    metadata={
                        "user_id": request.user_id,
                        "session_id": session_id,
                        "prompt": user_message,
                        "response": response[:500], # Truncate response for metadata storage (Save space)
                        "response_time_ms": response_time_ms,
                    }
                )
                logger.info(f"✅ Stored chat interaction in Qdrant with point ID: {point_id}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to store chat interaction in Qdrant: {e}")
        else:
            logger.warning(f"⚠️ Skipping Qdrant storage due to embedding failure for user: {request.user_id}")

        # Step 7: Log to Evidently for LLM Audit - PostgreSQL storage database in llm interactions
        await evidently_monitor.log_llm_response(
            db=db,
            user_id=request.user_id,
            session_id=session_id,
            prompt=user_message,
            response=response,
            response_time_ms=response_time_ms,
            tokens_used=tokens_estimate,
            cost=cost_estimate
        )

        return {
            "session_id": session_id,
            "response": response,
            "metadata": {
                "response_time_ms": response_time_ms,
                "tokens": tokens_estimate,
                "cost": f"${cost_estimate:.6f}",
                "context_retrieved": len(context_results),
                "vector_stored": query_vector is not None
            }
        }
    
    except Exception as e:
        logger.error(f"Error occurred while processing LLM request: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {e}")

@router.post("/recommend-route")
async def recommend_route(request: RouteRecommendRequest, ml_predictor: MLPredictor = Depends(get_ml_predictor)):
    """Get route recommendation from natural language query."""
    llm = LLMService()
    recommendation = await llm.recommend_routes(request.query, request.context)

    # If we got structured data, optionally copute real ETA/price using ML
    if "pickup" in recommendation and "drop" in recommendation:
        try:
            pred = await ml_predictor.predict_ride_metrics(
                pickup=recommendation["pickup"],
                drop=recommendation["drop"],
                vehicle_type=recommendation.get("vehicle_type", "Car"),
                hour=datetime.now().hour,
                day_of_week=datetime.now().weekday(),
                distance_km=recommendation.get("distance_km", 10),
            )
            recommendation["ml_estimated_time"] = pred["estimated_time_min"]
            recommendation["ml_estimated_price"] = pred["estimated_price_idr"]
        except Exception as e:
            recommendation["ml_error"] = str(e)

    return recommendation # Return raw recommendation, ML metrics are optional enhancements

@router.post("/ask-route")
async def ask_route(request: RouteQuestionRequest):
    """Ask a question about a route or map."""
    llm = LLMService()
    answer = await llm.answer_route_question(request.question, request.route_context)
    return {"answer": answer}

@router.post("/ask-price")
async def ask_price(request: PriceQuestionRequest):
    """Ask a question about pricing or surge."""
    llm = LLMService()
    answer = await llm.answer_price_question(request.question, request.price_context)
    return {"answer": answer}