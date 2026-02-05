"""
Query repository for SQL execution

Handles SQL query execution with type conversion and timing
"""
import time
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Any, Tuple
from app.repositories.base import BaseRepository


class QueryRepository(BaseRepository):
    """Handles SQL query execution with result formatting"""

    async def execute_sql(self, sql: str, params: List[Any] = None) -> Tuple[List[Dict[str, Any]], float]:
        """
        Execute SQL query and return results with execution time

        Converts asyncpg Records to dictionaries with proper type handling:
        - datetime → ISO string
        - Decimal → float

        Args:
            sql: SQL query to execute (use $1, $2, etc. for parameters)
            params: Optional list of parameters for the query

        Returns:
            Tuple of (results_list, execution_time_ms)
        """
        start_time = time.time()

        # Execute query with optional parameters
        if params:
            rows = await self.execute_query(sql, *params)
        else:
            rows = await self.execute_query(sql)

        # Convert asyncpg Record to dict with type handling
        results_list = []
        for row in rows:
            row_dict = dict(row)
            for key, value in row_dict.items():
                if isinstance(value, datetime):
                    row_dict[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    row_dict[key] = float(value)
            results_list.append(row_dict)

        execution_time_ms = (time.time() - start_time) * 1000

        return results_list, round(execution_time_ms, 2)
