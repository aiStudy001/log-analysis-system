# HTTP 컨텍스트 자동 수집 가이드

웹 프레임워크(Flask, FastAPI, Express)에서 HTTP 요청 정보 자동 수집

---

## 🎯 개요

웹 애플리케이션에서 로그를 남길 때 HTTP 요청 정보(path, method, IP 등)를 자동으로 포함시키는 기능입니다.

### 자동 수집되는 필드

| 필드 | 설명 | 예시 |
|-----|------|------|
| `path` | HTTP 요청 경로 | `"/api/users/123"` |
| `method` | HTTP 메서드 | `"GET"`, `"POST"`, `"PUT"` |
| `ip` | 클라이언트 IP 주소 | `"192.168.1.100"` |

추가로 원하는 필드도 포함 가능 (user_id, trace_id 등)

---

## 🐍 Python - Flask

### 미들웨어 설정

```python
from flask import Flask, request, g
from log_collector import AsyncLogClient

app = Flask(__name__)
logger = AsyncLogClient("http://localhost:8000")

@app.before_request
def set_log_context():
    """요청 시작 시 HTTP 컨텍스트 설정"""
    AsyncLogClient.set_request_context(
        path=request.path,
        method=request.method,
        ip=request.remote_addr,
        user_agent=request.user_agent.string
    )

@app.after_request
def clear_log_context(response):
    """요청 종료 시 컨텍스트 초기화"""
    AsyncLogClient.clear_request_context()
    return response

# 라우트에서 사용
@app.route('/api/users/<user_id>')
def get_user(user_id):
    logger.info(f"Getting user {user_id}")
    # 자동으로 포함됨:
    # {
    #   "message": "Getting user 123",
    #   "path": "/api/users/123",        ← 자동!
    #   "method": "GET",                 ← 자동!
    #   "ip": "192.168.1.100",          ← 자동!
    #   "user_agent": "Mozilla/5.0 ..."  ← 자동!
    # }

    user = db.get_user(user_id)
    logger.info("User fetched successfully", user_id=user_id)
    return {"user": user}
```

---

### 데코레이터 방식 (선택)

```python
from functools import wraps

def with_request_logging(f):
    """라우트에 HTTP 컨텍스트 자동 추가하는 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        AsyncLogClient.set_request_context(
            path=request.path,
            method=request.method,
            ip=request.remote_addr
        )
        try:
            return f(*args, **kwargs)
        finally:
            AsyncLogClient.clear_request_context()
    return decorated_function

@app.route('/api/products/<product_id>')
@with_request_logging
def get_product(product_id):
    logger.info(f"Getting product {product_id}")
    # path, method, ip 자동 포함됨
    return {"product_id": product_id}
```

---

## 🐍 Python - FastAPI

### 미들웨어 설정

```python
from fastapi import FastAPI, Request
from log_collector import AsyncLogClient

app = FastAPI()
logger = AsyncLogClient("http://localhost:8000")

@app.middleware("http")
async def log_context_middleware(request: Request, call_next):
    """모든 요청에 HTTP 컨텍스트 자동 설정"""
    # 컨텍스트 설정
    AsyncLogClient.set_request_context(
        path=request.url.path,
        method=request.method,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    try:
        response = await call_next(request)
        return response
    finally:
        # 요청 종료 시 컨텍스트 초기화
        AsyncLogClient.clear_request_context()

# 라우트에서 사용
@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    logger.info(f"Getting user {user_id}")
    # 자동으로 포함됨:
    # {
    #   "message": "Getting user 123",
    #   "path": "/api/users/123",     ← 자동!
    #   "method": "GET",              ← 자동!
    #   "ip": "192.168.1.100"        ← 자동!
    # }

    user = await db.get_user(user_id)
    logger.info("User fetched successfully", user_id=user_id)
    return {"user": user}
```

---

### 의존성 주입 방식 (선택)

```python
from fastapi import Depends

async def setup_log_context(request: Request):
    """의존성으로 컨텍스트 설정"""
    AsyncLogClient.set_request_context(
        path=request.url.path,
        method=request.method,
        ip=request.client.host if request.client else None
    )
    yield
    AsyncLogClient.clear_request_context()

@app.get("/api/products/{product_id}")
async def get_product(
    product_id: int,
    _: None = Depends(setup_log_context)
):
    logger.info(f"Getting product {product_id}")
    # path, method, ip 자동 포함됨
    return {"product_id": product_id}
```

---

## 🌐 JavaScript - Express

### 미들웨어 설정

```javascript
const express = require('express');
const { createLogClient } = require('log-collector');

const app = express();
const logger = createLogClient('http://localhost:8000');

// HTTP 컨텍스트 미들웨어
app.use((req, res, next) => {
    // AsyncLocalStorage를 사용해서 컨텍스트 전파
    const { WorkerThreadsLogClient } = require('log-collector/src/node-client');

    WorkerThreadsLogClient.runWithContext({
        path: req.path,
        method: req.method,
        ip: req.ip,
        user_agent: req.get('user-agent')
    }, () => {
        next();
    });
});

// 라우트에서 사용
app.get('/api/users/:userId', (req, res) => {
    logger.info(`Getting user ${req.params.userId}`);
    // 자동으로 포함됨:
    // {
    //   message: "Getting user 123",
    //   path: "/api/users/123",      ← 자동!
    //   method: "GET",               ← 자동!
    //   ip: "192.168.1.100",        ← 자동!
    //   user_agent: "Mozilla/5.0 ..." ← 자동!
    // }

    const user = db.getUser(req.params.userId);
    logger.info('User fetched successfully', { user_id: req.params.userId });
    res.json({ user });
});
```

---

### async/await 지원

```javascript
app.get('/api/products/:productId', async (req, res) => {
    logger.info(`Getting product ${req.params.productId}`);
    // HTTP 컨텍스트는 async 함수 내에서도 유지됨

    try {
        const product = await db.getProduct(req.params.productId);

        logger.info('Product fetched successfully', {
            product_id: req.params.productId
        });
        // path, method, ip 여전히 자동 포함됨

        res.json({ product });
    } catch (err) {
        logger.errorWithTrace('Failed to fetch product', err);
        // 에러 로그에도 HTTP 컨텍스트 포함됨
        res.status(500).json({ error: err.message });
    }
});
```

---

## 🔍 실전 예시

### Python - FastAPI 완전한 예제

```python
from fastapi import FastAPI, Request, HTTPException
from log_collector import AsyncLogClient
import time

app = FastAPI()
logger = AsyncLogClient(
    service="user-api",
    environment="production",
    service_version="v1.2.3"
)

@app.middleware("http")
async def log_context_middleware(request: Request, call_next):
    # HTTP 컨텍스트 설정
    AsyncLogClient.set_request_context(
        path=request.url.path,
        method=request.method,
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    # 요청 시작 로그
    start_time = time.time()
    logger.info(f"Request started: {request.method} {request.url.path}")

    try:
        response = await call_next(request)

        # 요청 완료 로그 (duration_ms 포함)
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Request completed: {response.status_code}",
            status_code=response.status_code,
            duration_ms=duration_ms
        )

        return response

    except Exception as e:
        # 예외 로그
        duration_ms = (time.time() - start_time) * 1000
        logger.error_with_trace(
            "Request failed",
            exception=e,
            duration_ms=duration_ms
        )
        raise

    finally:
        # 컨텍스트 초기화
        AsyncLogClient.clear_request_context()

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    logger.info("Fetching user from database", user_id=user_id)
    # 자동 포함: path, method, ip, user_agent

    user = await db.get_user(user_id)

    if not user:
        logger.warn("User not found", user_id=user_id)
        # 여전히 HTTP 컨텍스트 포함됨
        raise HTTPException(status_code=404, detail="User not found")

    logger.info("User fetched successfully", user_id=user_id, username=user.name)
    return {"user": user}

@app.post("/api/users")
async def create_user(user: UserCreate):
    logger.info("Creating new user", username=user.username)
    # POST 요청도 동일하게 path, method 포함

    new_user = await db.create_user(user)

    logger.info("User created", user_id=new_user.id, username=new_user.username)
    return {"user": new_user}
```

---

### JavaScript - Express 완전한 예제

```javascript
const express = require('express');
const { createLogClient } = require('log-collector');
const { WorkerThreadsLogClient } = require('log-collector/src/node-client');

const app = express();
app.use(express.json());

const logger = createLogClient('http://localhost:8000', {
    service: 'product-api',
    environment: 'production',
    serviceVersion: 'v2.1.0'
});

// HTTP 컨텍스트 미들웨어
app.use((req, res, next) => {
    WorkerThreadsLogClient.runWithContext({
        path: req.path,
        method: req.method,
        ip: req.ip,
        user_agent: req.get('user-agent')
    }, () => {
        const startTime = Date.now();

        // 요청 시작 로그
        logger.info(`Request started: ${req.method} ${req.path}`);

        // 응답 후킹
        res.on('finish', () => {
            const durationMs = Date.now() - startTime;
            logger.info(`Request completed: ${res.statusCode}`, {
                status_code: res.statusCode,
                duration_ms: durationMs
            });
        });

        next();
    });
});

// 라우트
app.get('/api/products/:productId', async (req, res) => {
    const { productId } = req.params;

    logger.info('Fetching product from database', { product_id: productId });
    // 자동 포함: path="/api/products/123", method="GET", ip="..."

    try {
        const product = await db.getProduct(productId);

        if (!product) {
            logger.warn('Product not found', { product_id: productId });
            return res.status(404).json({ error: 'Product not found' });
        }

        logger.info('Product fetched successfully', {
            product_id: productId,
            name: product.name
        });

        res.json({ product });

    } catch (err) {
        logger.errorWithTrace('Failed to fetch product', err, {
            product_id: productId
        });
        res.status(500).json({ error: 'Internal server error' });
    }
});

app.post('/api/products', async (req, res) => {
    logger.info('Creating new product', { name: req.body.name });
    // POST 요청도 동일하게 path, method 포함

    try {
        const newProduct = await db.createProduct(req.body);

        logger.info('Product created', {
            product_id: newProduct.id,
            name: newProduct.name
        });

        res.status(201).json({ product: newProduct });

    } catch (err) {
        logger.errorWithTrace('Failed to create product', err);
        res.status(500).json({ error: 'Internal server error' });
    }
});

app.listen(3000, () => {
    logger.info('Server started', { port: 3000 });
});
```

---

## 📊 로그 분석 예시

### 경로별 에러율 분석

```sql
SELECT
    path,
    COUNT(*) as total_requests,
    SUM(CASE WHEN level = 'ERROR' THEN 1 ELSE 0 END) as errors,
    ROUND(100.0 * SUM(CASE WHEN level = 'ERROR' THEN 1 ELSE 0 END) / COUNT(*), 2) as error_rate
FROM logs
WHERE path IS NOT NULL
GROUP BY path
ORDER BY error_rate DESC
LIMIT 10;
```

---

### HTTP 메서드별 평균 응답 시간

```sql
SELECT
    method,
    path,
    AVG(duration_ms) as avg_duration_ms,
    MAX(duration_ms) as max_duration_ms,
    COUNT(*) as request_count
FROM logs
WHERE method IS NOT NULL AND duration_ms IS NOT NULL
GROUP BY method, path
ORDER BY avg_duration_ms DESC
LIMIT 20;
```

---

### IP별 요청 수 (Rate Limiting 분석)

```sql
SELECT
    ip,
    COUNT(*) as request_count,
    COUNT(DISTINCT path) as unique_paths,
    MIN(created_at) as first_request,
    MAX(created_at) as last_request
FROM logs
WHERE ip IS NOT NULL
    AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY ip
ORDER BY request_count DESC
LIMIT 20;
```

---

## 🔧 고급 사용법

### 사용자 인증 정보 포함

```python
# FastAPI - JWT 토큰에서 user_id 추출
from fastapi import Depends
from fastapi.security import HTTPBearer

security = HTTPBearer()

@app.middleware("http")
async def log_context_middleware(request: Request, call_next):
    # 기본 HTTP 정보
    context = {
        "path": request.url.path,
        "method": request.method,
        "ip": request.client.host if request.client else None
    }

    # Authorization 헤더에서 user_id 추출
    auth_header = request.headers.get("authorization")
    if auth_header:
        try:
            token = auth_header.replace("Bearer ", "")
            payload = jwt.decode(token, SECRET_KEY)
            context["user_id"] = payload.get("user_id")
        except:
            pass

    AsyncLogClient.set_request_context(**context)

    try:
        return await call_next(request)
    finally:
        AsyncLogClient.clear_request_context()
```

---

### 분산 추적 (Distributed Tracing)

```python
# FastAPI - trace_id 전파
import uuid

@app.middleware("http")
async def log_context_middleware(request: Request, call_next):
    # 기존 trace_id 사용 또는 새로 생성
    trace_id = request.headers.get("x-trace-id") or str(uuid.uuid4())

    AsyncLogClient.set_request_context(
        path=request.url.path,
        method=request.method,
        ip=request.client.host if request.client else None,
        trace_id=trace_id  # ← 분산 추적용
    )

    # 응답 헤더에 trace_id 포함
    response = await call_next(request)
    response.headers["x-trace-id"] = trace_id

    AsyncLogClient.clear_request_context()
    return response
```

---

## ✅ 권장 사항

### 필수 포함 필드
- ✅ `path` - API 엔드포인트 식별
- ✅ `method` - HTTP 메서드
- ✅ `ip` - 클라이언트 추적 (Rate Limiting)

### 선택 포함 필드
- 🟡 `user_id` - 사용자별 로그 분석
- 🟡 `trace_id` - 분산 추적
- 🟡 `user_agent` - 클라이언트 종류 분석
- 🟡 `request_id` - 요청 고유 ID

### 주의사항
- ⚠️ **민감 정보 제외**: 패스워드, 토큰, 개인정보는 로그에 포함하지 마세요
- ⚠️ **쿼리 파라미터 주의**: URL에 민감 정보가 포함될 수 있습니다
- ⚠️ **성능**: 미들웨어는 모든 요청에서 실행되므로 가벼워야 합니다

---

## 🎯 다음 단계

1. ✅ **호출 위치 자동 추적** (완료) - function_name, file_path
2. ✅ **HTTP 경로 자동 수집** (완료) - path, method, ip
3. 🔜 **사용자 컨텍스트 관리** - user_id, trace_id 통합

---

## 📚 관련 문서

- [AUTO-CALLER-EXAMPLE.md](./AUTO-CALLER-EXAMPLE.md) - 호출 위치 자동 추적
- [FIELD-AUTO-COLLECTION.md](./FIELD-AUTO-COLLECTION.md) - 자동 수집 필드 분석
- [CODE-EXPLANATION.md](./CODE-EXPLANATION.md) - 코드 상세 설명
- [ENV-CONFIG-GUIDE.md](./ENV-CONFIG-GUIDE.md) - 환경 변수 설정
