from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_PATH = BASE_DIR / 'backend' / 'database' / 'taxi_trip_engineering.parquet'
MODEL_PATH = BASE_DIR / 'backend' / 'models'

from pydantic_settings import BaseSettings
from typing import List

class Settings(BaseSettings):
    PROJECT_NAME: str = "Taxi Trip Engineering API Integration"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    REDIS_URL: str = "redis://localhost:6379"
    DATABASE_URL: str = 

    class Config:
        env_file = ".env"

settings = Settings()