import numpy as np
import redis.asyncio as redis
from app.core.config import settings
import pandas as pd
import json
import logging
from sqlalchemy import text

logger = logging.getLogger(__name__)

class VehicleRecommender:
    def __init__(self, redis_client: redis.Redis):
        self.redis = redis_client

    async def recommend_vehicle(self, user_id: str, context: dict) -> dict:
        """
        Recommend a vehicle type based on user context and real-time active driver availability.
        Uses Redis caching to avoid Postgres lookup bottlenecks.
        """

        # 1. Fetch user embedding from Redis cache
        user_embedding = await self.redis.get(f"user_embedding:{user_id}")
        if user_embedding is None:
            user_embedding = np.random.rand(28).astype(np.float32) # Dummy embedding
        else:
            user_embedding = np.frombuffer(user_embedding, dtype=np.float32)

        # 2, Get active vehicle types with online drivers from Redis
        active_vehicles_key = "active_vehicle_types"
        active_vehicles_data = await self.redis.get(active_vehicles_key)

        if active_vehicles_data:
            # Redis cache hit
            vehicle_types = json.loads(active_vehicles_data)
        else:
            # 3. Cache miss: Query Postgres database on the drivers table
            vehicle_types = []
            try:

                from app.core.postgres_db import get_postgres_db
                async for db in get_postgres_db():
                    query = text("""
                        SELECT DISTINCT vehicle_type
                        FROM analytics.drivers
                        WHERE status = 'online'
                    """)
                    result = await db.execute(query)
                    rows = result.fetchall()
                    vehicle_types = [row[0] for row in rows if row[0] is not None]

                    if vehicle_types:
                        # Cache the results in Redis for 30 seconds
                        await self.redis.set(active_vehicles_key, json.dumps(vehicle_types), ex=30)
                        logger.info(f"✅ Cached {len(vehicle_types)} active vehicle types from PostgreSQL")
                        break

            except Exception as e:
                logger.error(f"❌ Error fetching active drivers from Postgres: {e}") 
                vehicle_types = ["HRV", "Innova", "Alphard", "Go Sedan", "Brio"] # Fallback list of vehicle types

        # 4. Generate dummy similarity scores for active vehicle types
        vehicle_embeddings = {vt: np.random.rand(128).astype(np.float32) for vt in vehicle_types}
        similarities = {
            vt: float(np.dot(user_embedding, vehicle_embeddings[vt]) / (np.linalg.norm(user_embedding) * np.linalg.norm(vehicle_embeddings[vt])))
            for vt in vehicle_types
        }

        # Determine recommendations
        recommended_vehicle = max(similarities, key=similarities.get)
        sorted_vehicles = sorted(similarities.items(), key=lambda x: x[1], reverse=True)
        alternatives = [(vt, score) for vt, score in sorted_vehicles if vt != recommended_vehicle][:2]

        return {
            "recommended_vehicle": recommended_vehicle,
            "alternatives": alternatives,
            "scores": similarities,
            "source": "redis_cache" if active_vehicles_data else "postgres_db"
        }