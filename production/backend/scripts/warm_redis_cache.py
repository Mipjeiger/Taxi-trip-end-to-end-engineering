import asyncio
import sys
from pathlib import Path
import logging

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

    async for db in get_postgres_db():
        # Get popular routes
        query = text("""
            SELECT 
                pickup_location,
                dropoff_location,
                COUNT(*) as trip_count,
                AVG(duration_minutes) as avg_duration,
                AVG(actual_fare) as avg_fare
            FROM analytics.trip
            WHERE status = 'Completed'
                AND pickup_location IS NOT NULL
                AND dropoff_location IS NOT NULL    
            GROUP BY pickup_location, dropoff_location
            ORDER BY trip_count DESC
            LIMIT 50
        """)

        result = await db.execute(query)
        routes = result.fetchall()
        logger.info(f"📊 Caching {len(routes)} Popular routes")

        cached_count = 0
        for route in routes:
            pickup = route[0]
            dropoff = route[1]

            # Build route features
            features = {
                 "routes": [
                    {
                        "vehicle_type": "Car",
                        "avg_duration_min": float(route[3]) if route[3] else None,
                        "avg_actual_fare": float(route[4]) if route[4] else None,
                        "trip_count": route[2]
                    }
                ],
                "pickup": pickup,
                "dropoff": dropoff,
                "count": 1
            }
            
            # Cache route features
            await RedisService.set_route_features(pickup, dropoff, features)
            cached_count += 1

            if cached_count % 10 == 0:
                logger.info(f"✅ Cached {cached_count} routes so far...")

        # Cache popular routes list
        logger.info(f"📊 Caching popular routes list")
        popular_routes = await TripRetriever.get_all_routes(db, limit=20)
        logger.info(f"✅ Cached {len(popular_routes)} popular routes list")

        logger.info("🎉 Redis cache warm-up completed successfully!")
        return {"cached_routes": cached_count}

if __name__ == "__main__":
    asyncio.run(warm_cache())