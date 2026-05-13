from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, field_validator
from typing import List, Dict, Optional, Literal
from datetime import datetime
import logging
from app.services.llm_services import LLMService
from app.api.dependencies import get_ml_predictor
from app.services.ml_predictor import MLPredictor

router = APIRouter()
logger = logging.getLogger(__name__)

class Message(BaseModel):
    role: Literal["user", "assistant", "system"] = Field(
        ..., description="Role of message sender"
    )
    content: str = Field(
        ..., min_length=1, description="Content of the message"
    )

    @field_validator("role")
    def validate_role(cls, v):
        if v not in ["user", "assistant", "system"]:
            raise ValueError(f"Role must be one of: user, assistant, system. Got: {v}")
        return v

class ChatRequest(BaseModel):
    messages: List[Message] = Field(..., min_items=1, description="List of messages in the conversation")
    temperature: float = Field(default=0.7, ge=0, le=2, description="Sampling temperature for response generation (0-2)")

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
async def chat_endpoint(request: ChatRequest):
    """Generate chat with the LLM."""
    try:
        if not request.messages:
            raise HTTPException(status_code=400, detail="Messages list cannot be empty.")

        for i, msg in enumerate(request.messages):
            if not msg.role:
                raise HTTPException(status_code=400, detail=f"Message {i} is missing 'role' field.")
            if not msg.content or not msg.content.strip():
                raise HTTPException(status_code=400, detail=f"Message {i} has empty 'content' field.")
            
        logger.info(f"✅ Chat request validated: {len(request.messages)} messages")

        # Convert pydantic message objects to dicts for LLMService
        messages_dict = [msg.model_dump() for msg in request.messages]
        
        # Define LLM service and get response
        llm = LLMService()
        response = await llm.chat(messages_dict, request.temperature)

        return {
            "response": response,
            "model": "llama-3.1-8b-instant",
            "status": "success"
        }
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ Error in chat endpoint: {type(e).__name__}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Chat failed: {str(e)}")


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