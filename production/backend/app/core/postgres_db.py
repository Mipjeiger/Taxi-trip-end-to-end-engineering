import logging
import os
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_PATH = BASE_DIR.parent / '.env'
logger.info(f"✅ Loaded environtment variables from: {ENV_PATH}")

if not ENV_PATH.exists():
    ENV_PATH = BASE_DIR / '.env'
    logging.debug(f"⚠️ .env file not found at {ENV_PATH}, trying fallback location: {ENV_PATH}")

load_dotenv(dotenv_path=ENV_PATH)

# ================================================================
# Analytics Database Connection (PostgreSQL)
# ================================================================

class AnalyticdDatabase:
    """Manages connection to PostgreSQL database for analytics
    Separate from Supabase connection used for transactional data to avoid performance impact on main app"""

    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()

    def _initialize_engine(self):
        """Initialize async engine for PostgreSQL connection"""
        try:
            user = os.getenv("POSTGRES_USER")
            password = os.getenv("POSTGRES_PASSWORD")
            host = os.getenv("POSTGRES_HOST")
            port = os.getenv("POSTGRES_PORT")
            db = os.getenv("POSTGRES_DB")

            if not all([user, password, host, port, db]):
                raise ValueError("PostgreSQL connection parameters are not fully set in environment variables.")
            
            # Construct async database URL and create engine
            database_url = f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"
            logger.info(f"📊 Initializing Analytics Database: {host}:{port}/{db}")

            # Create async engine and sessionmakers
            self.engine = create_async_engine(
                database_url, 
                echo=False, 
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True, # Test connections before using to avoid stale connections
                pool_recycle=3600 # Recycle connections after 1 hour to prevent timeouts
                )
            
            self.SessionLocal = sessionmaker(
                bind=self.engine, 
                class_=AsyncSession, 
                expire_on_commit=False,
                autocommit=False,
                autoflush=False)
            logger.info(f"✅ PostgreSQL analytics engine initialized successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize PostgreSQL analytics engine: {e}")
            raise

    async def verify_connection(self):
        """Verify connection to PostgreSQL database"""
        try:
            async with self.SessionLocal() as session:
                await session.execute(__import__("sqlalchemy").text("SELECT 1"))
            logger.info("✅ Successfully connected to PostgreSQL analytics database")
            return True
        
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL analytics database: {e}")
            return False
        
    async def close(self):
        """Close the database engine"""
        if self.engine:
            await self.engine.dispose()
            logger.info("✅ PostgreSQL analytics engine disposed successfully")

# GLobal instance singleton
postgres_con = AnalyticdDatabase()

# ================================================================
# Dependency for getting DB session in FastAPI routes
# ================================================================

async def get_postgres_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency to get analytics database session
    Use this instead of get_db() for analytics queries to avoid connection issues between supabase pool
    
    This function automatically sets the schema search path to include 'analytics'
    so you can query tables without specifying schema prefix.

    Usage in route:
        @router.get("/endpoint")
        async def my_endpoint(db: AsyncSession = Depends(get_postgres_db)):
    """
    async with postgres_con.SessionLocal() as session:
        try:
            await session.execute(text("SET search_path TO public, analytics"))
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()