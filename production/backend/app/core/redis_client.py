import redis.asyncio as redis
from app.core.config import settings
import logging
import json
from typing import Optional, Any

logger = logging.getLogger(__name__)

_redis = None

async def get_redis() -> redis.Redis:
    """Get or create Redis connection"""
    global _redis
    if _redis is None:
        try:
            _redis = await redis.from_url(
                settings.REDIS_URL, 
                decode_responses=True,
                socket_keepalive=True,
                socket_timeout=5,
                retry_on_timeout=True
            )
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

async def redis_get(key: str) -> Optional[str]:
    """Get value from Redis with error handling"""
    try:
        redis_conn = await get_redis()
        return await redis_conn.get(key)
    except Exception as e:
        logger.error(f"Redis GET error for key {key}: {e}")
        return None

async def redis_set(key: str, value: str, expire: int = 3600) -> bool:
    """Set value in Redis with expiration"""
    try:
        redis_conn = await get_redis()
        await redis_conn.setex(key, expire, value)
        return True
    except Exception as e:
        logger.error(f"Redis SET error for key {key}: {e}")
        return False

async def redis_delete(key: str) -> bool:
    """Delete key from Redis"""
    try:
        redis_conn = await get_redis()
        await redis_conn.delete(key)
        return True
    except Exception as e:
        logger.error(f"Redis DELETE error for key {key}: {e}")
        return False

async def redis_get_json(key: str) -> Optional[Any]:
    """Get JSON value from Redis"""
    data = await redis_get(key)
    if data:
        try:
            return json.loads(data)
        except:
            return None
    return None

async def redis_set_json(key: str, value: Any, expire: int = 3600) -> bool:
    """Set JSON value in Redis"""
    return await redis_set(key, json.dumps(value), expire)

async def redis_exists(key: str) -> bool:
    """Check if key exists in Redis"""
    try:
        redis_conn = await get_redis()
        return await redis_conn.exists(key) > 0
    except Exception as e:
        logger.error(f"Redis EXISTS error for key {key}: {e}")
        return False

async def redis_health_check() -> bool:
    """Check Redis health"""
    try:
        redis_conn = await get_redis()
        await redis_conn.ping()
        return True
    except:
        return False

