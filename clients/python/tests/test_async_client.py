"""
단위 테스트: AsyncLogClient 기본 동작 검증
로그 서버 없이도 실행 가능한 테스트
"""
import pytest
import time
from log_collector import AsyncLogClient


def test_client_initialization():
    """클라이언트 초기화 테스트"""
    client = AsyncLogClient("http://localhost:8000")
    assert client is not None
    assert client.server_url == "http://localhost:8000"


def test_log_queueing():
    """로그 큐잉 테스트 (블로킹 없음)"""
    client = AsyncLogClient("http://localhost:8000", batch_size=1000)

    start = time.time()
    client.log("INFO", "test message", test_id="queue_test")
    elapsed = time.time() - start

    # 앱 블로킹 < 0.001초 확인
    assert elapsed < 0.001, f"Blocking time {elapsed}s exceeded 0.001s"


def test_batch_size_option():
    """배치 크기 옵션 테스트"""
    client = AsyncLogClient("http://localhost:8000", batch_size=500)
    assert client.batch_size == 500


def test_flush_interval_option():
    """Flush 간격 옵션 테스트"""
    client = AsyncLogClient("http://localhost:8000", flush_interval=2.0)
    assert client.flush_interval == 2.0


def test_multiple_log_levels():
    """다양한 로그 레벨 테스트"""
    client = AsyncLogClient("http://localhost:8000", batch_size=100)

    # 다양한 레벨 로그 생성
    client.log("INFO", "info message")
    client.log("WARN", "warning message")
    client.log("ERROR", "error message")
    client.log("DEBUG", "debug message")
    client.log("FATAL", "fatal message")

    # 에러 없이 실행되어야 함
    assert True


def test_metadata_parameters():
    """메타데이터 전달 테스트"""
    client = AsyncLogClient("http://localhost:8000", batch_size=100)

    # 임의의 메타데이터 전달
    client.log("INFO", "test", user_id=123, action="login", success=True)

    # 에러 없이 실행되어야 함
    assert True


def test_service_name_option():
    """서비스 이름 옵션 테스트"""
    client = AsyncLogClient("http://localhost:8000", service="test-service")
    # AsyncLogClient가 service 파라미터를 지원한다면 검증
    # 현재 구현에서는 로그 호출 시 service를 전달
    client.log("INFO", "test", service="custom-service")
    assert True


def test_auto_caller_enabled():
    """호출 위치 자동 추적 테스트 (auto_caller=True)"""
    client = AsyncLogClient("http://localhost:8000", batch_size=100)

    # 로그 호출
    client.info("Test auto caller")

    # 큐에서 로그 확인
    assert len(client.queue) > 0
    log_entry = client.queue[-1]

    # function_name, file_path가 자동으로 포함되었는지 확인
    assert "function_name" in log_entry
    assert "file_path" in log_entry

    # 함수명이 현재 테스트 함수명과 일치하는지 확인
    assert log_entry["function_name"] == "test_auto_caller_enabled"

    # 파일 경로에 test_async_client.py가 포함되는지 확인
    assert "test_async_client.py" in log_entry["file_path"]


def test_auto_caller_disabled():
    """호출 위치 자동 추적 비활성화 테스트 (auto_caller=False)"""
    client = AsyncLogClient("http://localhost:8000", batch_size=100)

    # auto_caller=False로 로그 호출
    client.log("INFO", "Test without auto caller", auto_caller=False)

    # 큐에서 로그 확인
    assert len(client.queue) > 0
    log_entry = client.queue[-1]

    # function_name이 자동으로 추가되지 않았는지 확인
    # (수동으로 전달하지 않았으므로 없어야 함)
    assert "function_name" not in log_entry or log_entry["function_name"] is None


def test_auto_caller_manual_override():
    """호출 위치 수동 재정의 테스트"""
    client = AsyncLogClient("http://localhost:8000", batch_size=100)

    # 수동으로 function_name 전달 (자동 추적보다 우선)
    client.info("Test manual override", function_name="custom_function", file_path="/custom/path.py")

    # 큐에서 로그 확인
    assert len(client.queue) > 0
    log_entry = client.queue[-1]

    # 수동으로 전달한 값이 사용되었는지 확인
    assert log_entry["function_name"] == "custom_function"
    assert log_entry["file_path"] == "/custom/path.py"


def test_convenience_methods_auto_caller():
    """편의 메서드(info, debug 등)에서 호출 위치 자동 추적 테스트"""
    client = AsyncLogClient("http://localhost:8000", batch_size=100)

    # 여러 편의 메서드 테스트
    client.trace("Trace message")
    client.debug("Debug message")
    client.info("Info message")
    client.warn("Warn message")
    client.error("Error message")
    client.fatal("Fatal message")

    # 모든 로그가 큐에 추가되었는지 확인
    assert len(client.queue) == 6

    # 각 로그에 function_name이 포함되었는지 확인
    for log_entry in client.queue:
        assert "function_name" in log_entry
        # 모든 로그가 이 테스트 함수에서 호출되었으므로 함수명 일치
        assert log_entry["function_name"] == "test_convenience_methods_auto_caller"


def test_nested_function_auto_caller():
    """중첩 함수에서 호출 위치 자동 추적 테스트"""
    client = AsyncLogClient("http://localhost:8000", batch_size=100)

    def inner_function():
        client.info("Message from inner function")

    # 내부 함수 호출
    inner_function()

    # 큐에서 로그 확인
    assert len(client.queue) > 0
    log_entry = client.queue[-1]

    # function_name이 inner_function인지 확인
    assert log_entry["function_name"] == "inner_function"


# Feature 3: 사용자 컨텍스트 관리 테스트
def test_user_context_enabled():
    """사용자 컨텍스트 자동 포함 테스트"""
    client = AsyncLogClient("http://localhost:8000", batch_size=100)

    # 컨텍스트 없이 로그
    client.info("Without context")
    log_without_context = client.queue[-1]
    assert "user_id" not in log_without_context
    assert "trace_id" not in log_without_context

    # 컨텍스트 있이 로그
    with AsyncLogClient.user_context(user_id="user_123", trace_id="trace_xyz"):
        client.info("With context")
        log_with_context = client.queue[-1]

        # user_id, trace_id가 자동으로 포함되었는지 확인
        assert log_with_context["user_id"] == "user_123"
        assert log_with_context["trace_id"] == "trace_xyz"
        assert log_with_context["message"] == "With context"


def test_user_context_clear():
    """사용자 컨텍스트 초기화 테스트"""
    client = AsyncLogClient("http://localhost:8000", batch_size=100)

    # with 블록 내에서 컨텍스트 포함
    with AsyncLogClient.user_context(user_id="user_456"):
        client.info("Inside context")
        assert client.queue[-1]["user_id"] == "user_456"

    # with 블록 벗어나면 컨텍스트 자동 초기화
    client.info("Outside context")
    log_outside = client.queue[-1]
    assert "user_id" not in log_outside


def test_user_context_set_clear():
    """set/clear 방식 사용자 컨텍스트 테스트"""
    client = AsyncLogClient("http://localhost:8000", batch_size=100)

    # 컨텍스트 설정
    AsyncLogClient.set_user_context(user_id="user_789", session_id="sess_abc")

    client.info("After set")
    log_after_set = client.queue[-1]
    assert log_after_set["user_id"] == "user_789"
    assert log_after_set["session_id"] == "sess_abc"

    # 컨텍스트 초기화
    AsyncLogClient.clear_user_context()

    client.info("After clear")
    log_after_clear = client.queue[-1]
    assert "user_id" not in log_after_clear
    assert "session_id" not in log_after_clear


def test_user_context_nested():
    """중첩 사용자 컨텍스트 테스트"""
    client = AsyncLogClient("http://localhost:8000", batch_size=100)

    # 외부 컨텍스트: tenant_id
    with AsyncLogClient.user_context(tenant_id="tenant_1"):
        client.info("Outer context")
        outer_log = client.queue[-1]
        assert outer_log["tenant_id"] == "tenant_1"
        assert "user_id" not in outer_log

        # 내부 컨텍스트: user_id 추가
        with AsyncLogClient.user_context(user_id="user_999"):
            client.info("Inner context")
            inner_log = client.queue[-1]
            # tenant_id와 user_id 둘 다 포함되어야 함
            assert inner_log["tenant_id"] == "tenant_1"
            assert inner_log["user_id"] == "user_999"

        # 내부 컨텍스트 벗어나면 user_id 없음
        client.info("Back to outer")
        back_to_outer = client.queue[-1]
        assert back_to_outer["tenant_id"] == "tenant_1"
        assert "user_id" not in back_to_outer


def test_user_context_with_http_context():
    """HTTP 컨텍스트와 사용자 컨텍스트 함께 사용 테스트"""
    client = AsyncLogClient("http://localhost:8000", batch_size=100)

    # HTTP 컨텍스트 설정
    AsyncLogClient.set_request_context(path="/api/users", method="GET", ip="127.0.0.1")

    # 사용자 컨텍스트 설정
    with AsyncLogClient.user_context(user_id="user_combo", trace_id="trace_combo"):
        client.info("Combined contexts")
        log_entry = client.queue[-1]

        # HTTP 컨텍스트 필드
        assert log_entry["path"] == "/api/users"
        assert log_entry["method"] == "GET"
        assert log_entry["ip"] == "127.0.0.1"

        # 사용자 컨텍스트 필드
        assert log_entry["user_id"] == "user_combo"
        assert log_entry["trace_id"] == "trace_combo"

        # 기본 필드
        assert log_entry["message"] == "Combined contexts"

    # 정리
    AsyncLogClient.clear_request_context()


def test_user_context_manual_override():
    """사용자 컨텍스트보다 수동 값이 우선하는지 테스트"""
    client = AsyncLogClient("http://localhost:8000", batch_size=100)

    with AsyncLogClient.user_context(user_id="auto_user"):
        # 수동으로 user_id 전달
        client.info("Manual override", user_id="manual_user")
        log_entry = client.queue[-1]

        # 수동 값이 우선해야 함
        assert log_entry["user_id"] == "manual_user"
