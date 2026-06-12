import asyncio
import sys
import os
sys.path.append('/app')  # Add if running in Docker

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text, select
import logging
from dotenv import load_dotenv
from pathlib import Path

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)
logger.info(f"Loaded environment variables from {ENV_PATH}")

async def test_connection():
    # Use your actual database credentials from .env
    DATABASE_URL = "postgresql+asyncpg://your_user:your_password@your_host:5432/your_db"
    
    # Or read from environment
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")
    db = os.getenv("POSTGRES_DB")

    DATABASE_URL = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
    logger.info(f"Connecting to: postgresql+asyncpg://{user}:***@{host}:{port}/{db}")
    
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    async with engine.begin() as conn:
        # Test 1: Check if schema exists
        result = await conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'analytics'"))
        schema_exists = result.fetchone()
        logger.info(f"Analytics schema exists: {schema_exists is not None}")
        
        # Test 2: Query with explicit schema
        result = await conn.execute(text("SELECT COUNT(*) FROM analytics.trip"))
        count = result.scalar()
        logger.info(f"Total trips in analytics.trip: {count}")
        
        # Test 3: Get sample data
        result = await conn.execute(text("SELECT pickup_location, dropoff_location, ride_type FROM analytics.trip LIMIT 5"))
        rows = result.fetchall()
        logger.info("Sample trips:")
        for row in rows:
            logger.info(f"  - {row[0]} → {row[1]} ({row[2]})")
    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_connection())