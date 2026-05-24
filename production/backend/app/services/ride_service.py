import uuid
import math
import logging
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.ride import Ride

logger = logging.getLogger(__name__)

def _compute_features(pickup_encoded: int, drop_encoded: int) -> dict:
    """
    Derive hour/day/trig features from current time.
    These mirror what your ML model was trained on.
    """
    now = datetime.now(timezone.utc)
    hour = now.hour
    dow = now.weekday()

    return {
        "hour":        hour,
        "day_of_week": dow,
        "is_peak_hour": 1 if hour in range(7, 10) or hour in range(17, 20) else 0,
        "is_weekend":  1 if dow >= 5 else 0,
        "is_night":    1 if hour >= 22 or hour < 6 else 0,
        "hour_sin":    math.sin(2 * math.pi * hour / 24),
        "hour_cos":    math.cos(2 * math.pi * hour / 24),
        "day_sin":     math.sin(2 * math.pi * dow / 7),
        "day_cos":     math.cos(2 * math.pi * dow / 7),
    }

async def create_ride_in_db(
    db: AsyncSession,
    user_id: str,
    pickup_location: str,
    drop_location: str,
    vehicle_type: str,
    price: float,
    estimated_pickup_time_minute: float,
    estimated_drop_time_minute: float,
    pickup_encoded: int,
    drop_encoded: int,
    route_cluster: int,
    ride_distance: float,
    pickup_lat: float,
    pickup_lon: float,
    drop_lat: float,
    drop_lon: float,
    avg_rating: float = 0.0,
) -> Ride:
    """
    Insert a new ride row and return the ORM object.
    Called by the /rides/book route handler.
    """
    features = _compute_features(pickup_encoded, drop_encoded)

    ride = Ride(
        id=str(uuid.uuid4()),
        user_id=user_id,
        pickup_location=pickup_location,
        drop_location=drop_location,
        vehicle_type=vehicle_type,
        price=price,
        estimated_pickup_time_minute=estimated_pickup_time_minute,
        estimated_drop_time_minute=estimated_drop_time_minute,
        booking_status="pending",
        driver_status=None,
        avg_rating=avg_rating,
        pickup_encoded=pickup_encoded,
        drop_encoded=drop_encoded,
        route_cluster=route_cluster,
        ride_distance=ride_distance,
        pickup_lat=pickup_lat,
        pickup_lon=pickup_lon,
        drop_lat=drop_lat,
        drop_lon=drop_lon,
        created_at=datetime.now(timezone.utc),
        **features,   # hour, day_of_week, is_peak_hour, is_weekend, is_night, *_sin, *_cos
    )
    db.add(ride)
    await db.commit()
    await db.refresh(ride)
    logger.info(f"✅ Ride created: {ride.id} for user {user_id}")
    return ride
    
async def complete_ride_in_db(
        db: AsyncSession,
        ride_id: str,
) -> Optional[Ride]:
    """Mark a ride as completed. Called by /rides/{ride_id}/complete route handler."""
    result = await db.execute(select(Ride).where(Ride.id == ride_id))
    ride = result.scalar_one_or_none()

    if not ride:
        logger.warning(f"⚠️ Ride not found for completion: {ride_id}")
        return None
    
    ride.booking_status = "completed"
    ride.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(ride)
    logger.info(f"✅ Ride completed: {ride_id}")
    return ride

async def get_ride_history(
    db: AsyncSession,
    user_id: str,
    limit: int = 100,
) -> list[Ride]:
    """Fetch ride history for a user. Fixes your original 500 error."""
    result = await db.execute(
        select(Ride)
        .where(Ride.user_id == user_id)
        .order_by(Ride.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()