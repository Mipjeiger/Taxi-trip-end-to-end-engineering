import uuid
import math
import logging
import random
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.trip import Trip

logger = logging.getLogger(__name__)

def _compute_features(pickup_encoded: int, drop_encoded: int) -> dict:
    """
    Derive hour/day/trip features from current time.
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
    db,
    ride_id: str,
    pickup_location: str,
    dropoff_location: str,
    estimated_fare: float,
    distance_km: float,
    duration_minute: float,
    status: str
) -> Trip:
    """
    Insert a new ride row and return the ORM object.
    Called by the /rides/book route handler.
    """
    trip = Trip(
        ride_id=f"CNR{random.randint(1000000,9999999)}",
        rider_id=ride_id,
        pickup_location=pickup_location,
        dropoff_location=dropoff_location,
        status=status,
        estimated_fare=estimated_fare,
        distance_km=distance_km,
        duration_minute=duration_minute,
        created_at=datetime.now()
    )
    db.add(trip)
    await db.commit()
    await db.refresh(trip)

    return trip
    
async def complete_ride_in_db(
        db: AsyncSession,
        ride_id: str,
) -> Optional[Trip]:
    """Mark a ride as completed. Called by /rides/{ride_id}/complete route handler."""
    result = await db.execute(select(Trip).where(Trip.ride_id == ride_id))
    trip = result.scalar_one_or_none()

    if not trip:
        logger.warning(f"⚠️ Trip not found for completion: {ride_id}")
        return None
    
    trip.booking_status = "completed"
    trip.completed_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(trip)
    logger.info(f"✅ Trip completed: {ride_id}")
    return trip

async def get_ride_history(
    db: AsyncSession,
    user_id: str,
    limit: int = 100,
) -> list[Trip]:
    """Fetch trip history for a user. Fixes your original 500 error."""
    result = await db.execute(
        select(Trip)
        .where(Trip.rider_id == user_id)
        .order_by(Trip.created_at.desc())
        .limit(limit)
    )
    return result.scalars().all()