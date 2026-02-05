"""
LangGraph 워크플로우 정의

Text-to-SQL Agent의 전체 흐름을 정의합니다.
"""

from langgraph.graph import StateGraph, END
from .state import AgentState
from .nodes import (
    retrieve_schema_node,
    generate_sql_node,
    validate_sql_node,
    execute_query_node,
    generate_insight_node,
    should_retry,
    check_execution_success
)


def create_sql_agent() -> StateGraph:
    """
    Text-to-SQL Agent 그래프 생성

    Workflow:
        START → retrieve_schema → generate_sql → validate_sql
                                                      ↓
                                         [Valid] → execute_query
                                                      ↓
                                    [Success] → generate_insight → END
                                                      ↓
                                         [Fail] → END (error)

        validate_sql → [Invalid] → [retry < 3] → generate_sql (재시도)
                                   [retry >= 3] → END (error)
    """
    # StateGraph 초기화
    workflow = StateGraph(AgentState)

    # 노드 추가
    workflow.add_node("retrieve_schema", retrieve_schema_node)
    workflow.add_node("generate_sql", generate_sql_node)
    workflow.add_node("validate_sql", validate_sql_node)
    workflow.add_node("execute_query", execute_query_node)
    workflow.add_node("generate_insight", generate_insight_node)

    # 엣지 연결
    # 1. START → retrieve_schema
    workflow.set_entry_point("retrieve_schema")

    # 2. retrieve_schema → generate_sql
    workflow.add_edge("retrieve_schema", "generate_sql")

    # 3. generate_sql → validate_sql
    workflow.add_edge("generate_sql", "validate_sql")

    # 4. validate_sql → [조건부 분기]
    workflow.add_conditional_edges(
        "validate_sql",
        should_retry,
        {
            "execute": "execute_query",      # Valid → 실행
            "regenerate": "generate_sql",    # Invalid → 재생성
            "fail": END                      # 재시도 초과 → 종료
        }
    )

    # 5. execute_query → [조건부 분기]
    workflow.add_conditional_edges(
        "execute_query",
        check_execution_success,
        {
            "insight": "generate_insight",   # 성공 → 인사이트 생성
            "fail": END                      # 실패 → 종료
        }
    )

    # 6. generate_insight → END
    workflow.add_edge("generate_insight", END)

    # 그래프 컴파일
    return workflow.compile()


async def run_sql_query(question: str, max_results: int = 100) -> dict:
    """
    Text-to-SQL 쿼리 실행

    Args:
        question: 자연어 질문
        max_results: 최대 결과 수

    Returns:
        {
            "sql": "생성된 SQL",
            "results": [...],
            "count": 10,
            "execution_time_ms": 45.2,
            "insight": "분석 결과 설명",
            "error": "에러 메시지 (있으면)"
        }
    """
    # Agent 생성
    agent = create_sql_agent()

    # 초기 상태
    initial_state: AgentState = {
        "question": question,
        "max_results": max_results,
        "schema_info": "",
        "sample_data": "",
        "generated_sql": "",
        "validation_error": "",
        "retry_count": 0,
        "query_results": [],
        "execution_time_ms": 0.0,
        "error_message": "",
        "formatted_results": {},
        "insight": "",
        "messages": []
    }

    # Agent 실행
    final_state = await agent.ainvoke(initial_state)

    # 결과 포맷팅
    if final_state.get("error_message"):
        return {
            "error": final_state["error_message"],
            "sql": final_state.get("generated_sql"),
            "results": [],
            "count": 0,
            "execution_time_ms": 0,
            "insight": None
        }

    if final_state.get("validation_error") and final_state.get("retry_count", 0) >= 3:
        return {
            "error": f"SQL validation failed after 3 retries: {final_state['validation_error']}",
            "sql": final_state.get("generated_sql"),
            "results": [],
            "count": 0,
            "execution_time_ms": 0,
            "insight": None
        }

    return {
        "sql": final_state["generated_sql"],
        "results": final_state["formatted_results"].get("data", []),
        "count": final_state["formatted_results"].get("count", 0),
        "displayed": final_state["formatted_results"].get("displayed", 0),
        "truncated": final_state["formatted_results"].get("truncated", False),
        "execution_time_ms": final_state["execution_time_ms"],
        "insight": final_state["insight"],
        "error": None
    }
