"""
필터 추출 노드 (LLM 기반)

사용자 질문에서 서비스명과 시간 범위를 자동으로 추출합니다.
"""
from app.agent.state import AgentState
from app.agent.llm_factory import get_llm


async def extract_filters_node(state: AgentState) -> dict:
    """
    LLM을 사용하여 자연어 질문에서 필터 추출

    추출 대상:
    - service: 서비스명 (payment-api, order-api 등)
    - time_range: 시간 범위 (1h, 6h, 24h, 7d)

    Returns:
        dict: {
            "extracted_service": str | None,
            "extracted_time_range": str | None,
            "extraction_confidence": float,  # 0-1
            "events": list
        }
    """
    question = state.get("resolved_question", state["question"])

    # LLM 프롬프트
    prompt = f"""다음 자연어 질문에서 로그 필터를 추출하세요.

질문: "{question}"

추출할 필터:
1. **서비스명**: payment-api, order-api, user-api, auth-api, inventory-api, notification-api, web-app 중 하나
   - "결제", "페이먼트" → payment-api
   - "주문" → order-api
   - "사용자", "유저" → user-api
   - "인증", "로그인" → auth-api
   - "재고" → inventory-api
   - "알림", "노티" → notification-api

2. **시간 범위**: 1h, 6h, 24h, 48h, 7d 중 하나로 변환
   - "최근 N시간" → Nh (예: "최근 1시간" → "1h", "최근 2시간" → "2h")
   - "최근 N일" → Nd (예: "최근 7일" → "7d")
   - "오늘" → 24h
   - "어제" → 48h (어제부터 지금까지)
   - "이번 주" → 7d
   - "최근", "방금", "조금 전" → 1h (기본값)
   - 명시 없음 → null

**중요**:
- 질문에 명시적으로 언급된 것만 추출하세요
- 추측하지 마세요
- JSON 형식으로만 응답하세요

응답 형식:
{{
  "service": "payment-api" | "order-api" | "user-api" | "auth-api" | "inventory-api" | "notification-api" | "web-app" | null,
  "time_range": "1h" | "2h" | "6h" | "12h" | "24h" | "48h" | "7d" | null,
  "confidence": 0.0 ~ 1.0
}}"""

    try:
        # LLM 호출
        llm = get_llm()
        response = await llm.ainvoke(prompt)

        # JSON 파싱
        import json
        import re

        # Extract JSON from response
        content = response.content if hasattr(response, 'content') else str(response)
        json_match = re.search(r'\{[\s\S]*\}', content)

        if json_match:
            result = json.loads(json_match.group(0))
            extracted_service = result.get("service")
            extracted_time_range = result.get("time_range")
            confidence = result.get("confidence", 0.5)
        else:
            # LLM이 JSON을 반환하지 않으면 실패
            extracted_service = None
            extracted_time_range = None
            confidence = 0.0

        # 이벤트 생성
        event = {
            "type": "filters_extracted",
            "node": "extract_filters",
            "data": {
                "service": extracted_service,
                "time_range": extracted_time_range,
                "confidence": confidence,
                # NEW: LLM prompt and response for task history
                "llm_prompt": prompt,
                "llm_response": content
            }
        }

        return {
            "extracted_service": extracted_service,
            "extracted_time_range": extracted_time_range,
            "extraction_confidence": confidence,
            "events": [event]
        }

    except Exception as e:
        # 추출 실패 시 None 반환
        print(f"⚠️ Filter extraction failed: {e}")
        return {
            "extracted_service": None,
            "extracted_time_range": None,
            "extraction_confidence": 0.0,
            "events": [{
                "type": "filters_extracted",
                "node": "extract_filters",
                "data": {
                    "service": None,
                    "time_range": None,
                    "confidence": 0.0,
                    "error": str(e)
                }
            }]
        }
