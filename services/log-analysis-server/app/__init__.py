"""
FastAPI application factory

Creates and configures the FastAPI application with all middleware and routes
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.dependencies import init_db_pool, close_db_pool
from app.controllers import health, logs, query, websocket, alerts
from app.middleware import error_handler_middleware
from app.logging_config import setup_logging
import asyncio
import logging
from typing import Dict, Callable
import os

# Initialize structured logging
setup_logging(log_level=os.getenv("LOG_LEVEL", "INFO"))

logger = logging.getLogger(__name__)


class BackgroundTaskManager:
    """
    Manages background tasks with automatic restart and failure tracking

    Features:
    - Automatic restart on task failure
    - Exponential backoff for retries
    - Maximum failure count enforcement
    - Structured logging for task lifecycle
    """

    def __init__(self):
        self.tasks: Dict[str, asyncio.Task] = {}
        self.failure_counts: Dict[str, int] = {}
        self.max_failures = 5

    async def start_task(self, name: str, coro: Callable):
        """
        Start a background task with automatic restart on failure

        Args:
            name: Unique task identifier
            coro: Coroutine function to run
        """
        task = asyncio.create_task(self._run_with_restart(name, coro))
        self.tasks[name] = task
        self.failure_counts[name] = 0
        logger.info(f"✅ Started background task: {name}")

    async def _run_with_restart(self, name: str, coro: Callable):
        """
        Run task with automatic restart on failure

        Args:
            name: Task identifier
            coro: Coroutine function to execute
        """
        while self.failure_counts[name] < self.max_failures:
            try:
                await coro()
                # If task completes normally (shouldn't happen for infinite loops)
                logger.info(f"Background task '{name}' completed normally")
                break
            except asyncio.CancelledError:
                logger.info(f"Background task '{name}' was cancelled")
                break
            except Exception as e:
                self.failure_counts[name] += 1
                logger.error(
                    f"❌ Background task '{name}' failed "
                    f"(attempt {self.failure_counts[name]}/{self.max_failures}): {e}",
                    exc_info=True
                )

                if self.failure_counts[name] < self.max_failures:
                    # Exponential backoff: 2^failures seconds, max 5 minutes
                    wait_time = min(300, 2 ** self.failure_counts[name])
                    logger.info(f"🔄 Restarting '{name}' in {wait_time}s...")
                    await asyncio.sleep(wait_time)
                else:
                    logger.critical(
                        f"🚨 Background task '{name}' exceeded max failures ({self.max_failures}). "
                        f"Task will not restart automatically."
                    )
                    break

    def cancel_all(self):
        """Cancel all running background tasks"""
        for name, task in self.tasks.items():
            if not task.done():
                task.cancel()
                logger.info(f"Cancelled background task: {name}")


# Global background task manager
bg_task_manager = BackgroundTaskManager()


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

    # Global error handling middleware
    app.middleware("http")(error_handler_middleware)

    # Startup/Shutdown events
    @app.on_event("startup")
    async def startup():
        await init_db_pool()
        # Feature #5: Start background anomaly detection with automatic restart
        await bg_task_manager.start_task("anomaly_detection", periodic_anomaly_detection)

    @app.on_event("shutdown")
    async def shutdown():
        # Cancel all background tasks
        bg_task_manager.cancel_all()
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
    """
    Run anomaly detection every 5 minutes

    Automatically restarted by BackgroundTaskManager on failure.
    Exceptions are logged and handled by the manager.
    """
    from app.dependencies import get_query_repository
    from app.services.alerting_service import get_alerting_service
    from app.controllers.websocket import broadcast_alert

    logger.info("🚀 Anomaly detection background task started")

    while True:
        await asyncio.sleep(300)  # 5 minutes

        logger.debug("Running anomaly detection check...")

        # Run anomaly detection
        query_repo = get_query_repository()
        alerting_service = get_alerting_service(query_repo)
        alerts = await alerting_service.check_anomalies()

        # Broadcast alerts to connected clients
        if alerts:
            logger.info(f"🚨 Detected {len(alerts)} anomalies")
            for alert in alerts:
                await broadcast_alert(alert)
                logger.info(f"📢 Broadcasted alert: {alert.get('type', 'unknown')}")
        else:
            logger.debug("No anomalies detected")
