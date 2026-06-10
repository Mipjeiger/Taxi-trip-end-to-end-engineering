import logging
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from app.core.postgres_db import get_postgres_db
from app.services.trip_retriever import TripRetriever

router = APIRouter(prefix="/debug", tags=["Debug"])
logger = logging.getLogger(__name__)

@router.get("/db-status")
async def db_status(db: AsyncSession = Depends(get_postgres_db)):
    """Check database connection and display available trips"""
    try:
        # Test connection
        result = await db.execute(text("SELECT 1"))
        
        # Get trip count
        result = await db.execute(text("SELECT COUNT(*) FROM analytics.trip"))
        total = result.scalar()
        
        # Get completed trips
        result = await db.execute(text("SELECT COUNT(*) FROM analytics.trip WHERE status = 'Completed'"))
        completed = result.scalar()
        
        # Get sample trips
        result = await db.execute(text("""
            SELECT pickup_location, dropoff_location, ride_type, duration_minutes, actual_fare 
            FROM analytics.trip 
            WHERE status = 'Completed' 
            LIMIT 5
        """))
        samples = result.fetchall()
        
        return {
            "status": "connected",
            "total_trips": total,
            "completed_trips": completed,
            "sample_trips": [
                {
                    "pickup": s[0],
                    "dropoff": s[1],
                    "vehicle": s[2],
                    "duration_min": float(s[3]) if s[3] else None,
                    "fare": float(s[4]) if s[4] else None
                }
                for s in samples
            ]
        }
    except Exception as e:
        logger.error(f"Database debug error: {e}", exc_info=True)
        return {
            "status": "error",
            "error": str(e)
        }

@router.get("/test-route/{pickup}/{dropoff}")
async def test_route(pickup: str, dropoff: str, db: AsyncSession = Depends(get_postgres_db)):
    """Test if a specific route exists"""
    try:
        query = text("""
            SELECT ride_type, COUNT(*) as count, 
                   AVG(duration_minutes) as avg_duration,
                   AVG(actual_fare) as avg_fare
            FROM analytics.trip
            WHERE status = 'Completed'
                AND pickup_location ILIKE :pickup
                AND dropoff_location ILIKE :dropoff
            GROUP BY ride_type
        """)
        
        result = await db.execute(query, {"pickup": f"%{pickup}%", "dropoff": f"%{dropoff}%"})
        rows = result.fetchall()
        
        return {
            "pickup_search": pickup,
            "dropoff_search": dropoff,
            "found": len(rows) > 0,
            "routes": [
                {
                    "vehicle": r[0],
                    "count": r[1],
                    "avg_duration_min": float(r[2]) if r[2] else None,
                    "avg_fare": float(r[3]) if r[3] else None
                }
                for r in rows
            ]
        }
    except Exception as e:
        return {"error": str(e)}