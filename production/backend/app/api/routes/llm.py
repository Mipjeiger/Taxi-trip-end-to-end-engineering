import os
os.environ["TOKENIZERS_PARALLELISM"] = "false" # Disable parallelism warning from Hugging Face tokenizers

# Suppress HuggingFace warnings
import warnings
warnings.filterwarnings("ignore", message=".*unauthenticated requests.*")
warnings.filterwarnings("ignore", message=".*HF_TOKEN.*")

# Or set a dummy token (doesn't need to be real)
#os.environ["HF_TOKEN"] = "dummy_token_for_rate_limits"


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
from app.models.trip import Trip


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

        # ============================================================
        # STEP 1: Extract pickup and dropoff locations from query
        # ============================================================
        pickup = None
        dropoff = None

        # Multiple pattern to handle different user phrasings
        patterns = [
            r"(?:from|dari)\s+([^t]+?)\s+(?:to|ke|menuju)\s+([^?\.]+)",
            r"(?:between|antara)\s+([^a]+?)\s+(?:and|dan)\s+([^?\.]+)",
            r"(?:go|pergi)\s+(?:from|dari)\s+([^t]+?)\s+(?:to|ke)\s+([^?\.]+)",
            r"([^?\.]+?)\s+(?:to|ke)\s+([^?\.]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, user_message, re.IGNORECASE)
            if match:
                pickup = match.group(1).strip()
                dropoff = match.group(2).strip()
                logger.info(f"📍 Extracted locations - Pickup: '{pickup}', Dropoff: '{dropoff}'")
                
                break

        # Cleanup locations (remove extra words)
        if pickup:
            pickup = re.sub(r'^(from|dari|go|pergi)\s+', '', pickup, flags=re.IGNORECASE)
            pickup = pickup.strip()
        
        if dropoff:
            dropoff = dropoff.strip()

        # ============================================================
        # Test Database connection
        # ============================================================
        connection_test = await TripRetriever.test_connection(db)
        logger.info(f"✅ Database connection test: {connection_test}")

        if not connection_test.get("connected"):
            logger.error("❌ Database connection failed")
            return {
                "session_id": session_id,
                "response": "I'm having trouble connecting to the database. Please try again later.",
                "metadata": {"error": "Database connection failed"}
            }

        # ============================================================
        # STEP 2: Retrieve REAL trip data from PostgreSQL
        # ============================================================
        real_trips = []

        # If no trips found, try case-insensitive and partial matching
        if pickup and dropoff:
            logger.info(f"🔍 No exact matches found, trying flexible matching for pickup='{pickup}' and dropoff='{dropoff}'")
            real_trips = await TripRetriever.find_similar_routes(
                db=db,
                pickup_keyword=pickup,
                dropoff_keyword=dropoff,
                limit=5
            )
            logger.info(f"🔍 Retrieved {len(real_trips)} real trips from DB for pickup='{pickup}' and dropoff='{dropoff}'")

        # ============================================================
        # STEP 3: Build context message with REAL data
        # ============================================================
        context_message = None

        if real_trips:
            # Format real trip data gracefully
            trip_options = []
            for trip in real_trips:
                option = f"• {trip['vehicle_type']}:"
                if trip['avg_duration_min']:
                    option += f"~{trip['avg_duration_min']} minutes,"
                if trip['avg_distance_km']:
                    option += f"~{trip['avg_distance_km']} km,"
                if trip['avg_actual_fare']:
                    option += f"~Rp{trip['avg_actual_fare']:,}, "
                option += f"based on {trip['trip_count']} historical trips"
                if trip['avg_driver_rating']:
                    option += f" (⭐ {trip['avg_driver_rating']}/5 rating)"
                trip_options.append(option)

            context_content = f"""
            ═══════════════════════════════════════════════════════════
            REAL TRIP DATA from database for {pickup} -> {dropoff}:
            ═══════════════════════════════════════════════════════════

            {chr(10).join(trip_options)}

            ═══════════════════════════════════════════════════════════
            INSTRUCTIONS:
            1. ONLY use the vehicle types listed above (do not invent others)
            2. Present the actual numbers exactly as shown
            3. Ask user which vehicle they prefer
            4. Do NOT suggest public transportation (bus, train, grab, gojek, etc.)
            """

            context_message = {"role": "system", "content": context_content}
        else:
            context_content = f"""
            ═══════════════════════════════════════════════════════════
            NO HISTORICAL TRIP DATA FOUND in database for {pickup} -> {dropoff}.
            ═══════════════════════════════════════════════════════════
            
            Route searched: {pickup if pickup else "unknown"} -> {dropoff if dropoff else "unknown"}

            INSTRUCTIONS:
            1. Tell user: "I don't have historical trip data for '{pickup} to {dropoff}'"
            2. Ask user to try different locations or check spelling
            3. DO NOT invent routes, times, or prices from your knowledge
            4. DO NOT suggest public transportation (bus, train, grab, gojek, etc.)
            ═══════════════════════════════════════════════════════════
            """

            context_message = {"role": "system", "content": context_content}

        # ============================================================
        # STEP 4: Build final messages for LLM
        # ============================================================
        # Start with context message (highest priority)
        messages = [context_message]

        # Add original conversation history
        for msg in request.messages:
            messages.append(msg.model_dump())

        # Add optional Qdrant context if available (lower priority than real DB data)
        query_vector = embed_text(user_message)

        if query_vector:
            try:
                qdrant_vector_db.create_collection("chat_history", vector_size=384)
                context_results = qdrant_vector_db.search_vector(
                    collection_name="chat_history",
                    query_vector=query_vector,
                    limit=3
                )
                if context_results:
                    past_context = "\n".join([
                        f"- {r['metadata'].get('prompt', '?')[:100]}"
                        for r in context_results
                    ])
                    messages.append({
                        "role": "system",
                        "content": f"Past conversation context:\n{past_context}\n(Use this conversation flow, but prioritize REAL TRIP DATA above)"
                    })
            except Exception as e:
                logger.warning(f"❌ Qdrant search failed: {e}")

        # ============================================================
        # STEP 5: Call LLM with strict temperature
        # ============================================================
        logger.info(f"💬 Sending to LLM with real trip data: {len(real_trips)} options")
        response = await llm_service.chat(
            messages=messages,
            temperature=0.3, # Lower temperature = less hallucination, more reliance on provided data
            user_id=request.user_id,
            session_id=session_id
        )

        # ============================================================
        # STEP 6: Validate response (anti-hallucination checks)
        # ============================================================
        hallucination_keywords = ['transjakarta', 'bus', 'train', 'krl', 'mrt', 'lrt', 'angkot', 'grab', 
                                  'gojek', 'bluebird', 'maxim', 'didi', 'uber']
        detected_hallucinations = [kw for kw in hallucination_keywords if kw in response.lower()]
        
        if detected_hallucinations and not real_trips:
            logger.warning(f"⚠️ Hallucination detected in LLM response: {detected_hallucinations}")
            response = "I apologize, but I don't have real taxi data for that route. Could you please specify different pickup or dropoff" \
            "locations? I can only provide information based on our actual trip history data."

        # ============================================================
        # STEP 7: Store in Qdrant
        # ============================================================
        response_time_ms = int((time.time() - start_time) * 1000)
        tokens_estimate = len(user_message.split()) + len(response.split())
        cost_estimate = (tokens_estimate / 1000) * 0.0001 # Estimated cost estimation

        if query_vector:
            try:
                point_id = abs(hash(session_id + user_message)) % (10**9)
                
                # Qdrant store add point with metadata for monitoring
                qdrant_vector_db.add_point(
                    collection_name="chat_history",
                    point_id=str(point_id),
                    vector=query_vector,
                    metadata={
                        "user_id": request.user_id,
                        "session_id": session_id,
                        "prompt": user_message,
                        "response": response[:500],
                        "response_time_ms": response_time_ms,
                        "real_trips_used": len(real_trips)
                    }
                )
            except Exception as e:
                logger.warning(f"❌ Failed to store in Qdrant: {e}")

        # ============================================================
        # STEP 8: Log to Evidently to monitor for future analysis
        # ============================================================
        await evidently_monitor.log_llm_response(
            db=db,
            user_id=request.user_id,
            session_id=session_id,
            prompt=user_message,
            response=response,
            response_time_ms=response_time_ms,
            tokens_used=tokens_estimate,
            cost=cost_estimate,
        )

        return {
            "session_id": session_id,
            "response": response,
            "metadata": {
                "response_time_ms": response_time_ms,
                "tokens": tokens_estimate,
                "cost": f"${cost_estimate:.6f}",
                "real_trips_used": len(real_trips),
                "hallucination_blocked": len(detected_hallucinations) > 0,
                "pickup_extracted": pickup,
                "dropoff_extracted": dropoff
            }
        }
    
    except Exception as e:
        logger.error(f"❌ Error in /chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error processing chat: {str(e)}")

@router.post("/recommend-route")
async def recommend_route(request: RouteRecommendRequest, ml_predictor: MLPredictor = Depends(get_ml_predictor)):
    """Get route recommendation from natural language query."""
    recommendation = await llm_service.recommend_route(request.query, request.context)

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