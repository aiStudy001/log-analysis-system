# 클라이언트 라이브러리 코드 상세 설명

clients 폴더의 Python 및 JavaScript 로그 수집 라이브러리 구현 상세 분석

---

## 📁 디렉토리 구조

```
clients/
├── python/
│   ├── log_collector/
│   │   ├── __init__.py           # 패키지 진입점
│   │   └── async_client.py        # AsyncLogClient 구현
│   ├── setup.py                   # PyPI 패키지 설정
│   ├── test_manual.py             # 수동 테스트 스크립트
│   └── tests/                     # 자동화된 테스트
│       ├── test_async_client.py   # 단위 테스트
│       ├── test_integration.py    # 통합 테스트
│       └── test_performance.py    # 성능 벤치마크
│
└── javascript/
    ├── src/
    │   ├── index.js               # 환경 감지 & 팩토리
    │   ├── node-client.js         # Node.js (Worker Threads)
    │   ├── node-worker.js         # Worker Threads 스크립트
    │   ├── browser-client.js      # 브라우저 (Web Worker)
    │   └── browser-worker.js      # Web Worker 스크립트
    ├── package.json               # npm 패키지 설정
    ├── test-manual.js             # 수동 테스트 스크립트
    └── __tests__/                 # Jest 테스트
        └── client.test.js         # 단위 테스트
```

---

## 🐍 Python 클라이언트 상세 분석

### 파일: `python/log_collector/async_client.py`

#### 아키텍처 개요

```
애플리케이션 (메인 스레드)
    ↓ (deque 큐에 추가, ~0.05ms)
    ↓
로컬 큐 (collections.deque)
    ↓
백그라운드 스레드
    ↓ (비동기 배치 전송)
    ↓
asyncio 이벤트 루프
    ↓ (HTTP POST + gzip)
    ↓
로그 서버
```

**핵심 설계 원칙:**
1. **비블로킹 API**: 앱 코드는 큐에만 추가하고 즉시 리턴 (~0.05ms)
2. **백그라운드 처리**: 별도 스레드에서 배치 전송 처리
3. **스마트 배치**: 1000건 모이면 즉시 전송, 아니면 1초마다 전송
4. **재시도 로직**: Exponential backoff으로 최대 3회 재시도
5. **Graceful Shutdown**: 앱 종료 시 큐에 남은 로그 모두 전송

---

#### 클래스: `AsyncLogClient`

##### 1. 초기화 (`__init__`)

```python
def __init__(
    self,
    server_url: str,
    service: Optional[str] = None,
    environment: str = "development",
    service_version: str = "v0.0.0-dev",
    log_type: str = "BACKEND",
    batch_size: int = 1000,
    flush_interval: float = 1.0,
    max_queue_size: int = 10000,
    enable_compression: bool = True,
    max_retries: int = 3
)
```

**파라미터 설명:**

| 파라미터 | 타입 | 기본값 | 설명 |
|---------|------|--------|------|
| `server_url` | str | 필수 | 로그 서버 URL (예: http://localhost:8000) |
| `service` | str | None | 서비스 이름 (예: payment-api) |
| `environment` | str | "development" | 환경 (production, staging, development, test, local) |
| `service_version` | str | "v0.0.0-dev" | 서비스 버전 (예: v1.2.3) |
| `log_type` | str | "BACKEND" | 로그 타입 (BACKEND, FRONTEND, MOBILE, IOT, WORKER) |
| `batch_size` | int | 1000 | 배치 크기 (몇 개씩 모아서 전송) |
| `flush_interval` | float | 1.0 | Flush 간격 (초) |
| `max_queue_size` | int | 10000 | 최대 큐 크기 (메모리 보호) |
| `enable_compression` | bool | True | gzip 압축 활성화 (100건 이상) |
| `max_retries` | int | 3 | 최대 재시도 횟수 |

**초기화 과정:**

```python
# 1. 설정 저장
self.server_url = server_url.rstrip('/')
self.service = service
self.environment = environment
# ...

# 2. 로컬 큐 생성 (maxlen으로 메모리 보호)
self.queue = deque(maxlen=max_queue_size)

# 3. 백그라운드 워커 스레드 시작
self._worker_thread = Thread(
    target=self._flush_loop,
    daemon=True,  # 메인 프로세스 종료 시 자동 종료
    name="log-worker"
)
self._worker_thread.start()

# 4. Graceful shutdown 등록
atexit.register(self._graceful_shutdown)
```

---

##### 2. 기본 로깅 메서드

###### `log(level, message, **kwargs)`

**핵심 메서드 - 모든 로그의 진입점**

```python
def log(self, level: str, message: str, **kwargs: Any) -> None:
    log_entry = {
        "level": level,
        "message": message,
        "created_at": time.time(),
        **kwargs
    }

    # 공통 필드 자동 추가 (초기화 시 설정한 값)
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
```

**동작 원리:**
1. 로그 엔트리 딕셔너리 생성
2. 공통 필드 자동 추가 (service, environment 등)
3. `deque.append()` 호출 (O(1), ~0.05ms)
4. 즉시 리턴 → 앱 블로킹 없음

**사용 예시:**

```python
# 기본 로그
client.log("INFO", "User logged in", user_id="12345")

# 공통 필드 자동 포함됨
# → { level: "INFO", message: "...", user_id: "12345",
#     service: "payment-api", environment: "production" }

# 편의 메서드 사용
client.info("Payment processed", amount=100.50, currency="USD")
client.warn("High memory usage", memory_mb=850)
client.error("Database timeout", query="SELECT ...", timeout_ms=5000)
```

---

##### 3. 타이머 기능 (duration_ms 자동 측정)

###### A. `start_timer()` / `end_timer()`

**수동 타이머 패턴**

```python
def start_timer(self) -> float:
    """타이머 시작 - 현재 시간 반환"""
    return time.time()

def end_timer(
    self,
    start_time: float,
    level: str,
    message: str,
    **kwargs: Any
) -> None:
    """타이머 종료 - duration_ms 자동 계산 후 로그"""
    duration_ms = (time.time() - start_time) * 1000
    self.log(level, message, duration_ms=duration_ms, **kwargs)
```

**사용 예시:**

```python
# 데이터베이스 쿼리 시간 측정
timer = client.start_timer()
result = db.query("SELECT * FROM users WHERE id = ?", user_id)
client.end_timer(timer, "INFO", "Database query completed",
                 query="SELECT users", rows=len(result))

# 전송되는 로그:
# {
#   "level": "INFO",
#   "message": "Database query completed",
#   "duration_ms": 45.23,  ← 자동 계산
#   "query": "SELECT users",
#   "rows": 100
# }
```

---

###### B. `timer()` 컨텍스트 매니저

**with 문 패턴 (추천 ⭐)**

```python
@contextmanager
def timer(self, message: str, level: str = "INFO", **kwargs: Any):
    """컨텍스트 매니저 - 블록 실행 시간 자동 측정"""
    start_time = time.time()
    try:
        yield
    finally:
        duration_ms = (time.time() - start_time) * 1000
        self.log(level, message, duration_ms=duration_ms, **kwargs)
```

**사용 예시:**

```python
# API 호출 시간 측정
with client.timer("External API call", api="payment-gateway"):
    response = requests.post(
        "https://api.payment.com/charge",
        json={"amount": 100.50}
    )

# 전송되는 로그:
# {
#   "level": "INFO",
#   "message": "External API call",
#   "duration_ms": 342.15,  ← 자동 계산
#   "api": "payment-gateway"
# }

# 에러 발생 시에도 로그 전송됨
with client.timer("Risky operation", level="WARN"):
    risky_function()  # 예외 발생해도 duration_ms 기록됨
```

---

###### C. `measure()` 데코레이터

**함수 실행 시간 자동 측정**

```python
def measure(self, message: Optional[str] = None, level: str = "INFO"):
    """데코레이터 - 함수 실행 시간 자동 측정"""
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
```

**사용 예시:**

```python
# 비즈니스 로직 함수 측정
@client.measure("Process payment")
def process_payment(user_id, amount):
    # 결제 로직
    payment_api.charge(user_id, amount)
    return {"status": "success"}

# 함수 호출
result = process_payment("user123", 100.50)

# 성공 시 자동으로 로그:
# {
#   "level": "INFO",
#   "message": "Process payment",
#   "duration_ms": 234.56,
#   "function_name": "process_payment"
# }

# 실패 시 자동으로 에러 로그 (stack trace 포함):
# {
#   "level": "ERROR",
#   "message": "Process payment",
#   "duration_ms": 123.45,
#   "function_name": "process_payment",
#   "stack_trace": "Traceback (most recent call last)...",
#   "error_type": "PaymentError"
# }
```

---

##### 4. 에러 처리 기능

###### `error_with_trace(message, exception, **kwargs)`

**stack_trace 자동 추출 및 파싱**

```python
def error_with_trace(
    self,
    message: str,
    exception: Optional[Exception] = None,
    **kwargs: Any
) -> None:
    """에러 로그 + stack_trace 자동 추출"""

    # 1. Stack trace 추출
    if exception:
        stack_trace_str = ''.join(traceback.format_exception(
            type(exception),
            exception,
            exception.__traceback__
        ))
        error_type = type(exception).__name__
    else:
        # exception 없으면 현재 콜 스택 캡처
        stack_trace_str = ''.join(traceback.format_stack())
        error_type = None

    # 2. Stack trace 파싱 - function_name, file_path 추출
    tb_lines = stack_trace_str.strip().split('\n')
    function_name = None
    file_path = None

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

    # 3. 로그 전송
    self.log(
        "ERROR",
        message,
        stack_trace=stack_trace_str,
        error_type=error_type,
        function_name=function_name,
        file_path=file_path,
        **kwargs
    )
```

**사용 예시:**

```python
# 예외 처리 시 자동으로 stack trace 추출
try:
    result = risky_database_operation()
except DatabaseError as e:
    client.error_with_trace(
        "Database operation failed",
        exception=e,
        query="UPDATE users SET ...",
        user_id="12345"
    )

# 전송되는 로그:
# {
#   "level": "ERROR",
#   "message": "Database operation failed",
#   "stack_trace": "Traceback (most recent call last):\n  File \"/app/db.py\", line 45, in execute\n    ...",
#   "error_type": "DatabaseError",
#   "function_name": "execute",
#   "file_path": "/app/db.py",
#   "query": "UPDATE users SET ...",
#   "user_id": "12345"
# }
```

---

##### 5. 백그라운드 워커

###### `_flush_loop()` - 배치 전송 루프

```python
def _flush_loop(self) -> None:
    """배치 전송 루프 (백그라운드 스레드에서 실행)"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        while not self._stop_event.is_set():
            # 케이스 1: 배치 크기 도달 (1000건)
            if len(self.queue) >= self.batch_size:
                batch = [self.queue.popleft() for _ in range(self.batch_size)]
                loop.run_until_complete(self._send_batch(batch))

            # 케이스 2: Flush 간격 도달 (1초)
            elif len(self.queue) > 0:
                time.sleep(self.flush_interval)
                if len(self.queue) > 0:
                    batch = [self.queue.popleft() for _ in range(len(self.queue))]
                    loop.run_until_complete(self._send_batch(batch))

            # 케이스 3: 큐 비어있음
            else:
                time.sleep(0.1)
    finally:
        loop.close()
```

**동작 원리:**

1. **배치 크기 우선**: 큐에 1000건 이상 쌓이면 즉시 전송
2. **시간 간격 보장**: 1초마다 체크해서 남은 로그 전송
3. **대기 모드**: 큐가 비어있으면 0.1초 대기 (CPU 절약)

---

###### `_send_batch(batch, retry_count)` - 실제 전송

```python
async def _send_batch(self, batch: list, retry_count: int = 0) -> None:
    """배치 전송 (비동기 HTTP POST)"""

    # 1. JSON 직렬화
    payload = json.dumps({"logs": batch})

    # 2. 압축 (100건 이상일 때)
    headers = {"Content-Type": "application/json"}
    if self.enable_compression and len(batch) >= 100:
        payload = gzip.compress(payload.encode())
        headers["Content-Encoding"] = "gzip"

    # 3. HTTP POST
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.server_url}/logs",
                data=payload if isinstance(payload, bytes) else payload.encode(),
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=5)
            ) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")

    # 4. 재시도 로직 (Exponential Backoff)
    except Exception as e:
        if retry_count < self.max_retries:
            await asyncio.sleep(2 ** retry_count)  # 1초, 2초, 4초
            await self._send_batch(batch, retry_count + 1)
        else:
            print(f"[Log Client] Final retry failed: {e}")
```

**재시도 전략:**

| 시도 | 대기 시간 | 설명 |
|-----|----------|------|
| 1차 실패 | 1초 대기 | `2^0 = 1초` |
| 2차 실패 | 2초 대기 | `2^1 = 2초` |
| 3차 실패 | 4초 대기 | `2^2 = 4초` |
| 최종 실패 | 포기 | 로그 유실, 콘솔 경고 |

---

##### 6. Graceful Shutdown

###### `_graceful_shutdown()` - 종료 시 큐 비우기

```python
def _graceful_shutdown(self) -> None:
    """앱 종료 시 큐에 남은 로그 모두 전송"""
    if len(self.queue) > 0:
        print(f"[Log Client] Flushing {len(self.queue)} remaining logs...")
        batch = [self.queue.popleft() for _ in range(len(self.queue))]

        # 동기적으로 전송 (atexit에서는 비동기 불가)
        loop = asyncio.new_event_loop()
        try:
            loop.run_until_complete(self._send_batch(batch))
        finally:
            loop.close()
```

**등록 방법:**

```python
# __init__에서 자동 등록
atexit.register(self._graceful_shutdown)

# 프로세스 종료 시 자동 호출:
# - 정상 종료 (sys.exit)
# - KeyboardInterrupt (Ctrl+C)
# - 예외로 인한 종료
```

---

## 🌐 JavaScript 클라이언트 상세 분석

### 파일: `javascript/src/index.js`

#### 환경 자동 감지 팩토리

```javascript
export function createLogClient(serverUrl, options = {}) {
    // 브라우저 환경 감지
    if (typeof window !== 'undefined' && typeof Worker !== 'undefined') {
        const { WebWorkerLogClient } = require('./browser-client');
        return new WebWorkerLogClient(serverUrl, options);
    }
    // Node.js 환경 감지
    else if (typeof process !== 'undefined' && process.versions && process.versions.node) {
        const { WorkerThreadsLogClient } = require('./node-client');
        return new WorkerThreadsLogClient(serverUrl, options);
    }
    else {
        throw new Error('Unsupported environment');
    }
}
```

**동작 원리:**
- `window` 존재 → 브라우저 → `WebWorkerLogClient` 사용
- `process.versions.node` 존재 → Node.js → `WorkerThreadsLogClient` 사용
- 환경에 최적화된 구현 자동 선택

---

### 파일: `javascript/src/node-client.js`

#### Node.js 아키텍처 (Worker Threads)

```
메인 스레드 (애플리케이션)
    ↓ (postMessage, ~0.01ms)
    ↓
Worker Thread
    ↓ (배치 전송 로직)
    ↓
HTTP POST (fetch API)
    ↓
로그 서버
```

**핵심 차이점 (vs Python):**
- Python: 백그라운드 Thread + asyncio
- Node.js: Worker Threads (완전 격리된 V8 인스턴스)

---

#### 클래스: `WorkerThreadsLogClient`

##### 1. 초기화

```javascript
constructor(serverUrl, options = {}) {
    this.serverUrl = serverUrl;
    this.service = options.service || null;
    this.environment = options.environment || 'development';
    this.serviceVersion = options.serviceVersion || 'v0.0.0-dev';
    this.logType = options.logType || 'BACKEND';

    this.options = {
        batchSize: options.batchSize || 1000,
        flushInterval: options.flushInterval || 1000,
        enableCompression: options.enableCompression !== false
    };

    // Worker Threads 생성
    this._createWorker();

    // Graceful shutdown 설정
    this._setupGracefulShutdown();
}
```

**Worker Thread 생성:**

```javascript
_createWorker() {
    this.worker = new Worker(
        path.join(__dirname, 'node-worker.js'),
        {
            workerData: {
                serverUrl: this.serverUrl,
                ...this.options
            }
        }
    );

    // 에러 핸들링
    this.worker.on('error', (error) => {
        console.error('[Log Client] Worker error:', error);
    });
}
```

---

##### 2. 로깅 메서드

```javascript
log(level, message, metadata = {}) {
    if (!this.worker) {
        console.warn('[Log Client] Worker not initialized');
        return;
    }

    // 공통 필드 자동 추가
    const logEntry = {
        level,
        message,
        created_at: Date.now(),
        ...metadata
    };

    if (this.service) logEntry.service = logEntry.service || this.service;
    if (this.environment) logEntry.environment = logEntry.environment || this.environment;
    if (this.serviceVersion) logEntry.service_version = logEntry.service_version || this.serviceVersion;
    if (this.logType) logEntry.log_type = logEntry.log_type || this.logType;

    // Worker로 메시지 전달 (즉시 리턴!)
    this.worker.postMessage({
        type: 'log',
        data: logEntry
    });
}
```

**사용 예시:**

```javascript
const { createLogClient } = require('log-collector');

const logger = createLogClient('http://localhost:8000', {
    service: 'payment-api',
    environment: 'production',
    serviceVersion: 'v1.2.3'
});

// 기본 로그
logger.info('User logged in', { user_id: '12345' });

// 공통 필드 자동 포함:
// {
//   level: "INFO",
//   message: "User logged in",
//   user_id: "12345",
//   service: "payment-api",
//   environment: "production",
//   service_version: "v1.2.3",
//   log_type: "BACKEND"
// }
```

---

##### 3. 타이머 기능

###### A. `startTimer()` / `endTimer()`

```javascript
startTimer() {
    return Date.now();
}

endTimer(startTime, level, message, metadata = {}) {
    const durationMs = Date.now() - startTime;
    this.log(level, message, { ...metadata, duration_ms: durationMs });
}
```

**사용 예시:**

```javascript
// API 호출 시간 측정
const timer = logger.startTimer();
const response = await fetch('https://api.example.com/data');
const data = await response.json();
logger.endTimer(timer, 'INFO', 'API call completed', {
    endpoint: '/data',
    status: response.status
});
```

---

###### B. `measure()` 함수 래퍼

```javascript
measure(fn, message = null, level = 'INFO') {
    const startTime = this.startTimer();
    const functionName = fn.name || 'anonymous';

    try {
        const result = fn();

        // Promise 처리 (async 함수 지원)
        if (result && typeof result.then === 'function') {
            return result
                .then(res => {
                    const durationMs = Date.now() - startTime;
                    this.log(level, message || `${functionName} completed`, {
                        duration_ms: durationMs,
                        function_name: functionName
                    });
                    return res;
                })
                .catch(err => {
                    const durationMs = Date.now() - startTime;
                    this.errorWithTrace(
                        message || `${functionName} failed`,
                        err,
                        { duration_ms: durationMs, function_name: functionName }
                    );
                    throw err;
                });
        }

        // 동기 함수 처리
        const durationMs = Date.now() - startTime;
        this.log(level, message || `${functionName} completed`, {
            duration_ms: durationMs,
            function_name: functionName
        });
        return result;

    } catch (err) {
        const durationMs = Date.now() - startTime;
        this.errorWithTrace(
            message || `${functionName} failed`,
            err,
            { duration_ms: durationMs, function_name: functionName }
        );
        throw err;
    }
}
```

**사용 예시:**

```javascript
// 동기 함수 측정
const result = logger.measure(
    () => processPayment(userId, amount),
    'Payment processing'
);

// async 함수 측정
const data = await logger.measure(
    async () => {
        const response = await fetch('/api/users');
        return response.json();
    },
    'Fetch users'
);

// 자동으로 로그:
// {
//   level: "INFO",
//   message: "Fetch users",
//   duration_ms: 234.5,
//   function_name: "async"
// }
```

---

##### 4. 에러 처리

```javascript
errorWithTrace(message, error = null, metadata = {}) {
    let stackTrace = null;
    let errorType = null;
    let functionName = null;
    let filePath = null;

    if (error && error.stack) {
        stackTrace = error.stack;
        errorType = error.name || 'Error';

        // Stack trace 파싱
        const stackLines = stackTrace.split('\n');
        for (const line of stackLines) {
            // Node.js 스타일: "at functionName (/path/to/file.js:123:45)"
            const match = line.match(/at\s+([^\s]+)\s+\(([^:]+):(\d+):(\d+)\)/);
            if (match) {
                functionName = match[1];
                filePath = match[2];
                break;
            }
            // 단순 형식: "at /path/to/file.js:123:45"
            const simpleMatch = line.match(/at\s+([^:]+):(\d+):(\d+)/);
            if (simpleMatch) {
                filePath = simpleMatch[1];
                break;
            }
        }
    } else {
        // 현재 stack trace 캡처
        const err = new Error();
        stackTrace = err.stack;
    }

    this.log('ERROR', message, {
        ...metadata,
        stack_trace: stackTrace,
        error_type: errorType,
        function_name: functionName,
        file_path: filePath
    });
}
```

**사용 예시:**

```javascript
try {
    await riskyDatabaseOperation();
} catch (err) {
    logger.errorWithTrace('Database operation failed', err, {
        query: 'SELECT * FROM users',
        user_id: '12345'
    });
}

// 전송되는 로그:
// {
//   level: "ERROR",
//   message: "Database operation failed",
//   stack_trace: "Error: Connection timeout\n    at Database.connect (/app/db.js:45:15)\n    ...",
//   error_type: "Error",
//   function_name: "Database.connect",
//   file_path: "/app/db.js",
//   query: "SELECT * FROM users",
//   user_id: "12345"
// }
```

---

##### 5. Graceful Shutdown

```javascript
_setupGracefulShutdown() {
    const shutdownHandler = () => {
        this.flush();
        setTimeout(() => {
            if (this.worker) {
                this.worker.terminate();
            }
        }, 100);
    };

    process.on('exit', shutdownHandler);
    process.on('SIGINT', shutdownHandler);  // Ctrl+C
    process.on('SIGTERM', shutdownHandler); // kill
}
```

---

### 파일: `javascript/src/browser-client.js`

#### 브라우저 아키텍처 (Web Worker)

```
메인 스레드 (UI)
    ↓ (postMessage, ~0.01ms)
    ↓
Web Worker (별도 스레드)
    ↓ (배치 전송 로직)
    ↓
fetch API
    ↓
로그 서버
```

**핵심 장점:**
- UI 스레드 완전 격리
- 렌더링 성능 0% 영향
- 백그라운드에서 배치 처리

---

#### 클래스: `WebWorkerLogClient`

##### 초기화 (브라우저 특화)

```javascript
constructor(serverUrl, options = {}) {
    this.serverUrl = serverUrl;
    this.service = options.service || null;
    this.environment = options.environment || 'development';
    this.serviceVersion = options.serviceVersion || 'v0.0.0-dev';
    this.logType = options.logType || 'FRONTEND';  // ← 기본값이 FRONTEND

    // ... 나머지는 Node.js 클라이언트와 동일
}
```

**Web Worker 생성:**

```javascript
_createWorker() {
    this.worker = new Worker(
        new URL('./browser-worker.js', import.meta.url),
        { type: 'module' }
    );

    // Worker 초기화
    this.worker.postMessage({
        type: 'init',
        serverUrl: this.serverUrl,
        ...this.options
    });
}
```

---

##### Graceful Shutdown (브라우저 특화)

```javascript
_setupGracefulShutdown() {
    // 브라우저 종료 시
    window.addEventListener('beforeunload', () => {
        this.flush();
    });

    // 탭 전환/최소화 시 (모바일 대응)
    document.addEventListener('visibilitychange', () => {
        if (document.hidden) {
            this.flush();
        }
    });
}
```

**브라우저 이벤트 처리:**

| 이벤트 | 트리거 | 동작 |
|-------|--------|------|
| `beforeunload` | 탭 닫기, 새로고침 | 큐 flush |
| `visibilitychange` | 탭 전환, 최소화 | hidden → flush |

---

##### 사용 예시 (브라우저)

```javascript
import { createLogClient } from 'log-collector';

// 자동으로 WebWorkerLogClient 생성
const logger = createLogClient('http://localhost:8000', {
    service: 'web-app',
    environment: 'production',
    serviceVersion: 'v2.1.0',
    logType: 'FRONTEND'
});

// 사용자 인터랙션 로깅
document.getElementById('loginBtn').addEventListener('click', () => {
    const timer = logger.startTimer();

    login(username, password)
        .then(() => {
            logger.endTimer(timer, 'INFO', 'Login successful', {
                user_id: username,
                method: 'password'
            });
        })
        .catch((err) => {
            logger.errorWithTrace('Login failed', err, {
                user_id: username,
                method: 'password'
            });
        });
});

// 페이지 로드 시간 측정
window.addEventListener('load', () => {
    const loadTime = performance.timing.loadEventEnd - performance.timing.navigationStart;
    logger.info('Page loaded', {
        duration_ms: loadTime,
        page: window.location.pathname
    });
});
```

---

## 📊 성능 특성 비교

### Python vs JavaScript 클라이언트

| 특성 | Python | JavaScript (Node) | JavaScript (Browser) |
|-----|--------|------------------|---------------------|
| **블로킹 시간** | ~0.05ms | ~0.01ms | ~0.01ms |
| **백그라운드 처리** | Thread + asyncio | Worker Threads | Web Worker |
| **메모리 격리** | 부분 (GIL) | 완전 격리 | 완전 격리 |
| **배치 크기** | 1000 (기본) | 1000 (기본) | 1000 (기본) |
| **Flush 간격** | 1.0초 (기본) | 1.0초 (기본) | 1.0초 (기본) |
| **압축 임계값** | 100건 이상 | 100건 이상 | 100건 이상 |
| **재시도 전략** | Exponential backoff | Exponential backoff | Exponential backoff |

---

## 🎯 사용 패턴 요약

### 1. 기본 로깅

```python
# Python
client = AsyncLogClient("http://localhost:8000")
client.info("User action", user_id="123")
```

```javascript
// JavaScript
const logger = createLogClient('http://localhost:8000');
logger.info('User action', { user_id: '123' });
```

---

### 2. 초기화 옵션

```python
# Python - 프로덕션 설정
client = AsyncLogClient(
    "http://logs.company.com",
    service="payment-api",
    environment="production",
    service_version="v1.2.3",
    log_type="BACKEND",
    batch_size=1000,
    flush_interval=1.0,
    enable_compression=True
)
```

```javascript
// JavaScript - 프로덕션 설정
const logger = createLogClient('http://logs.company.com', {
    service: 'web-app',
    environment: 'production',
    serviceVersion: 'v2.1.0',
    logType: 'FRONTEND',
    batchSize: 1000,
    flushInterval: 1000,
    enableCompression: true
});
```

---

### 3. duration_ms 자동 측정

```python
# Python - 수동 타이머
timer = client.start_timer()
result = expensive_operation()
client.end_timer(timer, "INFO", "Operation completed")

# Python - 컨텍스트 매니저 (추천)
with client.timer("Database query"):
    result = db.query("SELECT ...")

# Python - 데코레이터
@client.measure("Process payment")
def process_payment(amount):
    return payment_api.charge(amount)
```

```javascript
// JavaScript - 수동 타이머
const timer = logger.startTimer();
const result = expensiveOperation();
logger.endTimer(timer, 'INFO', 'Operation completed');

// JavaScript - 함수 래퍼
const result = logger.measure(
    () => expensiveOperation(),
    'Operation completed'
);

// JavaScript - async 지원
const data = await logger.measure(
    async () => fetch('/api/data').then(r => r.json()),
    'Fetch data'
);
```

---

### 4. stack_trace 자동 추출

```python
# Python
try:
    risky_operation()
except Exception as e:
    client.error_with_trace("Operation failed", exception=e)
```

```javascript
// JavaScript
try {
    riskyOperation();
} catch (err) {
    logger.errorWithTrace('Operation failed', err);
}
```

---

## 🔍 Worker 구현 상세

### Python Worker (백그라운드 스레드)

**특징:**
- `threading.Thread` 사용
- `asyncio` 이벤트 루프 생성
- GIL 영향 (I/O 작업이라 문제 없음)

**배치 전송 로직:**

```python
while not self._stop_event.is_set():
    if len(self.queue) >= self.batch_size:
        # 배치 크기 도달 → 즉시 전송
        batch = [self.queue.popleft() for _ in range(self.batch_size)]
        loop.run_until_complete(self._send_batch(batch))

    elif len(self.queue) > 0:
        # 1초 대기 후 남은 로그 전송
        time.sleep(self.flush_interval)
        if len(self.queue) > 0:
            batch = [self.queue.popleft() for _ in range(len(self.queue))]
            loop.run_until_complete(self._send_batch(batch))

    else:
        # 큐 비어있음 → 0.1초 대기
        time.sleep(0.1)
```

---

### JavaScript Worker (Worker Threads / Web Worker)

**node-worker.js (Node.js):**

```javascript
const { parentPort, workerData } = require('worker_threads');

let queue = [];
const { batchSize, flushInterval, serverUrl } = workerData;

// 메시지 수신
parentPort.on('message', (msg) => {
    if (msg.type === 'log') {
        queue.push(msg.data);

        // 배치 크기 도달 → 즉시 전송
        if (queue.length >= batchSize) {
            sendBatch();
        }
    }
    else if (msg.type === 'flush') {
        sendBatch();
    }
});

// 주기적 flush
setInterval(() => {
    if (queue.length > 0) {
        sendBatch();
    }
}, flushInterval);

function sendBatch() {
    if (queue.length === 0) return;

    const batch = queue.splice(0, batchSize);

    // HTTP POST (fetch API)
    fetch(`${serverUrl}/logs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ logs: batch })
    })
    .catch(err => console.error('[Worker] Send failed:', err));
}
```

**browser-worker.js (브라우저):**

- `importScripts()` 대신 ES modules 사용
- `self.onmessage`로 메시지 수신
- `self.postMessage()`로 응답 전송
- 나머지 로직은 Node.js와 동일

---

## 🚀 최적화 기법

### 1. 메모리 관리

**Python:**
```python
self.queue = deque(maxlen=max_queue_size)  # maxlen으로 메모리 보호
```

**JavaScript:**
```javascript
if (queue.length > maxQueueSize) {
    queue.shift();  // 오래된 로그 제거
}
```

---

### 2. 압축 전략

**Python:**
```python
if self.enable_compression and len(batch) >= 100:
    payload = gzip.compress(payload.encode())
    headers["Content-Encoding"] = "gzip"
```

**압축 효과:**
- 100건 배치: ~10KB → ~2KB (80% 절감)
- 1000건 배치: ~100KB → ~15KB (85% 절감)

---

### 3. 재시도 로직

**Exponential Backoff:**
- 1차 실패: 1초 대기 (`2^0`)
- 2차 실패: 2초 대기 (`2^1`)
- 3차 실패: 4초 대기 (`2^2`)
- 최종 포기

**장점:**
- 서버 과부하 시 부하 분산
- 일시적 네트워크 오류 대응

---

## 📝 트러블슈팅

### Q1: 로그가 전송되지 않음

**체크리스트:**
1. 로그 서버 실행 중? → `curl http://localhost:8000/`
2. 배치 크기에 도달했거나 1초 경과? → `flush()` 호출
3. Worker가 생성됨? → 콘솔 에러 확인
4. 네트워크 연결? → 서버 로그 확인

**강제 전송:**
```python
# Python
client.flush()
```

```javascript
// JavaScript
logger.flush();
```

---

### Q2: 성능이 목표에 미달

**Python 목표:**
- 블로킹: < 0.1ms
- 처리량: > 5,000 logs/sec

**확인 방법:**
```python
import time

start = time.time()
for i in range(1000):
    client.log("INFO", f"Test {i}")
elapsed = time.time() - start

print(f"Per log: {elapsed/1000*1000:.3f}ms")  # 목표: < 0.1ms
```

**개선 방법:**
- `batch_size` 증가 (1000 → 2000)
- `flush_interval` 증가 (1.0 → 2.0)
- 압축 비활성화 (작은 로그일 때)

---

### Q3: Worker가 생성되지 않음

**Node.js:**
```javascript
// 에러 확인
worker.on('error', (err) => {
    console.error('Worker error:', err);
});
```

**브라우저:**
```javascript
// CORS 정책 확인
// Worker 파일이 같은 origin에 있어야 함
```

---

## 🎓 권장 사항

### 프로덕션 설정

**Python:**
```python
client = AsyncLogClient(
    "https://logs.company.com",
    service="my-service",
    environment="production",
    service_version="v1.2.3",
    batch_size=1000,
    flush_interval=1.0,
    enable_compression=True,
    max_retries=3
)
```

**JavaScript:**
```javascript
const logger = createLogClient('https://logs.company.com', {
    service: 'my-service',
    environment: 'production',
    serviceVersion: 'v1.2.3',
    batchSize: 1000,
    flushInterval: 1000,
    enableCompression: true
});
```

---

### 개발 환경 설정

**빠른 피드백:**
```python
# Python - 작은 배치, 짧은 간격
client = AsyncLogClient(
    "http://localhost:8000",
    batch_size=10,
    flush_interval=0.5
)
```

```javascript
// JavaScript - 작은 배치, 짧은 간격
const logger = createLogClient('http://localhost:8000', {
    batchSize: 10,
    flushInterval: 500
});
```

---

## 📚 추가 리소스

- [CLIENT-LIBRARIES.md](./CLIENT-LIBRARIES.md) - API 사용법 및 예제
- [TESTING-GUIDE.md](./TESTING-GUIDE.md) - 테스트 방법 및 환경 설정
- [DEPLOYMENT-GUIDE.md](./DEPLOYMENT-GUIDE.md) - PyPI/npm 배포 가이드
- [API-TEST-GUIDE.md](../API-TEST-GUIDE.md) - 서버 API 테스트 방법
