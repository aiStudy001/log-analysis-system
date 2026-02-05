"""
Stream service for agent execution and event streaming

Implements meal-planner pattern: separates agent logic from communication layer
- Layer 1: Agent (nodes) generates events
- Layer 2: Stream service transforms events
- Layer 3: Controllers send events via WebSocket/REST
"""

from typing import AsyncGenerator, Dict, Any
from app.agent.graph import create_sql_agent
from app.agent.state import AgentState
from app.services.cache_service import get_query_cache
from app.services.conversation_service import get_conversation_service


def build_initial_state(
    question: str,
    max_results: int,
    cache_key: str = "",
    cache_hit: bool = False,
    conversation_id: str = "default",
    time_range_structured: dict = None
) -> AgentState:
    """
    Build initial agent state

    Args:
        question: User's natural language question
        max_results: Maximum number of results to return
        cache_key: Cache key for this query (Feature #1)
        cache_hit: Whether this is a cache hit (Feature #1)
        conversation_id: Conversation session ID (Feature #2)
        time_range_structured: Optional structured time range from frontend

    Returns:
        Initial AgentState with default values
    """
    return {
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
        "messages": [],
        "events": [],  # Event accumulation (meal-planner pattern)
        "cache_hit": cache_hit,
        "cache_key": cache_key,
        "conversation_id": conversation_id,  # Feature #2
        "resolved_question": question,       # Feature #2 (default to original)
        "current_focus": {},                 # Feature #2
        "time_range_structured": time_range_structured  # NEW: Flexible time range
    }


def transform_event(event: dict, node_name: str) -> dict:
    """
    Transform internal node events to client-friendly events

    Args:
        event: Internal event from node
        node_name: Name of the node that generated the event

    Returns:
        Transformed event dict for client
    """
    event_type = event.get("type")
    status = event.get("status")
    data = event.get("data", {})

    # Node completion events
    if event_type == "node_complete":
        return {
            "type": "node_complete",
            "node": node_name,
            "status": status,
            "message": f"{node_name} 완료",
            "data": data
        }

    # Validation failed events
    elif event_type == "validation_failed":
        return {
            "type": "validation_failed",
            "node": node_name,
            "status": status,
            "message": f"SQL 검증 실패: {data.get('error', 'Unknown error')}",
            "data": data
        }

    # Execution failed events
    elif event_type == "execution_failed":
        return {
            "type": "execution_failed",
            "node": node_name,
            "status": status,
            "message": f"쿼리 실행 실패: {data.get('error', 'Unknown error')}",
            "data": data
        }

    # Filter extraction events (LLM-based)
    elif event_type == "filters_extracted":
        service = data.get("service")
        time_range = data.get("time_range")
        confidence = data.get("confidence", 0.0)

        parts = []
        if service:
            parts.append(f"서비스: {service}")
        if time_range:
            parts.append(f"시간: {time_range}")

        message = f"필터 추출: {', '.join(parts)}" if parts else "필터 추출 실패"

        return {
            "type": "filters_extracted",
            "node": node_name,
            "message": message,
            "data": data
        }

    # Clarification needed events (재질문)
    elif event_type == "clarification_needed":
        questions = data.get("questions", [])
        count = data.get("count", 0)

        return {
            "type": "clarification_needed",
            "node": node_name,
            "message": f"추가 정보가 필요합니다 ({count}개)",
            "data": data
        }

    # Clarification skipped events
    elif event_type == "clarification_skipped":
        return {
            "type": "clarification_skipped",
            "node": node_name,
            "message": data.get("message", "재질문 건너뜀"),
            "data": data
        }

    # Default: pass through
    return {
        "type": event_type,
        "node": node_name,
        "status": status,
        "data": data
    }


def format_final_result(final_state: AgentState) -> dict:
    """
    Format final agent state into result dict

    Args:
        final_state: Final state after agent execution

    Returns:
        Formatted result dict
    """
    # Error cases
    if final_state.get("error_message"):
        return {
            "type": "error",
            "error": final_state["error_message"],
            "sql": final_state.get("generated_sql"),
            "results": [],
            "count": 0,
            "execution_time_ms": 0,
            "insight": None
        }

    if final_state.get("validation_error") and final_state.get("retry_count", 0) >= 3:
        return {
            "type": "error",
            "error": f"SQL validation failed after 3 retries: {final_state['validation_error']}",
            "sql": final_state.get("generated_sql"),
            "results": [],
            "count": 0,
            "execution_time_ms": 0,
            "insight": None
        }

    # Success case
    return {
        "type": "complete",
        "sql": final_state["generated_sql"],
        "results": final_state["formatted_results"].get("data", []),
        "count": final_state["formatted_results"].get("count", 0),
        "displayed": final_state["formatted_results"].get("displayed", 0),
        "truncated": final_state["formatted_results"].get("truncated", False),
        "execution_time_ms": final_state["execution_time_ms"],
        "insight": final_state["insight"],
        "error": None
    }


async def stream_query_execution(
    question: str,
    max_results: int,
    schema_repo,
    query_repo,
    conversation_id: str = "default",
    time_range_structured: dict = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Stream agent execution events (meal-planner pattern)

    Yields events as they are generated by agent nodes:
    - cache_hit: When result is retrieved from cache (Feature #1)
    - context_resolved: When references are resolved (Feature #2)
    - node_complete: When a node finishes
    - validation_failed: When SQL validation fails
    - execution_failed: When query execution fails
    - complete: Final result with SQL and data

    Args:
        question: User's natural language question
        max_results: Maximum number of results
        schema_repo: SchemaRepository instance
        query_repo: QueryRepository instance
        conversation_id: Conversation session ID (Feature #2)
        time_range_structured: Optional structured time range from frontend

    Yields:
        Event dicts for client consumption
    """
    # 1. Check cache (Feature #1)
    cache = get_query_cache()
    cache_key = cache.get_cache_key(question, max_results)
    cached_result = await cache.get(cache_key)

    if cached_result:
        # Cache HIT - return immediately
        yield {
            "type": "cache_hit",
            "message": "결과를 캐시에서 가져왔습니다",
            "data": {"cache_key": cache_key}
        }
        # Return cached result with cache_hit flag
        cached_result["cache_hit"] = True
        yield cached_result
        return

    # 2. Cache MISS - execute agent
    initial_state = build_initial_state(
        question,
        max_results,
        cache_key=cache_key,
        cache_hit=False,
        conversation_id=conversation_id,  # Feature #2
        time_range_structured=time_range_structured  # NEW: Flexible time range
    )

    # 3. Create agent with injected repositories and conversation service (Feature #2)
    conversation_service = get_conversation_service()
    agent = create_sql_agent(schema_repo, query_repo, conversation_service)

    # 4. Stream events from graph and accumulate state
    accumulated_state = initial_state.copy()
    async for chunk in agent.astream(initial_state):
        for node_name, node_state in chunk.items():
            # Emit node_start event
            yield {
                "type": "node_start",
                "node": node_name,
                "message": f"{node_name} 시작"
            }

            # Extract events from node state and keep last event data
            last_event_data = {}
            if isinstance(node_state, dict) and "events" in node_state:
                for event in node_state["events"]:
                    # Transform internal event → client event
                    yield transform_event(event, node_name)
                    # Keep track of last event data for node_end
                    if "data" in event:
                        last_event_data = event["data"]

            # Emit node_end event with data from last event
            yield {
                "type": "node_end",
                "node": node_name,
                "message": f"{node_name} 완료",
                "data": last_event_data  # Include data from last event
            }

            # Merge node updates into accumulated state
            if isinstance(node_state, dict):
                accumulated_state.update(node_state)

    # 5. Format final result from accumulated state
    final_result = format_final_result(accumulated_state)

    # 6. Save turn to conversation service (Feature #2)
    if final_result.get("type") == "complete":
        conversation_service.add_turn(
            conversation_id,
            question,
            {
                "resolved_question": accumulated_state.get("resolved_question", question),
                "sql": accumulated_state.get("generated_sql", ""),
                "count": final_result.get("count", 0),
                "current_focus": accumulated_state.get("current_focus", {})
            }
        )

    # 7. Store successful results in cache (Feature #1)
    # 단, 재질문이 발생한 경우는 캐시하지 않음 (애매한 질문은 매번 재질문해야 함)
    had_clarifications = accumulated_state.get("clarifications_needed") and len(accumulated_state.get("clarifications_needed", [])) > 0

    if final_result.get("type") == "complete" and not final_result.get("error") and not had_clarifications:
        await cache.set(cache_key, final_result)

    yield final_result


async def execute_query(
    question: str,
    max_results: int,
    schema_repo,
    query_repo
) -> dict:
    """
    Execute query synchronously (for REST API)

    Collects all events and returns final result only.

    Args:
        question: User's natural language question
        max_results: Maximum number of results
        schema_repo: SchemaRepository instance
        query_repo: QueryRepository instance

    Returns:
        Final result dict
    """
    final_result = None

    async for event in stream_query_execution(
        question, max_results, schema_repo, query_repo
    ):
        # Collect only the final complete event
        if event.get("type") in ["complete", "error"]:
            final_result = event

    return final_result if final_result else {
        "type": "error",
        "error": "No result received from agent",
        "sql": None,
        "results": [],
        "count": 0,
        "execution_time_ms": 0,
        "insight": None
    }
