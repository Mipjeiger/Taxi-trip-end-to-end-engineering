from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class PredictionCache(BaseModel):
    pickup: str
    drop: str
    vehicle_type: str
    hour: int
    day_of_week: int
    distance_km: float
    time_min: float
    price_idr: float
    created_at: float = datetime.now().timestamp()

    # Create class config to estimate prediction cache (e.g. example data for documentation)
    class Config:
        json_schema_extra = {
            "example": {
                "pickup": "Kali Anyar",
                "drop": "Rawamangun",
                "vehicle_type": "Car",
                "hour": 14,
                "day_of_week": 3,
                "distance_km": 39.29,
                "time_min": 15.2,
                "price_idr": 114000.0
            }
        }

# Usage backend
Prediction = PredictionCache