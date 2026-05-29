import time
import logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List
from app.core.qdrant_client import qdrant_client

logger = logging.getLogger(__name__)
router = APIRouter()

class SemanticSearchRequest(BaseModel):
    query_embedding: List[float]
    limit: int = 5
    search_type: str = "llm" # llm, rides, driver

class SemanticSearchResponse(BaseModel):
    results: List[dict]
    total_found: int

@router.get("/health")
async def semantic_search_health():
    """Check Qdrant health"""
    return {
        "connected": qdrant_client.connected,
        "status": "✅ Connected to Qdrant" if qdrant_client.connected else "❌ Not connected to Qdrant"
    }

@router.post("/search")
async def semantic_search(request: SemanticSearchRequest) -> SemanticSearchResponse:
    """Semantic search through LLM interactions or ride requests"""
    try:
        if request.search_type == "llm":
            results = qdrant_client.semantic_search_llm(
                query_embedding=request.query_embedding,
                limit=request.limit
            )
        elif request.search_type == "rides":
            results = qdrant_client.find_similar_rides(
                query_embedding=request.query_embedding,
                limit=request.limit
            )
        else:
            raise HTTPException(status_code=400, detail="Invalid search_type.")
        
        return SemanticSearchResponse(
            results=results,
            total_found=len(results)
        )
    except Exception as e:
        logger.error(f"❌ Semantic search failed: {e}")
        raise HTTPException(status_code=500, detail="Semantic search failed.")
    

@router.post("/store-llm-prompt")
async def store_llm_prompt(
    prompt_id: str,
    prompt_text: str,
    response_text: str,
    prompt_embedding: List[float],
    response_embedding: List[float],
    user_id: str = None,
    session_id: str = None
):
    """Store LLM interaction with embeddings for semantic search"""
    try:
        success = qdrant_client.store_llm_prompt(
            prompt_id=prompt_id,
            prompt_text=prompt_text,
            response_text=response_text,
            prompt_embedding=prompt_embedding,
            response_embedding=response_embedding,
            metadata={
                "user_id": user_id,
                "session_id": session_id,
                "timestamp": time.time()
            }
        )

        if success:
            return {"status": "✅ LLM prompt stored successfully in Qdrant"}
        else:
            raise HTTPException(status_code=500, detail="Failed to store LLM prompt in Qdrant.")
    except Exception as e:
        logger.error(f"❌ Failed to store LLM prompt: {e}")
        raise HTTPException(status_code=500, detail="Failed to store LLM prompt in Qdrant.")