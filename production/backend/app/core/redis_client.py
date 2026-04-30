import redis.asyncio as redis
from app.core.config import settings

_redis = None

async def get_redis() -> redis.Redis:
    global _redis
    if _redis is None:
        _redis = await redis.from_url(settings.REDIS_URL, decode_responses=True)
    
    return _redis