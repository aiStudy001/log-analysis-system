"""
Health check controller
"""
from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/")
async def health_check():
    """Health check endpoint"""
    return {"status": "ok", "service": "log-analysis-server"}
