import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Dict, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

class TripRetriever:
    
    @staticmethod
    async def find_similar_routes(
        db: AsyncSession,
        pickup_keyword: str,
        dropoff_keyword: str,
        limit: int = 5
    ) -> List[Dict]:
        """Find real trips using raw SQL for reliability"""
        try:
            logger.info(f"🔍 Searching for trips from '{pickup_keyword}' to '{dropoff_keyword}'")
            
            # Strategy 1: Use raw SQL with explicit analytics schema
            query = text("""
                SELECT 
                    ride_type,
                    ROUND(AVG(duration_minutes), 1) as avg_duration,
                    ROUND(AVG(distance_km), 1) as avg_distance,
                    ROUND(AVG(actual_fare)) as avg_fare,
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
                    "pickup": f"{pickup_keyword}%",
                    "dropoff": f"{dropoff_keyword}%",
                    "limit": limit
                }
            )
            rows = result.fetchall()
            
            if rows:
                logger.info(f"✅ Found {len(rows)} vehicle types for {pickup_keyword} → {dropoff_keyword}")

                return [
                    {
                        "vehicle_type": row[0],
                        "avg_duration_min": row[1],
                        "avg_distance_km": row[2],
                        "avg_fare": row[3],
                        "avg_rating": row[4],
                        "trip_count": row[5]
                    }
                    for row in rows
                ]
            
            # If not foumd, log sample data from database
            sample_query = text("""
                SELECT DISTINCT pickup_location, dropoff_location 
                FROM analytics.trip 
                WHERE status = 'Completed' 
                LIMIT 10
            """)
            sample_result = await db.execute(sample_query)
            samples = sample_result.fetchall()
            
            logger.info("📋 Available routes in DB:")
            for s in samples:
                logger.info(f"   - '{s[0]}' → '{s[1]}'")
            
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
                "avg_actual_fare": row[4],
                "avg_driver_rating": row[5],
                "trip_count": row[6]
            })
        
        return trips_data
    
    @staticmethod
    async def search_by_location_fuzzy(
        db: AsyncSession,
        pickup_keyword: str,
        dropoff_keyword: str,
        limit: int = 10
    ) -> List[Dict]:
        """Get individual trip examples"""
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
                    day_of_week,
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
                    "pickup": f"{pickup_keyword}",
                    "dropoff": f"{dropoff_keyword}",
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
                    "day_of_week": row[10] if row[10] else None
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"❌ Fuzzy search failed: {e}")
            return []
        
    @staticmethod
    async def test_connection(db: AsyncSession) -> Dict:
        """Test dababase connection and schema access"""
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

            return [
                {
                    "pickup": row[0],
                    "dropoff": row[1],
                    "vehicle_type": row[2],
                    "trip_count": row[3]
                }
                for row in rows
            ]

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
                AND pickup_location ILIKE '%{pickup}%'
                AND dropoff_location ILIKE '%{dropoff}%'
                LIMIT 5
            """)
            result = await db.execute(query)
            rows = result.fetchall()
            logger.info(f"🔍 Direct query results for {pickup} → {dropoff}:")

            for row in rows:
                logger.info(f" - {row[0]}: {row[1]} → {row[2]}, fare: {row[3]}, duration: {row[4]} min")

            return rows
        
        except Exception as e:
            logger.error(f"❌ Direct query failed: {e}", exc_info=True)
            return []