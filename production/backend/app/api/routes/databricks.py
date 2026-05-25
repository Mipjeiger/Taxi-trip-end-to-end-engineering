import logging
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Any
from app.core.databricks_client import databricks_client

logger = logging.getLogger(__name__)
router = APIRouter() # Prefix for all routes in this file

@router.get("/health")
async def databricks_health():
    """Check Databricks client health."""
    return {
        "connected": databricks_client.connected,
        "status": "✅ Connected" if databricks_client.connected else "❌ Not connected"
    }

@router.get("/clusters")
async def list_clusters():
    """List all Databricks clusters."""
    try:
        clusters = databricks_client.list_clusters()
        return {
            "count": len(clusters),
            "clusters": [
                {
                    "cluster_id": c.cluster_id,
                    "cluster_name": c.cluster_name,
                    "state": c.state,
                    "spark_version": c.spark_version,
                }
                for c in clusters
            ]
        }
    except Exception as e:
        logger.error(f"❌ Error listing clusters: {e}")
        raise HTTPException(status_code=500, detail="Error listing clusters")
    
@router.get("/clusters/{cluster_id}/status")
async def get_cluster_status(cluster_id: str):
    """Get specific cluster status."""
    try:
        status = databricks_client.get_cluster_status(cluster_id)
        return status
    except Exception as e:
        logger.error(f"❌ Error getting cluster status for {cluster_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting cluster status for {cluster_id}")
    
@router.get("/jobs")
async def list_jobs():
    """List all Databricks jobs."""
    try:
        jobs = databricks_client.list_jobs()
        return {
            "count": len(jobs),
            "jobs": [
                {
                    "job_id": j.job_id,
                    "setting": j.settings.name if j.settings else "N/A",
                }
                for j in jobs
            ]
        }
    except Exception as e:
        logger.error(f"❌ Error listing jobs: {e}")
        raise HTTPException(status_code=500, detail="Error listing jobs")
    
@router.get("/jobs/{job_id}/runs")
async def get_job_runs(job_id: int, limit: int = 10):
    """Get recent runs for a specific job."""
    try:
        runs = databricks_client.get_job_runs(job_id, limit)
        return {
            "count": len(runs),
            "job_id": job_id,
            "runs": [
                {
                    "run_id": r.run_id,
                    "state": r.state.life_cycle_state if r.state else "N/A",
                    "start_time": r.start_time,
                    "end_time": r.end_time,
                }
                for r in runs
            ]
        }
    except Exception as e:
        logger.error(f"❌ Error getting job runs for job {job_id}: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting job runs for job {job_id}")
    
@router.post("/query")
async def execute_query(query: Dict[str, str]):
    """Execute SQL query on Databricks SQL Warehouse."""
    try:
        sql = query.get("sql")
        if not sql:
            raise HTTPException(status_code=400, detail="SQL query is required")
        
        result = databricks_client.query_warehouse(sql)
        return result
    except Exception as e:
        logger.error(f"❌ Error executing SQL query: {e}")
        raise HTTPException(status_code=500, detail="Error executing SQL query")
    
@router.get("/dashboard")
async def dashboard():
    """Databricks dashboard endpoint to aggregate key metrics."""
    try:
        clusters = databricks_client.list_clusters()
        jobs = databricks_client.list_jobs()

        return {
            "connected": databricks_client.connected,
            "clusters": {
                "total": len(clusters),
                "running": len([c for c in clusters if c.state == "RUNNING"]),
            },
            "jobs": {
                "total": len(jobs),
                "active": len([j for j in jobs if j.state == "ACTIVE"]),
            }
        }
    except Exception as e:
        logger.error(f"❌ Error fetching dashboard data: {e}")
        raise HTTPException(status_code=500, detail="Error fetching dashboard data")