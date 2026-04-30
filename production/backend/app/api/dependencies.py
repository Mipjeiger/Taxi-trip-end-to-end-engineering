"""Provides global services and dependencies for the API."""

from app.services.ml_predictor import MLPredictor
from app.main import ml_predictor, vehicle_recommender, surge_recommender, churn_recommender

async def get_ml_predictor() -> MLPredictor:
    """Dependency to get the ML Predictor instance."""
    return ml_predictor

async def get_vehicle_recommender():
    """Dependency to get the Vehicle Recommender instance."""
    return vehicle_recommender

async def get_surge_recommender():
    """Dependency to get the Surge Recommender instance."""
    return surge_recommender

async def get_churn_recommender():
    """Dependency to get the Churn Recommender instance."""
    return churn_recommender