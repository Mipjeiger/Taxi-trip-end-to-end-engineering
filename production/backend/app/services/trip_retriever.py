import logging
from sqlalchemy import select, func, and_, or_
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
            # Build case-insensitive partial match
            stmt = select(
                Trip.ride_type,
                func.avg(Trip.duration_minutes).label("avg_duration_min"),
                func.avg(Trip.distance_km).label("avg_distance_km"),
                func.avg(Trip.estimated_fare).label("avg_estimated_fare"),
                func.avg(Trip.actual_fare).label("avg_actual_fare"),
                func.avg(Trip.driver_rating).label("avg_driver_rating"),
                func.count().label("trip_count")
            ).where(
                and_(
                    Trip.status == "completed",
                    func.lower(Trip.pickup_location).contains(pickup_keyword.lower()),
                    func.lower(Trip.dropoff_location).contains(dropoff_keyword.lower())
                )
            ).group_by(Trip.ride_type).limit(limit)

            result = await db.execute(stmt)
            rows = result.all()

            if not rows:
                logger.warning(f"⚠️ No similar trips found for pickup '{pickup_keyword}' and dropoff '{dropoff_keyword}'")
                return []
            
            # Fomat results into list of dicts
            trips_data = []
            for row in rows:
                trips_data.append({
                    "vehicle_type": row.ride_type,
                    "avg_duration_min": round(row.avg_duration_min, 1) if row.avg_duration_min else None,
                    "avg_distance_km": round(row.avg_distance_km, 1) if row.avg_distance_km else None,
                    "avg_estimated_fare": int(row.avg_estimated_fare) if row.avg_estimated_fare else None,
                    "avg_actual_fare": int(row.avg_actual_fare) if row.avg_actual_fare else None,
                    "avg_driver_rating": round(row.avg_driver_rating, 1) if row.avg_driver_rating else None,
                    "trip_count": row.trip_count
                })

            logger.info(f"✅ Found {len(trips_data)} similar trip groups for pickup '{pickup_keyword}' and dropoff '{dropoff_keyword}'")
            return trips_data
        
        except Exception as e:
            logger.error(f"❌ Error retrieving similar trips: {e}", exc_info=True)
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
                    Trip.status == "completed",
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