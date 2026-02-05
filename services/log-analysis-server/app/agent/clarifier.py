"""
재질문 노드 (LLM 기반)

정규식 패턴 매칭 대신 LLM으로 질문을 분석하여:
1. 서비스 언급 여부 및 유형 (구체적 서비스 vs "서비스별" 집계)
2. 시간 정보 명확성
3. 집계 쿼리 vs 필터 쿼리 구분
4. 재질문 필요 여부 판단
"""
import json
import re
from app.agent.state import AgentState
from app.agent.llm_factory import get_llm


async def get_available_services_from_db(query_repo) -> list[str]:
    """
    데이터베이스에서 실제 존재하는 서비스 목록을 동적으로 가져옴

    Args:
        query_repo: QueryRepository instance (graph.py에서 주입)

    Returns:
        서비스명 목록 (예: ["payment-api", "order-api", "user-api"])
    """
    try:
        # DB에서 DISTINCT service 조회
        query = "SELECT DISTINCT service FROM logs WHERE service IS NOT NULL ORDER BY service"
        result = await query_repo.execute_query(query)

        # asyncpg.Record 객체면 'service' 필드 추출
        if result:
            # asyncpg.Record는 dict-like이므로 인덱스로도 접근 가능
            return [row['service'] if hasattr(row, 'keys') else row[0] for row in result]
        else:
            return []
    except Exception as e:
        # 실패 시 빈 배열 반환 (재질문 건너뜀)
        print(f"⚠️ Failed to fetch services from DB: {e}")
        return []


async def clarification_node(state: AgentState, query_repo=None) -> dict:
    """
    LLM으로 질문을 분석하고 재질문 필요 여부 판단
    """
    question = state.get("resolved_question", state["question"])

    # 재질문 횟수 체크 (무한 루프 방지)
    clarification_count = state.get("clarification_count", 0)
    if clarification_count >= 2:
        return {
            "clarifications_needed": [],
            "events": [{
                "type": "clarification_skipped",
                "node": "clarifier",
                "data": {
                    "reason": "max_attempts_reached",
                    "message": "재질문 최대 횟수 초과 - 현재 정보로 진행합니다"
                }
            }]
        }

    # LLM 프롬프트
    llm = get_llm()
    prompt = f"""다음 자연어 질문을 분석하세요.

질문: "{question}"

분석 항목:
1. **서비스 정보**:
   - has_service: 서비스 언급 여부 (true/false)
   - service_type: 서비스 유형
     - "specific": 구체적 서비스명 (payment-api, order-api 등)
     - "aggregation": 집계 표현 ("서비스별", "서비스별로", "각 서비스", "전체 서비스")
     - "none": 서비스 정보 없음
   - mentioned_services: 언급된 서비스명 배열 (있으면)

2. **쿼리 유형**:
   - is_aggregation: 집계 쿼리 여부 (GROUP BY 필요)
     - "서비스별 에러 개수" → true (GROUP BY service)
     - "시간대별 추이" → true (GROUP BY time)
     - "payment-api 에러 로그" → false (WHERE 필터만)
   - is_filter_query: 필터 쿼리 여부 (WHERE 필요)

3. **시간 정보**:
   - has_time: 시간 정보 명시 여부 (true/false)
   - time_clarity: 시간 명확성
     - "clear": 명확함 ("최근 1시간", "오늘")
     - "ambiguous": 모호함 ("얼마 전", "조금 전")
     - "none": 시간 정보 없음

4. **재질문 필요성**:
   - needs_service_clarification: 서비스 재질문 필요 (true/false)
     - 집계 쿼리면 false (전체 서비스 분석이므로)
     - 필터 쿼리인데 서비스 없으면 true
   - needs_time_clarification: 시간 재질문 필요 (true/false)
     - 모호한 시간 표현이면 true

**판단 기준**:
- "최근 24시간 서비스별 에러 개수":
  → service_type="aggregation", is_aggregation=true, needs_service_clarification=false

- "payment-api 에러 로그":
  → service_type="specific", mentioned_services=["payment-api"], needs_service_clarification=false

- "에러 로그 조회":
  → service_type="none", is_filter_query=true, needs_service_clarification=true

- "전체 서비스의 에러 로그 조회":
  → service_type="aggregation", is_filter_query=true, needs_service_clarification=false
  (모든 서비스의 로그를 조회하므로 WHERE 절 없이 실행)

- "조금 전 로그":
  → time_clarity="ambiguous", needs_time_clarification=true

**응답 형식** (JSON만):
{{
  "has_service": true/false,
  "service_type": "specific" | "aggregation" | "none",
  "mentioned_services": ["service1", ...],
  "is_aggregation": true/false,
  "is_filter_query": true/false,
  "has_time": true/false,
  "time_clarity": "clear" | "ambiguous" | "none",
  "needs_service_clarification": true/false,
  "needs_time_clarification": true/false,
  "reasoning": "간단한 설명"
}}"""

    try:
        response = await llm.ainvoke(prompt)
        content = response.content if hasattr(response, 'content') else str(response)

        # JSON 추출
        json_match = re.search(r'\{[\s\S]*\}', content)
        if not json_match:
            # LLM 분석 실패 시 통과
            return {"clarifications_needed": [], "events": []}

        analysis = json.loads(json_match.group(0))

        # 디버그: LLM 분석 결과 출력
        print(f"🔍 LLM Analysis for '{question}':")
        print(f"   - service_type: {analysis.get('service_type')}")
        print(f"   - is_aggregation: {analysis.get('is_aggregation')}")
        print(f"   - needs_service_clarification: {analysis.get('needs_service_clarification')}")
        print(f"   - reasoning: {analysis.get('reasoning')}")

        # 분석 결과로 재질문 생성
        clarifications = []

        # 서비스 재질문
        if analysis.get("needs_service_clarification", False):
            # 동적으로 서비스 목록 가져오기 (DB에서 실제 존재하는 서비스)
            available_services = await get_available_services_from_db(query_repo)

            if available_services:  # 서비스 목록이 있을 때만 재질문
                clarifications.append({
                    "type": "missing_info",
                    "field": "service",
                    "question": "어떤 서비스의 로그를 분석할까요?",
                    "options": available_services + ["전체"],  # 실제 서비스 + "전체"
                    "required": False
                })
            # 서비스 목록이 없으면 재질문 건너뜀 (DB 조회 실패 등)

        # 시간 재질문
        if analysis.get("needs_time_clarification", False):
            time_clarity = analysis.get("time_clarity", "none")
            if time_clarity == "ambiguous":
                clarifications.append({
                    "type": "ambiguous_time",
                    "field": "time",
                    "question": "시간 범위를 명확히 해주세요",
                    "options": [
                        "최근 1시간",
                        "최근 6시간",
                        "최근 24시간",
                        "최근 48시간",
                        "최근 7일",
                        "사용자 지정..."  # NEW: 모달 트리거
                    ],
                    "required": True,
                    "allow_custom": True  # NEW: 프론트엔드에 모달 지원 알림
                })
            elif time_clarity == "none" and analysis.get("is_aggregation"):
                # 집계 쿼리인데 시간 없으면 선택사항으로 물어봄
                clarifications.append({
                    "type": "missing_info",
                    "field": "time",
                    "question": "분석할 기간을 선택하세요",
                    "options": [
                        "최근 1시간",
                        "최근 6시간",
                        "최근 24시간",
                        "최근 48시간",
                        "최근 7일",
                        "사용자 지정...",  # NEW: 모달 트리거
                        "전체"
                    ],
                    "required": False,
                    "allow_custom": True  # NEW: 프론트엔드에 모달 지원 알림
                })

        # 재질문이 있으면 이벤트 발생
        if clarifications:
            return {
                "clarifications_needed": clarifications,
                "clarification_count": clarification_count + 1,
                "query_analysis": analysis,  # 분석 결과 저장
                "events": [{
                    "type": "clarification_needed",
                    "node": "clarifier",
                    "data": {
                        "questions": clarifications,
                        "count": len(clarifications),
                        "analysis": analysis,
                        # NEW: LLM prompt and response for task history
                        "llm_prompt": prompt,
                        "llm_response": content
                    }
                }]
            }

        # 재질문 없으면 통과
        return {
            "clarifications_needed": [],
            "query_analysis": analysis,  # 분석 결과는 저장
            "events": [{
                "type": "clarification_skipped",
                "node": "clarifier",
                "data": {
                    "reason": "no_clarification_needed",
                    "analysis": analysis,
                    # NEW: LLM prompt and response for task history
                    "llm_prompt": prompt,
                    "llm_response": content
                }
            }]
        }

    except Exception as e:
        # LLM 분석 실패 시 안전하게 통과
        print(f"⚠️ Clarification analysis failed: {e}")
        return {
            "clarifications_needed": [],
            "events": []
        }
