# Log Collector - Python Client

고성능 비동기 로그 수집 클라이언트 for Python

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 📋 Prerequisites

Before using this library, ensure you have:

- **Python 3.8+** installed
- **Package manager**: pip
- **Log server running**: See [Log Save Server Setup](../../services/log-save-server/README.md)
- **PostgreSQL database**: For log storage (v12+)
- **Basic async knowledge**: Understanding of threading and queue patterns

## 🎯 Why Use This Library?

### The Problem
Traditional logging blocks your application, creating performance bottlenecks:
- Each log = 1 HTTP request = ~50ms blocked time
- 100 logs/sec = 5 seconds of blocking per second (impossible!)
- Application threads wait for network I/O
- Database connection pool exhaustion

### The Solution
Asynchronous batch logging with zero blocking:
- ✅ **~0.1ms per log** - App never blocks waiting for network
- ✅ **Batches 1000 logs** - Single HTTP request instead of 1000
- ✅ **Background thread** - Separate daemon thread handles transmission
- ✅ **Auto compression** - gzip reduces bandwidth by ~70%
- ✅ **Reliable delivery** - Automatic retries with exponential backoff
- ✅ **Graceful shutdown** - Flushes queue before exit, zero log loss

### When to Use This
- High-traffic applications (>100 requests/sec)
- Performance-critical paths where blocking is unacceptable
- Microservices needing centralized structured logging
- Distributed tracing across services
- PostgreSQL-based log analysis and querying

### When NOT to Use This
- Low-traffic apps (<10 req/sec) - simple file logging is fine
- Quick debugging sessions - use print() for speed
- Need real-time log streaming - use dedicated streaming solutions
- Cannot run log server infrastructure - use cloud logging services

## 🚀 Quick Start (30 seconds)

### Step 1: Install
```bash
pip install log-collector-async
```

### Step 2: Use in your app
```python
from log_collector import AsyncLogClient

# Initialize logger
logger = AsyncLogClient("http://localhost:8000")

# Send logs - non-blocking, ~0.1ms
logger.info("Hello world!", user_id="123", action="test")
logger.warn("High memory usage", memory_mb=512)
logger.error("Database error", error="connection timeout")

# Logs are batched and sent automatically every 1 second or 1000 logs
```

### Step 3: Check logs in database
```bash
psql -h localhost -U postgres -d logs_db \
  -c "SELECT * FROM logs ORDER BY created_at DESC LIMIT 5;"
```

**Want more details?** See [Framework Integration](#-feature-2-http-컨텍스트-자동-수집) below.

**Want a working example?** Check out [Demo Applications](#-live-demo).

## 📺 Live Demo

See working examples with full context tracking:

### Python + FastAPI
- **Location**: [tests/demo-app/backend-python/](../../tests/demo-app/backend-python/)
- **Features**: Login, CRUD operations, error handling, slow API testing
- **Run**: `python tests/demo-app/backend-python/server.py`

### JavaScript + Express
- **Location**: [tests/demo-app/backend/](../../tests/demo-app/backend/)
- **Features**: Same features but with JavaScript
- **Run**: `node tests/demo-app/backend/server.js`

### Frontend Integration
- **Location**: [tests/demo-app/frontend/](../../tests/demo-app/frontend/)
- **Features**: Browser-based logging with proper CORS setup
- **Run**: Open `tests/demo-app/frontend/index-python.html` in browser

### Quick Demo Setup
```bash
# 1. Start log server (in Docker)
cd services/log-save-server
docker-compose up

# 2. Start backend (Python or JavaScript)
cd tests/demo-app/backend-python
python server.py

# 3. Open frontend
open ../frontend/index-python.html

# 4. Interact with app, then check logs
psql -h localhost -U postgres -d logs_db \
  -c "SELECT service, level, message FROM logs ORDER BY created_at DESC LIMIT 10;"
```

## 🔗 Integration with Full System

This client is part of a complete log analysis system. See the [main README](../../README.md) for the full picture.

### System Architecture

```
[Your App] → [Python Client] → [Log Save Server] → [PostgreSQL] → [Analysis Server] → [Frontend]
```

### Related Components

- **Log Save Server**: Receives logs via HTTP POST ([README](../../services/log-save-server/README.md))
- **Log Analysis Server**: Text-to-SQL with Claude Sonnet 4.5 ([README](../../services/log-analysis-server/README.md))
- **Frontend Dashboard**: Svelte 5 web interface ([README](../../frontend/README.md))
- **JavaScript Client**: JavaScript async log collection ([README](../javascript/README.md))
- **Database Schema**: PostgreSQL 15 with 21 fields ([schema.sql](../../database/schema.sql))

### Quick System Setup

For a complete local environment with all components:

```bash
# From root directory
docker-compose up -d
# Starts: PostgreSQL, Log Save Server, Log Analysis Server, Frontend
```

See [QUICKSTART.md](../../QUICKSTART.md) for detailed setup.

## ✨ 주요 기능

- ⚡ **비블로킹 로깅** - 앱 블로킹 < 0.1ms
- 🚀 **배치 전송** - 1000건 or 1초마다 자동 전송
- 📦 **자동 압축** - gzip 압축으로 네트워크 비용 절감
- 🔄 **Graceful Shutdown** - 앱 종료 시 큐 자동 flush
- 🎯 **자동 필드 수집** - 호출 위치, HTTP 컨텍스트, 사용자 컨텍스트 자동 포함
- 🌐 **웹 프레임워크 통합** - Flask, FastAPI, Django 지원
- 🔍 **분산 추적** - trace_id로 마이크로서비스 간 요청 추적

## 📦 Installation

```bash
pip install log-collector-async
```

Development dependencies (for testing):
```bash
pip install log-collector-async[dev]
```

## 💡 Basic Usage

### Standard Usage

```python
from log_collector import AsyncLogClient

# Initialize with options
logger = AsyncLogClient(
    server_url="http://localhost:8000",
    service="my-service",
    environment="production"
)

# Send logs (non-blocking, batched automatically)
logger.info("Application started")
logger.warn("High memory usage detected", memory_mb=512)
logger.error("Database connection failed", db_host="localhost")

# Automatic graceful shutdown on process exit
```

### Environment Variables

`.env` file or environment variables:
```bash
LOG_SERVER_URL=http://localhost:8000
SERVICE_NAME=payment-api
NODE_ENV=production
SERVICE_VERSION=v1.2.3
LOG_TYPE=BACKEND
```

```python
# Auto-load from environment variables
logger = AsyncLogClient()
```

## 🎯 Feature 1: 자동 호출 위치 추적

**모든 로그에 `function_name`, `file_path` 자동 포함!**

```python
def process_payment(amount):
    logger.info("Processing payment", amount=amount)
    # → function_name="process_payment", file_path="/app/payment.py" 자동 포함!

# 비활성화도 가능
logger.log("INFO", "Manual log", auto_caller=False)
```

**PostgreSQL 분석:**
```sql
SELECT function_name, COUNT(*) as call_count
FROM logs
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY function_name
ORDER BY call_count DESC;
```

## 🌐 Feature 2: HTTP 컨텍스트 자동 수집

**웹 프레임워크 환경에서 `path`, `method`, `ip` 자동 포함!**

### Flask 통합

```python
import time
import uuid
from flask import Flask, request, g
from log_collector import AsyncLogClient

app = Flask(__name__)
logger = AsyncLogClient("http://localhost:8000")

@app.before_request
def setup_log_context():
    """요청마다 로그 컨텍스트 생성"""
    # 로그 컨텍스트를 g 객체에 저장
    g.log_context = {
        'path': request.path,
        'method': request.method,
        'ip': request.remote_addr,
        'trace_id': request.headers.get('x-trace-id', str(uuid.uuid4()).replace('-', '')[:32])
    }

    # 사용자 ID가 있으면 추가
    if request.headers.get('x-user-id'):
        g.log_context['user_id'] = request.headers['x-user-id']

    # 요청 시작 시간 기록
    g.start_time = time.time()

    # 요청 시작 로그
    logger.info("Request received", **g.log_context)

@app.after_request
def log_response(response):
    """응답 완료 시 로그"""
    if hasattr(g, 'log_context') and hasattr(g, 'start_time'):
        duration_ms = int((time.time() - g.start_time) * 1000)
        logger.info("Request completed",
                   status_code=response.status_code,
                   duration_ms=duration_ms,
                   **g.log_context)
    return response

@app.route('/api/users/<user_id>')
def get_user(user_id):
    # 라우트 핸들러에서 컨텍스트를 메타데이터로 전달
    logger.info(f"Fetching user {user_id}",
                user_id_param=user_id,
                **g.log_context)
    # → path, method, ip, trace_id 모두 자동 포함!
    return {"user_id": user_id}

@app.route('/api/todos', methods=['POST'])
def create_todo():
    logger.info("Creating todo",
                todo_text=request.json.get('text'),
                **g.log_context)
    # ... handle todo creation
    return {"success": True}
```

### FastAPI 통합

```python
import time
import uuid
from fastapi import FastAPI, Request
from log_collector import AsyncLogClient

app = FastAPI()
logger = AsyncLogClient("http://localhost:8000")

@app.middleware("http")
async def log_context_middleware(request: Request, call_next):
    """HTTP 컨텍스트 미들웨어"""
    # 요청 시작 시간
    start_time = time.time()

    # trace_id 생성
    trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()).replace("-", "")[:32])

    # HTTP 컨텍스트
    log_context = {
        "path": request.url.path,
        "method": request.method,
        "ip": request.client.host if request.client else None,
        "trace_id": trace_id,
    }

    # 사용자 컨텍스트 추가
    user_id = request.headers.get("x-user-id")
    if user_id:
        log_context["user_id"] = user_id

    # 요청 컨텍스트를 request.state에 저장
    request.state.log_context = log_context
    request.state.start_time = start_time

    logger.info("Request received", **log_context)

    # 요청 처리
    response = await call_next(request)

    # 응답 완료
    duration_ms = int((time.time() - start_time) * 1000)
    logger.info("Request completed",
                status_code=response.status_code,
                duration_ms=duration_ms,
                **log_context)

    return response

@app.get("/api/users/{user_id}")
async def get_user(request: Request, user_id: int):
    # 라우트 핸들러에서 컨텍스트를 메타데이터로 전달
    log_ctx = request.state.log_context
    logger.info(f"Fetching user {user_id}",
                user_id_param=user_id,
                **log_ctx)
    # → path, method, ip, trace_id 모두 자동 포함!
    return {"user_id": user_id}

@app.post("/api/todos")
async def create_todo(request: Request, body: dict):
    log_ctx = request.state.log_context
    logger.info("Creating todo",
                todo_text=body.get('text'),
                **log_ctx)
    # ... handle todo creation
    return {"success": True}
```

## 👤 Feature 3: 사용자 컨텍스트 관리

**`user_id`, `trace_id`, `session_id` 등을 모든 로그에 자동 포함!**

### Context Manager 방식 (권장)

```python
# 특정 블록에만 컨텍스트 적용
with AsyncLogClient.user_context(
    user_id="user_123",
    trace_id="trace_xyz",
    session_id="sess_abc"
):
    logger.info("User logged in")
    # → user_id, trace_id, session_id 자동 포함!

    process_payment()
    logger.info("Payment completed")
    # → 하위 함수에서도 자동으로 컨텍스트 유지!

# with 블록 벗어나면 자동 초기화
```

### 중첩 컨텍스트 (자동 병합)

```python
# 외부: tenant_id
with AsyncLogClient.user_context(tenant_id="tenant_1"):
    logger.info("Tenant operation")
    # → tenant_id="tenant_1"

    # 내부: user_id 추가
    with AsyncLogClient.user_context(user_id="user_123"):
        logger.info("User operation")
        # → tenant_id="tenant_1", user_id="user_123" 둘 다 포함!
```

### 분산 추적 (Distributed Tracing)

```python
import uuid

def handle_request():
    trace_id = str(uuid.uuid4())

    with AsyncLogClient.user_context(trace_id=trace_id, user_id="user_123"):
        logger.info("Request received")
        call_service_a()  # Service A 호출
        call_service_b()  # Service B 호출
        logger.info("Request completed")
        # → 모든 로그가 같은 trace_id로 추적 가능!
```

**PostgreSQL 분석:**
```sql
-- trace_id로 전체 요청 흐름 추적
SELECT created_at, service, function_name, message, duration_ms
FROM logs
WHERE trace_id = 'your-trace-id'
ORDER BY created_at;
```

### Set/Clear 방식

```python
# 로그인 시
AsyncLogClient.set_user_context(
    user_id="user_123",
    session_id="sess_abc"
)

logger.info("User action")
# → user_id, session_id 자동 포함

# 로그아웃 시
AsyncLogClient.clear_user_context()
```

## 🔧 고급 기능

### 타이머 측정

```python
# 수동 타이머
timer = logger.start_timer()
result = expensive_operation()
logger.end_timer(timer, "INFO", "Operation completed")
# → duration_ms 자동 계산

# 함수 래퍼 (동기/비동기 자동 감지)
result = logger.measure(lambda: expensive_operation())
```

### 에러 추적

```python
try:
    risky_operation()
except Exception as e:
    logger.error_with_trace("Operation failed", exception=e)
    # → stack_trace, error_type, function_name, file_path 자동 포함!
```

### 수동 Flush

```python
# 중요한 로그를 즉시 전송
logger.flush()
```

## ⚙️ 설정 옵션

```python
logger = AsyncLogClient(
    server_url="http://localhost:8000",
    service="payment-api",
    environment="production",
    service_version="v1.2.3",
    log_type="BACKEND",
    batch_size=1000,          # 배치 크기 (기본: 1000)
    flush_interval=1.0,       # Flush 간격 초 (기본: 1.0)
    enable_compression=True   # gzip 압축 (기본: True)
)
```

## 📊 성능

- **앱 블로킹**: < 0.1ms per log
- **처리량**: > 10,000 logs/sec
- **메모리**: < 10MB (1000건 큐)
- **압축률**: ~70% (100건 이상 시 자동 압축)

## 🧪 테스트

```bash
# 단위 테스트
pytest tests/

# 통합 테스트 (로그 서버 필요)
pytest tests/test_integration.py

# 커버리지
pytest --cov=log_collector tests/
```

## 📝 로그 레벨

```python
logger.trace("Trace message")    # TRACE
logger.debug("Debug message")    # DEBUG
logger.info("Info message")      # INFO
logger.warn("Warning message")   # WARN
logger.error("Error message")    # ERROR
logger.fatal("Fatal message")    # FATAL
```

## 🔍 PostgreSQL 쿼리 예제

### 사용자별 로그 조회
```sql
SELECT * FROM logs
WHERE user_id = 'user_123'
ORDER BY created_at DESC
LIMIT 100;
```

### 에러 발생률
```sql
SELECT
    path,
    method,
    COUNT(*) as total_requests,
    COUNT(CASE WHEN level = 'ERROR' THEN 1 END) as errors,
    ROUND(100.0 * COUNT(CASE WHEN level = 'ERROR' THEN 1 END) / COUNT(*), 2) as error_rate
FROM logs
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY path, method
ORDER BY error_rate DESC;
```

### 함수별 성능
```sql
SELECT
    function_name,
    COUNT(*) as calls,
    AVG(duration_ms) as avg_ms,
    MAX(duration_ms) as max_ms
FROM logs
WHERE duration_ms IS NOT NULL
GROUP BY function_name
ORDER BY avg_ms DESC;
```

## 🚨 주의사항

1. **민감한 정보 포함 금지**
   ```python
   # ❌ 절대 안 됨!
   logger.info("Login", password="secret")

   # ✅ 식별자만 사용
   logger.info("Login successful", user_id="user_123")
   ```

2. **과도한 로깅 피하기**
   ```python
   # ❌ 루프 내부에서 과도한 로깅
   for i in range(10000):
       logger.debug(f"Processing {i}")

   # ✅ 주요 이벤트만 로깅
   logger.info(f"Batch processing started", count=10000)
   ```

## 🔧 Troubleshooting

### Logs not appearing in database

**Symptoms**:
- `logger.info()` runs without errors
- No logs visible in PostgreSQL
- No errors in console

**Checklist**:
1. ✅ **Log server running?**
   ```bash
   curl http://localhost:8000/
   # Should return: {"status": "ok"}
   ```

2. ✅ **PostgreSQL running?**
   ```bash
   psql -h localhost -U postgres -d logs_db -c "SELECT 1;"
   ```

3. ✅ **Schema created?**
   ```bash
   psql -h localhost -U postgres -d logs_db -c "\dt"
   # Should show 'logs' table
   ```

4. ✅ **Batch flushed?**
   - Wait 1 second (default flush interval)
   - OR manually flush: `logger.flush()`

5. ✅ **Check server logs**:
   ```bash
   cd services/log-save-server
   docker-compose logs -f
   # Look for "Received X logs" messages
   ```

---

### "Connection refused" errors

**Symptoms**:
```
requests.exceptions.ConnectionError: ('Connection aborted.', ConnectionRefusedError(111, 'Connection refused'))
```

**Cause**: Log server not running

**Solution**:
```bash
cd services/log-save-server
docker-compose up -d

# Verify it's running
curl http://localhost:8000/
```

---

### High memory usage

**Symptoms**:
- Application memory grows over time
- Eventually crashes with OOM error

**Cause**: Batch size too large or flush interval too long

**Solution**: Reduce batching parameters
```python
logger = AsyncLogClient(
    "http://localhost:8000",
    batch_size=500,      # Reduce from 1000
    flush_interval=0.5   # Reduce from 1.0
)
```

---

### Logs delayed or not sent on app shutdown

**Symptoms**:
- Last few logs before shutdown are missing
- Queue not flushing properly

**Cause**: App exits before background thread flushes

**Solution**: Call flush before exit
```python
import atexit
import signal

# Auto-flush on normal exit
atexit.register(logger.flush)

# Flush on SIGTERM
def handle_sigterm(signum, frame):
    logger.flush()
    sys.exit(0)

signal.signal(signal.SIGTERM, handle_sigterm)

# Or manually before exit
logger.flush()  # Blocks until queue is empty
```

---

### Thread daemon warnings on exit

**Symptoms**:
```
Exception ignored in: <module 'threading' from '/usr/lib/python3.8/threading.py'>
RuntimeError: can't create new thread at interpreter shutdown
```

**Cause**: Background thread still running during shutdown

**Solution**: Call flush to ensure clean shutdown
```python
# At the end of your application
logger.flush()
```

---

### UnicodeEncodeError with emojis (Windows)

**Symptoms**:
```
UnicodeEncodeError: 'cp949' codec can't encode character
```

**Cause**: Windows console encoding issue

**Solution**: Set UTF-8 encoding
```bash
# Set environment variable before running
set PYTHONIOENCODING=utf-8
python your_app.py

# Or in code
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

## 📋 Version Compatibility

| Component | Minimum Version | Tested Version | Notes |
|-----------|----------------|----------------|-------|
| **This Client** | 1.0.0 | 1.0.0 | Current release |
| **Log Save Server** | 1.0.0 | 1.0.0 | FastAPI 0.104+ |
| **PostgreSQL** | 12 | 15 | Requires JSONB support |
| **Log Analysis Server** | 1.0.0 | 1.0.0 | Optional (for Text-to-SQL) |
| **Python** | 3.8 | 3.11 | Runtime environment |

### Breaking Changes

- **v1.0.0**: Initial release

### Upgrade Guide

No upgrades yet. This is the initial release.

## 📚 추가 문서

- [HTTP-CONTEXT-GUIDE.md](HTTP-CONTEXT-GUIDE.md) - HTTP 컨텍스트 완전 가이드
- [USER-CONTEXT-GUIDE.md](USER-CONTEXT-GUIDE.md) - 사용자 컨텍스트 완전 가이드
- [FIELD-AUTO-COLLECTION.md](FIELD-AUTO-COLLECTION.md) - 자동 필드 수집 상세

## 🤝 기여

기여는 언제나 환영합니다!

## 📄 라이선스

MIT License - 자유롭게 사용하세요!

---

**Made with ❤️ by Log Analysis System Team**
