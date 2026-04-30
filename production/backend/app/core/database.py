from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

# Fetch database URL from settings
engine = create_async_engine(settings.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"), echo=True)
AsyncSessionLocal = sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
Base = declarative_base()

async def init_db():
    """Initialize the database connection and create tables."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)