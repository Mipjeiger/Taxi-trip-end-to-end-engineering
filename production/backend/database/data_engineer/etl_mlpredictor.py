import os
import logging
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Configuration
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent
ENV_PATH = BASE_DIR / '.env'
DATABASE_PATH = BASE_DIR / 'backend' / 'database' / 'taxi_trip_engineering_2.parquet'
load_dotenv(dotenv_path=ENV_PATH)

POSTGRES_USER = os.getenv('POSTGRES_USER')
POSTGRES_PASSWORD = os.getenv('POSTGRES_PASSWORD')
POSTGRES_HOST = os.getenv('POSTGRES_HOST')
POSTGRES_PORT = os.getenv('POSTGRES_PORT') or 5433
POSTGRES_DB = os.getenv('POSTGRES_DB')

class MLPredictorETL:
   
    def __init__(self, db: AsyncSession):
        self.db = db

    def get_vehicle_encoded(self, raw_vehicle_type: str) -> int:
        """Encode vehicle type to integer"""

        # 1. Map your parquet dataset values to your desired vehicle names
        PARQUET_TO_TARGET_MAPPING = {
            'Go Sedan': 'Go Sedan',
            'Premier Sedan': 'Premier Sedan',
            'Car': 'HRV',               
            'Auto': 'Brio',             
            'Uber XL': 'Innova',        
            'Motorcycle': 'Terios',     
            'eBike': 'Alphard'
        }

        VEHICLE_TYPE_ENCODING = {
            'Alphard': 0, 
            'HRV': 1, 
            'Go Sedan': 2,
            'Innova': 3, 
            'Premier Sedan': 4, 
            'Brio': 5, 
            'Terios': 6
        }

        # Translate the name first
        target_name = PARQUET_TO_TARGET_MAPPING.get(raw_vehicle_type, 'Brio')  # Default to 'Brio' if not found
        return VEHICLE_TYPE_ENCODING.get(target_name, 5)


    async def etl_data_to_postgres(self):
        """ETL process to load data from Parquet file to PostgreSQL"""
        try:
            # Load data from parquet
            logger.info(f"Loading data from {DATABASE_PATH}")
            df = pd.read_parquet(DATABASE_PATH)
            logger.info(f"Data loaded successfully with shape {df.shape}")

            # Insert data into PostgreSQL
            insert_query = text("""
                INSERT INTO analytics.ml_predictor (
                    pickup_encoded, drop_encoded, vehicle_encoded, hour, day_of_week,
                    route_cluster, distance_km, is_peak_hour, is_weekend, is_night,
                    hour_sin, hour_cos, day_sin, day_cos)
                VALUES (:pickup_encoded, :drop_encoded, :vehicle_encoded, :hour, :day_of_week,
                :route_cluster, :distance_km, :is_peak_hour, :is_weekend, :is_night,
                :hour_sin, :hour_cos, :day_sin, :day_cos)
                """)

            logger.info("Inserting data into PostgreSQL...")
            
            # Build records as same as dataframe columns to ingest on PostgreSQL
            data_to_insert = []
            for _, row in df.iterrows():
                record = {
                    "pickup_encoded": row['Pickup Encoded'],
                    "drop_encoded": row['Drop Encoded'], 
                    "vehicle_encoded": self.get_vehicle_encoded(row['Vehicle Type']),    
                    "hour": row['hour'],
                    "day_of_week": row['day_of_week'],
                    "route_cluster": row.get("route_cluster"),
                    "distance_km": row.get("Ride Distance"),
                    "is_peak_hour": int(row.get("is_peak_hour", 0)),
                    "is_weekend": int(row.get("is_weekend", 0)),
                    "is_night": int(row.get("is_night", 0)),
                    "hour_sin": row.get("hour_sin"),
                    "hour_cos": row.get("hour_cos"),
                    "day_sin": row.get("day_sin"),
                    "day_cos": row.get("day_cos")
                }

                data_to_insert.append(record)

            logger.info(f"Inserting {len(data_to_insert)} records into PostgreSQL...")
            await self.db.execute(insert_query, data_to_insert)

            # Commit the transaction
            await self.db.commit()
            logger.info("Data inserted successfully into PostgreSQL.")

        except Exception as e:
            await self.db.rollback()
            logger.error(f"❌ Failed to ETL data to PostgreSQL: {e}", exc_info=True)


async def main():
    # Async url construction for PostgreSQL
    DATABASE_URL = f"postgresql+asyncpg://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"

    engine = create_async_engine(DATABASE_URL, echo=False)

    # Session factory
    async_session = sessionmaker(engine,
                                 class_=AsyncSession,
                                 expire_on_commit=False)
    
    # Open session and run ETL
    async with async_session() as session:
        etl = MLPredictorETL(db=session)
        await etl.etl_data_to_postgres()

    # Close the engine
    await engine.dispose()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())