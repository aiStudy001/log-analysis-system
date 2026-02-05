"""
배포된 log-collector 패키지 사용 테스트
"""
from log_collector import AsyncLogClient
import time

print("=" * 60)
print("log-collector 패키지 테스트")
print("=" * 60)

# 클라이언트 생성
logger = AsyncLogClient(
    "http://localhost:8000",
    service="test-service",
    environment="development"
)

print("\n✅ 클라이언트 생성 완료")

# 기본 로그 전송
logger.info("테스트 로그 1")
logger.warn("경고 로그", warning_type="test")
logger.error("에러 로그", error_code="TEST_ERROR")

print("✅ 로그 3개 전송 완료")

# 자동 호출 위치 추적 테스트
def test_function():
    logger.info("함수에서 호출한 로그")
    # function_name과 file_path가 자동으로 포함됨

test_function()
print("✅ 자동 호출 위치 추적 테스트 완료")

# 사용자 컨텍스트 테스트
with AsyncLogClient.user_context(user_id="user_123", trace_id="trace_xyz"):
    logger.info("컨텍스트 포함 로그")
    # user_id와 trace_id가 자동으로 포함됨

print("✅ 사용자 컨텍스트 테스트 완료")

# Flush 대기
print("\n로그 전송 대기 중...")
time.sleep(2)

logger.flush()
print("✅ 모든 로그 전송 완료!")

print("\n" + "=" * 60)
print("테스트 완료! 로그 서버에서 확인하세요.")
print("=" * 60)
