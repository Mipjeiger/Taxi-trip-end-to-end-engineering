import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Optional
from app.services.redis_service import RedisService
from datetime import datetime

logger = logging.getLogger(__name__)

class TripRetriever:
    
    @staticmethod
    async def find_similar_routes(
        db: AsyncSession,
        pickup_keyword: str,
        dropoff_keyword: str,
        limit: int = 5
    ) -> List[Dict]:
        """Find real trips with Redis caching"""
        
        # Try Redis cache first
        cached = await RedisService.get_route_features(pickup_keyword, dropoff_keyword)
        if cached:
            logger.info(f"✅ Cache hit for {pickup_keyword} → {dropoff_keyword}")
            return cached.get('routes', [])

        try:
            logger.info(f"🔍 Searching for trips from '{pickup_keyword}' to '{dropoff_keyword}'")
            
            # Strategy 1: Use raw SQL with explicit analytics schema
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
            
            result = await db.execute(
                query,
                {
                    "pickup": f"%{pickup_keyword}%",  # ✅ Fixed: added wildcards
                    "dropoff": f"%{dropoff_keyword}%",  # ✅ Fixed: added wildcards
                    "limit": limit
                }
            )
            rows = result.fetchall()
            
            if rows:
                routes = TripRetriever._format_results(rows)  # ✅ Fixed: use _format_results
                
                # Cache the results
                await RedisService.set_route_features(
                    pickup_keyword,
                    dropoff_keyword,
                    {'routes': routes, 'timestamp': datetime.now().isoformat()},
                )
                return routes
            
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
                "avg_estimated_fare": row[3],
                "avg_actual_fare": row[3],  # ✅ Fixed: avg_fare is at index 3
                "avg_driver_rating": row[4],  # ✅ Fixed: avg_rating is at index 4
                "trip_count": row[5]  # ✅ Fixed: trip_count is at index 5
            })
        
        return trips_data
    
    @staticmethod
    async def search_by_location_fuzzy(
        db: AsyncSession,
        pickup_keyword: str,
        dropoff_keyword: str,
        limit: int = 10
    ) -> List[Dict]:
        """Get individual trip examples with fuzzy search"""
        try:
            query = text("""
                SELECT 
                    ride_id,
                    ride_type,
                    pickup_location,
                    dropoff_location,
                    duration_minutes,
                    distance_km,
                    estimated_fare,
                    actual_fare,
                    driver_rating,
                    completed_at,
                    EXTRACT(DOW FROM completed_at) as day_of_week
                FROM analytics.trip
                WHERE status = 'Completed'
                    AND LOWER(pickup_location) LIKE LOWER(CONCAT('%', :pickup, '%'))
                    AND LOWER(dropoff_location) LIKE LOWER(CONCAT('%', :dropoff, '%'))
                ORDER BY completed_at DESC
                LIMIT :limit
            """)
            
            result = await db.execute(
                query,
                {
                    "pickup": pickup_keyword,  # ✅ Fixed: no extra f-string
                    "dropoff": dropoff_keyword,
                    "limit": limit
                }
            )
            rows = result.fetchall()
            
            return [
                {
                    "ride_id": row[0],
                    "vehicle_type": row[1],
                    "pickup": row[2],
                    "dropoff": row[3],
                    "duration_min": float(row[4]) if row[4] else None,
                    "distance_km": float(row[5]) if row[5] else None,
                    "estimated_fare": float(row[6]) if row[6] else None,
                    "actual_fare": float(row[7]) if row[7] else None,
                    "rating": float(row[8]) if row[8] else None,
                    "date": row[9].isoformat() if row[9] else None,
                    "day_of_week": int(row[10]) if row[10] else None
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"❌ Fuzzy search failed: {e}")
            return []
        
    @staticmethod
    async def test_connection(db: AsyncSession) -> Dict:
        """Test database connection and schema access"""
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM analytics.trip"))
            count = result.scalar()

            result = await db.execute(text("SELECT COUNT(*) FROM analytics.trip WHERE status = 'Completed'"))
            completed = result.scalar()

            return {
                "connected": True,
                "total_trips": count,
                "completed_trips": completed,
                "message": f"Successfully accessed analytics.trip - total: {count}, completed: {completed}"
            }
        
        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}", exc_info=True)
            return {
                "connected": False,
                "error": str(e)
            }

    @staticmethod
    async def get_all_routes(db: AsyncSession) -> List[Dict]:
        """Get all unique routes for debugging and analysis"""

        # Try Redis cache first
        cached = await RedisService.get_popular_routes()

        if cached:
            logger.info("✅ Cache hit for popular routes")
            return cached

        try:
            query = text("""
                SELECT DISTINCT pickup_location, dropoff_location, ride_type, COUNT(*) as cnt
                FROM analytics.trip
                WHERE status = 'Completed'
                GROUP BY pickup_location, dropoff_location, ride_type
                ORDER BY cnt DESC
                LIMIT 20
            """)
            result = await db.execute(query)
            rows = result.fetchall()

            routes = [
                {
                    "pickup": row[0],
                    "dropoff": row[1],
                    "vehicle_type": row[2],
                    "trip_count": row[3]
                }
                for row in rows
            ]
            
            # Cache results
            if routes:
                await RedisService.set_popular_routes(routes)  # Cache for 1 hour
            
            return routes

        except Exception as e:
            logger.error(f"❌ Failed to retrieve routes: {e}", exc_info=True)
            return []
        
    @staticmethod
    async def debug_direct_query(db: AsyncSession, pickup: str, dropoff: str):
        """Direct SQL query to debug why data isn't found"""
        try:
            query = text("""
                SELECT ride_type, pickup_location, dropoff_location, actual_fare, duration_minutes
                FROM analytics.trip
                WHERE status = 'Completed'
                AND pickup_location ILIKE :pickup
                AND dropoff_location ILIKE :dropoff
                LIMIT 5
            """)
            
            result = await db.execute(
                query,
                {
                    "pickup": f"%{pickup}%",
                    "dropoff": f"%{dropoff}%"
                }
            )
            rows = result.fetchall()
            
            logger.info(f"🔍 Direct query results for {pickup} → {dropoff}:")
            if rows:
                for row in rows:
                    logger.info(f" - {row[0]}: {row[1]} → {row[2]}, fare: {row[3]}, duration: {row[4]} min")
            else:
                logger.info(" - No results found")
            
            return rows
        
        except Exception as e:
            logger.error(f"❌ Direct query failed: {e}", exc_info=True)
            return []