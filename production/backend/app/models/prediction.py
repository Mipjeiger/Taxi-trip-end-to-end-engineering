from pydantic import BaseModel
from typing import Optional

class PredictionCache(BaseModel):
    pickup: str
    drop: str
    vehicle_type: str
    hour: int
    day_of_week: int
    distance_km: float
    time_min: float
    price_idr: float
    created_at: float