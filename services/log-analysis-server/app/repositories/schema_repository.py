"""
Schema repository for table schema and sample data retrieval

Handles database schema introspection and sample data queries
"""
from app.repositories.base import BaseRepository


class SchemaRepository(BaseRepository):
    """Handles schema and sample data queries for Text-to-SQL agent"""

    async def get_table_schema(self, table_name: str = "logs") -> str:
        """
        Retrieve table schema information from information_schema

        Args:
            table_name: Name of the table to retrieve schema for

        Returns:
            Formatted string describing table schema
        """
        query = """
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = $1
        ORDER BY ordinal_position;
        """
        rows = await self.execute_query(query, table_name)

        schema_info = f"Table: {table_name}\nColumns:\n"
        for row in rows:
            nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
            default = f" DEFAULT {row['column_default']}" if row['column_default'] else ""
            schema_info += f"  - {row['column_name']}: {row['data_type']} {nullable}{default}\n"

        return schema_info

    async def get_sample_data(self) -> str:
        """
        Retrieve diverse sample data for LLM learning

        Returns 10 diverse log samples:
        - 3 recent ERROR logs
        - 3 slow API calls (>1000ms)
        - 4 diverse services

        Returns:
            Formatted string with sample logs
        """
        query = """
        (
            SELECT id, created_at, level, log_type, service, error_type, message, duration_ms, path
            FROM logs
            WHERE deleted = FALSE AND level = 'ERROR'
            ORDER BY created_at DESC
            LIMIT 3
        )
        UNION ALL
        (
            SELECT id, created_at, level, log_type, service, error_type, message, duration_ms, path
            FROM logs
            WHERE deleted = FALSE AND duration_ms > 1000
            ORDER BY created_at DESC
            LIMIT 3
        )
        UNION ALL
        (
            SELECT DISTINCT ON (service)
                id, created_at, level, log_type, service, error_type, message, duration_ms, path
            FROM logs
            WHERE deleted = FALSE
            ORDER BY service, created_at DESC
            LIMIT 4
        );
        """
        rows = await self.execute_query(query)

        sample_data = "Sample Data (Diverse 10 logs):\n"
        for row in rows:
            duration_info = f", {row['duration_ms']:.0f}ms" if row['duration_ms'] else ""
            error_info = f", {row['error_type']}" if row['error_type'] else ""
            path_info = f" {row['path']}" if row['path'] else ""
            message_preview = row['message'][:40] + "..." if len(row['message']) > 40 else row['message']
            sample_data += f"  - [{row['level']}] {row['service']}{duration_info}{error_info}{path_info}: {message_preview}\n"

        return sample_data
