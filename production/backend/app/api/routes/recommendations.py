from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict, Any
from datetime import datetime

from app.services.vehicle_recommender import VehicleRecommender
from app.services.surge_recommender import SurgeRecommender
from app.services.churn_recommender import ChurnRecommender
from app.core.redis_client import get_redis
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
async def recommend_vehicle(req: VehicleRequest, redis_pool: redis.Redis = Depends(get_redis)):
    try:
        recommender = VehicleRecommender(redis_pool)
        return await recommender.recommend_vehicle(req.user_id, req.context)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/surge/{location}")
async def recommend_surge(location: str, current_surge: float, redis_pool: redis.Redis = Depends(get_redis)):
    recommender = SurgeRecommender(redis_pool)
    return await recommender.recommend_action(location, current_hour=datetime.now().hour, current_surge=current_surge)