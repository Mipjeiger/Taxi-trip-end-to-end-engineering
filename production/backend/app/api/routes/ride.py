import pandas as pd
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
from core.config import DATABASE_PATH

"""Handles ride requests and history."""

router = APIRouter()

class RideRequest(BaseModel):
    pickup_location: str
    drop_location: str
    vehicle_type: str
    user_id: str

class RideResponse(BaseModel):
    id: str
    pickup_location: str
    drop_location: str
    vehicle_type: str
    price: float
    estimated_pickup_time_minute: float
    estimated_drop_time_minute: float
    status: str
    created_at: datetime

# Create function to map on row as responsbile
def map_row_to_response(row) -> RideResponse:
    """Conver Dataframe frow to RideResponse."""
    return RideResponse(
        id=str(row['id']),
        pickup_location=row['Pickup Location'].strip(),
        drop_location=row['Drop Location'].strip(),
        vehicle_type=row['Vehicle Type'].strip(),
        price=float(row['Booking Value']),
        estimated_pickup_time_min=float(row['estimated_pickup_time_minute']),
        estimated_drop_time_min=float(row['estimated_drop_time_minute']),
        status=str(row['Booking Status']).strip(),
        created_at=pd.to_datetime(row['Datetime'])
)

def load_rides_parquet() -> pd.DataFrame:
    """Load rides data from parquet file."""
    try:
        return pd.read_parquet(DATABASE_PATH)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Rides data not found.")
    
# Create router endpoint

@router.post("/request")
async def request_ride(ride_request: RideRequest):
    """"Reqyest a new ride."""
    try:
        df = load_rides_parquet()

        # Find matching ride from database
        matching_rides = df[
            (df['Pickup Location'] == ride_request.pickup_location) &
            (df['Drop Location'] == ride_request.drop_location) &
            (df['Vehicle Type'] == ride_request.vehicle_type)
        ]

        if matching_rides.empty:
            raise HTTPException(status_code=404, detail="No matching rides found.")
        
        # Get first matching ride
        ride_data = matching_rides.iloc[0]
        ride_response = map_row_to_response(ride_data)

        return {
            "message": f"Ride requested successfully for user {ride_request.user_id}.",
            "ride": ride_response,
            "success": True
        }
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get("/history/{user_id}", response_model=List[RideResponse])
async def get_ride_history(user_id: str, limit: int = 50):
    """Get ride history for user from database"""
    try:
        df = load_rides_parquet()

        # Filter by Booking ID containing user_id
        user_rides = df[df['Booking ID'] == user_id].head(limit)

        if user_rides.empty:
            raise HTTPException(status_code=404, detail=f"No rides found for user {user_id}.")
        
        # Convert rows to RideResponse objects
        rides = [map_row_to_response(row) for _, row in user_rides.iterrows()]

        return rides
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))