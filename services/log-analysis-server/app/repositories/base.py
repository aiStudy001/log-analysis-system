"""
Base repository with connection pool management

Provides common database access methods for all repositories
"""
import asyncpg
from typing import List, Any, Optional


class BaseRepository:
    """Base class for all repositories with connection pool access"""

    def __init__(self, pool: asyncpg.Pool):
        """
        Initialize repository with connection pool

        Args:
            pool: asyncpg connection pool
        """
        self.pool = pool

    async def execute_query(self, query: str, *args) -> List[asyncpg.Record]:
        """
        Execute query and return all results

        Args:
            query: SQL query string
            *args: Query parameters

        Returns:
            List of asyncpg.Record objects
        """
        async with self.pool.acquire() as conn:
            return await conn.fetch(query, *args)

    async def execute_single(self, query: str, *args) -> Optional[Any]:
        """
        Execute query and return single value

        Args:
            query: SQL query string
            *args: Query parameters

        Returns:
            Single value from first column of first row, or None
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchval(query, *args)

    async def execute_one(self, query: str, *args) -> Optional[asyncpg.Record]:
        """
        Execute query and return single row

        Args:
            query: SQL query string
            *args: Query parameters

        Returns:
            Single asyncpg.Record, or None
        """
        async with self.pool.acquire() as conn:
            return await conn.fetchrow(query, *args)
