"""
Log repository for statistics and service queries

Handles log-specific aggregation and statistics queries
"""
from typing import List, Dict, Any
from app.repositories.base import BaseRepository


class LogRepository(BaseRepository):
    """Handles log statistics and service discovery queries"""

    async def get_services(self) -> List[Dict[str, Any]]:
        """
        Get list of services with log counts

        Returns:
            List of dicts with 'name' and 'log_count' keys
        """
        query = """
        SELECT DISTINCT service as name, COUNT(*) as log_count
        FROM logs
        WHERE deleted = FALSE
        GROUP BY service
        ORDER BY service
        """
        rows = await self.execute_query(query)
        return [{"name": row["name"], "log_count": row["log_count"]} for row in rows]

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get comprehensive log statistics

        Returns:
            Dictionary with:
            - total_logs: Total count of active logs
            - level_distribution: Count by log level
            - service_distribution: Count by service (top 10)
            - recent_errors_1h: Error count in last hour
        """
        # Total count
        total_count = await self.execute_single(
            "SELECT COUNT(*) FROM logs WHERE deleted = FALSE"
        )

        # Level distribution
        level_counts = await self.execute_query("""
            SELECT level, COUNT(*) as count
            FROM logs
            WHERE deleted = FALSE
            GROUP BY level
            ORDER BY count DESC
        """)

        # Service distribution (top 10)
        service_counts = await self.execute_query("""
            SELECT service, COUNT(*) as count
            FROM logs
            WHERE deleted = FALSE
            GROUP BY service
            ORDER BY count DESC
            LIMIT 10
        """)

        # Recent errors (last 1 hour)
        recent_errors = await self.execute_single("""
            SELECT COUNT(*) FROM logs
            WHERE level = 'ERROR'
              AND created_at > NOW() - INTERVAL '1 hour'
              AND deleted = FALSE
        """)

        return {
            "total_logs": total_count,
            "level_distribution": [
                {"level": row["level"], "count": row["count"]}
                for row in level_counts
            ],
            "service_distribution": [
                {"service": row["service"], "count": row["count"]}
                for row in service_counts
            ],
            "recent_errors_1h": recent_errors
        }
