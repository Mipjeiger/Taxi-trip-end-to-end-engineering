import logging
from fastapi import APIRouter, Depends
from app.core.redis_client import redis_health_check
from app.core.postgres_db import get_postgres_db
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

router = APIRouter(prefix="/health", tags=["Health"])
logger = logging.getLogger(__name__)

@router.get("/redis")
async def health_redis():
    """Check Redis health"""
    is_healthy = await redis_health_check()
    return {
        "service": "Redis",
        "status": "healthy" if is_healthy else "unhealthy",
        "connected": is_healthy
    }

@router.get("/postgres")
async def health_postgres(db: AsyncSession = Depends(get_postgres_db)):
    """Check PostgreSQL health"""
    try:
        await db.execute(text("SELECT 1"))
        return {
            "service": "postgresql",
            "status": "healthy",
            "connected": True
        }
    except Exception as e:
        return {
            "service": "postgresql",
            "status": "unhealthy",
            "error": str(e)
        }

@router.get("/all")
async def health_all(db: AsyncSession = Depends(get_postgres_db)):
    """Check all services health"""
    redis_ok = await redis_health_check()
    
    pg_ok = False
    pg_error = None
    try:
        await db.execute(text("SELECT 1"))
        pg_ok = True
    except Exception as e:
        pg_error = str(e)
    
    return {
        "services": {
            "redis": {
                "status": "healthy" if redis_ok else "unhealthy",
                "connected": redis_ok
            },
            "postgresql": {
                "status": "healthy" if pg_ok else "unhealthy",
                "connected": pg_ok,
                "error": pg_error
            }
        },
        "overall": "healthy" if (redis_ok and pg_ok) else "degraded"
    }