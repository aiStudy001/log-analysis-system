"""
LangGraph 노드 구현

각 처리 단계를 담당하는 노드 함수들
"""

import os
import time
from datetime import datetime
from decimal import Decimal
from typing import Any

import asyncpg
from langchain_core.messages import HumanMessage

from .state import AgentState
from .prompts import SQL_GENERATION_PROMPT, INSIGHT_GENERATION_PROMPT
from .tools import (
    extract_sql_from_response,
    validate_sql_safety,
    validate_sql_syntax,
    format_query_results
)
from .llm_factory import get_llm


async def retrieve_schema_node(state: AgentState) -> dict:
    """
    Node 1: DB 스키마 정보 조회
    """
    # DB connection (환경 변수에서 읽기)
    conn = await asyncpg.connect(
        host=os.getenv("DATABASE_HOST", "localhost"),
        port=int(os.getenv("DATABASE_PORT", "5432")),
        database=os.getenv("DATABASE_NAME", "logs_db"),
        user=os.getenv("DATABASE_USER", "postgres"),
        password=os.getenv("DATABASE_PASSWORD", "password")
    )

    try:
        # 스키마 정보 가져오기
        schema_query = """
        SELECT
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_name = 'logs'
        ORDER BY ordinal_position;
        """
        schema_rows = await conn.fetch(schema_query)

        schema_info = "Table: logs\nColumns:\n"
        for row in schema_rows:
            nullable = "NULL" if row['is_nullable'] == 'YES' else "NOT NULL"
            default = f" DEFAULT {row['column_default']}" if row['column_default'] else ""
            schema_info += f"  - {row['column_name']}: {row['data_type']} {nullable}{default}\n"

        # 샘플 데이터 가져오기 (다양한 패턴 10개)
        # LLM이 집계, 성능 분석, 시계열 쿼리를 학습할 수 있도록 다양한 샘플 제공
        sample_query = """
        (
            -- 1. 최근 에러 로그 (에러 유형 포함) - 3개
            SELECT id, created_at, level, log_type, service, error_type, message, duration_ms, path
            FROM logs
            WHERE deleted = FALSE AND level = 'ERROR'
            ORDER BY created_at DESC
            LIMIT 3
        )
        UNION ALL
        (
            -- 2. 느린 API 샘플 (성능 분석용) - 3개
            SELECT id, created_at, level, log_type, service, error_type, message, duration_ms, path
            FROM logs
            WHERE deleted = FALSE AND duration_ms > 1000
            ORDER BY created_at DESC
            LIMIT 3
        )
        UNION ALL
        (
            -- 3. 다양한 서비스 샘플 (집계 분석용) - 4개 (각 서비스 1개씩)
            SELECT DISTINCT ON (service)
                id, created_at, level, log_type, service, error_type, message, duration_ms, path
            FROM logs
            WHERE deleted = FALSE
            ORDER BY service, created_at DESC
            LIMIT 4
        );
        """
        sample_rows = await conn.fetch(sample_query)

        sample_data = "Sample Data (Diverse 10 logs showing different patterns):\n"
        for row in sample_rows:
            duration_info = f", {row['duration_ms']:.0f}ms" if row['duration_ms'] else ""
            error_info = f", {row['error_type']}" if row['error_type'] else ""
            path_info = f" {row['path']}" if row['path'] else ""
            sample_data += f"  - [{row['level']}] {row['service']}{duration_info}{error_info}{path_info}: {row['message'][:40]}...\n"

    finally:
        await conn.close()

    return {
        "schema_info": schema_info,
        "sample_data": sample_data,
        "messages": [{"role": "system", "content": "Schema retrieved"}]
    }


async def generate_sql_node(state: AgentState) -> dict:
    """
    Node 2: SQL 생성 (Claude)
    """
    prompt = SQL_GENERATION_PROMPT.format(
        schema_info=state["schema_info"],
        sample_data=state["sample_data"],
        question=state["question"],
        max_results=state["max_results"]
    )

    # LLM 호출 (streaming 지원)
    llm = get_llm(streaming=True)
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    generated_sql = extract_sql_from_response(response.content)

    return {
        "generated_sql": generated_sql,
        "messages": [{"role": "assistant", "content": f"Generated SQL:\n{generated_sql}"}]
    }


async def validate_sql_node(state: AgentState) -> dict:
    """
    Node 3: SQL 검증
    """
    sql = state["generated_sql"]

    # 안전성 검증
    is_safe, safety_error = validate_sql_safety(sql)
    if not is_safe:
        return {
            "validation_error": safety_error,
            "retry_count": state.get("retry_count", 0) + 1,
            "messages": [{"role": "system", "content": f"Validation failed: {safety_error}"}]
        }

    # 구문 검증
    is_valid, syntax_error = validate_sql_syntax(sql)
    if not is_valid:
        return {
            "validation_error": syntax_error,
            "retry_count": state.get("retry_count", 0) + 1,
            "messages": [{"role": "system", "content": f"Syntax error: {syntax_error}"}]
        }

    return {
        "validation_error": None,
        "messages": [{"role": "system", "content": "SQL validation passed"}]
    }


async def execute_query_node(state: AgentState) -> dict:
    """
    Node 4: SQL 실행
    """
    sql = state["generated_sql"]
    start_time = time.time()

    conn = await asyncpg.connect(
        host=os.getenv("DATABASE_HOST", "localhost"),
        port=int(os.getenv("DATABASE_PORT", "5432")),
        database=os.getenv("DATABASE_NAME", "logs_db"),
        user=os.getenv("DATABASE_USER", "postgres"),
        password=os.getenv("DATABASE_PASSWORD", "password")
    )

    try:
        # 쿼리 실행
        results = await conn.fetch(sql)

        # asyncpg Record → dict 변환
        results_list = []
        for row in results:
            row_dict = dict(row)
            # datetime → ISO string, Decimal → float
            for key, value in row_dict.items():
                if isinstance(value, datetime):
                    row_dict[key] = value.isoformat()
                elif isinstance(value, Decimal):
                    row_dict[key] = float(value)
            results_list.append(row_dict)

        execution_time_ms = (time.time() - start_time) * 1000

        # 결과 포맷팅
        formatted = format_query_results(results_list, limit=state["max_results"])

        return {
            "query_results": results_list,
            "execution_time_ms": round(execution_time_ms, 2),
            "formatted_results": formatted,
            "error_message": None,
            "messages": [{"role": "system", "content": f"Query executed: {len(results_list)} rows"}]
        }

    except Exception as e:
        return {
            "error_message": str(e),
            "messages": [{"role": "system", "content": f"Execution failed: {str(e)}"}]
        }

    finally:
        await conn.close()


async def generate_insight_node(state: AgentState) -> dict:
    """
    Node 5: 인사이트 생성 (Claude)
    """
    # 결과가 너무 많으면 요약
    results_preview = state["query_results"][:10]  # 최대 10개만 보여줌

    prompt = INSIGHT_GENERATION_PROMPT.format(
        question=state["question"],
        sql=state["generated_sql"],
        results=results_preview,
        count=len(state["query_results"]),
        execution_time_ms=state["execution_time_ms"]
    )

    # LLM 호출 (streaming 지원)
    llm = get_llm(streaming=True)
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    insight = response.content

    return {
        "insight": insight,
        "messages": [{"role": "assistant", "content": f"Insight: {insight}"}]
    }


def should_retry(state: AgentState) -> str:
    """
    조건부 엣지: 재시도 여부 결정
    """
    if state.get("validation_error"):
        retry_count = state.get("retry_count", 0)
        if retry_count < 3:  # 최대 3회 재시도
            return "regenerate"
        else:
            return "fail"
    return "execute"


def check_execution_success(state: AgentState) -> str:
    """
    조건부 엣지: 실행 성공 여부
    """
    if state.get("error_message"):
        return "fail"
    return "insight"
