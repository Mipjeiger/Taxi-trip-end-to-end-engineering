import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from app.core.postgres_db import get_postgres_db
from app.core.database import get_pg_db

logger = logging.getLogger(__name__)
router = APIRouter()

class QueryRequest(BaseModel):
    """Request body for executing custom SQL query"""
    sql: str

@router.get("/health")
async def anyltics_health(db: AsyncSession = Depends(get_postgres_db)):
    """Check PostgreSQL connection health"""
    try:
        await db.execute(text("SELECT 1"))
        return {
            "connected": True,
            "status": "✅ Analytics database connection is healthy"
        }
    except Exception as e:
        logger.error(f"❌ Analytics database connection failed: {e}")
        return {
            "connected": False,
            "status": f"❌ Analytics database connection failed: {e}"
        }

@router.post("/query")
async def run_query(req: QueryRequest, db: AsyncSession = Depends(get_postgres_db)):
    """Run a custom SQL query against Postgresql and return results"""
    try:
        query = req.sql
        result = await db.execute(text(query))
        rows = result.fetchall()

        return {
            "data": [dict(row) for row in rows],
            "rows": len(rows)
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error executing query: {e}")
    
@router.get("/tables")
async def list_tables(db: AsyncSession = Depends(get_postgres_db)):
    """List all tables in PostgreSQL"""
    try:
        query = text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'analytics'
        """)
        result = await db.execute(query)
        tables = [row[0] for row in result.fetchall()]

        return {"tables": tables}
    except Exception as e:
        logger.error(f"❌ Error listing tables: {e}")
        raise HTTPException(status_code=400, detail=f"Error listing tables: {e}")

@router.get("/summary")
async def summary(db: AsyncSession = Depends(get_postgres_db)):
    """Get a summary of the PostgreSQL database"""
    try:
        # Get all tables in analytics schema
        tables_query = text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'analytics'
        """)
        result = await db.execute(tables_query)
        tables = [row[0] for row in result.fetchall()]

        summary = {}
        for table_name in tables:
            count_query = text(f"SELECT COUNT(*) FROM analytics.{table_name}")
            count_result = await db.execute(count_query)
            count = count_result.fetchone()[0]
            summary[table_name] = count

        return {"summary": summary}
    except Exception as e:
        logger.error(f"❌ Error generating summary: {e}")
        raise HTTPException(status_code=400, detail=f"Error generating summary: {e}")
    
@router.get("/rides/stats")
async def ride_statistics(db: AsyncSession = Depends(get_postgres_db)):
    """Get ride statistics such as average price, average distance, and total rides"""
    try:
        query = text("""
            SELECT 
                COUNT(*) AS total_rides,
                AVG(actual_fare) AS avg_fare,
                AVG(distance_km) AS avg_distance,
                AVG(duration_minutes) AS avg_duration,
                AVG(driver_rating) AS avg_driver_rating
            FROM analytics.trip
        """)
        result = await db.execute(query)
        row = result.fetchone()

        return {
            "total_rides": row[0],
            "avg_fare": float(row[1] if row[1] is not None else 0),
            "avg_distance": float(row[2] if row[2] is not None else 0),
            "avg_duration": float(row[3] if row[3] is not None else 0)
        }
    except Exception as e:
        logger.error(f"❌ Error fetching ride statistics: {e}")
        raise HTTPException(status_code=400, detail=f"Error fetching ride statistics: {e}")
    
@router.get("/driver/top")
async def top_drivers(limit: int = 10 ,db: AsyncSession = Depends(get_postgres_db)):
    """Get top rated drivers"""
    try:
        query = text("""
            SELECT
                    d.driver_id,
                    d.rating,
                    COUNT(t.ride_id) AS total_rides
            FROM analytics.drivers d
            LEFT JOIN analytics.trip t 
                ON d.driver_id = t.driver_id
            GROUP BY d.driver_id, d.rating
            ORDER BY d.rating DESC
            LIMIT :limit
        """)
        result = await db.execute(query, {"limit": limit})
        rows = result.fetchall()

        return {
            "drivers": [
                {
                    "driver_id": row[0],
                    "avg_rating": float(row[1] if row[1] else 0),
                    "total_rides": row[2]
                }
                for row in rows
            ]
        }
    except Exception as e:
        logger.error(f"❌ Error fetching top drivers: {e}")
        raise HTTPException(status_code=400, detail=f"Error fetching top drivers: {e}")