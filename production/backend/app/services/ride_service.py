import uuid
import math
import logging
import random
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.models.trip import Trip
from app.models.prediction import DriverStatus, BookingStatus

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
    db: AsyncSession,
    user_id: str,
    pickup_location: str,
    drop_location: str,
    vehicle_type: str,
    price: float,
    estimated_pickup_time_minute: float,  # VTAT
    estimated_drop_time_minute: float,    # CTAT
    pickup_encoded: int,
    drop_encoded: int,
    route_cluster: int,
    ride_distance: float,
    pickup_lat: float,
    pickup_lon: float,
    drop_lat: float,
    drop_lon: float
) -> Trip:
    """
    Insert a new ride row with all ML features.
    """
    try:
        # Generate unique ride_id
        ride_id = f"CNR{random.randint(1000000, 9999999)}"
        booking_datetime = datetime.now()
        
        # Calculate timestamps from predictions
        # CTAT = estimated_drop_time_minute (total ride time)
        # VTAT = estimated_pickup_time_minute (vehicle arrival time)
        completed_at = booking_datetime + timedelta(minutes=estimated_drop_time_minute)
        vehicle_arrival_at = booking_datetime + timedelta(minutes=estimated_pickup_time_minute)
        
        # Extract time features
        hour = booking_datetime.hour
        day_of_week = booking_datetime.weekday()
        
        # Create Trip instance with ALL fields
        trip = Trip(
            ride_id=ride_id,
            rider_id=user_id,
            driver_status=DriverStatus.OFFLINE.value,
            pickup_location=pickup_location,
            dropoff_location=drop_location,
            pickup_lat=pickup_lat,
            pickup_lng=pickup_lon,
            dropoff_lat=drop_lat,
            dropoff_lng=drop_lon,
            status=BookingStatus.PENDING.value,
            ride_type=vehicle_type,
            estimated_fare=price,
            actual_fare=price,
            distance_km=ride_distance,
            duration_minutes=estimated_drop_time_minute,  # CTAT stored here
            driver_rating=None,
            booking_status=BookingStatus.PENDING.value,
            created_at=booking_datetime,
            vehicle_arrival_at=vehicle_arrival_at,        # VTAT timestamp
            completed_at=completed_at,                    # CTAT timestamp
            # NEW ML Features
            vtat_minutes=estimated_pickup_time_minute,
            ctat_minutes=estimated_drop_time_minute,
            pickup_encoded=pickup_encoded,
            drop_encoded=drop_encoded,
            route_cluster=route_cluster,
            # Time features
            day_of_week=day_of_week,
            demand_pressure=500.0,  # Default, can be passed in
            hour=hour
        )
        
        db.add(trip)
        await db.commit()
        await db.refresh(trip)
        
        logger.info(f"✅ Ride created: {ride_id}")
        logger.info(f"   VTAT: {estimated_pickup_time_minute}min → {vehicle_arrival_at}")
        logger.info(f"   CTAT: {estimated_drop_time_minute}min → {completed_at}")
        logger.info(f"   Encodings: pickup={pickup_encoded}, drop={drop_encoded}, cluster={route_cluster}")
        
        return trip
    
    except Exception as e:
        logger.error(f"❌ Failed to create ride in DB: {e}", exc_info=True)
        await db.rollback()
        raise
    
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