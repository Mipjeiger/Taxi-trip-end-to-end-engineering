import logging
import uuid
import numpy as np
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta

from app.core.database import get_db
from app.models.ride import Ride
from app.models.prediction import (
    RideCreationRequest,
    RideResponse,
    BookingStatus,
    VehicleArrivalStatus,
    DriverStatus
)
from app.services.ml_predictor import MLPredictor
from app.api.dependencies import get_ml_predictor

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/request", response_model=RideResponse)
async def create_ride_with_prediction(
    request: RideCreationRequest,
    db: AsyncSession = Depends(get_db),
    ml_predictor: MLPredictor = Depends(get_ml_predictor)
):
    """
    Create new ride with ML predictions including VTAT vehicle arrival.
    
    Flow:
    1. Get ML predictions (VTAT, CTAT, price)
    2. Create ride record in database
    3. Return ride with vehicle arrival timestamp
    """
    try:
        booking_datetime = datetime.now()
        
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
        
        # Extract ML features for database storage
        feature_dict = await _extract_ride_features(
            pickup=request.pickup_location,
            drop=request.drop_location,
            vehicle_type=request.vehicle_type,
            booking_datetime=booking_datetime,
            distance_km=request.distance_km
        )

        # Create ride record
        new_ride = Ride(
            id=f"RIDE-{uuid.uuid4().hex[:12].upper()}",
            user_id=request.user_id,
            pickup_location=request.pickup_location,
            drop_location=request.drop_location,
            vehicle_type=request.vehicle_type,
            price=prediction.get('estimated_price_idr'),
            estimated_pickup_time_minute=prediction.get('estimated_vehicle_arrival_minute'),  # VTAT
            estimated_drop_time_minute=prediction.get('estimated_drop_time_minute'),         # CTAT
        

        # FIXED: Changed 'status' to 'booking_status' to match Ride model
        booking_status = BookingStatus.PENDING.value,
        created_at = booking_datetime,
        completed_at = None

        # FIXED: Removed vtat=vtat_timestamp because it's not defined in Ride model, and we will store VTAT as estimated_pickup_time_minute
        # ML Features
        **feature_dict
        )

        # Store in new ride record
        db.add(new_ride)
        await db.commit()
        await db.refresh(new_ride)
        logger.info(f"✅ Ride created: {new_ride.id} | Booking Status: {new_ride.booking_status}")

        return RideResponse.model_validate(new_ride)
    
    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Ride creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create ride: {str(e)}")


@router.get("/history/{user_id}", response_model=list[RideResponse])
async def get_ride_history(
    user_id: str,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """
    Get ride history for user.
    
    Parameters:
    - user_id: User ID (path parameter)
    - limit: Maximum number of rides to return (default 100)
    """
    try:
        query = select(Ride).where(Ride.user_id == user_id)
        query = query.order_by(Ride.created_at.desc()).limit(limit)
        
        result = await db.execute(query)
        rides = result.scalars().all()
        
        return [RideResponse.model_validate(ride) for ride in rides]
    
    except Exception as e:
        logger.error(f"Error fetching ride history: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{ride_id}", response_model=RideResponse)
async def get_ride_details(ride_id: str, db: AsyncSession = Depends(get_db)):
    """Get specific ride details including VTAT vehicle arrival"""
    try:
        query = select(Ride).where(Ride.id == ride_id)
        result = await db.execute(query)
        ride = result.scalars().first()
        
        if not ride:
            raise HTTPException(status_code=404, detail=f"Ride {ride_id} not found")
        
        return RideResponse.model_validate(ride)
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching ride: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/{ride_id}/status")
async def update_ride_status(
    ride_id: str,
    new_status: BookingStatus,
    db: AsyncSession = Depends(get_db)
):
    """
    Update ride status (Completed, Cancelled by Driver, etc.)
    
    Valid statuses: Completed, Cancelled by Driver, No Driver Found, 
                   Cancelled by Customer, Incomplete, Pending
    """
    try:
        query = select(Ride).where(Ride.id == ride_id)
        result = await db.execute(query)
        ride = result.scalars().first()
        
        if not ride:
            raise HTTPException(status_code=404, detail=f"Ride {ride_id} not found")
        
        # Update status
        ride.booking_status = new_status.value
        
        # Set completed_at if ride is completed
        if new_status == BookingStatus.COMPLETED:
            ride.completed_at = datetime.utcnow()
        
        await db.commit()
        await db.refresh(ride)
        
        logger.info(f"✅ Ride {ride_id} status updated to {new_status.value}")
        
        return {
            "success": True,
            "ride_id": ride_id,
            "status": ride.booking_status,
            "completed_at": ride.completed_at.isoformat() if ride.completed_at else None
        }
    
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating ride status: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/by_status")
async def get_stats_by_status(db: AsyncSession = Depends(get_db)):
    """Get ride statistics grouped by booking status"""
    try:
        query = select(Ride)
        result = await db.execute(query)
        all_rides = result.scalars().all()
        
        # Count by status
        status_counts = {}
        for ride in all_rides:
            status = ride.booking_status
            status_counts[status] = status_counts.get(status, 0) + 1
        
        return {
            "total_rides": len(all_rides),
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
async def vtat_analysis(db: AsyncSession = Depends(get_db)):
    """Analyze VTAT predictions vs actual arrival times"""
    try:
        # FIXED: Query based on estimated_pickup_time_minute instead of vtat
        query = select(Ride).where(Ride.estimated_pickup_time_minute.isnot(None))
        result = await db.execute(query)
        rides_with_vtat = result.scalars().all()
        
        if not rides_with_vtat:
            return {"message": "No VTAT data available"}
        
        # Calculate statistics
        vtat_minutes = []
        for ride in rides_with_vtat:
            vtat_minutes.append(ride.estimated_pickup_time_minute)
        
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