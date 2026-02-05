"""
Dependency injection for FastAPI

Manages connection pool and provides repository/service instances
"""
import asyncpg
import logging
from typing import Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log
)
from app.config import settings

logger = logging.getLogger(__name__)


# Global connection pool
_pool: Optional[asyncpg.Pool] = None

# Connection configuration
POOL_RETRY_ATTEMPTS = 3
POOL_TIMEOUT_SECONDS = 10
CONNECTION_TIMEOUT_SECONDS = 5


@retry(
    stop=stop_after_attempt(POOL_RETRY_ATTEMPTS),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type((
        asyncpg.PostgresConnectionError,
        asyncpg.InterfaceError,
        OSError  # Network errors
    )),
    before_sleep=before_sleep_log(logger, logging.WARNING)
)
async def init_db_pool():
    """
    Initialize database connection pool with retry logic

    Retries up to 3 times with exponential backoff on connection failures.
    Raises exception after max retries exceeded.
    """
    global _pool
    try:
        _pool = await asyncpg.create_pool(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            database=settings.DATABASE_NAME,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD,
            min_size=settings.DB_POOL_MIN_SIZE,
            max_size=settings.DB_POOL_MAX_SIZE,
            timeout=POOL_TIMEOUT_SECONDS,
            command_timeout=CONNECTION_TIMEOUT_SECONDS
        )
        logger.info("✅ Database connection pool created successfully")
        print("✅ Database connection pool created (Read-Only)")
    except Exception as e:
        logger.error(f"❌ Failed to create database pool after {POOL_RETRY_ATTEMPTS} attempts: {e}")
        raise


async def close_db_pool():
    """Close database connection pool on shutdown"""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
        print("✅ Database connection pool closed")


def get_pool() -> asyncpg.Pool:
    """Get database pool (raises error if not initialized)"""
    if not _pool:
        raise RuntimeError("Database pool not initialized")
    return _pool


# Repository dependencies
def get_schema_repository():
    """Get SchemaRepository instance"""
    from app.repositories.schema_repository import SchemaRepository
    return SchemaRepository(get_pool())


def get_query_repository():
    """Get QueryRepository instance"""
    from app.repositories.query_repository import QueryRepository
    return QueryRepository(get_pool())


def get_log_repository():
    """Get LogRepository instance"""
    from app.repositories.log_repository import LogRepository
    return LogRepository(get_pool())


# Service dependencies (Feature #2)
def get_conversation_service_dep():
    """Get ConversationService instance (FastAPI dependency)"""
    from app.services.conversation_service import get_conversation_service
    return get_conversation_service()
