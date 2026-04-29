from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List
from datetime import datetime

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
    estimated_time_pickup: float
    estimated_time_dropoff: float
    status: str
    created_at: datetime

# Create router endpoint for requesting a ride
@router.post("/request")
async def request_ride(ride_request: RideRequest):
    # In real production app, store in DB, match with driver, calculate price, etc.
    return {
        "ride_id": "ride_123",
        "status": "searching",
        "estimated_driver_arrival": 3.5,
        "message": "Driver assigned soon"
    }

@router.get("/history/{user_id}")
async def get_ride_history(user_id: str, limit: int = 20):
    # Mock data - connect to DB in real app
    mock_rides = [
        {
            "id": "CID5129306",
            "pickup_location": "Palmerah",
            "drop_location": "Karet Semanggi",
            "vehicle_type": "Premier Sedan",
            "price": 41020.96,
            "estimated_time_min": 15,
            "status": "completed",
            "created_at": datetime.now().isoformat()
        }
    ]