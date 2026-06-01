import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from pydantic import BaseModel
from app.core.postgres_db import get_postgres_db

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
async def run_query(req: QueryRequest):
    """Run a custom SQL query against DuckDB and return results"""
    try:
        result = duckdb_client.raw_query(req.sql)
        return {"data": result, "rows": len(result)}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error executing query: {e}")
    
@router.get("/duckdb/tables")
async def list_tables():
    """List all tables in DuckDB"""
    result = duckdb_client.raw_query("SHOW TABLES")
    return {"tables": result}

@router.get("/duckdb/summary")
async def summary():
    """Get a summary of the DuckDB database"""
    try:
        tables = duckdb_client.raw_query("SHOW TABLES")
        summary = {}

        for table in tables:
            table_name = table[0]
            count_result = duckdb_client.raw_query(f"SELECT COUNT(*) FROM {table_name}")
            summary[table_name] = count_result[0][0]
        
        return {"summary": summary}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error generating summary: {e}")