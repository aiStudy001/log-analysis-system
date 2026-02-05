"""
LangGraph 노드 구현 (Refactored with Repository Pattern + Event Accumulation)

각 처리 단계를 담당하는 노드 함수들
- Repository 주입으로 DB 접근
- Event Accumulation 패턴 (meal-planner)
"""

import logging
from langchain_core.messages import HumanMessage

logger = logging.getLogger(__name__)

from .state import AgentState
from .prompts import SQL_GENERATION_PROMPT, INSIGHT_GENERATION_PROMPT
from .tools import (
    extract_sql_from_response,
    validate_sql_safety,
    validate_sql_syntax,
    format_query_results
)
from .llm_factory import get_llm, llm_invoke_with_retry, LLMError
from .context_resolver import extract_focus_entities


async def retrieve_schema_node(state: AgentState, schema_repo) -> dict:
    """
    Node 1: DB 스키마 정보 조회 (Repository 주입)

    Args:
        state: Agent state
        schema_repo: SchemaRepository instance (injected)
    """
    try:
        # Repository를 통한 스키마 조회
        schema_info = await schema_repo.get_table_schema()
        sample_data = await schema_repo.get_sample_data()

        return {
            "schema_info": schema_info,
            "sample_data": sample_data,
            "messages": [{"role": "system", "content": "Schema retrieved"}],
            "events": [{
                "type": "node_complete",
                "node": "retrieve_schema",
                "status": "completed",
                "data": {
                    "schema_retrieved": True,
                    "sample_count": 10
                }
            }]
        }
    except Exception as e:
        logger.error(f"Schema retrieval failed: {e}", exc_info=True)
        return {
            "error_message": f"스키마 조회 실패: {str(e)}",
            "events": [{
                "type": "node_complete",
                "node": "retrieve_schema",
                "status": "failed",
                "data": {
                    "error": str(e)
                }
            }]
        }


async def generate_sql_node(state: AgentState) -> dict:
    """
    Node 2: SQL 생성 (Claude)
    """
    # Feature #2: Use resolved_question if available (context-aware)
    question = state.get("resolved_question", state["question"])

    prompt = SQL_GENERATION_PROMPT.format(
        schema_info=state["schema_info"],
        sample_data=state["sample_data"],
        question=question,
        max_results=state["max_results"]
    )

    # LLM 호출 with timeout and retry
    llm = get_llm(streaming=True)

    try:
        response = await llm_invoke_with_retry(llm, [HumanMessage(content=prompt)])
        generated_sql = extract_sql_from_response(response.content)

        return {
            "generated_sql": generated_sql,
            "messages": [{"role": "assistant", "content": f"Generated SQL:\n{generated_sql}"}],
            "events": [{
                "type": "node_complete",
                "node": "generate_sql",
                "status": "completed",
                "data": {
                    "sql_generated": True,
                    "sql_length": len(generated_sql),
                    # NEW: LLM prompt and response for task history
                    "llm_prompt": prompt,
                    "llm_response": generated_sql
                }
            }]
        }
    except LLMError as e:
        # LLM failed after retries - return error state
        return {
            "error_message": str(e),
            "validation_error": "LLM_TIMEOUT",
            "retry_count": state.get("retry_count", 0) + 1,
            "events": [{
                "type": "node_complete",
                "node": "generate_sql",
                "status": "failed",
                "data": {
                    "error": str(e),
                    "error_type": "LLM_TIMEOUT"
                }
            }]
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
            "messages": [{"role": "system", "content": f"Validation failed: {safety_error}"}],
            "events": [{
                "type": "validation_failed",
                "node": "validate_sql",
                "status": "failed",
                "data": {
                    "error": safety_error,
                    "retry_count": state.get("retry_count", 0) + 1
                }
            }]
        }

    # 구문 검증
    is_valid, syntax_error = validate_sql_syntax(sql)
    if not is_valid:
        return {
            "validation_error": syntax_error,
            "retry_count": state.get("retry_count", 0) + 1,
            "messages": [{"role": "system", "content": f"Syntax error: {syntax_error}"}],
            "events": [{
                "type": "validation_failed",
                "node": "validate_sql",
                "status": "failed",
                "data": {
                    "error": syntax_error,
                    "retry_count": state.get("retry_count", 0) + 1
                }
            }]
        }

    return {
        "validation_error": None,
        "messages": [{"role": "system", "content": "SQL validation passed"}],
        "events": [{
            "type": "node_complete",
            "node": "validate_sql",
            "status": "completed",
            "data": {
                "validation_passed": True
            }
        }]
    }


async def execute_query_node(state: AgentState, query_repo) -> dict:
    """
    Node 4: SQL 실행 (Repository 주입)

    Args:
        state: Agent state
        query_repo: QueryRepository instance (injected)
    """
    sql = state["generated_sql"]

    try:
        # Repository를 통한 쿼리 실행
        results_list, execution_time_ms = await query_repo.execute_sql(sql)

        # 결과 포맷팅
        formatted = format_query_results(results_list, limit=state["max_results"])

        # Feature #2: Extract focus entities for context tracking
        focus = extract_focus_entities(
            state.get("resolved_question", state["question"]),
            sql,
            results_list
        )

        return {
            "query_results": results_list,
            "execution_time_ms": execution_time_ms,
            "formatted_results": formatted,
            "error_message": None,
            "current_focus": focus,  # Feature #2
            "messages": [{"role": "system", "content": f"Query executed: {len(results_list)} rows"}],
            "events": [{
                "type": "node_complete",
                "node": "execute_query",
                "status": "completed",
                "data": {
                    "result_count": len(results_list),
                    "execution_time_ms": execution_time_ms
                }
            }]
        }

    except Exception as e:
        return {
            "error_message": str(e),
            "messages": [{"role": "system", "content": f"Execution failed: {str(e)}"}],
            "events": [{
                "type": "execution_failed",
                "node": "execute_query",
                "status": "failed",
                "data": {
                    "error": str(e)
                }
            }]
        }


async def generate_insight_node(state: AgentState) -> dict:
    """
    Node 5: 인사이트 생성 (Claude)

    Feature #3: Handles both single-step and multi-step results
    """
    # Feature #3: Check if multi-step
    if state.get("is_multi_step"):
        return await generate_multi_step_insight(state)
    else:
        return await generate_single_step_insight(state)


async def generate_single_step_insight(state: AgentState) -> dict:
    """
    Generate insight for single-step query (original behavior)
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

    # LLM 호출 with timeout and retry
    llm = get_llm(streaming=True)

    try:
        response = await llm_invoke_with_retry(llm, [HumanMessage(content=prompt)])
        insight = response.content

        return {
            "insight": insight,
            "messages": [{"role": "assistant", "content": f"Insight: {insight}"}],
            "events": [{
                "type": "node_complete",
                "node": "generate_insight",
                "status": "completed",
                "data": {
                    "insight_generated": True,
                    "multi_step": False,
                    # NEW: LLM prompt and response for task history
                    "llm_prompt": prompt,
                    "llm_response": insight
                }
            }]
        }
    except LLMError as e:
        # LLM failed - return error with empty insight
        return {
            "insight": f"Error generating insight: {str(e)}",
            "error_message": str(e),
            "events": [{
                "type": "node_complete",
                "node": "generate_insight",
                "status": "failed",
                "data": {
                    "error": str(e),
                    "error_type": "LLM_TIMEOUT"
                }
            }]
        }


async def generate_multi_step_insight(state: AgentState) -> dict:
    """
    Feature #3: Generate comprehensive insight from multiple steps
    """
    step_results = state.get("step_results", [])
    original_question = state.get("resolved_question", state["question"])

    # Build comprehensive summary of all steps
    steps_summary = "\n\n".join([
        f"Step {r['step_index'] + 1}: {r['description']}\n"
        f"Question: {r['question']}\n"
        f"SQL: {r['sql']}\n"
        f"Results: {r['result_count']} rows in {r['execution_time_ms']}ms\n"
        f"Sample data: {r['results'][:3] if r['results'] else 'No data'}"
        for r in step_results
    ])

    prompt = f"""You are a log analysis expert. Analyze multi-step query results and provide comprehensive insights in Korean.

# Original Question
{original_question}

# Execution Steps
{steps_summary}

# Your Task
Provide a comprehensive analysis (4-6 sentences):
1. **종합 요약**: What did we discover across all steps?
2. **핵심 인사이트**: Key patterns, anomalies, or findings
3. **원인 분석**: Root cause analysis if applicable
4. **추천 액션**: Actionable recommendations

Use Korean. Be specific with numbers and data from the steps.

Analysis:"""

    llm = get_llm(streaming=True)

    try:
        response = await llm_invoke_with_retry(llm, [HumanMessage(content=prompt)])
        insight = response.content

        return {
            "insight": insight,
            "messages": [{"role": "assistant", "content": f"Multi-step Insight: {insight}"}],
            "events": [{
                "type": "node_complete",
                "node": "generate_insight",
                "status": "completed",
                "data": {
                    "insight_generated": True,
                    "multi_step": True,
                    "total_steps": len(step_results),
                    # NEW: LLM prompt and response for task history
                    "llm_prompt": prompt,
                    "llm_response": insight
                }
            }]
        }
    except LLMError as e:
        # LLM failed - return error with fallback insight
        return {
            "insight": f"Error generating multi-step insight: {str(e)}",
            "error_message": str(e),
            "events": [{
                "type": "node_complete",
                "node": "generate_insight",
                "status": "failed",
                "data": {
                    "error": str(e),
                    "error_type": "LLM_TIMEOUT",
                    "multi_step": True
                }
            }]
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
