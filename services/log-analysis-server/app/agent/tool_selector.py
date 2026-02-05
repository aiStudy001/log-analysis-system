"""
Tool Selection Node

Routes queries to the optimal execution tool (SQL, grep, metrics).
"""

import re


def select_tool_for_question(question: str) -> str:
    """
    Select optimal tool based on question patterns

    Args:
        question: User's question

    Returns:
        "sql" | "grep" | "metrics"
    """
    question_lower = question.lower()

    # Pattern matching keywords → grep
    pattern_keywords = [
        '패턴', '유사한', 'matching', '포함된', '메시지에서',
        'contains', 'like', '검색', 'search'
    ]
    if any(kw in question_lower for kw in pattern_keywords):
        # Check if specific pattern is mentioned
        if re.search(r'["\'](.+?)["\']', question):
            return "grep"

    # Metrics/aggregation keywords → metrics (if available)
    metrics_keywords = [
        '전체', '통계', 'summary', '개요', 'overview',
        'dashboard', '대시보드', 'metrics', '메트릭'
    ]
    if any(kw in question_lower for kw in metrics_keywords):
        # For now, use SQL (metrics API not implemented yet)
        return "sql"

    # Default to SQL for all other queries
    return "sql"


async def tool_selector_node(state: dict) -> dict:
    """
    Select optimal tool based on question

    Args:
        state: AgentState

    Returns:
        Updated state with selected_tool
    """
    question = state.get("resolved_question", state["question"])
    selected_tool = select_tool_for_question(question)

    # For now, only SQL is fully implemented
    # grep and metrics are placeholders for future expansion
    if selected_tool != "sql":
        # Fallback to SQL
        selected_tool = "sql"

    return {
        "selected_tool": selected_tool,
        "events": [{
            "type": "tool_selected",
            "node": "tool_selector",
            "status": "completed",
            "data": {
                "tool": selected_tool,
                "reason": get_selection_reason(selected_tool)
            }
        }]
    }


def get_selection_reason(tool: str) -> str:
    """Get human-readable reason for tool selection"""
    reasons = {
        "sql": "Best for structured queries and data filtering",
        "grep": "Best for pattern matching and text search",
        "metrics": "Best for aggregated statistics and metrics"
    }
    return reasons.get(tool, "Default tool")
