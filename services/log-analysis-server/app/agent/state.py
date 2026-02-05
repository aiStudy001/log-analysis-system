"""
LangGraph 상태 정의

Text-to-SQL 워크플로우의 상태를 관리합니다.
"""

from typing import TypedDict, Annotated, Sequence
from operator import add


class AgentState(TypedDict):
    """Text-to-SQL Agent 상태"""

    # 입력
    question: str                    # 사용자 질문
    max_results: int                 # 최대 결과 수

    # 스키마 정보
    schema_info: str                 # 테이블 스키마
    sample_data: str                 # 샘플 데이터

    # SQL 생성
    generated_sql: str               # 생성된 SQL
    validation_error: str            # 검증 에러 (있으면)
    retry_count: int                 # 재시도 횟수

    # 실행 결과
    query_results: list              # 쿼리 실행 결과
    execution_time_ms: float         # 실행 시간
    error_message: str               # 에러 메시지

    # 최종 출력
    formatted_results: dict          # 포맷된 결과
    insight: str                     # AI 분석 인사이트

    # 메시지 히스토리 (디버깅용)
    messages: Annotated[Sequence[dict], add]  # 처리 과정 로그

    # 이벤트 스트리밍 (meal-planner 패턴)
    events: Annotated[list[dict], add]        # 노드 이벤트 (스트리밍용)

    # Cache metadata (Feature #1)
    cache_hit: bool                  # 캐시에서 가져온 결과인지
    cache_key: str                   # 캐시 키

    # Conversation context (Feature #2)
    conversation_id: str             # 세션 ID
    resolved_question: str           # 참조 해석된 질문
    current_focus: dict              # 현재 focus {service, error_type, time_range}

    # Filter extraction (LLM-based)
    extracted_service: str           # LLM이 추출한 서비스명
    extracted_time_range: str        # LLM이 추출한 시간 범위
    extraction_confidence: float     # 추출 신뢰도 (0-1)

    # Clarification (재질문)
    clarifications_needed: list      # 필요한 재질문 목록
    user_clarifications: dict        # 사용자의 답변
    clarification_count: int         # 재질문 횟수 (무한루프 방지)
    query_analysis: dict             # LLM 질문 분석 결과 (service_type, is_aggregation 등)

    # Tool selection (Feature #6)
    selected_tool: str               # "sql" | "grep" | "metrics"
