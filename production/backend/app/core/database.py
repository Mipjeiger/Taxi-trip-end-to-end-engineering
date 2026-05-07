from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings
from typing import AsyncGenerator

# 1. Define Base here
Base = declarative_base()

# 2. Setup Engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG, # For only echo SQL in debug mode
    pool_pre_ping=True, # Check connection health before using
    connect_args={
        "statement_cache_size": 0,
        "prepared_statement_cache_size": 0
    }
)

# 4. Setup session factory
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def init_db():
    """Initialize the database connection and create tables."""
    from app.models.ride import Ride # Import models inside the function to register

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency function that yields a db session.
    This ensures the session is closed automatically after the request is done.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()