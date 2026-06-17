import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta
from app.core.redis_client import redis_get, redis_set, redis_delete, get_redis

"""
Redis service for caching and real-time features.
Centralizes all Redis operations for consistency.
"""
logger = logging.getLogger(__name__)

# Cache key constants
CACHE_KEYS = {
    "ROUTE_FEATURES": "route_features:{pickup}:{dropoff}",
    "LOCATION_ENCODING": "loc_enc:{loc_type}:{location}",
    "VTAT_PREDICTION": "vtat_pred:{ride_id}",
    "POPULAR_ROUTES": "popular_routes",
    "VEHICLE_TYPES": "vehicle_types",
    "DEMAND_PRESSURE": "demand_pressure:{pickup}:{dropoff}",
}

class RedisService:
    """Service for Redis caching operations"""

    @staticmethod
    async def get_route_features(pickup: str, dropoff: str) -> Optional[Dict]:
        """Get cached route features"""
        key = CACHE_KEYS["ROUTE_FEATURES"].format(pickup=pickup, dropoff=dropoff)
        data = await redis_get(key)

        if data:
            try:
                return json.loads(data)
            except:
                return None
        return None
    
    @staticmethod
    async def set_route_features(pickup: str, dropoff: str, features: Dict, ttl: int = 86400):
        """Cache route features with TTL (default 24 hours)"""
        key = CACHE_KEYS["ROUTE_FEATURES"].format(pickup=pickup, dropoff=dropoff)
        await redis_set(key, json.dumps(features), ttl)

    @staticmethod
    async def get_location_encoding(location: str, loc_type: str = "pickup") -> Optional[int]:
        """Get cached location encoding"""
        key = CACHE_KEYS["LOCATION_ENCODING"].format(loc_type=loc_type, location=location.lower())
        data = await redis_get(key)

        if data:
            try:
                return int(data)
            except:
                return None
        return None
    
    @staticmethod
    async def set_location_encoding(location: str, loc_type: str, encoding: int, ttl: int = 86400):
        """Cache location encoding with TTL (default 24 hours)"""
        key = CACHE_KEYS["LOCATION_ENCODING"].format(loc_type=loc_type, location=location.lower())
        await redis_set(key, str(encoding), expire=ttl)

    @staticmethod
    async def cache_vtat_prediction(ride_id: str, vtat_minutes: float, ttl: int = 3600):
        """Cached VTAT prediction for a ride"""
        key = CACHE_KEYS["VTAT_PREDICTION"].format(ride_id=ride_id)
        await redis_set(key, str(vtat_minutes), expire=ttl)

    @staticmethod
    async def get_vtat_prediction(ride_id: str) -> Optional[float]:
        """Get cached VTAT prediction for a ride"""
        key = CACHE_KEYS["VTAT_PREDICTION"].format(ride_id=ride_id)
        data = await redis_get(key)

        if data:
            try:
                return float(data)
            except:
                return None
        return None
    
    @staticmethod
    async def invalidate_route_cache(pickup: str = None, dropoff: str = None):
        """Invalidate route cache entries"""
        if pickup and dropoff:
            key = CACHE_KEYS["ROUTE_FEATURES"].format(pickup=pickup, dropoff=dropoff)
            await redis_delete(key)
        else:
            # Invalidate all route features (use with caution)
            redis = await get_redis()
            keys = await redis.keys("route_features:*")
            if keys:
                await redis.delete(*keys)

    @staticmethod
    async def get_popular_routes(limit: int = 10) -> List[Dict]:
        """Get cached popular routes"""
        data = await redis_get(CACHE_KEYS["POPULAR_ROUTES"])
        if data:
            try:
                routes = json.loads(data)
                return routes[:limit]
            except:
                pass
        return []
    
    @staticmethod
    async def set_popular_routes(routes: List[Dict], ttl: int = 3600):
        """Cache popular routes"""
        await redis_set(CACHE_KEYS["POPULAR_ROUTES"], json.dumps(routes), expire=ttl)