# User Context Management Guide

## 개요

사용자 컨텍스트 관리 기능을 사용하면 `user_id`, `trace_id`, `session_id`, `tenant_id` 같은 사용자별 정보를 모든 로그에 자동으로 포함시킬 수 있습니다.

**HTTP Context vs User Context 비교:**

| 항목 | HTTP Context | User Context |
|------|-------------|--------------|
| **설정 위치** | 웹 프레임워크 미들웨어 | 애플리케이션 코드 |
| **자동화** | 요청마다 자동 설정 | 개발자가 명시적으로 설정 |
| **포함 정보** | path, method, ip | user_id, trace_id, session_id, tenant_id |
| **사용 사례** | HTTP 요청 추적 | 사용자 행동 추적, 분산 추적 |

---

## Python 사용법

### 1. 기본 사용 (Context Manager)

```python
from log_collector import AsyncLogClient

logger = AsyncLogClient("http://localhost:8000")

# with 블록 내에서 자동으로 컨텍스트 포함
with AsyncLogClient.user_context(user_id="user_123", trace_id="trace_xyz"):
    logger.info("Processing payment")
    # → user_id="user_123", trace_id="trace_xyz" 자동 포함

    process_payment()
    logger.info("Payment completed")
    # → user_id, trace_id 자동 포함

# with 블록 벗어나면 컨텍스트 자동 초기화
logger.info("Outside context")
# → user_id, trace_id 없음
```

### 2. Set/Clear 방식

```python
# 로그인 시 컨텍스트 설정
def on_user_login(user_id: str):
    AsyncLogClient.set_user_context(
        user_id=user_id,
        session_id=generate_session_id(),
        tenant_id=get_tenant_id(user_id)
    )
    logger.info("User logged in")
    # → user_id, session_id, tenant_id 자동 포함

# 로그아웃 시 컨텍스트 초기화
def on_user_logout():
    logger.info("User logging out")
    # → user_id 등 포함된 상태

    AsyncLogClient.clear_user_context()
    logger.info("User logged out")
    # → user_id 등 없음
```

### 3. 중첩 컨텍스트

```python
# 외부 컨텍스트: tenant_id
with AsyncLogClient.user_context(tenant_id="tenant_1"):
    logger.info("Tenant operation started")
    # → tenant_id="tenant_1"

    # 내부 컨텍스트: user_id 추가
    with AsyncLogClient.user_context(user_id="user_123"):
        logger.info("User operation")
        # → tenant_id="tenant_1", user_id="user_123" 둘 다 포함

    logger.info("Back to tenant context")
    # → tenant_id="tenant_1" (user_id 없음)
```

### 4. Flask 통합 예제

```python
from flask import Flask, session
from log_collector import AsyncLogClient

app = Flask(__name__)
logger = AsyncLogClient("http://localhost:8000")

@app.before_request
def set_contexts():
    # HTTP 컨텍스트 (path, method, ip)
    AsyncLogClient.set_request_context(
        path=request.path,
        method=request.method,
        ip=request.remote_addr
    )

    # 사용자 컨텍스트 (user_id, session_id)
    if 'user_id' in session:
        AsyncLogClient.set_user_context(
            user_id=session['user_id'],
            session_id=session.sid
        )

@app.after_request
def clear_contexts(response):
    AsyncLogClient.clear_request_context()
    AsyncLogClient.clear_user_context()
    return response

@app.route('/api/profile')
def get_profile():
    logger.info("Fetching user profile")
    # → path="/api/profile", method="GET", ip="127.0.0.1"
    # → user_id="user_123", session_id="sess_abc" (자동 포함!)

    return {"profile": "data"}
```

### 5. FastAPI 통합 예제

```python
from fastapi import FastAPI, Request, Depends
from log_collector import AsyncLogClient

app = FastAPI()
logger = AsyncLogClient("http://localhost:8000")

# JWT 토큰에서 user_id 추출 (예시)
async def get_current_user(request: Request):
    token = request.headers.get("Authorization")
    # JWT 검증 후 user_id 추출
    return {"user_id": "user_123", "tenant_id": "tenant_1"}

@app.middleware("http")
async def log_context_middleware(request: Request, call_next):
    # HTTP 컨텍스트
    AsyncLogClient.set_request_context(
        path=request.url.path,
        method=request.method,
        ip=request.client.host if request.client else None
    )

    # JWT에서 사용자 정보 추출
    user = await get_current_user(request) if "Authorization" in request.headers else None
    if user:
        AsyncLogClient.set_user_context(**user)

    try:
        response = await call_next(request)
        return response
    finally:
        AsyncLogClient.clear_request_context()
        AsyncLogClient.clear_user_context()

@app.get("/api/data")
async def get_data():
    logger.info("Fetching data")
    # → path="/api/data", method="GET", ip="127.0.0.1"
    # → user_id="user_123", tenant_id="tenant_1"
    return {"data": "result"}
```

---

## JavaScript 사용법

### 1. 기본 사용 (runWithUserContext)

```javascript
const { WorkerThreadsLogClient } = require('./src/node-client');

const logger = new WorkerThreadsLogClient('http://localhost:8000');

// 특정 블록에만 컨텍스트 적용
WorkerThreadsLogClient.runWithUserContext({
    user_id: 'user_123',
    trace_id: 'trace_xyz',
    session_id: 'sess_abc'
}, () => {
    logger.info('Processing payment');
    // → user_id, trace_id, session_id 자동 포함

    processPayment();
    logger.info('Payment completed');
    // → user_id, trace_id, session_id 자동 포함
});

// 블록 밖에서는 컨텍스트 없음
logger.info('Outside context');
// → user_id, trace_id, session_id 없음
```

### 2. Promise와 함께 사용

```javascript
// async/await 함수와 함께 사용
await WorkerThreadsLogClient.runWithUserContext(
    { user_id: 'user_123', trace_id: 'trace_xyz' },
    async () => {
        logger.info('Fetching user data');
        // → user_id, trace_id 자동 포함

        const data = await fetchUserData();

        logger.info('Data fetched successfully');
        // → user_id, trace_id 자동 포함

        return data;
    }
);
```

### 3. Set/Clear 방식 (주의사항 있음)

```javascript
// ⚠️ 주의: 동기 코드에서만 안전하게 작동
// 비동기 작업에는 runWithUserContext() 사용 권장

// 로그인 시
WorkerThreadsLogClient.setUserContext({
    user_id: 'user_123',
    session_id: 'sess_abc'
});

logger.info('User action');
// → user_id, session_id 자동 포함

// 로그아웃 시
WorkerThreadsLogClient.clearUserContext();
```

### 4. Express 통합 예제

```javascript
const express = require('express');
const { WorkerThreadsLogClient } = require('./src/node-client');

const app = express();
const logger = new WorkerThreadsLogClient('http://localhost:8000');

// JWT 미들웨어 (예시)
function extractUser(req, res, next) {
    const token = req.headers.authorization;
    if (token) {
        // JWT 검증 후 user 정보 추출
        req.user = { user_id: 'user_123', tenant_id: 'tenant_1' };
    }
    next();
}

// HTTP + User 컨텍스트 미들웨어
app.use(extractUser);
app.use((req, res, next) => {
    // HTTP 컨텍스트 설정
    const httpContext = {
        path: req.path,
        method: req.method,
        ip: req.ip
    };

    WorkerThreadsLogClient.runWithContext(httpContext, () => {
        // User 컨텍스트 추가 설정 (JWT에서 추출한 경우)
        if (req.user) {
            WorkerThreadsLogClient.runWithUserContext(req.user, () => {
                logger.info('Request started');
                // → path, method, ip, user_id, tenant_id 모두 포함!
                next();
            });
        } else {
            logger.info('Request started (anonymous)');
            // → path, method, ip만 포함
            next();
        }
    });
});

app.get('/api/profile', (req, res) => {
    logger.info('Fetching user profile');
    // → path="/api/profile", method="GET", ip="::1"
    // → user_id="user_123", tenant_id="tenant_1"

    res.json({ profile: 'data' });
});

app.listen(3000, () => {
    logger.info('Server started on port 3000');
});
```

### 5. 중첩 컨텍스트

```javascript
// 외부 컨텍스트: tenant_id
WorkerThreadsLogClient.runWithUserContext({ tenant_id: 'tenant_1' }, () => {
    logger.info('Tenant operation');
    // → tenant_id="tenant_1"

    // 내부 컨텍스트: user_id 추가
    WorkerThreadsLogClient.runWithUserContext({ user_id: 'user_123' }, () => {
        logger.info('User operation');
        // → tenant_id="tenant_1", user_id="user_123" 둘 다 포함
    });

    logger.info('Back to tenant context');
    // → tenant_id="tenant_1" (user_id 없음)
});
```

---

## 실전 활용 패턴

### 1. 분산 추적 (Distributed Tracing)

```python
import uuid

def handle_request():
    trace_id = str(uuid.uuid4())

    with AsyncLogClient.user_context(trace_id=trace_id):
        logger.info("Request received")
        # → trace_id="abc-123-xyz"

        call_service_a()  # Service A 호출
        call_service_b()  # Service B 호출

        logger.info("Request completed")
        # → 같은 trace_id로 전체 흐름 추적 가능!
```

### 2. Multi-Tenant 애플리케이션

```python
def process_tenant_request(tenant_id: str, user_id: str):
    with AsyncLogClient.user_context(tenant_id=tenant_id, user_id=user_id):
        logger.info("Processing request")
        # → tenant_id, user_id 자동 포함

        # 모든 하위 함수 호출에서도 자동으로 포함됨
        fetch_tenant_data()
        process_user_action()
        send_notification()

        logger.info("Request completed")

# PostgreSQL 분석 쿼리
# SELECT tenant_id, user_id, COUNT(*) as action_count
# FROM logs
# WHERE message LIKE '%action%'
# GROUP BY tenant_id, user_id;
```

### 3. 에러 추적 with Context

```python
def process_payment(user_id: str):
    with AsyncLogClient.user_context(user_id=user_id):
        try:
            logger.info("Starting payment")
            # → user_id 포함

            charge_credit_card()

        except Exception as e:
            logger.error_with_trace("Payment failed", exception=e)
            # → user_id, stack_trace, error_type 모두 포함!
            # 어떤 사용자의 결제가 실패했는지 즉시 파악 가능
            raise
```

### 4. Background Job with Context

```javascript
// Celery, Bull.js 등 백그라운드 작업에서도 사용
async function processJob(jobData) {
    await WorkerThreadsLogClient.runWithUserContext(
        {
            user_id: jobData.user_id,
            job_id: jobData.job_id,
            trace_id: jobData.trace_id
        },
        async () => {
            logger.info('Job started');
            // → user_id, job_id, trace_id 자동 포함

            await performTask();

            logger.info('Job completed');
            // → 같은 컨텍스트 정보 포함
        }
    );
}
```

---

## PostgreSQL 분석 쿼리

### 1. 사용자별 로그 조회

```sql
-- 특정 사용자의 모든 로그
SELECT created_at, level, message, function_name
FROM logs
WHERE metadata->>'user_id' = 'user_123'
ORDER BY created_at DESC
LIMIT 100;
```

### 2. 분산 추적 조회

```sql
-- trace_id로 전체 요청 흐름 추적
SELECT
    created_at,
    service,
    function_name,
    message,
    duration_ms
FROM logs
WHERE metadata->>'trace_id' = 'trace_xyz'
ORDER BY created_at;
```

### 3. 테넌트별 통계

```sql
-- 테넌트별 에러 발생 현황
SELECT
    metadata->>'tenant_id' as tenant_id,
    COUNT(*) as error_count,
    COUNT(DISTINCT metadata->>'user_id') as affected_users
FROM logs
WHERE level = 'ERROR'
    AND created_at > NOW() - INTERVAL '1 day'
GROUP BY metadata->>'tenant_id'
ORDER BY error_count DESC;
```

### 4. 사용자 행동 분석

```sql
-- 사용자별 액션 카운트
SELECT
    metadata->>'user_id' as user_id,
    metadata->>'tenant_id' as tenant_id,
    COUNT(*) as action_count,
    AVG((metadata->>'duration_ms')::float) as avg_duration_ms
FROM logs
WHERE message LIKE '%completed%'
    AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY metadata->>'user_id', metadata->>'tenant_id'
ORDER BY action_count DESC
LIMIT 20;
```

### 5. 세션 분석

```sql
-- 세션별 로그 타임라인
SELECT
    metadata->>'session_id' as session_id,
    metadata->>'user_id' as user_id,
    MIN(created_at) as session_start,
    MAX(created_at) as session_end,
    COUNT(*) as log_count,
    COUNT(CASE WHEN level = 'ERROR' THEN 1 END) as error_count
FROM logs
WHERE metadata->>'session_id' IS NOT NULL
    AND created_at > NOW() - INTERVAL '1 day'
GROUP BY metadata->>'session_id', metadata->>'user_id'
ORDER BY session_start DESC;
```

---

## 권장 사항

### ✅ DO

1. **Context Manager 사용 (Python)**
   ```python
   with AsyncLogClient.user_context(user_id="user_123"):
       # 자동으로 시작 및 종료
   ```

2. **runWithUserContext 사용 (JavaScript)**
   ```javascript
   WorkerThreadsLogClient.runWithUserContext({ user_id: 'user_123' }, () => {
       // 자동으로 관리됨
   });
   ```

3. **최소한의 정보만 포함**
   ```python
   # 좋음
   user_context(user_id="user_123", trace_id="trace_xyz")

   # 나쁨 (과도한 정보)
   user_context(
       user_id="user_123",
       full_name="John Doe",
       email="john@example.com",  # ❌ PII 정보
       credit_card="1234-5678"    # ❌ 민감 정보
   )
   ```

4. **분산 추적을 위해 trace_id 사용**
   ```python
   trace_id = str(uuid.uuid4())
   with AsyncLogClient.user_context(trace_id=trace_id):
       # 마이크로서비스 간 전체 흐름 추적 가능
   ```

### ❌ DON'T

1. **민감한 정보 포함 금지**
   ```python
   # 절대 안 됨!
   user_context(
       password="secret123",      # ❌
       credit_card="1234-5678",   # ❌
       ssn="123-45-6789"          # ❌
   )
   ```

2. **JavaScript에서 set/clear 남용 금지**
   ```javascript
   // ❌ 비동기 작업에서 안전하지 않음
   WorkerThreadsLogClient.setUserContext({ user_id: 'user_123' });
   await asyncOperation();  // 컨텍스트가 유실될 수 있음!

   // ✅ runWithUserContext 사용
   await WorkerThreadsLogClient.runWithUserContext(
       { user_id: 'user_123' },
       () => asyncOperation()
   );
   ```

3. **과도한 컨텍스트 중첩 피하기**
   ```python
   # ❌ 너무 복잡
   with user_context(a=1):
       with user_context(b=2):
           with user_context(c=3):
               with user_context(d=4):
                   # 4단계 중첩은 과도함

   # ✅ 한 번에 설정
   with user_context(a=1, b=2, c=3):
       # 명확하고 간단
   ```

---

## 테스트 예제

### Python 테스트

```python
def test_user_context():
    """사용자 컨텍스트 자동 포함 테스트"""
    client = AsyncLogClient("http://localhost:8000")

    # 컨텍스트 없이 로그
    client.log("INFO", "No context")
    # → user_id 없음

    # 컨텍스트 있이 로그
    with AsyncLogClient.user_context(user_id="user_123", trace_id="trace_xyz"):
        client.log("INFO", "With context")
        # → user_id="user_123", trace_id="trace_xyz" 포함

    # 컨텍스트 밖에서 다시 로그
    client.log("INFO", "After context")
    # → user_id 없음
```

### JavaScript 테스트

```javascript
test('user context auto-inclusion', () => {
    const logger = new WorkerThreadsLogClient('http://localhost:8000');

    // 컨텍스트 없이 로그
    logger.info('No context');
    // → user_id 없음

    // 컨텍스트 있이 로그
    WorkerThreadsLogClient.runWithUserContext({
        user_id: 'user_123',
        trace_id: 'trace_xyz'
    }, () => {
        logger.info('With context');
        // → user_id, trace_id 자동 포함
    });

    // 컨텍스트 밖에서 다시 로그
    logger.info('After context');
    // → user_id 없음
});
```

---

## 요약

1. **HTTP Context vs User Context**
   - HTTP Context: 웹 프레임워크가 자동으로 관리 (path, method, ip)
   - User Context: 개발자가 명시적으로 설정 (user_id, trace_id, session_id)

2. **Python 권장 방법**
   ```python
   with AsyncLogClient.user_context(user_id="user_123"):
       # 모든 로그에 자동 포함
   ```

3. **JavaScript 권장 방법**
   ```javascript
   WorkerThreadsLogClient.runWithUserContext({ user_id: 'user_123' }, () => {
       // 모든 로그에 자동 포함
   });
   ```

4. **주요 사용 사례**
   - 분산 추적 (trace_id)
   - 멀티 테넌트 (tenant_id)
   - 사용자 행동 추적 (user_id)
   - 세션 분석 (session_id)

5. **보안 주의사항**
   - 민감한 정보 (비밀번호, 카드 번호 등) 포함 금지
   - PII 정보는 최소화
   - 로그는 검색 가능한 형태로 저장됨을 기억
