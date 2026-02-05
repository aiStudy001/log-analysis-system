"""
LangGraph 워크플로우 정의 (Refactored with Repository Injection)

Text-to-SQL Agent의 전체 흐름을 정의합니다.
Repository pattern을 사용하여 DB 접근을 추상화합니다.
"""

from functools import partial
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
from .context_resolver import resolve_context_node
from .filter_extractor import extract_filters_node
from .clarifier import clarification_node


def create_sql_agent(schema_repo, query_repo, conversation_service=None) -> StateGraph:
    """
    Text-to-SQL Agent 그래프 생성 (Repository 주입)

    Args:
        schema_repo: SchemaRepository instance
        query_repo: QueryRepository instance
        conversation_service: ConversationService instance (Feature #2)

    Simplified Workflow:
        START → resolve_context → extract_filters → clarifier → retrieve_schema → generate_sql →
                  (Feature #2)      (LLM-based)      (재질문)
                validate_sql → execute_query → generate_insight → END

        clarifier → [needs clarification] → END (wait for user response)
                    [no clarification] → retrieve_schema

        validate_sql → [Invalid] → [retry < 3] → generate_sql (재시도)
                                   [retry >= 3] → END (error)
    """
    # StateGraph 초기화
    workflow = StateGraph(AgentState)

    # 노드 추가 with Repository Injection (functools.partial)
    # Feature #2: Add context resolution node
    if conversation_service:
        workflow.add_node(
            "resolve_context",
            partial(resolve_context_node, conversation_service=conversation_service)
        )

    workflow.add_node("extract_filters", extract_filters_node)
    workflow.add_node(
        "clarifier",
        partial(clarification_node, query_repo=query_repo)
    )
    workflow.add_node(
        "retrieve_schema",
        partial(retrieve_schema_node, schema_repo=schema_repo)
    )
    workflow.add_node("generate_sql", generate_sql_node)
    workflow.add_node("validate_sql", validate_sql_node)
    workflow.add_node(
        "execute_query",
        partial(execute_query_node, query_repo=query_repo)
    )
    workflow.add_node("generate_insight", generate_insight_node)

    # 엣지 연결
    # Feature #2: START → resolve_context (if available) → extract_filters → retrieve_schema
    if conversation_service:
        workflow.set_entry_point("resolve_context")
        workflow.add_edge("resolve_context", "extract_filters")
    else:
        # Backward compatibility: original entry point
        workflow.set_entry_point("extract_filters")

    # LLM filter extraction → clarification
    workflow.add_edge("extract_filters", "clarifier")

    # Clarification → [조건부 분기]
    def route_after_clarification(state: AgentState) -> str:
        """재질문 필요 여부에 따라 라우팅"""
        if state.get("clarifications_needed"):
            return "wait"  # 사용자 응답 대기
        return "continue"  # 정상 진행

    workflow.add_conditional_edges(
        "clarifier",
        route_after_clarification,
        {
            "wait": END,              # 재질문 필요 → 종료 (사용자 응답 대기)
            "continue": "retrieve_schema"  # 재질문 없음 → 정상 진행
        }
    )

    # Direct path: retrieve_schema → generate_sql
    workflow.add_edge("retrieve_schema", "generate_sql")

    # generate_sql → validate_sql
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

    # generate_insight → END
    workflow.add_edge("generate_insight", END)

    # 그래프 컴파일
    return workflow.compile()
