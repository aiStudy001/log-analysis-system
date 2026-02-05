"""
통합 테스트: 로그 서버와의 E2E 검증
실행 전 요구사항:
1. PostgreSQL 실행 (localhost:5432)
2. 로그 서버 실행 (localhost:8000)
3. 스키마 생성 완료
"""
import pytest
import time
import requests
from log_collector import AsyncLogClient


@pytest.fixture
def log_server_url():
    """로그 서버 URL (서버 실행 필요)"""
    return "http://localhost:8000"


@pytest.fixture
def check_server_running(log_server_url):
    """로그 서버 실행 여부 확인"""
    try:
        response = requests.get(log_server_url, timeout=1)
        if response.status_code != 200:
            pytest.skip("로그 서버가 실행되지 않았습니다")
    except requests.exceptions.RequestException:
        pytest.skip("로그 서버가 실행되지 않았습니다")


def test_end_to_end_logging(log_server_url, check_server_running):
    """E2E: 로그 전송 → 서버 수신 → DB 저장"""
    client = AsyncLogClient(log_server_url, batch_size=5, flush_interval=1.0)

    # 5개 로그 전송
    for i in range(5):
        client.log("INFO", f"Integration test {i}", test_id="e2e_test", iteration=i)

    # Flush 대기
    time.sleep(2)

    # 서버 통계 확인
    response = requests.get(f"{log_server_url}/stats")
    assert response.status_code == 200

    stats = response.json()
    assert stats['total_logs'] >= 5, f"Expected >= 5 logs, got {stats['total_logs']}"


def test_batch_sending(log_server_url, check_server_running):
    """배치 전송 테스트: 10개 로그 → 자동 배치 전송"""
    client = AsyncLogClient(log_server_url, batch_size=10)

    # 10개 로그 → 자동 배치 전송
    for i in range(10):
        client.log("INFO", f"Batch test {i}", test_id="batch_test", iteration=i)

    # 배치 전송 대기
    time.sleep(1.5)

    # 서버 통계 확인
    response = requests.get(f"{log_server_url}/stats")
    assert response.status_code == 200

    stats = response.json()
    assert stats['total_logs'] >= 10


def test_flush_interval(log_server_url, check_server_running):
    """Flush 간격 테스트: 1초 후 자동 전송"""
    client = AsyncLogClient(log_server_url, batch_size=1000, flush_interval=1.0)

    # 5개만 보내기 (배치 크기 미달)
    for i in range(5):
        client.log("INFO", f"Flush interval test {i}", test_id="flush_test")

    # 1초 대기 → flush_interval에 의해 자동 전송되어야 함
    time.sleep(1.5)

    # 서버 통계 확인
    response = requests.get(f"{log_server_url}/stats")
    assert response.status_code == 200


def test_manual_flush(log_server_url, check_server_running):
    """수동 flush 테스트"""
    client = AsyncLogClient(log_server_url, batch_size=1000, flush_interval=60)

    # 3개 로그 (배치 크기 미달, flush_interval도 길음)
    for i in range(3):
        client.log("INFO", f"Manual flush test {i}", test_id="manual_flush_test")

    # 수동 flush 호출
    client.flush()

    # 약간의 대기
    time.sleep(0.5)

    # 서버 통계 확인
    response = requests.get(f"{log_server_url}/stats")
    assert response.status_code == 200


def test_multiple_services(log_server_url, check_server_running):
    """여러 서비스의 로그 동시 전송"""
    services = ["auth-service", "api-service", "db-service", "cache-service"]

    client = AsyncLogClient(log_server_url, batch_size=20)

    # 각 서비스에서 5개씩 로그 전송
    for service in services:
        for i in range(5):
            client.log(
                "INFO",
                f"Log from {service} #{i}",
                service=service,
                test_id="multi_service_test"
            )

    # 배치 전송 대기
    time.sleep(2)

    # 서버 통계 확인
    response = requests.get(f"{log_server_url}/stats")
    assert response.status_code == 200
    stats = response.json()
    assert stats['total_logs'] >= 20


def test_error_logging(log_server_url, check_server_running):
    """에러 로그 전송 테스트"""
    client = AsyncLogClient(log_server_url, batch_size=5)

    # 에러 로그 전송
    for i in range(5):
        client.log(
            "ERROR",
            f"Database connection failed: attempt {i}",
            error_code="DB_CONN_ERR",
            service="db-service",
            test_id="error_test"
        )

    time.sleep(1.5)

    # 서버 통계 확인
    response = requests.get(f"{log_server_url}/stats")
    assert response.status_code == 200

    stats = response.json()
    # 레벨별 분포에 ERROR가 있어야 함
    assert 'level_distribution' in stats
    assert any(item['level'] == 'ERROR' for item in stats['level_distribution'])


def test_auto_caller_integration(log_server_url, check_server_running):
    """호출 위치 자동 추적 통합 테스트 (E2E)"""
    client = AsyncLogClient(log_server_url, batch_size=5, flush_interval=1.0)

    # auto_caller 활성화된 상태로 로그 전송
    client.info("Auto caller test - line 1", test_id="auto_caller_integration")
    client.debug("Auto caller test - line 2", test_id="auto_caller_integration")
    client.warn("Auto caller test - line 3", test_id="auto_caller_integration")

    # 편의 메서드를 통한 로그도 테스트
    def helper_function():
        client.info("Message from helper function", test_id="auto_caller_integration")

    helper_function()

    # Flush 대기
    time.sleep(2)

    # 서버 통계 확인 (에러 없이 전송되었는지)
    response = requests.get(f"{log_server_url}/stats")
    assert response.status_code == 200

    stats = response.json()
    assert stats['total_logs'] >= 4

    # Note: function_name, file_path가 실제로 DB에 저장되었는지는
    # PostgreSQL 직접 쿼리로 확인 필요:
    # SELECT function_name, file_path, message
    # FROM logs
    # WHERE metadata->>'test_id' = 'auto_caller_integration';


def test_auto_caller_disabled_integration(log_server_url, check_server_running):
    """호출 위치 자동 추적 비활성화 통합 테스트"""
    client = AsyncLogClient(log_server_url, batch_size=5, flush_interval=1.0)

    # auto_caller=False로 로그 전송
    client.log(
        "INFO",
        "Auto caller disabled test",
        auto_caller=False,
        test_id="auto_caller_disabled"
    )

    # Flush 대기
    time.sleep(2)

    # 서버 통계 확인 (에러 없이 전송되었는지)
    response = requests.get(f"{log_server_url}/stats")
    assert response.status_code == 200


def test_timer_with_auto_caller(log_server_url, check_server_running):
    """타이머 기능과 auto_caller 통합 테스트"""
    client = AsyncLogClient(log_server_url, batch_size=5, flush_interval=1.0)

    # 타이머 사용 시에도 auto_caller가 동작해야 함
    timer = client.start_timer()
    time.sleep(0.1)  # 작업 시뮬레이션
    client.end_timer(timer, "INFO", "Timer test completed", test_id="timer_auto_caller")

    # 컨텍스트 매니저 타이머
    with client.timer("Context manager timer test"):
        time.sleep(0.05)

    # Flush 대기
    time.sleep(2)

    # 서버 통계 확인
    response = requests.get(f"{log_server_url}/stats")
    assert response.status_code == 200


def test_error_with_trace_integration(log_server_url, check_server_running):
    """error_with_trace와 auto_caller 통합 테스트"""
    client = AsyncLogClient(log_server_url, batch_size=5, flush_interval=1.0)

    # 예외 발생 시뮬레이션
    try:
        raise ValueError("Test exception for integration test")
    except Exception as e:
        client.error_with_trace(
            "Integration test exception",
            exception=e,
            test_id="error_trace_integration"
        )

    # Flush 대기
    time.sleep(2)

    # 서버 통계 확인
    response = requests.get(f"{log_server_url}/stats")
    assert response.status_code == 200

    # Note: stack_trace, error_type, function_name, file_path가 DB에 저장되었는지는
    # PostgreSQL 직접 쿼리로 확인:
    # SELECT stack_trace, error_type, function_name, file_path
    # FROM logs
    # WHERE metadata->>'test_id' = 'error_trace_integration';


# Feature 3: 사용자 컨텍스트 관리 통합 테스트
def test_user_context_integration(log_server_url, check_server_running):
    """사용자 컨텍스트 자동 포함 통합 테스트 (E2E)"""
    client = AsyncLogClient(log_server_url, batch_size=10, flush_interval=1.0)

    # 컨텍스트 없이 로그
    client.info("Without user context", test_id="user_context_integration")

    # 컨텍스트 있이 로그
    with AsyncLogClient.user_context(
        user_id="integration_user_123",
        trace_id="integration_trace_xyz"
    ):
        client.info("With user context 1", test_id="user_context_integration")
        client.info("With user context 2", test_id="user_context_integration")
        client.warn("User context warning", test_id="user_context_integration")

    # 컨텍스트 밖에서 다시 로그
    client.info("After user context", test_id="user_context_integration")

    # Flush 대기
    time.sleep(2)

    # 서버 통계 확인 (에러 없이 전송되었는지)
    response = requests.get(f"{log_server_url}/stats")
    assert response.status_code == 200

    stats = response.json()
    assert stats['total_logs'] >= 5

    # Note: user_id, trace_id가 실제로 DB에 저장되었는지는
    # PostgreSQL 직접 쿼리로 확인 필요:
    # SELECT
    #   message,
    #   metadata->>'user_id' as user_id,
    #   metadata->>'trace_id' as trace_id
    # FROM logs
    # WHERE metadata->>'test_id' = 'user_context_integration'
    # ORDER BY created_at;


def test_user_context_with_http_context_integration(log_server_url, check_server_running):
    """HTTP 컨텍스트와 사용자 컨텍스트 함께 사용 통합 테스트"""
    client = AsyncLogClient(log_server_url, batch_size=10, flush_interval=1.0)

    # HTTP 컨텍스트 설정
    AsyncLogClient.set_request_context(
        path="/api/test",
        method="POST",
        ip="192.168.1.100"
    )

    # 사용자 컨텍스트와 함께 사용
    with AsyncLogClient.user_context(
        user_id="combined_user_456",
        trace_id="combined_trace_abc",
        session_id="combined_session_xyz"
    ):
        client.info("Combined contexts test 1", test_id="combined_contexts_integration")
        client.debug("Combined contexts test 2", test_id="combined_contexts_integration")

    # 정리
    AsyncLogClient.clear_request_context()

    # Flush 대기
    time.sleep(2)

    # 서버 통계 확인
    response = requests.get(f"{log_server_url}/stats")
    assert response.status_code == 200

    stats = response.json()
    assert stats['total_logs'] >= 2

    # Note: HTTP와 User 컨텍스트가 모두 DB에 저장되었는지 확인:
    # SELECT
    #   message,
    #   metadata->>'path' as path,
    #   metadata->>'method' as method,
    #   metadata->>'ip' as ip,
    #   metadata->>'user_id' as user_id,
    #   metadata->>'trace_id' as trace_id,
    #   metadata->>'session_id' as session_id
    # FROM logs
    # WHERE metadata->>'test_id' = 'combined_contexts_integration';


def test_user_context_nested_integration(log_server_url, check_server_running):
    """중첩 사용자 컨텍스트 통합 테스트"""
    client = AsyncLogClient(log_server_url, batch_size=10, flush_interval=1.0)

    # 외부 컨텍스트
    with AsyncLogClient.user_context(tenant_id="tenant_integration"):
        client.info("Outer context", test_id="nested_user_context_integration")

        # 내부 컨텍스트
        with AsyncLogClient.user_context(user_id="nested_user_789"):
            client.info("Inner context (both)", test_id="nested_user_context_integration")

        client.info("Back to outer", test_id="nested_user_context_integration")

    # Flush 대기
    time.sleep(2)

    # 서버 통계 확인
    response = requests.get(f"{log_server_url}/stats")
    assert response.status_code == 200

    # Note: 중첩 컨텍스트가 올바르게 저장되었는지 확인:
    # SELECT
    #   message,
    #   metadata->>'tenant_id' as tenant_id,
    #   metadata->>'user_id' as user_id
    # FROM logs
    # WHERE metadata->>'test_id' = 'nested_user_context_integration'
    # ORDER BY created_at;
