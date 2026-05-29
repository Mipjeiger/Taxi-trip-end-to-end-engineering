import logging
from fastapi import APIRouter, HTTPException
from app.core.duckdb_client import duckdb_client

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/health")
async def anyltics_health():
    """Check DuckDB connection health"""
    return {
        "connected": duckdb_client.connected,
        "status": "✅ Connected to DuckDB" if duckdb_client.connected else "❌ Not connected to DuckDB"
    }

@router.get("/events")
async def get_events(limit: int = 100):
    """Retrieve recent events from DuckDB for analytics"""
    try:
        events = duckdb_client.query(f"SELECT * FROM taxi_trip_data_events LIMIT {limit}")
        return {"count": len(events), "events": events}
    except Exception as e:
        logger.error(f"❌ Failed to retrieve events from DuckDB: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve events from DuckDB")
    
@router.get("/analytics")
async def get_analytics():
    """Get key metrics from DuckDB for analytics dashboard"""
    try:
        analytics = duckdb_client.get_analytics()
        return analytics
    except Exception as e:
        logger.error(f"❌ Failed to retrieve analytics from DuckDB: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve analytics from DuckDB")
    
@router.post("/query")
async def execute_query(sql: str):
    """Execute custom SQL query on DuckDB"""
    try:
        result = duckdb_client.query(sql)
        return {"result": result}
    except Exception as e:
        logger.error(f"❌ Failed to execute query on DuckDB: {e}")
        raise HTTPException(status_code=500, detail="Failed to execute query on DuckDB")