import logging
from fastapi import APIRouter, Depends
from app.services.redis_service import redis_service
from app.core.database import get_pg_db
from app.core.postgres_db import get_postgres_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.redis_client import get_redis
from datetime import datetime
from app.services.redis_service import CACHE_VERSION
from app.core.qdrant_client import qdrant_vector_db
from app.services.ml_predictor import MLPredictor
from app.api.dependencies import get_ml_predictor

router = APIRouter(prefix="/health", tags=["Health"])
logger = logging.getLogger(__name__)

@router.get("/redis")
async def health_redis():
    """Check Redis health and cache integrity"""
    return await redis_service.health_check()

@router.get("/qdrant")
async def qdrant_health():
    """Check Qdrant Cloud health"""
    return qdrant_vector_db.health_check()

@router.get("/cache/validate/{pickup}/{dropoff}")
async def validate_cache(
    pickup: str,
    dropoff: str,
    db: AsyncSession = Depends(get_postgres_db)
):
    """Validate cache against database for a specific route"""
    try:
        is_valid = await redis_service.validate_cache_against_db(db, pickup, dropoff)
        
        # Get cache status
        cached = await redis_service.get_route_features(pickup, dropoff)
        
        return {
            "pickup": pickup,
            "dropoff": dropoff,
            "cache_valid": is_valid,
            "cache_exists": cached is not None,
            "cached_routes": len(cached) if cached else 0,
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "status": "validation_failed"
        }

@router.post("/cache/clear")
async def clear_cache():
    """Clear all cache (use with caution)"""
    try:
        await redis_service.invalidate_route_cache()
        return {
            "success": True,
            "message": "All cache cleared",
            "timestamp": datetime.now().isoformat()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }

@router.get("/cache/stats")
async def cache_stats(db: AsyncSession = Depends(get_postgres_db)):
    """Get cache statistics"""
    try:
        redis = await get_redis()
        
        # Get all cache keys
        pattern = f"route_features:{CACHE_VERSION}:*"
        keys = await redis.keys(pattern)
        
        # Get database counts
        db_query = text("""
            SELECT 
                COUNT(*) as total_trips,
                COUNT(DISTINCT pickup_location) as unique_pickups,
                COUNT(DISTINCT dropoff_location) as unique_dropoffs
            FROM analytics.trip
            WHERE status = 'Completed'
        """)
        result = await db.execute(db_query)
        db_stats = result.fetchone()
        
        return {
            "cache_entries": len(keys),
            "cache_version": CACHE_VERSION,
            "database": {
                "total_trips": db_stats[0],
                "unique_pickups": db_stats[1],
                "unique_dropoffs": db_stats[2]
            },
            "timestamp": datetime.now().isoformat()
        }
        
    except Exception as e:
        return {
            "error": str(e),
            "status": "failed"
        }
    
@router.get("/ml")
async def ml_health(ml_predictor: MLPredictor = Depends(get_ml_predictor)):
    """
    Check ML model health
    """
    return {
        "status": "healthy" if ml_predictor.is_loaded else "unhealthy",
        "models_loaded": ml_predictor.is_loaded,
        "ctat_model": bool(ml_predictor.models.get('ctat_primary')),
        "vtat_model": bool(ml_predictor.models.get('vtat_primary')),
        "scaler_available": bool(ml_predictor.scalers.get('ultra')),
        "features_count": len(ml_predictor.features) if ml_predictor.features else 0
    }