import logging
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.postgres_db import get_postgres_db
from app.services.llm_audit import llm_monitor

router = APIRouter(prefix="/evidently", tags=["Evidently"])
logger = logging.getLogger(__name__)

@router.get("/generate-report")
async def generate_report(db: AsyncSession = Depends(get_postgres_db)):
    """Generate Evidently AI report from LLM interactions"""
    try:
        report_path = await llm_monitor.generate_report_from_db(db)
        if report_path:
            return {
                "status": "success",
                "report_path": report_path,
                "message": "Report generated successfully"
            }
        else:
            return {
                "status": "warning",
                "message": "Not enough data to generate report"
            }
    except Exception as e:
        logger.error(f"❌ Failed to generate report: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/statistics")
async def get_statistics():
    """Get LLM statistics from local files"""
    try:
        stats = llm_monitor.get_statistics()
        return stats
    except Exception as e:
        logger.error(f"❌ Failed to get statistics: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """Check Evidently health"""
    return {
        "status": "healthy",
        "storage_path": str(llm_monitor.storage_path),
        "reports_dir": str(llm_monitor.reports_dir)
    }