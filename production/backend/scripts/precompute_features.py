"""Precompute features and store them in Redis for faster API responses."""

import sys
from pathlib import Path

# Add backend dir to sys.path BEFORE importing from app
backend_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_dir))

import asyncio
import redis.asyncio as redis
import pandas as pd
import logging
import pickle
from pathlib import Path
from app.core.config import DATABASE_PATH

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent
REDIS_URL = "redis://Redis:6379"

async def precompute_features():
    """Load data, compute features, and cache them in Redis."""
    try:
        r = await redis.from_url(REDIS_URL, decode_responses=True)
        df = pd.read_parquet(DATABASE_PATH)
        logger.info("✅ Connected to Redis")

        # Calculate group averages
        route_stats = df.groupby(['Pickup Encoded', 'Drop Encoded']).agg({
            'Avg CTAT': 'mean',
            'Booking Value': 'mean'
        }).reset_index()

        # Write each route's features as a Redis hash
        for _, row in route_stats.iterrows():
            pickup = int(row['Pickup Encoded'])
            drop = int(row['Drop Encoded'])
            key = f"features:route:{pickup}:{drop}"
            
            await r.hset(key, mapping={
                "avg_ctat": float(row['Avg CTAT']),
                "avg_booking_value": float(row['Booking Value'])
            })

            await r.expire(key, 86400) # Set expiry for 24 hours

    except Exception as e:
        logger.error(f"❌ Error during precomputation: {e}")
        raise

async def main():
    await precompute_features()

if __name__ == "__main__":
    asyncio.run(main())