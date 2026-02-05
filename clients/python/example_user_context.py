"""
사용자 컨텍스트 자동 수집 예제 (Python)

실행 방법:
    python example_user_context.py

테스트 시나리오:
    1. Context Manager 방식
    2. Set/Clear 방식
    3. 중첩 컨텍스트
    4. 분산 추적 (trace_id)
"""
import sys
import os
import time
import uuid

# 로컬 log_collector 모듈 사용
sys.path.insert(0, os.path.dirname(__file__))
from log_collector import AsyncLogClient

# 로그 클라이언트 초기화
logger = AsyncLogClient(
    "http://localhost:8000",
    service="user-context-example",
    environment="development"
)

def example_1_context_manager():
    """예제 1: Context Manager 방식 (권장)"""
    print("\n=== 예제 1: Context Manager 방식 ===")

    # 컨텍스트 없이 로그
    logger.info("Operation without context")
    # → user_id 없음

    # 컨텍스트 있이 로그
    with AsyncLogClient.user_context(
        user_id="user_123",
        trace_id="trace_xyz",
        session_id="sess_abc"
    ):
        logger.info("User logged in")
        # → user_id, trace_id, session_id 자동 포함!

        logger.info("User viewing dashboard")
        # → 같은 컨텍스트 정보 포함

        simulate_payment()

    # with 블록 벗어나면 컨텍스트 자동 초기화
    logger.info("Operation after context cleared")
    # → user_id 없음


def simulate_payment():
    """결제 시뮬레이션 (컨텍스트 자동 전파)"""
    logger.info("Processing payment")
    # → 상위 컨텍스트의 user_id, trace_id 자동 포함!

    time.sleep(0.1)  # 결제 처리 시뮬레이션

    logger.info("Payment completed", amount=99.99, currency="USD")
    # → user_id, trace_id + 추가 필드


def example_2_set_clear():
    """예제 2: Set/Clear 방식"""
    print("\n=== 예제 2: Set/Clear 방식 ===")

    # 로그인 시 컨텍스트 설정
    AsyncLogClient.set_user_context(
        user_id="user_456",
        session_id="sess_xyz"
    )

    logger.info("User logged in (set/clear style)")
    # → user_id, session_id 포함

    logger.info("Browsing products")
    # → 계속 포함됨

    # 로그아웃 시 컨텍스트 초기화
    AsyncLogClient.clear_user_context()

    logger.info("User logged out")
    # → user_id 없음


def example_3_nested_context():
    """예제 3: 중첩 컨텍스트"""
    print("\n=== 예제 3: 중첩 컨텍스트 ===")

    # 외부 컨텍스트: tenant_id
    with AsyncLogClient.user_context(tenant_id="tenant_acme"):
        logger.info("Tenant operation started")
        # → tenant_id="tenant_acme"

        # 내부 컨텍스트: user_id 추가
        with AsyncLogClient.user_context(user_id="user_789"):
            logger.info("User operation in tenant")
            # → tenant_id="tenant_acme", user_id="user_789" 둘 다 포함!

            logger.info("Fetching tenant data for user")
            # → 같은 컨텍스트

        logger.info("Back to tenant-only context")
        # → tenant_id="tenant_acme" (user_id 없음)


def example_4_distributed_tracing():
    """예제 4: 분산 추적 (trace_id)"""
    print("\n=== 예제 4: 분산 추적 ===")

    # 요청마다 고유한 trace_id 생성
    trace_id = str(uuid.uuid4())

    with AsyncLogClient.user_context(
        trace_id=trace_id,
        user_id="user_999"
    ):
        logger.info("Request received")
        # → trace_id, user_id 포함

        # 여러 서비스 호출 (시뮬레이션)
        call_service_a()
        call_service_b()
        call_service_c()

        logger.info("Request completed")
        # → 같은 trace_id로 전체 흐름 추적 가능!


def call_service_a():
    """Service A 호출 시뮬레이션"""
    logger.info("Calling Service A")
    # → 상위 컨텍스트의 trace_id 자동 포함!
    time.sleep(0.05)
    logger.info("Service A responded")


def call_service_b():
    """Service B 호출 시뮬레이션"""
    logger.info("Calling Service B")
    time.sleep(0.08)
    logger.info("Service B responded")


def call_service_c():
    """Service C 호출 시뮬레이션"""
    logger.info("Calling Service C")
    time.sleep(0.06)
    logger.info("Service C responded")


def example_5_error_tracking():
    """예제 5: 에러 추적 with Context"""
    print("\n=== 예제 5: 에러 추적 ===")

    with AsyncLogClient.user_context(
        user_id="user_error_test",
        trace_id="trace_error_123"
    ):
        logger.info("Starting risky operation")

        try:
            # 의도적으로 에러 발생
            raise ValueError("Simulated error for testing")

        except Exception as e:
            logger.error_with_trace("Operation failed", exception=e)
            # → user_id, trace_id, stack_trace, error_type 모두 포함!
            # 어떤 사용자의 작업이 실패했는지 즉시 파악 가능


def main():
    """모든 예제 실행"""
    print("=" * 60)
    print("사용자 컨텍스트 자동 수집 예제")
    print("=" * 60)

    example_1_context_manager()
    time.sleep(0.5)

    example_2_set_clear()
    time.sleep(0.5)

    example_3_nested_context()
    time.sleep(0.5)

    example_4_distributed_tracing()
    time.sleep(0.5)

    example_5_error_tracking()
    time.sleep(0.5)

    # Flush 대기
    print("\n=== Flushing logs... ===")
    logger.flush()
    time.sleep(2)

    print("\n=== 완료! ===")
    print("\nPostgreSQL에서 확인:")
    print("  SELECT")
    print("    created_at,")
    print("    metadata->>'user_id' as user_id,")
    print("    metadata->>'trace_id' as trace_id,")
    print("    message")
    print("  FROM logs")
    print("  WHERE service = 'user-context-example'")
    print("  ORDER BY created_at DESC")
    print("  LIMIT 20;")


if __name__ == '__main__':
    main()
