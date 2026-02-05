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
