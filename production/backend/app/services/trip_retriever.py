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
            # Clean and prepare search terms -> The prompter can be lowercase
            pickup_search = pickup_keyword.strip().lower()
            dropoff_search = dropoff_keyword.strip().lower()
            logger.info(f"🔍 Searching for trips with pickup containing '{pickup_search}' and dropoff containing '{dropoff_search}'")

            # Build case-insensitive partial match
            pickup_conditions = or_(
                func.lower(Trip.pickup_location).contains(pickup_search),
                func.lower(Trip.pickup_location).like(f"%{pickup_search}%"),
                func.lower(func.replace(Trip.pickup_location, ' ', '')).contains(pickup_search.replace(' ', '')),
                func.lower(pickup_search).contains(func.lower(Trip.pickup_location))
            )

            dropoff_locations = or_(
                func.lower(Trip.dropoff_location).contains(dropoff_search),
                func.lower(Trip.dropoff_location).like(f"%{dropoff_search}%"),
                func.lower(func.replace(Trip.dropoff_location, ' ', '')).contains(dropoff_search.replace(' ', '')),
                func.lower(dropoff_search).contains(func.lower(Trip.dropoff_location))
            )
            
            # First todo: Exact matches (case insensitive)
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
                    pickup_conditions,
                    dropoff_locations
                )
            ).group_by(Trip.ride_type).limit(limit)

            result = await db.execute(stmt)
            rows = result.all()

            if rows:
                logger.info(f"✅ Found {len(rows)} vehicle types for {pickup_search} → {dropoff_search}")
            
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
                return trips_data
        
            # Second todo: Get ALL trips from pickup to anywhere
            logger.info(f"⚠️ No exact matches, trying broader search for '{pickup_search}'")

            stmt_broad = select(
                Trip.ride_type,
                Trip.dropoff_location,
                func.avg(Trip.duration_minutes).label("avg_duration_min"),
                func.avg(Trip.distance_km).label("avg_distance_km"),
                func.avg(Trip.actual_fare).label("avg_actual_fare"),
                func.count().label("trip_count")
            ).where(
                and_(
                    Trip.status == "completed",
                    pickup_conditions
                )
            ).group_by(Trip.ride_type, Trip.dropoff_location).limit(limit)

            result_broad = await db.execute(stmt_broad)
            broad_rows = result_broad.all()

            if broad_rows:
                logger.info(f"✅ Found {len(broad_rows)} trips from {pickup_search} to various destinations")
                trips_data = []
                for row in broad_rows:
                    trips_data.append({
                        "vehicle_type": row.ride_type,
                        "destination": row.dropoff_location,
                        "avg_duration_min": round(row.avg_duration_min, 1) if row.avg_duration_min else None,
                        "avg_distance_km": round(row.avg_distance_km, 1) if row.avg_distance_km else None,
                        "avg_actual_fare": int(row.avg_actual_fare) if row.avg_actual_fare else None,
                        "trip_count": row.trip_count,
                        "note": f"Trips from {pickup_search} to {row.dropoff_location}"
                    })
                return trips_data
            
            # Third todo: Show sample of available locations from database
            logger.warning(f"❌ No trips found for {pickup_search} → {dropoff_search}")

            # Get sample of available pickup locations to help user
            sample_stmt = select(Trip.pickup_location, func.count().label("count")
                                 ).where(Trip.status == "completed"
                                 ).group_by(Trip.pickup_location
                                 ).order_by(func.count().desc()
                                 ).limit(10)
                                 
            sample_result = await db.execute(sample_stmt)
            sample_locations = [row.pickup_location for row in sample_result.fetchall()]
            logger.info(f"📋 Available pickup locations sample: {sample_locations[:5]}")

            return []
        
        except Exception as e:
            logger.error(f"❌ Error retrieving similar trips: {e}", exc_info=True)
            return []
    
    @staticmethod
    async def get_all_available_locations(db: AsyncSession) -> List[str]:
        """Get list of all unique pickup locations for suggestion"""
        try:
            stmt = select(Trip.pickup_location.distinct()).where(Trip.status == "completed").limit(50)
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