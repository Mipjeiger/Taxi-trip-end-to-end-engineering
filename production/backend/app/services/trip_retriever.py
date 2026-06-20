import logging
import random
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Optional
from app.services.redis_service import redis_service
from datetime import datetime

logger = logging.getLogger(__name__)

class TripRetriever:
    
    @staticmethod
    async def get_all_routes(db: AsyncSession, limit: int = 20) -> List[Dict]:
        """Get all unique routes for debugging and analysis with Redis caching"""
        
        # Try Redis cache first
        cached = await redis_service.get_popular_routes()
        if cached:
            logger.info("✅ Cache hit for popular routes")
            return cached[:limit]
        
        try:
            query = text("""
                SELECT 
                    pickup_location,
                    dropoff_location,
                    ride_type,
                    COUNT(*) as trip_count,
                    ROUND(AVG(actual_fare), 0) as avg_fare,
                    ROUND(AVG(duration_minutes), 1) as avg_duration
                FROM analytics.trip
                WHERE status = 'Completed'
                    AND pickup_location IS NOT NULL
                    AND dropoff_location IS NOT NULL
                GROUP BY pickup_location, dropoff_location, ride_type
                ORDER BY trip_count DESC
                LIMIT :limit
            """)
            
            result = await db.execute(query, {"limit": limit})
            rows = result.fetchall()
            
            routes = [
                {
                    "pickup": row[0],
                    "dropoff": row[1],
                    "vehicle_type": row[2],
                    "trip_count": row[3],
                    "avg_fare": float(row[4]) if row[4] else None,
                    "avg_duration": float(row[5]) if row[5] else None
                }
                for row in rows
            ]
            
            # Cache results
            if routes:
                await redis_service.set_popular_routes(routes)
                logger.info(f"✅ Cached {len(routes)} popular routes")
            
            return routes
            
        except Exception as e:
            logger.error(f"❌ Failed to get routes: {e}")
            return []

    @staticmethod
    async def find_similar_routes(
        db: AsyncSession,
        pickup_keyword: str,
        dropoff_keyword: str,
        limit: int = 5
    ) -> List[Dict]:
        """Find real trips with Redis caching and validation"""

        if not pickup_keyword or not dropoff_keyword:
            logger.warning("⚠️ Missing pickup or dropoff keyword")
            return []
        
        # Try Redis cache first with validation
        cached = await redis_service.get_route_features(pickup_keyword, dropoff_keyword)
        
        if cached is not None:
            # Validate cache against database (every 10th request or random sample)
            if random.random() < 0.1:  # 10% validation rate
                is_valid = await redis_service.validate_cache_against_db(
                    db, pickup_keyword, dropoff_keyword
                )
                if not is_valid:
                    logger.info(f"🔄 Cache invalid for {pickup_keyword} → {dropoff_keyword}, refreshing")
                    cached = None
                else:
                    logger.info(f"✅ Valid cache hit for {pickup_keyword} → {dropoff_keyword}")
                    return cached
            else:
                logger.info(f"✅ Cache hit for {pickup_keyword} → {dropoff_keyword}")
                return cached
        
        try:
            logger.info(f"🔍 Querying DB for {pickup_keyword} → {dropoff_keyword}")
            
            query = text("""
                SELECT 
                    ride_type,
                    ROUND(AVG(duration_minutes), 1) as avg_duration,
                    ROUND(AVG(distance_km), 1) as avg_distance,
                    ROUND(AVG(actual_fare), 2) as avg_fare,
                    ROUND(AVG(driver_rating), 1) as avg_rating,
                    COUNT(*) as trip_count
                FROM analytics.trip
                WHERE status = 'Completed'
                    AND pickup_location ILIKE :pickup
                    AND dropoff_location ILIKE :dropoff
                GROUP BY ride_type
                ORDER BY trip_count DESC
                LIMIT :limit
            """)
            
            result = await db.execute(query, {
                "pickup": f"%{pickup_keyword}%",
                "dropoff": f"%{dropoff_keyword}%",
                "limit": limit
            })
            rows = result.fetchall()
            
            if rows:
                routes = TripRetriever._format_results(rows)
                
                # Only cache if we have real data
                if routes:
                    cache_data = {
                        'routes': routes,
                        'pickup': pickup_keyword,
                        'dropoff': dropoff_keyword,
                        'count': len(routes)
                    }
                    await redis_service.set_route_features(
                        pickup_keyword,
                        dropoff_keyword,
                        cache_data
                    )
                    logger.info(f"✅ Cached {len(routes)} routes for {pickup_keyword} → {dropoff_keyword}")
                else:
                    logger.warning(f"⚠️ No real data found for {pickup_keyword} → {dropoff_keyword}")
                
                return routes
            
            # No real data found - return empty list (don't cache empty results)
            logger.info(f"ℹ️ No trips found for {pickup_keyword} → {dropoff_keyword}")
            return []

        except Exception as e:
            logger.error(f"❌ Failed to retrieve trips: {e}", exc_info=True)
            return []
    
    @staticmethod
    def _format_results(rows) -> List[Dict]:
        """Format database results consistently"""
        trips_data = []
        for row in rows:
            trips_data.append({
                "vehicle_type": row[0],
                "avg_duration_min": row[1],
                "avg_distance_km": row[2],
                "avg_fare": row[3],
                "avg_driver_rating": row[4],
                "trip_count": row[5]
            })
        return trips_data
    
    @staticmethod
    async def get_driver_for_ride(db: AsyncSession, ride_id: str) -> Optional[Dict]:
        """Get driver details for a specific ride"""
        try:
            query = text("""
                SELECT
                    t.driver_status,
                    t.driver_rating,
                    d.driver_id,
                    d.name,
                    d.vehicle_type,
                    d.plate,
                    d.total_trips
                FROM analytics.trip t
                LEFT JOIN analytics.drivers d ON d.vehicle_type = t.ride_type
                WHERE t.ride_id = :ride_id
                LIMIT 1
            """)

            result = await db.execute(query, {"ride_id": ride_id})
            row = result.fetchone()

            if row:
                return {
                    "driver_status": row[0],
                    "driver_rating": row[1],
                    "driver_id": row[2],
                    "name": row[3],
                    "vehicle_type": row[4],
                    "plate": row[5],
                    "total_trips": row[6]
                }
            return None
        
        except Exception as e:
            logger.error(f"❌ Failed to retrieve driver for ride {ride_id}: {e}", exc_info=True)
            return None