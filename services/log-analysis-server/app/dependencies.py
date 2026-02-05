"""
Dependency injection for FastAPI

Manages connection pool and provides repository/service instances
"""
import asyncpg
from typing import Optional
from app.config import settings


# Global connection pool
_pool: Optional[asyncpg.Pool] = None


async def init_db_pool():
    """Initialize database connection pool on startup"""
    global _pool
    _pool = await asyncpg.create_pool(
        host=settings.DATABASE_HOST,
        port=settings.DATABASE_PORT,
        database=settings.DATABASE_NAME,
        user=settings.DATABASE_USER,
        password=settings.DATABASE_PASSWORD,
        min_size=settings.DB_POOL_MIN_SIZE,
        max_size=settings.DB_POOL_MAX_SIZE
    )
    print("✅ Database connection pool created (Read-Only)")


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
