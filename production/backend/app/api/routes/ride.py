import pandas as pd
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, ConfigDict
from typing import List, Optional
from datetime import datetime
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.ride import Ride

"""Handles ride requests and history."""

router = APIRouter()

class RideRequest(BaseModel):
    pickup_location: str
    drop_location: str
    vehicle_type: str
    user_id: str

class RideResponse(BaseModel):
    id: str
    user_id: str
    pickup_location: str
    drop_location: str
    vehicle_type: str
    price: float
    estimated_pickup_time_minute: float
    estimated_drop_time_minute: float
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)

# Create function to map on row as responsbile
def map_row_to_response(row) -> RideResponse:
    """Conver Dataframe frow to RideResponse."""
    return RideResponse(
        id=str(row['id']),
        user_id=str(row['user_id']),
        pickup_location=row['Pickup Location'].strip(),
        drop_location=row['Drop Location'].strip(),
        vehicle_type=row['Vehicle Type'].strip(),
        price=float(row['Booking Value']),
        estimated_pickup_time_minute=float(row['estimated_pickup_time_minute']),
        estimated_drop_time_minute=float(row['estimated_drop_time_minute']),
        status=str(row['Booking Status']).strip(),
        created_at=pd.to_datetime(row['Datetime'])
)
   
# Create router endpoint
@router.post("/request")
async def request_ride(ride_request: RideRequest, db: AsyncSession = Depends(get_db)):
    """"Reqyest a new ride."""
    try:
        # Connect to postgresql database
        query = select(Ride).where(
            Ride.pickup_location == ride_request.pickup_location,
            Ride.drop_location == ride_request.drop_location,
            Ride.vehicle_type == ride_request.vehicle_type
        )
        result = await db.execute(query)
        ride_data = result.scalars().first()

        if not ride_data:
            raise HTTPException(status_code=404, detail="No matching rides found in database.")
        
        return {
            "message": f"Ride requested successfully for user {ride_request.user_id}.",
            "ride": ride_data.to_dict(),
            "success": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/history/{user_id}", response_model=List[RideResponse])
async def get_ride_history(user_id: str, limit: int = 100, db: AsyncSession = Depends(get_db)):
    """Get ride history for user from PostgreSQL database."""
    try:
        # Strip the user_id to handle any accidental whitespace
        clean_user_id = user_id.strip()

        # Query Postgres
        query = select(Ride).where(Ride.user_id == clean_user_id).limit(limit)
        result = await db.execute(query)
        rides = result.scalars().all()

        # Return empty list if no rides history found
        return rides
    
    except Exception as e:
        print(f"Error fetching history: {e}")
        raise HTTPException(status_code=500, detail=str(e))