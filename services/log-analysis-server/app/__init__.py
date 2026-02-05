"""
FastAPI application factory

Creates and configures the FastAPI application with all middleware and routes
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.dependencies import init_db_pool, close_db_pool
from app.controllers import health, logs, query, websocket, alerts
import asyncio


def create_app() -> FastAPI:
    """Create and configure FastAPI application"""

    app = FastAPI(
        title="Log Analysis Server",
        version="2.0.0",
        description="Text-to-SQL Agent powered by LangGraph + Claude Sonnet 4.5"
    )

    # CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Startup/Shutdown events
    @app.on_event("startup")
    async def startup():
        await init_db_pool()
        # Feature #5: Start background anomaly detection
        asyncio.create_task(periodic_anomaly_detection())

    @app.on_event("shutdown")
    async def shutdown():
        await close_db_pool()

    # Register routes
    app.include_router(health.router)
    app.include_router(logs.router)
    app.include_router(query.router)
    app.include_router(websocket.router)
    app.include_router(alerts.router)  # Feature #5

    return app


# Feature #5: Background anomaly detection
async def periodic_anomaly_detection():
    """Run anomaly detection every 5 minutes"""
    from app.dependencies import get_query_repository
    from app.services.alerting_service import get_alerting_service
    from app.controllers.websocket import broadcast_alert

    while True:
        try:
            await asyncio.sleep(300)  # 5 minutes

            # Run anomaly detection
            query_repo = get_query_repository()
            alerting_service = get_alerting_service(query_repo)
            alerts = await alerting_service.check_anomalies()

            # Broadcast alerts to connected clients
            if alerts:
                for alert in alerts:
                    await broadcast_alert(alert)

        except Exception as e:
            print(f"Anomaly detection error: {e}")
