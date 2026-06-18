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
from sqlalchemy import text

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/request", response_model=RideResponse)
async def create_ride_with_prediction(
    request: RideCreationRequest,
    db: AsyncSession = Depends(get_pg_db),
    ml_predictor: MLPredictor = Depends(get_ml_predictor)
):
    """
    Create new ride by fetching historical averages from Completed trips in the database,
    and enriching with ML-predicted VTAT & CTAT timestamps.
    
    Flow:
    1. Query DB for avg values from Completed trips matching route + vehicle type
    2. Get ML predictions for VTAT & CTAT timestamps only
    3. Create ride record using DB-sourced values + ML timestamps
    4. Return ride response
    5. estimated_fare from EDA on DataScience which is already integrated machine learning prediction 
    within production/backend/database/data_science_engineering.ipynb
    """
    try:
        booking_datetime = datetime.now()
        
        # 1. Fetch historical averages from Completed trips
        result = await db.execute(
            text("""
                SELECT
                    AVG(estimated_fare) AS avg_estimated_fare,
                    AVG(actual_fare) AS avg_actual_fare,
                    AVG(distance_km) AS avg_distance_km,
                    AVG(duration_minutes) AS avg_duration_minutes,
                    AVG(driver_rating) AS avg_driver_rating,
                    AVG(demand_pressure) AS avg_demand_pressure
                FROM analytics.trip
                WHERE pickup_location = :pickup
                AND dropoff_location = :dropoff
                AND ride_type = :vehicle_type
                AND booking_status = 'Completed'
            """),
            {
                "pickup": request.pickup_location,
                "dropoff": request.drop_location,
                "vehicle_type": request.vehicle_type,
            }
        )
        row = result.fetchone()

        # Use DB averages if available, otherwise fallback to request values
        if row and row[0] is not None:
            estimated_fare = round(float(row[0]), 2)
            actual_fare = round(float(row[1]), 2) if row[1] else request.price
            distance_km = round(float(row[2]), 2) if row[2] else request.distance_km
            duration_minutes = round(float(row[3]), 2) if row[3] else request.duration_minutes
            driver_rating = round(float(row[4]), 2) if row[4] else request.driver_rating
            demand_pressure = round(float(row[5]), 2) if row[5] else request.demand_pressure
            logger.info(f"📊 DB historical match found for {request.pickup_location} → {request.drop_location} ({request.vehicle_type})")
        else:
            # No historical match — fall back to request input values
            estimated_fare = request.price
            actual_fare = request.price
            distance_km = request.distance_km
            duration_minutes = request.duration_minutes
            driver_rating = request.driver_rating
            demand_pressure = request.demand_pressure
            logger.warning(f"⚠️ No DB match for route, using request values as fallback")

        # 2. ML Predictions for VTAT & CTAT timestamps only
        prediction = await ml_predictor.predict_ride_metrics(
            pickup=request.pickup_location,
            drop=request.drop_location,
            vehicle_type=request.vehicle_type,
            hour=booking_datetime.hour,
            day_of_week=booking_datetime.weekday(),
            distance_km=distance_km,
            booking_datetime=booking_datetime,
            demand_pressure=demand_pressure,
            rating_avg=driver_rating
        )

        ctat_minutes = prediction.get('estimated_drop_time_minute', 0.0)
        vtat_minutes = prediction.get('estimated_vehicle_arrival_minute', 0.0)
        vehicle_arrival_at = booking_datetime + timedelta(minutes=vtat_minutes)

        # 3. Determine booking status from DB history
        status_result = await db.execute(
            text("""
                SELECT booking_status, driver_status, status
                FROM analytics.trip
                WHERE pickup_location = :pickup
                    AND dropoff_location = :dropoff
                    AND ride_type = :vehicle_type
                    AND booking_status = 'Completed'
                ORDER BY created_at DESC
                LIMIT 1
            """),
            {
                "pickup": request.pickup_location,
                "dropoff": request.drop_location,
                "vehicle_type": request.vehicle_type
            }
        )
        status_row = status_result.fetchone()

        if status_row:
            booking_status = status_row[0] # "Completed"
            driver_status = status_row[1] # e.g. "Online"
            status = status_row[2] # e.g. "Completed"
            completed_at = (booking_datetime + timedelta(minutes=ctat_minutes)).strftime("%Y-%m-%d %H:%M:%S")
        else:
            booking_status = BookingStatus.PENDING.value
            driver_status = DriverStatus.OFFLINE.value
            status = BookingStatus.PENDING.value
            completed_at = "No Trip"

        # 4. Create ride record with DB sourced values
        new_trip = Trip(
            ride_id=f"CNR{random.randint(1000000,9999999)}",
            rider_id=request.user_id,
            pickup_location=request.pickup_location,
            dropoff_location=request.drop_location,
            ride_type=request.vehicle_type,
            estimated_fare=estimated_fare,
            actual_fare=actual_fare,
            distance_km=distance_km,
            duration_minutes=duration_minutes,
            driver_rating=driver_rating,
            booking_status=booking_status,
            driver_status=driver_status,
            status=status,
            pickup_lat=request.pickup_lat,
            pickup_lng=request.pickup_lng,
            dropoff_lat=request.dropoff_lat,
            dropoff_lng=request.dropoff_lng,
            created_at=booking_datetime,
            vehicle_arrival_at=vehicle_arrival_at,
            completed_at=completed_at,
            demand_pressure=demand_pressure,
            day_of_week=booking_datetime.weekday(),
            hour=booking_datetime.hour,
        )
            
        db.add(new_trip)
        await db.commit()
        await db.refresh(new_trip)
        logger.info(f"✅ Trip created: {new_trip.ride_id} | Status: {new_trip.booking_status}")

        return RideResponse.model_validate(new_trip)

    except Exception as e:
        await db.rollback()
        logger.error(f"❌ Trip creation failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create trip: {str(e)}")
    
@router.post("/rides/book")
async def book_ride(
    payload: RideBookRequest,
    db: AsyncSession = Depends(get_pg_db)
):
    """
    Book a ride with ML predictions.
    
    Expected payload includes:
    - user_id: Customer ID
    - pickup_location/drop_location: Route locations
    - vehicle_type: Type of vehicle
    - price: Estimated price
    - estimated_pickup_time_minute: VTAT (vehicle arrival time)
    - estimated_drop_time_minute: CTAT (total ride time)
    - pickup_encoded/drop_encoded: Encoded locations for ML
    - route_cluster: Route cluster ID
    - ride_distance: Distance in km
    - pickup_lat/lon/drop_lat/lon: Coordinates
    """
    try:
        # Create ride in database using all fields from payload
        ride = await create_ride_in_db(
            db=db,
            user_id=payload.user_id,
            pickup_location=payload.pickup_location,
            drop_location=payload.drop_location,
            vehicle_type=payload.vehicle_type,
            price=payload.price,
            estimated_pickup_time_minute=payload.estimated_pickup_time_minute,
            estimated_drop_time_minute=payload.estimated_drop_time_minute,
            pickup_encoded=payload.pickup_encoded,
            drop_encoded=payload.drop_encoded,
            route_cluster=payload.route_cluster,
            ride_distance=payload.ride_distance,
            pickup_lat=payload.pickup_lat,
            pickup_lon=payload.pickup_lon,
            drop_lat=payload.drop_lat,
            drop_lon=payload.drop_lon
        )
        
        # Publish to Kafka (non-blocking)
        try:
            await kafka_producer.send_event("ride-requests", {
                "event_type": "ride_booked",
                "ride_id": ride.ride_id,
                "user_id": ride.rider_id,
                "vehicle_type": ride.ride_type,
                "price": ride.actual_fare,
                "pickup_location": ride.pickup_location,
                "drop_location": ride.dropoff_location,
                "estimated_pickup_time_minute": payload.estimated_pickup_time_minute,
                "estimated_drop_time_minute": payload.estimated_drop_time_minute,
                "vehicle_arrival_at": ride.vehicle_arrival_at.isoformat() if ride.vehicle_arrival_at else None,
                "completed_at": ride.completed_at.isoformat() if ride.completed_at else None,
                "timestamp": time.time()
            })
        except Exception as e:
            logger.warning(f"⚠️ Kafka event failed (non-blocking): {e}")
        
        # Return ride details
        return {
            "success": True,
            "ride_id": ride.ride_id,
            "booking_status": ride.booking_status,
            "vehicle_arrival_at": ride.vehicle_arrival_at,
            "completed_at": ride.completed_at,
            "estimated_pickup_time_minute": payload.estimated_pickup_time_minute,
            "estimated_drop_time_minute": payload.estimated_drop_time_minute,
            "message": "Ride booked successfully"
        }
    
    except Exception as e:
        logger.error(f"❌ Error booking ride: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to book ride: {str(e)}")

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
            trip.completed_at = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        
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