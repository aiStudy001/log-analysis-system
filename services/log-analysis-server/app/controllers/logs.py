"""
Log statistics and services controller
"""
from fastapi import APIRouter, HTTPException, Depends
from app.dependencies import get_log_repository

router = APIRouter(tags=["logs"])


@router.get("/services")
async def get_services(log_repo=Depends(get_log_repository)):
    """Get list of services with log counts"""
    try:
        services = await log_repo.get_services()
        return {"services": services}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats(log_repo=Depends(get_log_repository)):
    """Get comprehensive log statistics"""
    try:
        stats = await log_repo.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
