"""
Context Resolution Node

Resolves references and pronouns in user questions using conversation history.
"""
from langchain_core.messages import HumanMessage
from .llm_factory import get_llm
import re


CONTEXT_AWARE_ANALYSIS_PROMPT = """당신은 대화 맥락을 이해하는 질문 분석 전문가입니다.
사용자의 질문을 대화 히스토리와 현재 포커스를 고려하여 분석하고 명확하게 만드세요.

# 대화 히스토리
{history}

# 현재 포커스
{focus}

# 사용자 질문
{question}

# 분석 작업

1. **참조 해석**: 질문에 대명사나 참조가 있으면 구체적으로 변환
   - "그 에러" → 이전 대화에서 언급된 구체적 error_type
   - "그 서비스" → 이전 대화에서 언급된 구체적 service
   - "그때" → 이전 대화에서 언급된 구체적 time_range
   - "더 자세히" → 이전 쿼리 파라미터 유지

2. **맥락 보강**: 대화 히스토리나 포커스 정보를 활용하여 질문을 더 명확하게
   - 포커스에 service가 있고 질문에 명시 안 되어 있으면 암묵적으로 같은 서비스 가정
   - 이전에 특정 시간대를 분석했다면 연속성 고려
   - 단, 사용자가 명시적으로 다른 대상을 지정하면 그것을 우선

3. **원본 유지**: 참조나 맥락 보강이 필요 없으면 원본 질문 그대로 반환

# 출력 형식
명확하게 해석된 질문만 반환하세요. 설명이나 주석 없이 질문만 출력하세요.

해석된 질문:"""


def contains_references(question: str) -> bool:
    """
    Check if question contains references that need resolution

    Args:
        question: User question

    Returns:
        True if references detected
    """
    reference_patterns = [
        r'\b그\s*(에러|서비스|API|시간|경우)\b',  # 그 에러, 그 서비스
        r'\b그때\b',                              # 그때
        r'\b더\s*자세히\b',                       # 더 자세히
        r'\b같은\s*(서비스|에러)\b',              # 같은 서비스
        r'\b이\s*(에러|서비스)\b',                # 이 에러
    ]

    for pattern in reference_patterns:
        if re.search(pattern, question):
            return True
    return False


def extract_focus_entities(question: str, sql: str, results: list) -> dict:
    """
    Extract focus entities from question and SQL

    Args:
        question: User question
        sql: Generated SQL
        results: Query results

    Returns:
        Dict with extracted focus entities (service, error_type, time_range)
    """
    focus = {}

    # Extract service from SQL
    service_match = re.search(r"service\s*=\s*'([^']+)'", sql, re.IGNORECASE)
    if service_match:
        focus["service"] = service_match.group(1)

    # Extract error_type from SQL
    error_match = re.search(r"error_type\s*=\s*'([^']+)'", sql, re.IGNORECASE)
    if error_match:
        focus["error_type"] = error_match.group(1)

    # Extract time range from SQL
    time_match = re.search(r"INTERVAL\s*'(\d+\s*\w+)'", sql, re.IGNORECASE)
    if time_match:
        focus["time_range"] = time_match.group(1)

    return focus


async def resolve_context_node(state: dict, conversation_service) -> dict:
    """
    Analyze question with conversation context (ALWAYS runs LLM)

    Args:
        state: AgentState
        conversation_service: ConversationService instance

    Returns:
        Updated state with resolved_question and current_focus
    """
    question = state["question"]
    conversation_id = state.get("conversation_id", "default")

    # Get conversation context
    context = conversation_service.get_context(conversation_id)

    # ALWAYS run LLM analysis
    prompt = CONTEXT_AWARE_ANALYSIS_PROMPT.format(
        history=format_history(context.get("history", [])),
        focus=context.get("focus", {}),
        question=question
    )

    llm = get_llm(streaming=False)
    response = await llm.ainvoke([HumanMessage(content=prompt)])
    resolved = response.content.strip()

    # Check if question was modified
    resolution_needed = (resolved != question)

    return {
        "resolved_question": resolved,
        "current_focus": context.get("focus", {}),
        "events": [{
            "type": "context_resolved",
            "node": "resolve_context",
            "status": "completed",
            "data": {
                "resolution_needed": resolution_needed,
                "original_question": question,
                "resolved_question": resolved if resolution_needed else None,
                "focus": context.get("focus", {}),
                # LLM prompt and response for task history
                "llm_prompt": prompt,
                "llm_response": resolved
            }
        }]
    }


def format_history(history: list) -> str:
    """
    Format conversation history for prompt

    Args:
        history: List of previous turns

    Returns:
        Formatted string for LLM prompt
    """
    if not history:
        return "No previous conversation"

    formatted = []
    for i, turn in enumerate(history, 1):
        formatted.append(
            f"{i}. Q: {turn['question']}\n"
            f"   SQL: {turn['sql']}\n"
            f"   Results: {turn['count']}건"
        )

    return "\n".join(formatted)
