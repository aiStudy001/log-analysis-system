"""
필터 추출 노드 (LLM 기반)

사용자 질문에서 서비스명과 시간 범위를 자동으로 추출합니다.
"""
from app.agent.state import AgentState
from app.agent.llm_factory import get_llm
from datetime import datetime


def validate_time_range_structured(time_range: dict) -> tuple[bool, str]:
    """
    구조화된 시간 범위 유효성 검증

    Returns:
        (is_valid, error_message)
    """
    if not time_range or time_range.get("type") is None:
        return True, ""

    if time_range["type"] == "relative":
        relative = time_range.get("relative")
        if not relative:
            return False, "Missing relative time data"

        value = relative.get("value")
        unit = relative.get("unit")

        limits = {
            "h": (1, 720),
            "d": (1, 365),
            "w": (1, 52),
            "m": (1, 12)
        }

        if unit not in limits:
            return False, f"Invalid unit: {unit}"

        min_val, max_val = limits[unit]
        if not (min_val <= value <= max_val):
            return False, f"Value {value} out of range [{min_val}, {max_val}] for unit {unit}"

    elif time_range["type"] == "absolute":
        absolute = time_range.get("absolute")
        if not absolute:
            return False, "Missing absolute date data"

        try:
            start = datetime.fromisoformat(absolute["start"])
            end = datetime.fromisoformat(absolute["end"])
        except ValueError as e:
            return False, f"Invalid date format: {e}"

        if start >= end:
            return False, "Start date must be before end date"

        if end > datetime.now():
            return False, "End date cannot be in the future"

        if (end - start).days > 365:
            return False, "Date range cannot exceed 1 year"

    return True, ""


async def extract_filters_node(state: AgentState) -> dict:
    """
    필터 추출: structured 우선 (사용자 지정 시간만), fallback to LLM

    우선순위:
    1. time_range_structured (사용자 지정 시간 - 모달에서만 전달) - 검증 후 사용
    2. LLM 자동 추출 (자연어 표현 + preset 드롭다운)

    추출 대상:
    - service: 서비스명 (payment-api, order-api 등)
    - time_range_structured: 구조화된 시간 범위 (상대/절대)

    Returns:
        dict: {
            "extracted_service": str | None,
            "extracted_time_range": str | None (DEPRECATED),
            "extracted_time_range_structured": TimeRangeStructured,
            "extraction_confidence": float,
            "events": list
        }
    """
    # 1. 사용자 지정 시간(모달)만 우선 사용 (preset 드롭다운은 LLM이 추출)
    has_custom_time = state.get("time_range_structured") is not None

    if has_custom_time:
        structured = state["time_range_structured"]

        # 유효성 검증
        is_valid, error_msg = validate_time_range_structured(structured)
        if not is_valid:
            return {
                "extracted_time_range_structured": None,
                "events": [{
                    "type": "validation_error",
                    "node": "extract_filters",
                    "data": {
                        "error": error_msg,
                        "field": "time_range"
                    }
                }]
            }

        # 검증 통과 - 사용자 지정 시간 사용 (충돌 없음)
        print(f"✅ Using custom time_range from modal: {structured}")

        # 서비스는 여전히 LLM으로 추출
        # 시간은 사용자 지정 값 사용 (LLM 추출 건너뜀)
        extracted_time_range_structured = structured
        time_extraction_source = "custom_input"
    else:
        # preset 드롭다운 또는 질문 텍스트 → LLM이 추출
        extracted_time_range_structured = None
        time_extraction_source = "llm_extraction"

    # 2. LLM 추출 (기존 로직 + 확장)
    question = state.get("resolved_question", state["question"])

    # 현재 날짜 (자연어 표현 해석용)
    today = datetime.now().strftime("%Y-%m-%d")

    # 프롬프트 생성 (사용자 지정 시간이 있으면 서비스만 추출)
    if has_custom_time:
        # 서비스만 추출하는 간단한 프롬프트 (사용자 지정 시간 사용 중)
        prompt = f"""다음 자연어 질문에서 서비스명을 추출하세요.

질문: "{question}"

추출할 서비스:
- payment-api, order-api, user-api, auth-api, inventory-api, notification-api, web-app 중 하나
- "결제", "페이먼트" → payment-api
- "주문" → order-api
- "사용자", "유저" → user-api
- "인증", "로그인" → auth-api
- "재고" → inventory-api
- "알림", "노티" → notification-api

**중요**: 질문에 명시적으로 언급된 것만 추출하세요. 없으면 null을 반환하세요.

응답 형식 (JSON만):
{{
  "service": "payment-api" | "order-api" | "user-api" | "auth-api" | "inventory-api" | "notification-api" | "web-app" | null,
  "confidence": 0.0 ~ 1.0
}}"""
    else:
        # 서비스 + 시간 모두 추출하는 전체 프롬프트
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

2. **시간 범위** (구조화된 형식):
   a) 상대 시간:
      - "최근 N시간/일/주/월" → {{"type": "relative", "relative": {{"value": N, "unit": "h/d/w/m"}}}}
      - 예: "최근 3시간" → {{"type": "relative", "relative": {{"value": 3, "unit": "h"}}, "absolute": null}}
      - 예: "최근 10일" → {{"type": "relative", "relative": {{"value": 10, "unit": "d"}}, "absolute": null}}
      - 예: "최근 2주" → {{"type": "relative", "relative": {{"value": 2, "unit": "w"}}, "absolute": null}}
      - 예: "최근 1개월" → {{"type": "relative", "relative": {{"value": 1, "unit": "m"}}, "absolute": null}}

   b) 절대 날짜:
      - "YYYY-MM-DD부터 YYYY-MM-DD까지" 형식
      - 예: "2025년 1월 1일부터 1월 31일까지" →
        {{"type": "absolute", "relative": null, "absolute": {{"start": "2025-01-01", "end": "2025-01-31"}}}}

   c) 자연어 표현 (오늘 날짜: {today}):
      - "작년" → {{"type": "absolute", "relative": null, "absolute": {{"start": "2024-01-01", "end": "2024-12-31"}}}}
      - "이번 달" → {{"type": "absolute", "relative": null, "absolute": {{"start": "2025-02-01", "end": "2025-02-28"}}}}
      - "지난주" → {{"type": "absolute", "relative": null, "absolute": {{"start": "2025-01-27", "end": "2025-02-02"}}}}
      - "오늘" → {{"type": "relative", "relative": {{"value": 24, "unit": "h"}}, "absolute": null}}
      - "어제" → {{"type": "relative", "relative": {{"value": 48, "unit": "h"}}, "absolute": null}}
      - "최근", "방금", "조금 전" → {{"type": "relative", "relative": {{"value": 1, "unit": "h"}}, "absolute": null}}

   d) 명시 없음:
      - {{"type": null, "relative": null, "absolute": null}}

**중요**:
- 질문에 명시적으로 언급된 것만 추출하세요
- 오늘 날짜({today})를 기준으로 상대적 날짜를 계산하세요
- JSON 형식으로만 응답하세요

응답 형식 (JSON만):
{{
  "service": "payment-api" | "order-api" | "user-api" | "auth-api" | "inventory-api" | "notification-api" | "web-app" | null,
  "time_range": {{
    "type": "relative" | "absolute" | null,
    "relative": {{"value": N, "unit": "h/d/w/m"}} | null,
    "absolute": {{"start": "YYYY-MM-DD", "end": "YYYY-MM-DD"}} | null
  }},
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
            confidence = result.get("confidence", 0.5)

            # 시간 추출 (사용자 지정 시간이 없을 때만)
            if not has_custom_time:
                extracted_time_range_structured = result.get("time_range")  # 구조화된 형식

                # 검증 (LLM이 반환한 time_range도 검증)
                if extracted_time_range_structured:
                    is_valid, error_msg = validate_time_range_structured(extracted_time_range_structured)
                    if not is_valid:
                        print(f"⚠️ LLM extracted invalid time_range: {error_msg}")
                        extracted_time_range_structured = None
            # else: extracted_time_range_structured는 이미 위에서 설정됨 (사용자 지정)
        else:
            # LLM이 JSON을 반환하지 않으면 실패
            extracted_service = None
            if not has_custom_time:
                extracted_time_range_structured = None
            confidence = 0.0

        # 이벤트 생성 (항상 전송 - 프론트엔드가 충돌 검사)
        event_data = {
            "service": extracted_service,
            "time_range": extracted_time_range_structured,  # 구조화된 형식 (또는 사용자 지정 값)
            "confidence": confidence,
            # NEW: LLM prompt and response for task history
            "llm_prompt": prompt,
            "llm_response": content
        }

        event = {
            "type": "filters_extracted",
            "node": "extract_filters",
            "data": event_data
        }

        return {
            "extracted_service": extracted_service,
            "extracted_time_range": None,  # DEPRECATED
            "extracted_time_range_structured": extracted_time_range_structured,
            "extraction_confidence": confidence,
            "events": [event]
        }

    except Exception as e:
        # 추출 실패 시 None 반환
        print(f"⚠️ Filter extraction failed: {e}")
        return {
            "extracted_service": None,
            "extracted_time_range": None,  # DEPRECATED
            "extracted_time_range_structured": None,
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
