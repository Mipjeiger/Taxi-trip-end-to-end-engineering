from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

from app.services.ml_predictor import MLPredictor
from app.api.dependencies import get_ml_predictor

router = APIRouter()

# create class for request with pydantic
class RideRequest(BaseModel):
    pickup_location: str
    drop_location: str
    vehicle_type: str = Field("Car", pattern="^(Car|Motorcycle|Auto|Go Sedan|Premier Sedan|eBike|Uber XL)$")
    hour: Optional[int] = None
    day_of_week: Optional[int] = None

class RidePredictionResponse(BaseModel):
    pickup_location: str
    drop_location: str
    distance_km: float
    estimated_pickup_time_minute: float
    estimated_drop_time_minute: float
    vtat_min: float
    ctat_min: float
    estimated_price_idr: float
    average_speed_kmh: float
    price_per_km: float
    vehicle_type: str

# Create router endpoint
@router.post("/route", response_model=RidePredictionResponse)
async def predict_route(request: RideRequest, ml_predictor: MLPredictor = Depends(get_ml_predictor)):
    """Predict ride metrics using trained ML models"""
    if request.hour is None:
        request.hour = datetime.now().hour
    if request.day_of_week is None:
        request.day_of_week = datetime.now().weekday()

    try:
        prediction = await ml_predictor.predict_ride_metrics(
            pickup_location=request.pickup_location,
            drop_location=request.drop_location,
            vehicle_type=request.vehicle_type,
            hour=request.hour,
            day_of_week=request.day_of_week
        )
        return prediction
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))