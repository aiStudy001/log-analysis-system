"""
Alerts Controller

API endpoints for alerting and monitoring.
"""

from fastapi import APIRouter, Depends
from app.services.alerting_service import get_alerting_service
from app.dependencies import get_query_repository

router = APIRouter(tags=["alerts"], prefix="/alerts")


@router.get("/history")
async def get_alert_history(
    limit: int = 20,
    query_repo=Depends(get_query_repository)
):
    """
    Get recent alert history

    Args:
        limit: Maximum number of alerts to return

    Returns:
        List of recent alerts
    """
    alerting_service = get_alerting_service(query_repo)
    return {
        "alerts": alerting_service.get_alert_history(limit)
    }


@router.post("/check")
async def check_anomalies_now(
    query_repo=Depends(get_query_repository)
):
    """
    Manually trigger anomaly check

    Returns:
        Detected alerts
    """
    alerting_service = get_alerting_service(query_repo)
    alerts = await alerting_service.check_anomalies()
    return {
        "alerts": alerts,
        "count": len(alerts)
    }
