from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool
from app.core.config import settings
from typing import AsyncGenerator
import ssl
import asyncpg
import logging
import time
import psycopg2

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

# 3.Setup Engine for PostgreSQL connection for raw SQL queries (psycopg2)
engine_pg = create_async_engine(
    settings.POSTGRES_URL,
    echo=False, # No need to echo for raw SQL connection
    poolclass=NullPool, # Avoid connection pooling issues in serverless
    connect_args={
        "connect_timeout": 30,
        "sslmode": 'require'
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

# 4.2 Setup session factory for PostgreSQL connection (psycopg2)
AsyncSessionLocalPg = async_sessionmaker(
    bind=engine_pg,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

async def init_db():
    """Initialize the database connection and create tables."""
    from app.models.ride import Ride # Import models inside the function to register

    conn = await asyncpg.connect(
        host=settings.SUPABASE_HOST,
        port=settings.SUPABASE_PORT,
        user=settings.SUPABASE_USER,
        password=settings.SUPABASE_PASSWORD,
        database=settings.SUPABASE_DB,
        ssl=ssl_context,
        statement_cache_size=4
    )   
    try:
        async with engine.begin() as sa_conn:
            await sa_conn.run_sync(Base.metadata.create_all)
        logger.info("✅ Database initialized and tables created")
    finally:
        await conn.close()

async def init_pg_db():
    """Initialize the PostgreSQL database connection for raw SQL queries."""
    global engine_pg
    try:
        engine_pg = psycopg2.connect(
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            dbname=settings.POSTGRES_DB,
            sslmode='require',
            connect_timeout=30
        )
        logger.info("✅ PostgreSQL connection initialized for raw SQL queries.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize PostgreSQL connection: {e}")
        engine_pg = None

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

async def get_pg_db() -> AsyncGenerator[psycopg2.extensions.connection, None]:
    """Dependency function that yields a psycopg2 connection for raw SQL queries."""
    async with AsyncSessionLocalPg() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

def get_supabase_connection():
    """Get a psycopg2 connection to Supabase for raw SQL queries."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=settings.SUPABASE_HOST,
                port=settings.SUPABASE_PORT,
                user=settings.SUPABASE_USER,
                password=settings.SUPABASE_PASSWORD,
                dbname=settings.SUPABASE_DB
            )
            return conn
        
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"⚠️  Failed to connect to Supabase (attempt {attempt + 1}/{max_retries}): {str(e)}. Retrying...")
                time.sleep(5)  # Wait before retrying
            else:
                raise

def get_postgres_connection():
    """Get a psycopg2 connection to PostgreSQL for raw SQL queries."""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=settings.POSTGRES_HOST,
                port=settings.POSTGRES_PORT,
                user=settings.POSTGRES_USER,
                password=settings.POSTGRES_PASSWORD,
                dbname=settings.POSTGRES_DB,
                sslmode='require',
                connect_timeout=30
            )
            return conn
        
        except Exception as e:
            if attempt < max_retries - 1:
                logger.warning(f"⚠️ Failed to connect to PostgreSQL (attempt {attempt + 1}/{max_retries}): {str(e)}. Retrying...")
                time.sleep(5)  # Wait before retrying
            else:
                raise