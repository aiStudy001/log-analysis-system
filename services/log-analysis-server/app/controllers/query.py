"""
Text-to-SQL query controller
"""
from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import QueryRequest, QueryResponse, SummarizeRequest, SummarizeResponse
from app.services.stream_service import execute_query
from app.dependencies import get_schema_repository, get_query_repository
from app.agent.llm_factory import get_llm

router = APIRouter(tags=["query"])


@router.post("/query", response_model=QueryResponse)
async def query_logs(
    request: QueryRequest,
    schema_repo=Depends(get_schema_repository),
    query_repo=Depends(get_query_repository)
):
    """
    Execute Text-to-SQL query synchronously

    Examples:
        - "최근 1시간 에러 로그"
        - "payment-api에서 가장 많이 발생한 에러 top 5"
        - "느린 API 찾기 (1초 이상)"
    """
    try:
        result = await execute_query(
            question=request.question,
            max_results=request.max_results,
            schema_repo=schema_repo,
            query_repo=query_repo
        )

        if result.get("type") == "error":
            raise HTTPException(status_code=400, detail=result["error"])

        return QueryResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/summarize", response_model=SummarizeResponse)
async def summarize_conversation(request: SummarizeRequest):
    """
    Summarize conversation messages using LLM

    Args:
        request: SummarizeRequest with list of messages

    Returns:
        SummarizeResponse with summary text
    """
    try:
        llm = get_llm(streaming=False)

        # Format messages for prompt
        formatted_messages = []
        for i, msg in enumerate(request.messages, 1):
            if msg.role == 'user':
                formatted_messages.append(f"{i}. Q: {msg.content}")
            elif msg.role == 'ai':
                result_info = f"{msg.count}건" if msg.count else "N/A"
                formatted_messages.append(f"   A: {result_info}")
                if msg.insight:
                    formatted_messages.append(f"   인사이트: {msg.insight[:100]}...")

        conversation_text = "\n".join(formatted_messages)

        # Summarization prompt
        prompt = f"""다음 대화 내용을 핵심만 간결하게 요약하세요.

# 대화 내용
{conversation_text}

# 요약 지침
- 주요 질문과 결과를 중심으로 요약
- 1-3문장으로 간결하게
- 서비스명, 에러 유형, 시간 범위 등 핵심 정보 포함
- "사용자가 ~를 조회하여 ~건의 결과를 확인했습니다" 형식

요약:"""

        response = await llm.ainvoke(prompt)
        summary = response.content.strip()

        return SummarizeResponse(summary=summary)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"요약 실패: {str(e)}")
