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
            GROUP BY pickup_location, dropoff_location
            ORDER BY trip_count DESC
            LIMIT 50
        """)

        result = await db.execute(query)
        routes = result.fetchall()
        logger.info(f"📊 Caching {len(routes)} Popular routes")

        for route in routes:
            pickup = route[0]
            dropoff = route[1]

            # Build route features
            features = {
                "trip_count": route[2],
                "avg_duration": float(route[3]) if route[3] else None,
                "avg_fare": float(route[4]) if route[4] else None,
                "routes": [
                    {
                        "vehicle_type": "Car",
                        "avg_duration_min": float(route[3]) if route[3] else None,
                        "avg_actual_fare": float(route[4]) if route[4] else None,
                        "trip_count": route[2]
                    }
                ]
            }
            
            # Cache route features
            await RedisService.set_route_features(pickup, dropoff, features)
            logger.info(f"✅ Cached route: {pickup} → {dropoff}")

        # Cache popular routes list
        popular_routes = [
            {
                "pickup": r[0],
                "dropoff": r[1],
                "count": r[2]
            }
            for r in routes[:10]
        ]
        await RedisService.set_popular_routes(popular_routes)
        
        logger.info("✅ Redis cache warm-up complete!")

if __name__ == "__main__":
    asyncio.run(warm_cache())