import redis.asyncio as redis
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

_redis = None

async def get_redis() -> redis.Redis:
    """Get or create Redis connection"""
    global _redis
    if _redis is None:
        try:
            _redis = await redis.from_url(settings.REDIS_URL, decode_responses=True)
            await _redis.ping() # Test connection
            logger.info("✅ Connected to Redis successfully")
        except Exception as e:
            logger.error(f"❌ Redis connection failed: {e}")
            _redis = None
            raise
    
    return _redis

async def close_redis():
    """Close Redis connection"""
    global _redis
    if _redis is not None:
        await _redis.close()
        _redis = None
        logger.info("✅ Redis connection closed")

# For redis operations connection handling
async def redis_get(key: str) -> str | None:
    """Get value from Redis"""
    try:
        redis_conn = await get_redis()
        return await redis_conn.get(key)
    except Exception as e:
        logger.error(f"Redis GET error: {e}")
        return None


async def redis_set(key: str, value: str, expire: int = 3600) -> bool:
    """Set value in Redis with expiration"""
    try:
        redis_conn = await get_redis()
        await redis_conn.setex(key, expire, value)
        return True
    except Exception as e:
        logger.error(f"Redis SET error: {e}")
        return False


async def redis_delete(key: str) -> bool:
    """Delete key from Redis"""
    try:
        redis_conn = await get_redis()
        await redis_conn.delete(key)
        return True
    except Exception as e:
        logger.error(f"Redis DELETE error: {e}")
        return False