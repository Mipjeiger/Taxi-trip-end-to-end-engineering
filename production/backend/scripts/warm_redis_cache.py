import asyncio
import sys
from pathlib import Path
import logging
import json

# Add backend to path
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

from app.core.postgres_db import get_postgres_db
from app.services.redis_service import RedisService
from app.services.trip_retriever import TripRetriever
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

"""
Warm up Redis cache with popular routes and location encodings.
Run this after data ingestion or periodically.
"""

async def warm_cache():
    """Pre-populate Redis cache with frequently accessed data"""
    logger.info("🚀 Starting Redis cache warm-up")

    try:
        async for db in get_postgres_db():
            # Get popular routes
            query = text("""
                SELECT 
                    pickup_location,
                    dropoff_location,
                    ride_type,
                    COUNT(*) as trip_count,
                    AVG(duration_minutes) as avg_duration,
                    AVG(actual_fare) as avg_fare,
                    AVG(driver_rating) as avg_driver_rating
                FROM analytics.trip
                WHERE status = 'Completed'
                    AND pickup_location IS NOT NULL
                    AND dropoff_location IS NOT NULL    
                GROUP BY pickup_location, dropoff_location, ride_type
                ORDER BY trip_count DESC
            """)

            result = await db.execute(query)
            routes = result.fetchall()
            logger.info(f"📊 Caching {len(routes)} Popular routes")

            cached_count = 0
            popular_routes_list = []


            for route in routes:
                pickup = route[0]
                dropoff = route[1]
                ride_type = route[2]
                trip_count = route[3]
                avg_duration = float(route[4]) if route[4] else None
                avg_fare = float(route[5]) if route[5] else None
                avg_rating = float(route[6]) if route[6] else None

                # Build route features
                features = {
                    "routes": [
                        {
                            "vehicle_type": ride_type,
                            "avg_duration_min": avg_duration,
                            "avg_actual_fare": avg_fare,
                            "avg_driver_rating": avg_rating,
                            "trip_count": trip_count
                        }
                    ],
                    "pickup": pickup,
                    "dropoff": dropoff,
                    "count": 1,
                    "timestamp": __import__('datetime').datetime.now().isoformat()
                }
                
                # Cache route features in Redis
                success = await RedisService.set_route_features(pickup, dropoff, features)
                if success:
                    cached_count += 1
                    logger.info(f"✅ Cached route: {pickup} -> {dropoff} with features: {features}")

                # Add to popular routes list
                popular_routes_list.append({
                    "pickup": pickup,
                    "dropoff": dropoff,
                    "trip_count": trip_count,
                    "avg_fare": avg_fare,
                    "avg_duration": avg_duration,
                    "vehicle_type": ride_type
                })

            # cache popular routes list in Redis
            if popular_routes_list:
                await RedisService.set_popular_routes(popular_routes_list)
                logger.info(f"✅ Cached popular routes list with {len(popular_routes_list)} entries")

            # Verify cache
            await verify_cache(db)
            return {"cached_routes": cached_count}

    except Exception as e:
        logger.error(f"❌ Error during cache warm-up: {e}", exc_info=True)
        raise

async def verify_cache(db):
    """Verify that popular routes are cached in Redis"""
    try:
        from app.core.redis_client import get_redis
        redis_conn = await get_redis()

        # Get popular routes from Redis
        keys = await redis_conn.keys("route_features:*")
        logger.info(f"📊 Redis has {len(keys)} route_feature keys")

        # Show first 5 keys
        if keys:
            logger.info(f"🔑 Sample cached keys:")
            for key in keys[:5]:
                value = await redis_conn.get(key)
                if value:
                    try:
                        parsed = json.loads(value)
                        pickup = parsed.get('pickup', 'unknown')
                        dropoff = parsed.get('dropoff', 'unknown')
                        logger.info(f" : 🔑 {key}: {pickup} -> {dropoff}")
                    except:
                        logger.info(f" - {key}: {value[:100]}...")
        
        else:
            logger.warning("⚠️ No route_feature keys found in Redis")

    except Exception as e:
        logger.error(f"❌ Error verifying cache: {e}", exc_info=True)

if __name__ == "__main__":
    asyncio.run(warm_cache())