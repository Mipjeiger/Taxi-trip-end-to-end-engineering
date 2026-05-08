from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from app.core.config import settings
from typing import AsyncGenerator
import ssl
import asyncpg
import logging

# Get logger
logger = logging.getLogger(__name__)

# 1. Define Base here
class Base(DeclarativeBase):
    pass

# Create SSL context for supabase connection
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

# 2. Setup Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG, # For only echo SQL in debug mode
    poolclass=NullPool, # Critical for serverless environments to avoid connection issues
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0,
        "command_timeout": 60,
        "timeout": 30,
        "ssl": ssl_context,
    }
)

# 4. Setup session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

async def init_db():
    """Initialize the database connection and create tables."""
    from app.models.ride import Ride # Import models inside the function to register

    # Raw asyncpg connection - completely bypasses SQLAIchemy's
    conn = await asyncpg.connect(
        host=settings.SUPABASE_HOST,
        port=settings.SUPABASE_PORT,
        user=settings.SUPABASE_USER,
        password=settings.SUPABASE_PASSWORD,
        database=settings.SUPABASE_DB,
        ssl=ssl_context,
        statement_cache_size=0,
    )
    try:
        async with engine.begin() as sa_conn:
            await sa_conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database initialized and tables created")
    finally:
        await conn.close()

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency function that yields a db session. This ensures the session is closed automatically after the request is done."""
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()