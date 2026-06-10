import asyncio
import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from dotenv import load_dotenv
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)
print(f"Loaded environment variables from {ENV_PATH}")

if not ENV_PATH.exists():
    raise FileNotFoundError(f"Environment file not found at {ENV_PATH}")


"""This dir for testing database query directly for LLM Integration. 
Not for unit testing or integration testing of API endpoints."""

async def test_query():
    database_url = f"postgresql+asyncpg://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"

    engine = create_async_engine(database_url)
    async with engine.begin() as conn:
        # Test raw sql query
        result = await conn.execute(
            text("SELECT * FROM analytics.trip WHERE pickup_location ILIKE '%Pasar%' LIMIT 5")
        )
        rows = result.fetchall()
        print(f"Found {len(rows)} trips with 'Pasar' in pickup location:")
        
        for row in rows:
            print(f"  - {row.pickup_location} → {row.dropoff_location} ({row.ride_type})")

    
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_query())