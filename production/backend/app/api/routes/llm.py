import logging
import time
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.postgres_db import get_postgres_db
from app.core.qdrant_client import qdrant_vector_db
from app.core.evidently_monitor import evidently_monitor
from app.services.llm_services import llm_service
from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from app.services.llm_services import LLMService
from datetime import datetime
import uuid
from app.services.ml_predictor import MLPredictor
from app.api.dependencies import get_ml_predictor

router = APIRouter()
logger = logging.getLogger(__name__)

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

@router.post("/chat")
async def chat_endpoint(request: ChatRequest , db: AsyncSession = Depends(get_postgres_db)):
    """Generate Chat endpoint with LLM, Qdrant vector search, and Evidently monitoring."""
    start_time = time.time()
    session_id = request.session_id or str(uuid.uuid4())

    try:
        # Step 1: Search for context using Qdrant
        context_results = []
        if request.context and isinstance(request.context, dict) and request.context.get("vector"):
            logger.info(f"🔍 Searching Qdrant for context related to: {request.context}")

            # Create collection if not exists
            logger.info("🔍 About to create/check chat_history collection")
            qdrant_vector_db.create_collection("chat_history")

            # Search for similar conversation history based on the provided context
            logger.info("🔍 Calling search_similar")
            context_results = qdrant_vector_db.search_vector(
                collection_name="chat_history",
                query_vector=request.context.get["vector"], # Assuming context includes a pre-computed vector
                limit=3
            )
            logger.info(f"🔍 Found {len(context_results)} relevant context entries in Qdrant")

        # Step 2: Call LLM with context
        user_message = request.messages[-1].content if request.messages else ""
        logger.info(f"💬 LLM Request: {user_message}")

        messages = [msg.model_dump() for msg in request.messages]
        response = await llm_service.chat(messages, request.temperature)

        # Step 3: Calculate metrics
        response_time_ms = int((time.time() - start_time) * 1000)
        tokens_estimate = len(user_message.split()) + len(response.split()) # Simple token estimation
        cost_estimate = (tokens_estimate / 1000) * 0.0001 # Groq pricing estimate

        # Step 4: Store in Qdrant for future context
        try:
            vector = request.context.get("vector", []) if isinstance(request.context, dict) else []
            logger.info(f"🔍 Storing conversation user: {request.user_id} in Qdrant with session_id: {session_id}")
            
            if vector:
                    qdrant_vector_db.add_point(
                    collection_name="chat_history",
                    point_id=str(hash(session_id) % (10**9)), # Simple hash for unique ID
                    vector=vector, # Store vector for future similarity search
                    metadata={
                        "user_id": request.user_id,
                        "session_id": session_id,
                        "response": response,
                        "timestamp": time.time()
                    }
                )
            else:
                logger.warning("⚠️ No vector provided in context, skipping Qdrant storage for this interaction.")
        except Exception as e:
            logger.warning(f"⚠️ Failed to store conversation in Qdrant: {e}")

        # Step 5: Log metrics with Evidently
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
                "context_retrieved": len(context_results)
            }
        }
    
    except Exception as e:
        logger.error(f"❌ Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing chat request: {e}")

@router.post("/recommend-route")
async def recommend_route(request: RouteRecommendRequest, ml_predictor: MLPredictor = Depends(get_ml_predictor)):
    """Get route recommendation from natural language query."""
    llm = LLMService()
    recommendation = await llm.recommend_route(request.query, request.context)

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