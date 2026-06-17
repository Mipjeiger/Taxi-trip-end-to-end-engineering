import os
os.environ["TOKENIZERS_PARALLELISM"] = "false"

# Suppress HuggingFace warnings
import warnings
warnings.filterwarnings("ignore", message=".*unauthenticated requests.*")
warnings.filterwarnings("ignore", message=".*HF_TOKEN.*")

import logging
import time
import uuid
import json
import re
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
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
# Lazy-loaded embedding model
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
        vectors = list(model.embed([text]))
        return vectors[0].tolist()
    except Exception as e:
        logger.error(f"❌ Embedding generation failed: {e}")
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
    messages: List[Message]
    temperature: float = Field(default=0.7, ge=0, le=2)
    context: Optional[Dict] = None

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
async def chat_endpoint(request: ChatRequest, db: AsyncSession = Depends(get_postgres_db)):
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

        # Pattern 1: "from X to Y" or "dari X ke Y"
        pattern = r"(?:from|dari)\s+([^t]+?)\s+(?:to|ke)\s+([^?\.]+)"
        match = re.search(pattern, user_message, re.IGNORECASE)

        if match:
            pickup = match.group(1).strip()
            dropoff = match.group(2).strip()
        else:
            # Pattern 2: "X to Y"
            pattern2 = r"([^?\.]+?)\s+(?:to|ke)\s+([^?\.]+)"
            match2 = re.search(pattern2, user_message, re.IGNORECASE)
            if match2:
                pickup = match2.group(1).strip()
                dropoff = match2.group(2).strip()

        logger.info(f"📍 Extracted locations: pickup='{pickup}', dropoff='{dropoff}'")

        # ============================================================
        # STEP 2: Test Database connection (handle both dict and bool)
        # ============================================================
        try:
            connection_test = await TripRetriever.test_connection(db)
            
            # Handle both return types (dict or bool)
            is_connected = False
            if isinstance(connection_test, dict):
                is_connected = connection_test.get("connected", False)
            else:
                is_connected = connection_test
            
            if not is_connected:
                logger.error("❌ Database connection failed")
                return {
                    "session_id": session_id,
                    "response": "I'm having trouble connecting to the database. Please try again later.",
                    "metadata": {"error": "Database connection failed"}
                }
        except Exception as e:
            logger.error(f"Database test failed: {e}")
            # Continue anyway - the main query will fail if not connected

        # ============================================================
        # STEP 3: Retrieve REAL trip data from PostgreSQL
        # ============================================================
        real_trips = []
        if pickup and dropoff:
            real_trips = await TripRetriever.find_similar_routes(
                db=db,
                pickup_keyword=pickup,
                dropoff_keyword=dropoff,
                limit=5
            )
            logger.info(f"🔍 Retrieved {len(real_trips)} real trips from DB for '{pickup}' → '{dropoff}'")

        # ============================================================
        # STEP 4: Build response based on real data
        # ============================================================
        if real_trips:
            # Build response with real data
            response_text = f"✅ Found {len(real_trips)} vehicle options from {pickup} to {dropoff}:\n\n"
            for i, trip in enumerate(real_trips, 1):
                response_text += f"{i}. **{trip['vehicle_type']}**: "
                if trip.get('avg_duration_min'):
                    response_text += f"~{trip['avg_duration_min']} minutes, "
                if trip.get('avg_distance_km'):
                    response_text += f"{trip['avg_distance_km']} km, "
                if trip.get('avg_actual_fare'):
                    response_text += f"~Rp{trip['avg_actual_fare']:,}, "
                response_text += f"based on {trip['trip_count']} completed trip"
                if trip['trip_count'] > 1:
                    response_text += "s"
                if trip.get('avg_driver_rating'):
                    response_text += f" (driver rating: {trip['avg_driver_rating']}⭐)"
                response_text += "\n"
            response_text += "\nWhich vehicle would you like to book?"
            
            # Use this as the final response
            final_response = response_text
            
        else:
            # No trips found - provide helpful message
            final_response = f"I couldn't find any trips from '{pickup}' to '{dropoff}' in our database.\n\n"
            final_response += "Here are some popular routes we have data for:\n"
            
            # Get sample routes for suggestions
            all_routes = await TripRetriever.get_all_routes(db)
            if all_routes:
                unique_routes = {}
                for route in all_routes[:5]:
                    key = f"{route['pickup']} → {route['dropoff']}"
                    if key not in unique_routes:
                        unique_routes[key] = route['vehicle']
                        final_response += f"• {key} ({route['vehicle']})\n"
            
            final_response += "\nCould you try one of these routes or check your spelling?"

        # ============================================================
        # STEP 5: Build context message for LLM (if we want LLM enhancement)
        # ============================================================
        # Note: You can skip LLM entirely when we have real data
        # Or use LLM to enhance the response
        
        if real_trips:
            # Use LLM to polish the response (optional)
            context_message = {
                "role": "system",
                "content": f"""
                You are a helpful taxi assistant. Based on this real data:
                {final_response}
                
                Present this information in a friendly, natural way. 
                Do not add any information not in the data above.
                Do not suggest public transportation.
                """
            }
            
            messages = [context_message]
            for msg in request.messages:
                messages.append(msg.model_dump())
            
            # Call LLM for natural language polish
            response = await llm_service.chat(
                messages=messages,
                temperature=0.3,
                user_id=request.user_id,
                session_id=session_id
            )
        else:
            # No real data, use direct response without LLM
            response = final_response

        # ============================================================
        # STEP 6: Validate response (anti-hallucination checks)
        # ============================================================
        hallucination_keywords = ['transjakarta', 'bus', 'train', 'krl', 'mrt', 'lrt', 'angkot', 'grab', 
                                  'gojek', 'bluebird', 'maxim', 'didi', 'uber']
        detected_hallucinations = [kw for kw in hallucination_keywords if kw in response.lower()]
        
        if detected_hallucinations and not real_trips:
            logger.warning(f"⚠️ Hallucination detected: {detected_hallucinations}")
            response = "I apologize, but I don't have real taxi data for that route. Could you please specify different pickup or dropoff locations?"

        # ============================================================
        # STEP 7: Store in Qdrant (optional, don't fail if it errors)
        # ============================================================
        response_time_ms = int((time.time() - start_time) * 1000)
        tokens_estimate = len(user_message.split()) + len(response.split())
        cost_estimate = (tokens_estimate / 1000) * 0.0001

        query_vector = embed_text(user_message)
        if query_vector:
            try:
                qdrant_vector_db.create_collection("chat_history", vector_size=384)
                point_id = abs(hash(session_id + user_message)) % (10**9)
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
                logger.warning(f"⚠️ Failed to store in Qdrant: {e}")

        # ============================================================
        # STEP 8: Log to Evidently
        # ============================================================
        try:
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
        except Exception as e:
            logger.warning(f"⚠️ Failed to log to Evidently: {e}")

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

# ===============================================================
# Other Endpoints
# ===============================================================

@router.post("/recommend-route")
async def recommend_route(request: RouteRecommendRequest, ml_predictor: MLPredictor = Depends(get_ml_predictor)):
    """Get route recommendation from natural language query."""
    llm = LLMService()
    recommendation = await llm.recommend_route(request.query, request.context)

    if "pickup" in recommendation and "drop" in recommendation:
        try:
            pred = await ml_predictor.predict_ride_metrics(
                pickup=recommendation["pickup"],
                drop=recommendation["drop"],
                vehicle_type=recommendation.get("vehicle_type", "HRV"),
                hour=datetime.now().hour,
                day_of_week=datetime.now().weekday(),
                distance_km=recommendation.get("distance_km", 10),
            )
            recommendation["ml_estimated_time"] = pred["estimated_time_min"]
            recommendation["ml_estimated_price"] = pred["estimated_price_idr"]
        except Exception as e:
            recommendation["ml_error"] = str(e)

    return recommendation

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

@router.get("/db-test")
async def test_database(db: AsyncSession = Depends(get_postgres_db)):
    """Test database connection and return sample data."""
    try:
        result = await db.execute(text("SELECT COUNT(*) FROM analytics.trip"))
        total = result.scalar()

        result = await db.execute(text("SELECT COUNT(*) FROM analytics.trip WHERE status = 'Completed'"))
        completed = result.scalar()

        result = await db.execute(text("""
            SELECT pickup_location, dropoff_location, ride_type, COUNT(*) as cnt
            FROM analytics.trip 
            WHERE status = 'Completed'
            GROUP BY pickup_location, dropoff_location, ride_type
            ORDER BY cnt DESC
            LIMIT 10
        """))
        samples = result.fetchall()

        return {
            "status": "connected",
            "total_trips": total,
            "completed_trips": completed,
            "sample_routes": [
                {
                    "pickup": s[0],
                    "dropoff": s[1],
                    "vehicle": s[2],
                    "count": s[3]
                } 
                for s in samples
            ]
        }
    
    except Exception as e:
        logger.error(f"Database test error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
    
@router.get("/debug-route/{pickup}/{dropoff}")
async def debug_route(pickup: str, dropoff: str, db: AsyncSession = Depends(get_postgres_db)):
    """Debug endpoint to check why route isn't found."""
    try:
        direct_result = await TripRetriever.debug_direct_query(db, pickup, dropoff) # Test direct SQL query
        similar = await TripRetriever.find_similar_routes(db, pickup, dropoff) # Test similar routes retrieval
        
        # Get all routes sample for debugging
        all_routes = await TripRetriever.get_all_routes(db)

        return {
            "pickup": pickup,
            "dropoff": dropoff,
            "direct_query_result": len(direct_result),
            "direct_query_data": [{"vehicle": r[0], "pickup": r[1], "dropoff": r[2], "fare": r[3], "duration": r[4]}
                                  for r in direct_result],
            "similar_routes_found": len(similar),
            "similar_routes_data": similar,
            "all_routes_sample": all_routes[:10] if all_routes else []
        }
    
    except Exception as e:
        logger.error(f"Debug route error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Debug error: {str(e)}")
    
