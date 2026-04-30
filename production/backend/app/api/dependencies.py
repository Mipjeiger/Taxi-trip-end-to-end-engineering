from typing import Optional
from app.services.ml_predictor import MLPredictor
from app.services.vehicle_recommender import VehicleRecommender
from app.services.surge_recommender import SurgeRecommender
from app.services.churn_recommender import ChurnRecommender
from app.services.matching_recommender import MatchingRecommender
from app.services.route_recommender import RouteRecommender
from app.core.redis_client import get_redis
import redis.asyncio as redis

# These will be set in main.py lifespan
_ml_predictor: Optional[MLPredictor] = None
_vehicle_recommender: Optional[VehicleRecommender] = None
_surge_recommender: Optional[SurgeRecommender] = None
_churn_recommender: Optional[ChurnRecommender] = None
_matching_recommender: Optional[MatchingRecommender] = None
_route_recommender: Optional[RouteRecommender] = None

def set_ml_predictor(instance: MLPredictor):
    global _ml_predictor
    _ml_predictor = instance

def set_vehicle_recommender(instance: VehicleRecommender):
    global _vehicle_recommender
    _vehicle_recommender = instance

def set_surge_recommender(instance: SurgeRecommender):
    global _surge_recommender
    _surge_recommender = instance

def set_churn_recommender(instance: ChurnRecommender):
    global _churn_recommender
    _churn_recommender = instance

def set_matching_recommender(instance: MatchingRecommender):
    global _matching_recommender
    _matching_recommender = instance

def set_route_recommender(instance: RouteRecommender):
    global _route_recommender
    _route_recommender = instance

async def get_ml_predictor() -> MLPredictor:
    return _ml_predictor

async def get_vehicle_recommender() -> VehicleRecommender:
    return _vehicle_recommender

async def get_surge_recommender() -> SurgeRecommender:
    return _surge_recommender

async def get_churn_recommender() -> ChurnRecommender:
    return _churn_recommender

async def get_matching_recommender() -> MatchingRecommender:
    return _matching_recommender

async def get_route_recommender() -> RouteRecommender:
    return _route_recommender

async def get_redis_client() -> redis.Redis:
    return await get_redis()