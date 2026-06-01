import logging
from fastapi import APIRouter, HTTPException
from app.core.duckdb_client import duckdb_client
from pydantic import BaseModel

logger = logging.getLogger(__name__)
router = APIRouter()

class QueryRequest(BaseModel):
    """Request body for executing custom SQL query"""
    sql: str

@router.get("/health")
async def anyltics_health():
    """Check DuckDB connection health"""
    return {
        "connected": duckdb_client.connected,
        "status": "✅ Connected to DuckDB" if duckdb_client.connected else "❌ Not connected to DuckDB"
    }

@router.post("/duckdb/query")
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