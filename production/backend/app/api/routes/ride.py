import logging
import time
import uuid
import json
import numpy as np
import random
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.core.database import get_db, get_pg_db
#from app.models.ride import Ride
from app.models.trip import Trip
from app.models.prediction import (
    RideCreationRequest,
    RideResponse,
    BookingStatus,
    VehicleArrivalStatus,
    DriverStatus,
    RideBookRequest
)
from app.services.ml_predictor import MLPredictor
from app.api.dependencies import get_ml_predictor
from app.services.ride_service import (
    create_ride_in_db,
    complete_ride_in_db,
    get_ride_history
)
from app.services.kafka_producer import kafka_producer
from app.core.redis_client import redis_get, redis_set

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/request", response_model=RideResponse)
async def create_ride_with_prediction(
    request: RideCreationRequest,
    db: AsyncSession = Depends(get_pg_db),
    ml_predictor: MLPredictor = Depends(get_ml_predictor)
):
    """
    Create new ride with ML predictions including VTAT & CTAT Machine learning models implementation.
    
    Flow:
    1. Get ML predictions (VTAT, CTAT, price)
    2. Create ride record in database
    3. Return ride with vehicle arrival timestamp
    """
    try:
        booking_datetime = datetime.now()
        hour = booking_datetime.hour
        day_of_week = booking_datetime.weekday()
        
        # Get ML predictions
        prediction = await ml_predictor.predict_ride_metrics(
            pickup=request.pickup_location,
            drop=request.drop_location,
            vehicle_type=request.vehicle_type,
            hour=booking_datetime.hour,
            day_of_week=booking_datetime.weekday(),
            distance_km=request.distance_km,
            booking_datetime=booking_datetime,
            demand_pressure=request.demand_pressure,
            rating_avg=request.rating_avg
        )

        # Compute timestamps
        ctat_minutes = prediction.get('estimated_drop_time_minute', 0.0)
        vtat_minutes = prediction.get('estimated_pickup_time_minute', 0.0)
        completed_at = booking_datetime + timedelta(minutes=ctat_minutes)
        vehicle_arrival_at = booking_datetime + timedelta(minutes=vtat_minutes)
        
        # Extract ML features for database storage
        feature_dict = await _extract_ride_features(
            pickup=request.pickup_location,
            drop=request.drop_location,
            vehicle_type=request.vehicle_type,
            booking_datetime=booking_datetime,
            distance_km=request.distance_km
        ) or {}

        # Create ride record
        new_trip = Trip(
            ride_id=f"CNR{random.randint(1000000,9999999)}",
            rider_id=request.user_id,
            pickup_location=request.pickup_location,
            dropoff_location=request.drop_location,
            ride_type=request.vehicle_type,
            estimated_fare=prediction.get('estimated_price_idr'),
            actual_fare=request.price,
            distance_km=request.distance_km,
            duration_minutes=ctat_minutes,
            driver_rating=request.rating_avg,
            booking_status=BookingStatus.PENDING.value,
            driver_status=DriverStatus.OFFLINE.value,
            pickup_lat=request.pickup_lat,
            pickup_lng=request.pickup_lng,
            dropoff_lat=request.dropoff_lat,
            dropoff_lng=request.dropoff_lng,
            created_at=booking_datetime,
            completed_at=completed_at,

            **feature_dict
        )

        # Store in new ride record
        db.add(new_trip)
        await db.commit()
        await db.refresh(new_trip)
        logger.info(f"✅ Trip created: {new_trip.id} | Booking Status: {new_trip.booking_status}")

        return RideResponse.model_validate(new_trip)
    
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Trip creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create trip: {str(e)}")
    
@router.post("/rides/book")
async def book_ride(payload: RideBookRequest, db: AsyncSession = Depends(get_pg_db)):
    try:
        ride = await create_ride_in_db(db, **payload.model_dump())
    except Exception as e:
        logger.error(f"Error booking ride: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
    # Publish to Kafka - non-blocking, won't fail the booking if kafka is down
    await kafka_producer.send_event("ride-requests", {
        "event_type": "ride_booked",
        "ride_id": ride.id,
        "user_id": ride.user_id,
        "vehicle_type": ride.vehicle_type,
        "price": ride.price,
        "pickup_location": ride.pickup_location,
        "drop_location": ride.drop_location,
        "timestamp": time.time()
    });

    return ride

@router.get("/rides/history/{user_id}")
async def ride_history(user_id: str, limit: int = 100, db: AsyncSession = Depends(get_pg_db)):
    """
    This 500 endpoint - now uses ride_service
    which queries only columns that actually exist in the DB"""
    try:
        rides = await get_ride_history(db, user_id, limit)
        return rides
    except Exception as e:
        logger.error(f"Error fetching ride history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ride_id}", response_model=RideResponse)
async def get_ride_details(ride_id: str, db: AsyncSession = Depends(get_pg_db)):
    """Get specific ride details including VTAT vehicle arrival"""
    try:
        query = select(Trip).where(Trip.ride_id == ride_id)
        result = await db.execute(query)
        trip = result.scalars().first()
        
        if not trip:
            raise HTTPException(status_code=404, detail=f"Trip {ride_id} not found")
        
        return RideResponse.model_validate(trip)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching trip: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{ride_id}/status")
async def update_ride_status(
    ride_id: str,
    new_status: BookingStatus,
    db: AsyncSession = Depends(get_pg_db)
):
    """
    Update ride status (Completed, Cancelled by Driver, etc.)
    
    Valid statuses: Completed, Cancelled by Driver, No Driver Found, 
                   Cancelled by Customer, Incomplete, Pending
    """
    try:
        query = select(Trip).where(Trip.ride_id == ride_id)
        result = await db.execute(query)
        trip = result.scalars().first()
        
        if not trip:
            raise HTTPException(status_code=404, detail=f"Trip {ride_id} not found")
        
        # Update status
        trip.booking_status = new_status.value
        
        # Set completed_at if ride is completed
        if new_status == BookingStatus.COMPLETED:
            trip.completed_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(trip)
        
        logger.info(f"✅ Trip {ride_id} status updated to {new_status.value}")
        
        return {
            "success": True,
            "ride_id": ride_id,
            "status": trip.booking_status,
            "completed_at": trip.completed_at.isoformat() if trip.completed_at else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating ride status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/by_status")
async def get_stats_by_status(db: AsyncSession = Depends(get_pg_db)):
    """Get trip statistics grouped by booking status"""
    try:
        query = select(Trip)
        result = await db.execute(query)
        all_trips = result.scalars().all()
        
        # Count by status
        status_counts = {}
        for trip in all_trips:
            status = trip.booking_status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_trips": len(all_trips),
            "by_status": status_counts,
            "summary": {
                "completed": status_counts.get(BookingStatus.COMPLETED.value, 0),
                "cancelled": (
                    status_counts.get(BookingStatus.CANCELLED_BY_DRIVER.value, 0) +
                    status_counts.get(BookingStatus.CANCELLED_BY_CUSTOMER.value, 0)
                ),
                "no_driver": status_counts.get(BookingStatus.NO_DRIVER_FOUND.value, 0),
                "pending": status_counts.get(BookingStatus.PENDING.value, 0)
            }
        }
    
    except Exception as e:
        logger.error(f"Error fetching stats: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/vtat_analysis")
async def vtat_analysis(db: AsyncSession = Depends(get_pg_db)):
    """Analyze VTAT predictions vs actual arrival times"""
    try:
        # FIXED: Query based on estimated_pickup_time_minute instead of vtat
        query = select(Trip).where(Trip.estimated_pickup_time_minute.isnot(None))
        result = await db.execute(query)
        trips_with_vtat = result.scalars().all()
        
        if not trips_with_vtat:
            return {"message": "No VTAT data available"}
        
        # Calculate statistics
        vtat_minutes = []
        for trip in trips_with_vtat:
            vtat_minutes.append(trip.estimated_pickup_time_minute)
        
        if vtat_minutes:
            vtat_array = np.array(vtat_minutes)
            return {
                "total_predictions": len(vtat_minutes),
                "vtat_statistics": {
                    "mean_minutes": float(np.mean(vtat_array)),
                    "median_minutes": float(np.median(vtat_array)),
                    "std_dev": float(np.std(vtat_array)),
                    "min_minutes": float(np.min(vtat_array)),
                    "max_minutes": float(np.max(vtat_array))
                }
            }
        else:
            return {"message": "Unable to calculate VTAT statistics"}
    
    except Exception as e:
        logger.error(f"Error analyzing VTAT: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


# Helper function
async def _extract_ride_features(
    pickup: str,
    drop: str,
    vehicle_type: str,
    booking_datetime: datetime,
    distance_km: float
) -> dict:
    """Extract ML features for database storage"""
    try:
        hour = booking_datetime.hour
        day_of_week = booking_datetime.weekday()
        
        # Time-based features
        is_peak_hour = 1 if (7 <= hour <= 9 or 17 <= hour <= 19) else 0
        is_weekend = 1 if day_of_week >= 5 else 0
        is_night = 1 if hour >= 22 or hour < 5 else 0
        
        # Cyclical encoding
        hour_sin = np.sin(2 * np.pi * hour / 24)
        hour_cos = np.cos(2 * np.pi * hour / 24)
        day_sin = np.sin(2 * np.pi * day_of_week / 7)
        day_cos = np.cos(2 * np.pi * day_of_week / 7)
        
        return {
            "pickup_encoded": hash(pickup) % 1000,
            "drop_encoded": hash(drop) % 1000,
            "hour": hour,
            "day_of_week": day_of_week,
            "route_cluster": hash(f"{pickup}_{drop}") % 100,
            "ride_distance": distance_km,
            "is_peak_hour": is_peak_hour,
            "is_weekend": is_weekend,
            "is_night": is_night,
            "hour_sin": hour_sin,
            "hour_cos": hour_cos,
            "day_sin": day_sin,
            "day_cos": day_cos
        }
    
    except Exception as e:
        logger.warning(f"Error extracting features: {e}, using defaults")
        return {
            "pickup_encoded": 0,
            "drop_encoded": 0,
            "hour": 0,
            "day_of_week": 0,
            "route_cluster": 0,
            "ride_distance": distance_km,
            "is_peak_hour": 0,
            "is_weekend": 0,
            "is_night": 0,
            "hour_sin": 0.0,
            "hour_cos": 1.0,
            "day_sin": 0.0,
            "day_cos": 1.0
        }
    
async def get_or_encode_location(location: str, loc_type: str = "pickup") -> int:
    """Cache location encoding in Redis to avoid recomputation"""
    cache_key = f"loc_enc:{loc_type}:{location.lower()}"
    cached = await redis_get(cache_key)
    
    if cached:
        return int(cached)
    
    # Fallback to hash encoding location matcher
    encoded = abs(hash(location)) % 1000
    await redis_set(cache_key, str(encoded), expire=86400)

    return encoded