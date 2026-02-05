"""
비동기 로그 클라이언트 - 프로덕션 구성

성능 목표:
- 앱 블로킹: < 0.1ms
- 배치 전송: 5-10ms (압축 사용 시)
- 메모리: < 10MB
- 유실률: < 0.01%
"""

import asyncio
import gzip
import json
import time
import atexit
import traceback
import functools
import os
import inspect
from collections import deque
from threading import Thread, Event
from typing import Dict, Any, Optional, Callable
from contextlib import contextmanager
from contextvars import ContextVar
import aiohttp

try:
    from dotenv import load_dotenv
    load_dotenv()  # .env 파일 자동 로드
except ImportError:
    pass  # python-dotenv 없으면 환경 변수만 사용

# HTTP 요청 컨텍스트 저장용 (웹 프레임워크 통합용)
_request_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar('request_context', default=None)

# 사용자 컨텍스트 저장용 (user_id, trace_id, session_id 등)
_user_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar('user_context', default=None)


class AsyncLogClient:
    """
    비동기 로그 수집 클라이언트

    특징:
    - 로컬 큐 + 백그라운드 스레드
    - 스마트 배치 (1000건 or 1초)
    - 압축 전송 (100건 이상)
    - Graceful shutdown
    - 재시도 로직 (3회)
    - duration_ms 자동 측정
    - stack_trace 자동 추출
    """

    def __init__(
        self,
        server_url: str = None,
        service: Optional[str] = None,
        environment: str = None,
        service_version: str = None,
        log_type: str = None,
        batch_size: int = 1000,
        flush_interval: float = 1.0,
        max_queue_size: int = 10000,
        enable_compression: bool = True,
        max_retries: int = 3,
        enable_global_error_handler: bool = False
    ):
        """
        Args:
            server_url: 로그 서버 URL (기본: 환경 변수 LOG_SERVER_URL)
            service: 서비스 이름 (기본: 환경 변수 SERVICE_NAME)
            environment: 환경 (기본: 환경 변수 ENVIRONMENT 또는 'development')
            service_version: 서비스 버전 (기본: 환경 변수 SERVICE_VERSION 또는 'v0.0.0-dev')
            log_type: 로그 타입 (기본: 환경 변수 LOG_TYPE 또는 'BACKEND')
            batch_size: 배치 크기 (기본: 1000)
            flush_interval: Flush 간격 (초, 기본: 1.0)
            max_queue_size: 최대 큐 크기 (기본: 10000)
            enable_compression: gzip 압축 활성화 (기본: True)
            max_retries: 최대 재시도 횟수 (기본: 3)
            enable_global_error_handler: 글로벌 에러 핸들러 활성화 (기본: False)

        환경 변수 우선순위: 명시적 파라미터 > 환경 변수 > 기본값

        .env 파일 예시:
            LOG_SERVER_URL=http://localhost:8000
            SERVICE_NAME=payment-api
            ENVIRONMENT=production
            SERVICE_VERSION=v1.2.3
            LOG_TYPE=BACKEND
            ENABLE_GLOBAL_ERROR_HANDLER=true
        """
        # 환경 변수에서 자동 로드 (우선순위: 파라미터 > 환경 변수 > 기본값)
        self.server_url = (server_url or os.getenv('LOG_SERVER_URL', 'http://localhost:8000')).rstrip('/')
        self.service = service or os.getenv('SERVICE_NAME')
        self.environment = environment or os.getenv('ENVIRONMENT', 'development')
        self.service_version = service_version or os.getenv('SERVICE_VERSION', 'v0.0.0-dev')
        self.log_type = log_type or os.getenv('LOG_TYPE', 'BACKEND')
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.max_queue_size = max_queue_size
        self.enable_compression = enable_compression
        self.max_retries = max_retries
        self.enable_global_error_handler = enable_global_error_handler or os.getenv('ENABLE_GLOBAL_ERROR_HANDLER', 'false').lower() == 'true'

        self.queue = deque(maxlen=max_queue_size)
        self._stop_event = Event()
        self._worker_thread: Optional[Thread] = None
        self._original_excepthook = None

        # 백그라운드 워커 시작
        self._start_background_worker()

        # Graceful shutdown 등록
        atexit.register(self._graceful_shutdown)

        # 글로벌 에러 핸들러 설정 (옵션)
        if self.enable_global_error_handler:
            self._setup_global_error_handler()

    def log(
        self,
        level: str,
        message: str,
        auto_caller: bool = True,
        **kwargs: Any
    ) -> None:
        """
        로그 추가 (비블로킹, ~0.05ms)

        Args:
            level: 로그 레벨 (TRACE, DEBUG, INFO, WARN, ERROR, FATAL)
            message: 로그 메시지
            auto_caller: 호출 위치 자동 추적 활성화 (기본: True)
            **kwargs: 추가 필드 (trace_id, user_id, duration_ms 등)
        """
        log_entry = {
            "level": level,
            "message": message,
            "created_at": time.time(),
            **kwargs
        }

        # 호출 위치 자동 추적 (function_name, file_path)
        if auto_caller:
            try:
                # 현재 프레임의 호출자 정보 추출
                frame = inspect.currentframe()
                if frame and frame.f_back:
                    caller_frame = frame.f_back
                    log_entry.setdefault("function_name", caller_frame.f_code.co_name)
                    log_entry.setdefault("file_path", caller_frame.f_code.co_filename)
            except Exception:
                # 프레임 추출 실패 시 무시
                pass

        # HTTP 요청 컨텍스트 자동 추가 (웹 프레임워크에서 설정한 경우)
        request_ctx = _request_context.get()
        if request_ctx:
            for key, value in request_ctx.items():
                log_entry.setdefault(key, value)

        # 사용자 컨텍스트 자동 추가 (user_id, trace_id, session_id 등)
        user_ctx = _user_context.get()
        if user_ctx:
            for key, value in user_ctx.items():
                log_entry.setdefault(key, value)

        # 공통 필드 자동 추가
        if self.service:
            log_entry.setdefault("service", self.service)
        if self.environment:
            log_entry.setdefault("environment", self.environment)
        if self.service_version:
            log_entry.setdefault("service_version", self.service_version)
        if self.log_type:
            log_entry.setdefault("log_type", self.log_type)

        # 큐에 추가만 (즉시 리턴!)
        self.queue.append(log_entry)

    def start_timer(self) -> float:
        """
        타이머 시작

        Returns:
            시작 시간 (time.time())

        Example:
            timer = client.start_timer()
            result = expensive_operation()
            client.end_timer(timer, "INFO", "Operation completed")
        """
        return time.time()

    def end_timer(
        self,
        start_time: float,
        level: str,
        message: str,
        **kwargs: Any
    ) -> None:
        """
        타이머 종료 및 로그 전송 (duration_ms 자동 계산)

        Args:
            start_time: start_timer()의 반환값
            level: 로그 레벨
            message: 로그 메시지
            **kwargs: 추가 필드
        """
        duration_ms = (time.time() - start_time) * 1000
        self.log(level, message, duration_ms=duration_ms, **kwargs)

    @contextmanager
    def timer(self, message: str, level: str = "INFO", **kwargs: Any):
        """
        컨텍스트 매니저 타이머 (duration_ms 자동 측정)

        Args:
            message: 로그 메시지
            level: 로그 레벨 (기본: INFO)
            **kwargs: 추가 필드

        Example:
            with client.timer("Database query"):
                result = db.query("SELECT ...")
        """
        start_time = time.time()
        try:
            yield
        finally:
            duration_ms = (time.time() - start_time) * 1000
            self.log(level, message, duration_ms=duration_ms, **kwargs)

    def measure(self, message: Optional[str] = None, level: str = "INFO"):
        """
        함수 실행 시간 측정 데코레이터 (duration_ms 자동 측정)

        Args:
            message: 로그 메시지 (기본: 함수명)
            level: 로그 레벨 (기본: INFO)

        Example:
            @client.measure("Process payment")
            def process_payment(amount):
                return payment_api.charge(amount)
        """
        def decorator(func: Callable) -> Callable:
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                start_time = time.time()
                try:
                    result = func(*args, **kwargs)
                    duration_ms = (time.time() - start_time) * 1000
                    log_message = message or f"{func.__name__} completed"
                    self.log(
                        level,
                        log_message,
                        duration_ms=duration_ms,
                        function_name=func.__name__
                    )
                    return result
                except Exception as e:
                    duration_ms = (time.time() - start_time) * 1000
                    error_message = message or f"{func.__name__} failed"
                    self.error_with_trace(
                        error_message,
                        exception=e,
                        duration_ms=duration_ms,
                        function_name=func.__name__
                    )
                    raise
            return wrapper
        return decorator

    def error_with_trace(
        self,
        message: str,
        exception: Optional[Exception] = None,
        **kwargs: Any
    ) -> None:
        """
        에러 로그 + stack_trace 자동 추출

        Args:
            message: 에러 메시지
            exception: Exception 객체 (선택, 없으면 현재 stack trace)
            **kwargs: 추가 필드

        Example:
            try:
                risky_operation()
            except Exception as e:
                client.error_with_trace("Operation failed", exception=e)
        """
        # Stack trace 추출
        if exception:
            stack_trace_str = ''.join(traceback.format_exception(
                type(exception),
                exception,
                exception.__traceback__
            ))
            error_type = type(exception).__name__
        else:
            stack_trace_str = ''.join(traceback.format_stack())
            error_type = None

        # Stack trace에서 function_name, file_path 자동 추출
        tb_lines = stack_trace_str.strip().split('\n')
        function_name = None
        file_path = None

        # 마지막 호출 위치 파싱
        for line in reversed(tb_lines):
            if 'File "' in line:
                try:
                    # 예: File "/path/to/file.py", line 123, in function_name
                    parts = line.split(',')
                    if len(parts) >= 3:
                        file_path = parts[0].split('"')[1]
                        func_part = parts[2].strip()
                        if func_part.startswith('in '):
                            function_name = func_part[3:].strip()
                        break
                except:
                    pass

        self.log(
            "ERROR",
            message,
            stack_trace=stack_trace_str,
            error_type=error_type,
            function_name=function_name,
            file_path=file_path,
            **kwargs
        )

    # 편의 메서드
    def trace(self, message: str, auto_caller: bool = True, **kwargs: Any) -> None:
        """TRACE 레벨 로그"""
        self._log_with_caller_adjustment("TRACE", message, auto_caller, **kwargs)

    def debug(self, message: str, auto_caller: bool = True, **kwargs: Any) -> None:
        """DEBUG 레벨 로그"""
        self._log_with_caller_adjustment("DEBUG", message, auto_caller, **kwargs)

    def info(self, message: str, auto_caller: bool = True, **kwargs: Any) -> None:
        """INFO 레벨 로그"""
        self._log_with_caller_adjustment("INFO", message, auto_caller, **kwargs)

    def warn(self, message: str, auto_caller: bool = True, **kwargs: Any) -> None:
        """WARN 레벨 로그"""
        self._log_with_caller_adjustment("WARN", message, auto_caller, **kwargs)

    def error(self, message: str, auto_caller: bool = True, **kwargs: Any) -> None:
        """ERROR 레벨 로그"""
        self._log_with_caller_adjustment("ERROR", message, auto_caller, **kwargs)

    def fatal(self, message: str, auto_caller: bool = True, **kwargs: Any) -> None:
        """FATAL 레벨 로그"""
        self._log_with_caller_adjustment("FATAL", message, auto_caller, **kwargs)

    def _log_with_caller_adjustment(
        self,
        level: str,
        message: str,
        auto_caller: bool,
        **kwargs: Any
    ) -> None:
        """
        편의 메서드를 위한 로그 호출 (호출자 프레임 조정)
        편의 메서드를 통해 호출되므로 한 단계 위의 프레임을 추적
        """
        if auto_caller:
            try:
                # 2단계 위의 프레임 추출 (호출자 -> 편의 메서드 -> 이 메서드)
                frame = inspect.currentframe()
                if frame and frame.f_back and frame.f_back.f_back:
                    caller_frame = frame.f_back.f_back
                    kwargs.setdefault("function_name", caller_frame.f_code.co_name)
                    kwargs.setdefault("file_path", caller_frame.f_code.co_filename)
            except Exception:
                pass

        # auto_caller=False로 설정해서 log()에서 중복 추출 방지
        self.log(level, message, auto_caller=False, **kwargs)

    def _start_background_worker(self) -> None:
        """백그라운드 워커 스레드 시작"""
        self._worker_thread = Thread(
            target=self._flush_loop,
            daemon=True,
            name="log-worker"
        )
        self._worker_thread.start()

    def _flush_loop(self) -> None:
        """배치 전송 루프 (백그라운드 스레드)"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        try:
            while not self._stop_event.is_set():
                if len(self.queue) >= self.batch_size:
                    # 1000건 모이면 즉시 전송
                    batch = [self.queue.popleft() for _ in range(self.batch_size)]
                    loop.run_until_complete(self._send_batch(batch))

                elif len(self.queue) > 0:
                    # 1초 지나면 쌓인 것만이라도 전송
                    time.sleep(self.flush_interval)
                    if len(self.queue) > 0:
                        batch = [self.queue.popleft() for _ in range(len(self.queue))]
                        loop.run_until_complete(self._send_batch(batch))
                else:
                    # 큐가 비어있으면 대기
                    time.sleep(0.1)
        finally:
            loop.close()

    async def _send_batch(self, batch: list, retry_count: int = 0) -> None:
        """
        배치 전송 (비동기 HTTP POST)

        Args:
            batch: 로그 배치
            retry_count: 현재 재시도 횟수
        """
        # JSON 직렬화
        payload = json.dumps({"logs": batch})

        # 압축 (100건 이상)
        headers = {"Content-Type": "application/json"}
        if self.enable_compression and len(batch) >= 100:
            payload = gzip.compress(payload.encode())
            headers["Content-Encoding"] = "gzip"

        # HTTP POST
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    f"{self.server_url}/logs",
                    data=payload if isinstance(payload, bytes) else payload.encode(),
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(total=5)
                ) as response:
                    if response.status != 200:
                        raise Exception(f"HTTP {response.status}: {await response.text()}")

        except Exception as e:
            # 재시도 로직
            if retry_count < self.max_retries:
                # Exponential backoff
                await asyncio.sleep(2 ** retry_count)
                await self._send_batch(batch, retry_count + 1)
            else:
                print(f"[Log Client] Final retry failed: {e}")

    def _graceful_shutdown(self) -> None:
        """Graceful shutdown - 앱 종료 시 큐 비우기"""
        if len(self.queue) > 0:
            print(f"[Log Client] Flushing {len(self.queue)} remaining logs...")
            batch = [self.queue.popleft() for _ in range(len(self.queue))]

            # 이벤트 루프 안전하게 처리
            try:
                loop = asyncio.get_running_loop()
                # 이미 실행 중인 루프가 있으면 태스크 생성
                asyncio.create_task(self._send_batch(batch))
            except RuntimeError:
                # 실행 중인 루프가 없으면 새로 생성
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(self._send_batch(batch))
                finally:
                    loop.close()

    def flush(self) -> None:
        """수동 flush - 큐에 있는 모든 로그 즉시 전송"""
        if len(self.queue) > 0:
            batch = [self.queue.popleft() for _ in range(len(self.queue))]
            try:
                loop = asyncio.get_running_loop()
                # 이미 실행 중인 루프가 있으면 태스크 생성
                asyncio.create_task(self._send_batch(batch))
            except RuntimeError:
                # 실행 중인 루프가 없으면 새로 생성
                loop = asyncio.new_event_loop()
                try:
                    loop.run_until_complete(self._send_batch(batch))
                finally:
                    loop.close()

    async def close(self) -> None:
        """클라이언트 종료 (async 메서드)"""
        self._stop_event.set()
        if self._worker_thread and self._worker_thread.is_alive():
            self._worker_thread.join(timeout=5)

        # 남은 로그 전송
        if len(self.queue) > 0:
            print(f"[Log Client] Flushing {len(self.queue)} remaining logs...")
            batch = [self.queue.popleft() for _ in range(len(self.queue))]
            await self._send_batch(batch)

        # 글로벌 에러 핸들러 해제
        if self.enable_global_error_handler:
            self._teardown_global_error_handler()

    def _setup_global_error_handler(self) -> None:
        """
        글로벌 에러 핸들러 설정
        모든 uncaught exceptions를 자동으로 로깅
        """
        import sys

        # 기존 excepthook 저장
        self._original_excepthook = sys.excepthook

        def exception_handler(exc_type, exc_value, exc_traceback):
            # 에러 로깅 (error_type은 error_with_trace가 자동으로 설정)
            self.error_with_trace(
                "Uncaught exception",
                exception=exc_value,
                auto_caller=False
            )

            # 기존 excepthook 호출
            if self._original_excepthook:
                self._original_excepthook(exc_type, exc_value, exc_traceback)

        sys.excepthook = exception_handler

    def _teardown_global_error_handler(self) -> None:
        """글로벌 에러 핸들러 해제"""
        import sys

        if self._original_excepthook:
            sys.excepthook = self._original_excepthook
            self._original_excepthook = None

    # HTTP 요청 컨텍스트 관리 (웹 프레임워크 통합용)
    @staticmethod
    def set_request_context(**context: Any) -> None:
        """
        HTTP 요청 컨텍스트 설정 (웹 프레임워크 미들웨어에서 호출)

        Args:
            **context: HTTP 요청 정보 (path, method, ip 등)

        Example (Flask):
            from flask import request
            AsyncLogClient.set_request_context(
                path=request.path,
                method=request.method,
                ip=request.remote_addr
            )

        Example (FastAPI):
            AsyncLogClient.set_request_context(
                path=request.url.path,
                method=request.method,
                ip=request.client.host
            )
        """
        _request_context.set(context)

    @staticmethod
    def clear_request_context() -> None:
        """
        HTTP 요청 컨텍스트 초기화

        Example:
            AsyncLogClient.clear_request_context()
        """
        _request_context.set(None)

    @staticmethod
    def get_request_context() -> Optional[Dict[str, Any]]:
        """
        현재 HTTP 요청 컨텍스트 조회

        Returns:
            현재 설정된 컨텍스트 또는 None
        """
        return _request_context.get()

    # 사용자 컨텍스트 관리 (user_id, trace_id, session_id 등)
    @staticmethod
    def set_user_context(**context: Any) -> None:
        """
        사용자 컨텍스트 설정 (애플리케이션 코드에서 호출)

        Args:
            **context: 사용자 정보 (user_id, trace_id, session_id, tenant_id 등)

        Example:
            # 인증 후 사용자 ID 설정
            AsyncLogClient.set_user_context(
                user_id="user_12345",
                trace_id="trace_xyz",
                session_id="sess_abc"
            )

            # 이후 모든 로그에 자동으로 포함됨
            logger.info("User action completed")
            # → user_id="user_12345", trace_id="trace_xyz" 자동 포함
        """
        _user_context.set(context)

    @staticmethod
    def clear_user_context() -> None:
        """
        사용자 컨텍스트 초기화

        Example:
            # 로그아웃 시
            AsyncLogClient.clear_user_context()
        """
        _user_context.set(None)

    @staticmethod
    def get_user_context() -> Optional[Dict[str, Any]]:
        """
        현재 사용자 컨텍스트 조회

        Returns:
            현재 설정된 컨텍스트 또는 None
        """
        return _user_context.get()

    @staticmethod
    @contextmanager
    def user_context(**context: Any):
        """
        사용자 컨텍스트 컨텍스트 매니저 (with 문 사용)

        Args:
            **context: 사용자 정보 (user_id, trace_id 등)

        Example:
            # 특정 블록에만 컨텍스트 적용
            with AsyncLogClient.user_context(user_id="user_123", trace_id="trace_xyz"):
                logger.info("Processing user request")
                # → user_id, trace_id 자동 포함
                process_payment()
            # with 블록 벗어나면 컨텍스트 자동 초기화

            # 중첩 컨텍스트도 가능 (병합됨)
            with AsyncLogClient.user_context(tenant_id="tenant_1"):
                with AsyncLogClient.user_context(user_id="user_123"):
                    logger.info("Nested context")
                    # → tenant_id, user_id 둘 다 포함
        """
        # 현재 컨텍스트를 가져와서 새로운 컨텍스트와 병합
        current_context = _user_context.get()
        if current_context:
            # 기존 컨텍스트와 병합 (새로운 값이 우선)
            merged_context = {**current_context, **context}
        else:
            merged_context = context

        token = _user_context.set(merged_context)
        try:
            yield
        finally:
            _user_context.reset(token)
