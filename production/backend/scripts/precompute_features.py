"""Precompute features and store them in Redis for faster API responses."""

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
REDIS_URL = "redis://localhost:6379"

async def precompute_features():
    """Load data, compute features, and cache them in Redis."""
    try:
        r = await redis.from_url(REDIS_URL, decode_responses=True)
        logger.info("✅ Connected to Redis")

        # Load parquet database
        parquet_file = DATABASE_PATH
        if not parquet_file.exists():
            logger.error(f"❌ Parquet file not found at {parquet_file}")
            return
        
        df = pd.read_parquet(parquet_file)
        logger.info(f"✅ Loaded {len(df)} records")

        # Precompute route stats
        route_stats = df.groupby(['Pickup Encoded', 'Drop Encoded']).agg({
            'Avg CTAT': ['mean', 'std'],
            'Booking Value': 'mean',
        }).to_dict()

        # Precompute hourly stats
        hourly_stats = df.groupby('hour').agg({
            'Avg CTAT': 'mean',
            'Booking Value': 'mean',
        }).to_dict()

        # Cache to Redis with a TTL of 24 hours
        await r.set("route_stats", pickle.dumps(route_stats), ex=86400)
        await r.set("hourly_stats", pickle.dumps(hourly_stats), ex=86400)
        await r.set("total_records", len(df), ex=86400)

        logger.info("✅ Precomputed features all cached in Redis")
        await r.close()

    except Exception as e:
        logger.error(f"❌ Error during precomputation: {e}")
        raise

async def main():
    await precompute_features()

if __name__ == "__main__":
    asyncio.run(main())