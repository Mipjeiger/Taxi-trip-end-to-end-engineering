from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime

from app.services.vehicle_recommender import VehicleRecommender
from app.services.surge_recommender import SurgeRecommender
from app.services.churn_recommender import ChurnRecommender
from app.core.redis_client import get_redis
from app.api.dependencies import get_churn_recommender, get_vehicle_recommender, get_surge_recommender
import redis.asyncio as redis

router = APIRouter()

# Create classes for request engineering methods
class VehicleRequest(BaseModel):
    user_id: str
    context: Dict[str, Any]

class ChurnRequest(BaseModel):
    last_ride_days: int
    avg_rating: float
    total_trips: int

@router.post("/vehicle")
async def recommend_vehicle(req: VehicleRequest, recommender: VehicleRecommender = Depends(get_vehicle_recommender)):
    try:
        return await recommender.recommend_vehicle(req.user_id, req.context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/surge/{location}")
async def recommend_surge(location: str, current_surge: float, recommender: SurgeRecommender = Depends(get_surge_recommender)):
    return await recommender.recommend_action(location, current_hour=datetime.now().hour, current_surge=current_surge)

@router.post("/churn/{user_id}")
async def churn_promo(user_id: str, features: ChurnRequest, recommender: ChurnRecommender = Depends(get_churn_recommender)):
    return await recommender.recommend_promo(user_id, features.last_ride_days, features.avg_rating, features.total_trips)