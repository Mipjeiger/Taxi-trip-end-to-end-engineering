import numpy as np
import redis.asyncio as redis
from core.config import DATABASE_PATH
import pandas as pd

class VehicleRecommender:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    # Create class for str vehicle type
    class VehicleType:
        vehicle_type: str

    async def recommend_vehicle(self, user_id: str, context: dict) -> dict:
        """
        Recommend a vehicle type based on user context and historical data compatible to redis with DATABASE_PATH.
        In real scenario, fetch user embedding and compute similarity with vehicle embeddings."""
        # Simulate fetching user embedding from Redis
        user_embedding = await self.redis.get(f"user_embedding:{user_id})")
        if user_embedding is None:
            user_embedding = np.random.rand(128)  # Dummy embedding for new users
            await self.redis.set(f"user_embedding:{user_id}", user_embedding.tobytes())
        else:
            user_embedding = np.frombuffer(user_embedding, dtype=np.float32)
        
        # Simulate vehicle type by embedding to database path
        df = pd.read_parquet(DATABASE_PATH)
        vehicle_typess = df['Vehicle Type'].unique()
        vehicle_embeddings = {vt: np.random.rand(128) for vt in vehicle_typess}

        # Compute similarity (dummy implementation)
        similarities = {vt: np.random.rand() for vt in vehicle_typess}
        recommended_vehicle = max(similarities, key=similarities.get)
        sorted_vehicles = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
        # Get alternatives based on scores for top 3 vehicles
        alternatives = [(vt, score) for vt, score in sorted_vehicles if vt != recommended_vehicle][:2]
        return {
            "recommended_vehicle": recommended_vehicle,
            "alternatives": alternatives,
            "scores": similarities
        }