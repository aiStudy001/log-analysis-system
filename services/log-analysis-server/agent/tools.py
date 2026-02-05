"""
유틸리티 함수들
"""

import re
import sqlparse
from typing import Optional


def extract_sql_from_response(response: str) -> str:
    """
    LLM 응답에서 SQL 추출

    Handles:
    - ```sql ... ``` code blocks
    - ```... ``` code blocks
    - Raw SQL
    """
    # Try to find SQL in code blocks
    sql_block_match = re.search(r'```sql\n(.*?)\n```', response, re.DOTALL)
    if sql_block_match:
        return sql_block_match.group(1).strip()

    code_block_match = re.search(r'```\n(.*?)\n```', response, re.DOTALL)
    if code_block_match:
        return code_block_match.group(1).strip()

    # Try to find SELECT statement
    select_match = re.search(r'(SELECT.*?;)', response, re.DOTALL | re.IGNORECASE)
    if select_match:
        return select_match.group(1).strip()

    # Return as-is
    return response.strip()


def validate_sql_safety(sql: str) -> tuple[bool, Optional[str]]:
    """
    SQL 안전성 검증

    Returns:
        (is_safe, error_message)
    """
    sql_upper = sql.upper().strip()

    # Must start with SELECT
    if not sql_upper.startswith("SELECT"):
        return False, "Only SELECT queries are allowed"

    # Dangerous keywords
    dangerous_keywords = [
        "INSERT", "UPDATE", "DELETE", "DROP", "CREATE",
        "ALTER", "TRUNCATE", "GRANT", "REVOKE", "EXEC",
        "EXECUTE", "DECLARE", "CURSOR"
    ]

    for keyword in dangerous_keywords:
        if re.search(rf'\b{keyword}\b', sql_upper):
            return False, f"Dangerous keyword detected: {keyword}"

    # Must include deleted = FALSE
    if "DELETED" not in sql_upper:
        return False, "Must include 'deleted = FALSE' condition"

    return True, None


def validate_sql_syntax(sql: str) -> tuple[bool, Optional[str]]:
    """
    SQL 구문 검증

    Returns:
        (is_valid, error_message)
    """
    try:
        # Parse SQL
        parsed = sqlparse.parse(sql)

        if not parsed:
            return False, "Empty or invalid SQL"

        # Check if it's a SELECT statement
        statement = parsed[0]
        if statement.get_type() != 'SELECT':
            return False, "Only SELECT statements allowed"

        return True, None

    except Exception as e:
        return False, f"Syntax error: {str(e)}"


def format_query_results(results: list, limit: int = 100) -> dict:
    """
    쿼리 결과 포맷팅
    """
    if not results:
        return {
            "count": 0,
            "data": [],
            "message": "No results found"
        }

    # Limit results
    limited_results = results[:limit]

    return {
        "count": len(results),
        "displayed": len(limited_results),
        "data": limited_results,
        "truncated": len(results) > limit
    }


def create_error_response(error: str, sql: Optional[str] = None) -> dict:
    """
    에러 응답 생성
    """
    return {
        "error": error,
        "sql": sql,
        "results": [],
        "count": 0
    }
