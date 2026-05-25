import logging
from fastapi import APIRouter, HTTPException
from app.services.llm_audit import llm_monitor

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/evidently", tags=["Evidently"])

@router.get("/health")
async def health_check():
    """Health check endpoint for Evidently integration"""
    return {"status": "ok", "evidently_integration": True}

@router.get("/llm/statistics")
async def get_llm_statistics():
    """Get LLM Monitoring statistics and drift report"""
    try:
        stats = llm_monitor.get_statistics()
        return {"data": stats}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching LLM statistics: {str(e)}")
    
@router.post("/llm/report")
async def generate_llm_report():
    """Generate LLM audit report"""
    try:
        report_path = llm_monitor.generate_report()
        if not report_path:
            raise HTTPException(status_code=500, detail="Failed to generate LLM report")
        
        return {"report_path": report_path, "status": "report generated successfully"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating LLM report: {str(e)}")
    
@router.get("/llm/reports")
async def list_llm_reports():
    """List available LLM audit reports"""
    try:
        reports = list(llm_monitor.reports_dir.glob("*.html"))
        return {"reports": [{"name": r.name, "path": str(r)} for r in reports],
                "count": len(reports)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing LLM reports: {str(e)}")