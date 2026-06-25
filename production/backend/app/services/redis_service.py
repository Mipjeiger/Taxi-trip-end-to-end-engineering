import json
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timedelta

from app.core.redis_client import redis_get, redis_set, redis_delete, get_redis
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

"""
Redis service for caching and real-time features.
Centralizes all Redis operations for consistency.
"""
logger = logging.getLogger(__name__)

# Cache key constants
CACHE_VERSION = "v2" # Increment version to invalidate old cache
CACHE_KEYS = {
    "ROUTE_FEATURES": f"route_features:{CACHE_VERSION}:{{pickup}}:{{dropoff}}",
    "LOCATION_ENCODING": f"loc_enc:{CACHE_VERSION}:{{loc_type}}:{{location}}",
    "VTAT_PREDICTION": f"vtat_pred:{CACHE_VERSION}:{{ride_id}}",
    "POPULAR_ROUTES": f"popular_routes:{CACHE_VERSION}",
    "VEHICLE_TYPES": f"vehicle_types:{CACHE_VERSION}",
    "DRIVER_AVAILABILITY": f"driver_availability:{CACHE_VERSION}:{{location}}",
    "ROUTE_VALIDATION": f"route_validation:{CACHE_VERSION}:{{pickup}}:{{dropoff}}",
}

class RedisService:
    """Service for Redis caching operations"""

    @staticmethod
    async def get_route_features(pickup: str, dropoff: str) -> Optional[Dict]:
        """Get cached route features"""
        if not pickup or not dropoff:
            return None

        key = CACHE_KEYS["ROUTE_FEATURES"].format(pickup=pickup, dropoff=dropoff)
        data = await redis_get(key)

        if data:
            try:
                parsed = json.loads(data)

                # Validate cached data structure
                if not RedisService._validate_route_data(parsed):
                    logger.warning(f"⚠️ Invalid cached route data for key {key}: {parsed}")
                    await redis_delete(key)
                    return None
                
                # Check if cache is stale (older than 6 hours)
                timestamp = parsed.get("timestamp")
                if timestamp:
                    try:
                        cache_time = datetime.fromisoformat(timestamp)
                        if datetime.now() - cache_time > timedelta(hours=6):
                            logger.info(f"🔄 Cache stale for {pickup} → {dropoff}, refreshing")
    
                            return None
                    
                    except ValueError:
                        logger.error(f"❌ Invalid timestamp format in cache for key {key}: {timestamp}")
                        return None
                    
                # Verify the data matches the requested route
                cached_pickup = parsed.get('pickup', '').lower()
                cached_dropoff = parsed.get('dropoff', '').lower()

                if cached_pickup != pickup.lower().strip() or cached_dropoff != dropoff.lower().strip():
                    logger.warning(f"⚠️ Cache route mismatch for key {key}: expected {pickup} → {dropoff}, got {cached_pickup} → {cached_dropoff}")
                    await redis_delete(key)
                    return None
                    
                logger.info(f"✅ Valid cache hit for {pickup} → {dropoff} ({len(parsed.get('routes', []))} routes)")
                return parsed.get('routes', [])
            
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.error(f"❌ Error parsing cached route data for key {key}: {e}")
                await redis_delete(key)
                return None

        return None
    
    @staticmethod
    def _validate_route_data(data: Dict) -> bool:
        """Validate that cached route data has the correct structure"""
        if not isinstance(data, dict):
            return False
        
        # Check required fields
        if 'routes' not in data:
            return False
        
        if not isinstance(data['routes'], list):
            return False
        
        # Validate each route has required fields
        for route in data['routes']:
            if not isinstance(route, dict):
                return False
            
            # Check required fields in valid route
            required_fields = ['vehicle_type']
            for field in required_fields:
                if field not in route:
                    return False

        return True

    @staticmethod
    async def set_route_features(
        pickup: str, 
        dropoff: str, 
        features: Dict, 
        ttl: int = 21600  # 6 hours max
    ) -> bool:
        """
        Cache route features with validation and expiration.
        Only caches if data is valid.
        """
        if not pickup or not dropoff:
            logger.error("❌ Pickup and dropoff locations must be provided")
            return False

        # Validate data before caching
        if not RedisService._validate_route_data(features):
            logger.error(f"❌ Invalid data structure for {pickup} → {dropoff}, not caching")
            return False
        
        # Don't cache empty results (prevents hallucination)
        if not features.get('routes'):
            logger.info(f"⚠️ No valid routes to cache for {pickup} → {dropoff}")
            return False
        
        # Add timestamp for freshness tracking
        features['timestamp'] = datetime.now().isoformat()
        features['pickup'] = pickup
        features['dropoff'] = dropoff
        features['source'] = 'database'
        features['version'] = CACHE_VERSION
        
        key = CACHE_KEYS["ROUTE_FEATURES"].format(
            pickup=pickup.lower(), 
            dropoff=dropoff.lower()
        )
        
        try:
            success = await redis_set(key, json.dumps(features), expire=ttl)
            if success:
                logger.info(f"✅ Cached {len(features.get('routes', []))} routes for {pickup} → {dropoff}")
            return success
        
        except Exception as e:
            logger.error(f"❌ Failed to cache route data: {e}")
            return False

    @staticmethod
    async def get_driver_availability(vehicle_type: str) -> Optional[List[Dict]]:
        """Get cached driver availability for a vehicle type"""
        key = CACHE_KEYS["DRIVER_AVAILABILITY"].format(location=vehicle_type.lower())
        data = await redis_get(key)

        if data:
            try:
                parsed = json.loads(data)

                # Validate structure
                if not isinstance(parsed, list):
                    await redis_delete(key)
                    return None
                
                # Validate each driver
                for driver in parsed:
                    if not isinstance(driver, dict) or 'driver_id' not in driver:
                        await redis_delete(key)
                        return None
                    
                return parsed
                
            except json.JSONDecodeError:
                await redis_delete(key)
                return None
            
        return None
    
    @staticmethod
    async def set_driver_availability(vehicle_type: str, drivers: List[Dict], ttl: int = 300) -> bool:
        """Cached driver availability for a vehicle type"""
        if not vehicle_type or not drivers:
            return False
        
        # Validate drivers
        for driver in drivers:
            if not isinstance(driver, dict) or 'driver_id' not in driver:
                logger.error(f"❌ Invalid driver data for vehicle type {vehicle_type}: {driver}")
                return False
            
        key = CACHE_KEYS["DRIVER_AVAILABILITY"].format(location=vehicle_type.lower())

        try:
            await redis_set(key, json.dumps(drivers), expire=ttl)
            logger.info(f"✅ Cached availability for {len(drivers)} drivers of type {vehicle_type} (TTL: {ttl}s)")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to cache driver availability: {e}")
            return False

    @staticmethod
    async def get_location_encoding(location: str, loc_type: str = "pickup") -> Optional[int]:
        """Get cached location encoding with validation"""
        
        key = CACHE_KEYS["LOCATION_ENCODING"].format(loc_type=loc_type, location=location.lower())
        data = await redis_get(key)
        
        if data:
            
            try:
                parsed = json.loads(data)
                
                # Validate structure
                if not isinstance(parsed, dict) or 'encoding' not in parsed:
                    await redis_delete(key)
                    return None
                
                # Validate encoding is an integer
                encoding = parsed.get('encoding')
                if not isinstance(encoding, int):
                    await redis_delete(key)
                    return None
                
                return encoding
                
            except (json.JSONDecodeError, ValueError, TypeError):
                await redis_delete(key)
                return None
        
        return None
    
    @staticmethod
    async def set_location_encoding(
        location: str, 
        encoding: int, 
        loc_type: str = "pickup", 
        ttl: int = 86400  # 24 hours
    ) -> bool:
        """Cache location encoding with validation"""
        if not isinstance(encoding, int) or encoding < 0:
            logger.error(f"❌ Invalid encoding value: {encoding}")
            return False
        
        key = CACHE_KEYS["LOCATION_ENCODING"].format(loc_type=loc_type, location=location.lower())
        
        try:
            await redis_set(key, json.dumps({
                'encoding': encoding,
                'location': location,
                'timestamp': datetime.now().isoformat()
            }), expire=ttl)
            return True
        except Exception as e:
            logger.error(f"❌ Failed to cache location encoding: {e}")
            return False

    @staticmethod
    async def cache_vtat_prediction(ride_id: str, vtat_minutes: float, ttl: int = 3600):
        """Cached VTAT prediction for a ride"""
        key = CACHE_KEYS["VTAT_PREDICTION"].format(ride_id=ride_id)
        await redis_set(key, json.dumps({'vtat': vtat_minutes}), expire=ttl)

    @staticmethod
    async def get_vtat_prediction(ride_id: str) -> Optional[float]:
        """Get cached VTAT prediction for a ride"""
        key = CACHE_KEYS["VTAT_PREDICTION"].format(ride_id=ride_id)
        data = await redis_get(key)

        if data:
            try:
                parsed = json.loads(data)
                if isinstance(parsed, dict) and 'vtat' in parsed:
                    return float(parsed['vtat'])
            except (json.JSONDecodeError, ValueError, TypeError):
                pass
        return None
    
    @staticmethod
    async def invalidate_route_cache(pickup: str = None, dropoff: str = None):
        """Safely invalidate cache entries"""
        if pickup and dropoff:
            key = CACHE_KEYS["ROUTE_FEATURES"].format(pickup=pickup.lower().strip(), dropoff=dropoff.lower().strip())
            await redis_delete(key)
            logger.info(f"🗑️ Invalidated cache for {pickup} → {dropoff}")
        else:
            # Invalidate all route features with version prefix
            redis = await get_redis()
            pattern = f"route_features:{CACHE_VERSION}:*"
            keys = await redis.keys(pattern)
            if keys:
                await redis.delete(*keys)
                logger.info(f"🗑️ Invalidated {len(keys)} cache entries")

    @staticmethod
    async def get_popular_routes(limit: int = 20) -> List[Dict]:
        """Get cached popular routes with validation"""
        data = await redis_get(CACHE_KEYS["POPULAR_ROUTES"])
        
        if data:
            try:
                parsed = json.loads(data)
                
                # Validate structure
                if not isinstance(parsed, list):
                    await redis_delete(CACHE_KEYS["POPULAR_ROUTES"])
                    return []
                
                # Validate each route
                valid_routes = []
                for route in parsed[:limit]:
                    if isinstance(route, dict) and 'pickup' in route and 'dropoff' in route:
                        valid_routes.append(route)
                
                if len(valid_routes) != len(parsed[:limit]):
                    logger.warning("⚠️ Some popular routes had invalid structure")
                
                return valid_routes
                
            except (json.JSONDecodeError, ValueError):
                await redis_delete(CACHE_KEYS["POPULAR_ROUTES"])
                return []
        
        return []
    
    @staticmethod
    async def set_popular_routes(routes: List[Dict], ttl: int = 3600) -> bool:
        """Cache popular routes with validation"""
        if not routes:
            logger.warning("⚠️ Attempted to cache empty popular routes")
            return False
        
        # Validate each route
        valid_routes = []
        for route in routes:
            if isinstance(route, dict) and 'pickup' in route and 'dropoff' in route:
                valid_routes.append(route)
        
        if not valid_routes:
            logger.error("❌ No valid routes to cache")
            return False
        
        try:
            await redis_set(
                CACHE_KEYS["POPULAR_ROUTES"], 
                json.dumps(valid_routes), 
                expire=ttl
            )
            logger.info(f"✅ Cached {len(valid_routes)} popular routes")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to cache popular routes: {e}")
            return False
        
    @staticmethod
    async def validate_cache_against_db(
        db: AsyncSession,
        pickup: str,
        dropoff: str
    ) -> bool:
        """
        Validate cached data against database.
        Returns True if cache matches database, False otherwise.
        """
        try:
            # Query database for the route
            query = text("""
                SELECT COUNT(*) 
                FROM analytics.trip
                WHERE status = 'Completed'
                  AND pickup_location ILIKE :pickup
                  AND dropoff_location ILIKE :dropoff
            """)
            
            result = await db.execute(query, {
                "pickup": f"%{pickup}%",
                "dropoff": f"%{dropoff}%"
            })
            db_count = result.scalar()
            
            # Get cached data
            cached = await RedisService.get_route_features(pickup, dropoff)
            
            # If database has trips but cache says none, invalidate cache
            if db_count > 0 and cached is None:
                logger.warning(f"⚠️ Cache mismatch for {pickup} → {dropoff}, invalidating")
                await RedisService.invalidate_route_cache(pickup, dropoff)
                return False
            
            # If cache has data but database has no trips (stale cache)
            if db_count == 0 and cached is not None:
                logger.warning(f"⚠️ Cache mismatch for {pickup} → {dropoff}, invalidating")
                await RedisService.invalidate_route_cache(pickup, dropoff)
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Cache validation failed: {e}")
            await db.rollback()
            return False
        
    @staticmethod
    async def health_check() -> Dict:
        """Check Redis health and cache integrity"""
        try:
            redis = await get_redis()
            await redis.ping()
            
            # Check if popular routes exist
            popular = await redis_get(CACHE_KEYS["POPULAR_ROUTES"])
            
            return {
                "status": "healthy",
                "connected": True,
                "popular_routes_cached": popular is not None,
                "cache_version": CACHE_VERSION,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "connected": False,
                "error": str(e)
            }
        
# Singleton instance for RedisService
redis_service = RedisService()