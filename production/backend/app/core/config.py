from pathlib import Path
from pydantic_settings import BaseSettings
from typing import List

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATABASE_PATH = BASE_DIR / 'backend' / 'database' / 'taxi_trip_engineering.parquet'
MODEL_PATH = BASE_DIR / 'backend' / 'models'

class Settings(BaseSettings):
    PROJECT_NAME: str = "Taxi Trip Engineering API Integration"
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:3001"]
    REDIS_URL: str = "redis://localhost:6379"

    # Match to .env postgresql
    DB_USER: str
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int = 5432
    DB_NAME: str

    @property
    def DATABASE_URL(self) -> str:
        # Construct the reliable DSN string
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        extra = "ignore" # Ignore extra fields in .env that are not defined in Settings

settings = Settings()