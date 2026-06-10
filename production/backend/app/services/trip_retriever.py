import logging
from sqlalchemy import text, select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List, Optional, Dict
from app.models.trip import Trip

logger = logging.getLogger(__name__)

class TripRetriever:
    """Retrieve real trip data from sql table (analytics.trip) to ground LLM responses"""

    @staticmethod
    async def find_similar_routes(
        db: AsyncSession,
        pickup_keyword: str,
        dropoff_keyword: str,
        limit: int = 5
    ) -> List[Dict]:
        """Find real trips with similar pickup/dropoff locations.
        Returns aggregated statistics per vehicle type.
        """
        try:
            # User raw SQL to ensure schema is correct
            query = text("""
                SELECT
                    ride_type,
                    AVG(duration_minutes) as avg_duration_min,
                    AVG(distance_km) as avg_distance_km,
                    AVG(estimated_fare) as avg_estimated_fare,
                    AVG(actual_fare) as avg_actual_fare,
                    AVG(driver_rating) as avg_driver_rating,
                    COUNT(*) as trip_count
                FROM analytics.trip
                WHERE status = 'Completed'
                    AND pickup_location ILIKE :pickup_pattern
                    AND dropoff_location ILIKE :dropoff_pattern
                GROUP BY ride_type
                LIMIT :limit
            """)

            result = await db.execute(
                query,
                {
                    "pickup_pattern": f"%{pickup_keyword}%",
                    "dropoff_pattern": f"%{dropoff_keyword}%",
                    "limit": limit
                }
            )
            rows = result.fetchall()

            if rows:
                logger.info(f"✅ Found {len(rows)} vehicle types for {pickup_keyword} → {dropoff_keyword}")
                trips_data = []
                for row in rows:
                    trips_data.append({
                        "vehicle_type": row[0],
                        "avg_duration_min": round(row[1], 1) if row[1] else None,
                        "avg_distance_km": round(row[2], 1) if row[2] else None,
                        "avg_estimated_fare": int(row[3]) if row[3] else None,
                        "avg_actual_fare": int(row[4]) if row[4] else None,
                        "avg_driver_rating": round(row[5], 1) if row[5] else None,
                        "trip_count": row[6]
                    })

                return trips_data
            
            # If no results, try broader search with fuzzy matching using SQLAlchemy ORM
            logger.warning(f"⚠️ No exact matches found for '{pickup_keyword}' → '{dropoff_keyword}', trying broader search...")

            # Get all available routes for debugging
            sample_query = text("""
                SELECT DISTINCT pickup_location, dropoff_location, ride_type 
                FROM analytics.trip 
                WHERE status = 'Completed' 
                LIMIT 10
            """)
            sample_result = await db.execute(sample_query)
            sample_rows = sample_result.fetchall()
            
            if sample_rows:
                logger.info("📋 Available routes in database:")
                for row in sample_rows:
                    logger.info(f"   - {row[0]} → {row[1]} ({row[2]})")
            
            return []
        
        except Exception as e:
            logger.error(f"❌ Error retrieving similar trips: {e}", exc_info=True)
            return []
    
    @staticmethod
    async def test_connection(db: AsyncSession) -> Dict:
        """Test database connection and return stats"""
        try:
            result = await db.execute(text("SELECT COUNT(*) FROM analytics.trip"))
            count = result.scalar()
            
            result = await db.execute(text("SELECT COUNT(*) FROM analytics.trip WHERE status = 'Completed'"))
            completed = result.scalar()

            return {
                "connected": True,
                "total_trips": count,
                "completed_trips": completed,
                "message": f"Successfully connected to database. Total trips: {count}, Completed trips: {completed}"
            }
        
        except Exception as e:
            logger.error(f"❌ Database connection test failed: {e}", exc_info=True)
            return {
                "connected": False,
                "total_trips": None,
                "completed_trips": None,
                "message": f"Database connection failed: {e}"
            }

    @staticmethod
    async def get_all_available_locations(db: AsyncSession) -> List[str]:
        """Get list of all unique pickup locations for suggestion"""
        try:
            stmt = select(Trip.pickup_location.distinct()).where(Trip.status == "Completed").limit(50)
            result = await db.execute(stmt)
            locations = [row[0] for row in result.fetchall() if row[0]]
            return locations
        
        except Exception as e:
            logger.error(f"❌ Error retrieving available locations: {e}", exc_info=True)
            return []

    @staticmethod
    async def search_by_location_fuzzy(
        db: AsyncSession,
        pickup_keyword: str,
        dropoff_keyword: str,
        limit: int = 10
    ) -> List[Dict]:
        """Get individual trip examples for more detailed context using fuzzy search on pickup/dropoff locations."""
        try:
            stmt = select(
                Trip.ride_id,
                Trip.ride_type,
                Trip.pickup_location,
                Trip.dropoff_location,
                Trip.duration_minutes,
                Trip.distance_km,
                Trip.estimated_fare,
                Trip.actual_fare,
                Trip.driver_rating,
                Trip.completed_at
            ).where(
                and_(
                    Trip.status == "Completed",  # ← Changed from "completed" to "Completed"
                    func.lower(Trip.pickup_location).contains(pickup_keyword.lower()),
                    func.lower(Trip.dropoff_location).contains(dropoff_keyword.lower())
                )
            ).limit(limit)

            result = await db.execute(stmt)
            rows = result.all()

            return [
                {
                    "ride_id": row.ride_id,
                    "vehicle_type": row.ride_type,
                    "pickup": row.pickup_location,
                    "dropoff": row.dropoff_location,
                    "duration_min": row.duration_minutes,
                    "distance_km": row.distance_km,
                    "fare": row.actual_fare or row.estimated_fare,
                    "rating": row.driver_rating,
                    "date": row.completed_at.isoformat() if row.completed_at else None
                }
                for row in rows
            ]
        except Exception as e:
            logger.error(f"❌ Error retrieving trip examples: {e}", exc_info=True)
            return []