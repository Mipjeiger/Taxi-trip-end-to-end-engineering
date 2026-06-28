from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
from app.core.prometheus_metrics import REGISTRY
from app.services.ml_monitor import ml_monitor
from datetime import datetime
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Router prometheus metrics endpoint
@router.get("/metrics")
async def get_metrics():
    try:
        return Response(
            content=generate_latest(REGISTRY),
            media_type=CONTENT_TYPE_LATEST
        )
    
    except Exception as e:
        logger.error(f"Error generating metrics: {e}")
        return {"error": str(e)}
    
@router.get("/ml-stats")
async def get_ml_stats(hours: int = 24):
    """Get ML prediction statistics for monitoring"""
    try:
        stats = ml_monitor.get_error_stats(hours)
        error_stats = ml_monitor.get_error_stats(hours)

        return {
            "prediction_stats": stats,
            "error_stats": error_stats,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Error fetching ML stats: {e}")
        return {"error": str(e)}