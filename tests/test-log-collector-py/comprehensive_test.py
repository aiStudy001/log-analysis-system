"""
log-collector 패키지 종합 기능 테스트
모든 기능을 체계적으로 테스트합니다.
"""
from log_collector import AsyncLogClient
import time

print("=" * 80)
print("log-collector 종합 기능 테스트")
print("=" * 80)

# 클라이언트 생성
logger = AsyncLogClient(
    "http://localhost:8000",
    service="comprehensive-test-py",
    environment="test"
)

print("\n✅ 클라이언트 생성 완료")

# ============================================================================
# 테스트 1: 기본 로그 레벨
# ============================================================================
print("\n[테스트 1] 기본 로그 레벨")
logger.trace("TRACE 레벨 로그")
logger.debug("DEBUG 레벨 로그")
logger.info("INFO 레벨 로그")
logger.warn("WARN 레벨 로그", warning_type="test_warning")
logger.error("ERROR 레벨 로그", error_code="TEST_001")
logger.fatal("FATAL 레벨 로그", severity="critical")
print("✅ 모든 로그 레벨 테스트 완료")

# ============================================================================
# 테스트 2: 자동 호출 위치 추적 (function_name, file_path)
# ============================================================================
print("\n[테스트 2] 자동 호출 위치 추적")

def outer_function():
    logger.info("외부 함수에서 호출")

    def inner_function():
        logger.info("내부 함수에서 호출")

    inner_function()

outer_function()
logger.info("전역에서 호출")
print("✅ 호출 위치 자동 추적 테스트 완료")

# ============================================================================
# 테스트 3: 사용자 컨텍스트
# ============================================================================
print("\n[테스트 3] 사용자 컨텍스트")

# Context Manager 방식
with AsyncLogClient.user_context(user_id="user_001", session_id="sess_abc"):
    logger.info("사용자 컨텍스트 포함 로그")

# 중첩 컨텍스트
with AsyncLogClient.user_context(tenant_id="tenant_001"):
    logger.info("테넌트 컨텍스트")

    with AsyncLogClient.user_context(user_id="user_002"):
        logger.info("테넌트 + 사용자 컨텍스트")

# 분산 추적
import uuid
trace_id = str(uuid.uuid4()).replace('-', '')[:32]

with AsyncLogClient.user_context(trace_id=trace_id, user_id="user_003"):
    logger.info("분산 추적 시작")
    time.sleep(0.1)
    logger.info("분산 추적 진행 중")
    time.sleep(0.1)
    logger.info("분산 추적 완료")

print("✅ 사용자 컨텍스트 테스트 완료")

# ============================================================================
# 테스트 4: 타이머 (duration_ms)
# ============================================================================
print("\n[테스트 4] 타이머 기능")

# 수동 타이머
timer = logger.start_timer()
time.sleep(0.5)
logger.end_timer(timer, "INFO", "수동 타이머 테스트 (약 500ms)")

# 함수 래퍼 (동기)
def slow_operation():
    time.sleep(0.3)
    return "완료"

result = logger.measure(slow_operation)
print(f"  결과: {result}")

# 함수 래퍼 (비동기)
import asyncio

async def async_operation():
    await asyncio.sleep(0.2)
    return "비동기 완료"

asyncio.run(logger.measure(async_operation))

print("✅ 타이머 기능 테스트 완료")

# ============================================================================
# 테스트 5: 에러 추적 (error_with_trace)
# ============================================================================
print("\n[테스트 5] 에러 추적")

# 기본 에러
try:
    result = 10 / 0
except ZeroDivisionError as e:
    logger.error_with_trace("나누기 0 에러", exception=e)

# 중첩 함수에서 에러
def level1():
    def level2():
        def level3():
            raise ValueError("깊은 에러 발생")
        level3()
    level2()

try:
    level1()
except ValueError as e:
    logger.error_with_trace("중첩 함수 에러", exception=e, error_context="level1->level2->level3")

# 사용자 컨텍스트와 함께 에러
with AsyncLogClient.user_context(user_id="user_error", trace_id="trace_error"):
    try:
        raise RuntimeError("사용자 작업 중 에러")
    except RuntimeError as e:
        logger.error_with_trace("사용자 작업 실패", exception=e)

print("✅ 에러 추적 테스트 완료")

# ============================================================================
# 테스트 6: 메타데이터 및 커스텀 필드
# ============================================================================
print("\n[테스트 6] 메타데이터 및 커스텀 필드")

logger.info("주문 생성",
    order_id="ORD-12345",
    user_id="user_999",
    amount=99.99,
    currency="USD",
    items=3
)

logger.info("API 요청",
    method="POST",
    endpoint="/api/orders",
    status_code=201,
    response_time_ms=45
)

print("✅ 메타데이터 테스트 완료")

# ============================================================================
# 테스트 7: 수동 flush
# ============================================================================
print("\n[테스트 7] 수동 Flush")
logger.flush()
print("✅ Flush 완료")

# ============================================================================
# 완료
# ============================================================================
print("\n로그 전송 대기 중...")
time.sleep(3)

print("\n" + "=" * 80)
print("모든 테스트 완료!")
print("=" * 80)
print("\nPostgreSQL에서 확인:")
print("  SELECT")
print("    created_at,")
print("    level,")
print("    message,")
print("    function_name,")
print("    file_path,")
print("    metadata->>'user_id' as user_id,")
print("    metadata->>'trace_id' as trace_id,")
print("    duration_ms,")
print("    stack_trace")
print("  FROM logs")
print("  WHERE service = 'comprehensive-test-py'")
print("  ORDER BY created_at DESC")
print("  LIMIT 30;")
print("=" * 80)
