# Log Collector - JavaScript/Node.js Client

고성능 비동기 로그 수집 클라이언트 for JavaScript/Node.js

[![Node Version](https://img.shields.io/badge/node-12%2B-green)](https://nodejs.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)

## 📋 Prerequisites

Before using this library, ensure you have:

- **Node.js 14+** or **Browser** (modern browsers with Web Worker support)
- **Package manager**: npm or yarn
- **Log server running**: See [Log Save Server Setup](../../services/log-save-server/README.md)
- **PostgreSQL database**: For log storage (v12+)
- **Basic async knowledge**: Understanding of async/await and Promise patterns

## 🎯 Why Use This Library?

### The Problem
Traditional logging blocks your application, creating performance bottlenecks:
- Each log = 1 HTTP request = ~50ms blocked time
- 100 logs/sec = 5 seconds of blocking per second (impossible!)
- Application threads wait for network I/O
- Database connection pool exhaustion

### The Solution
Asynchronous batch logging with zero blocking:
- ✅ **~0.01ms per log** - App never blocks waiting for network
- ✅ **Batches 1000 logs** - Single HTTP request instead of 1000
- ✅ **Background workers** - Web Worker/Worker Threads handle transmission
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
- Quick debugging sessions - use console.log for speed
- Need real-time log streaming - use dedicated streaming solutions
- Cannot run log server infrastructure - use cloud logging services

## 🚀 Quick Start (30 seconds)

### Step 1: Install
```bash
npm install log-collector-async
# or
yarn add log-collector-async
```

### Step 2: Use in your app
```javascript
import { createLogClient } from 'log-collector-async';

// Initialize logger
const logger = createLogClient('http://localhost:8000');

// Send logs - non-blocking, ~0.01ms
logger.info('Hello world!', { user_id: '123', action: 'test' });
logger.warn('High memory usage', { memory_mb: 512 });
logger.error('Database error', { error: 'connection timeout' });

// Logs are batched and sent automatically every 1 second or 1000 logs
```

### Step 3: Check logs in database
```bash
psql -h localhost -U postgres -d logs_db \
  -c "SELECT * FROM logs ORDER BY created_at DESC LIMIT 5;"
```

**Want more details?** See [Framework Integration](#http-컨텍스트-자동-수집) below.

**Want a working example?** Check out [Demo Applications](#-live-demo).

## 📺 Live Demo

See working examples with full context tracking:

### JavaScript + Express
- **Location**: [tests/demo-app/backend/](../../tests/demo-app/backend/)
- **Features**: Login, CRUD operations, error handling, slow API testing
- **Run**: `node tests/demo-app/backend/server.js`

### Python + FastAPI
- **Location**: [tests/demo-app/backend-python/](../../tests/demo-app/backend-python/)
- **Features**: Same features but with Python
- **Run**: `python tests/demo-app/backend-python/server.py`

### Frontend Integration
- **Location**: [tests/demo-app/frontend/](../../tests/demo-app/frontend/)
- **Features**: Browser-based logging with proper CORS setup
- **Run**: Open `tests/demo-app/frontend/index.html` in browser

### Quick Demo Setup
```bash
# 1. Start log server (in Docker)
cd services/log-save-server
docker-compose up

# 2. Start backend (JavaScript or Python)
cd tests/demo-app/backend
node server.js

# 3. Open frontend
open ../frontend/index.html

# 4. Interact with app, then check logs
psql -h localhost -U postgres -d logs_db \
  -c "SELECT service, level, message FROM logs ORDER BY created_at DESC LIMIT 10;"
```

## 🔗 Integration with Full System

This client is part of a complete log analysis system. See the [main README](../../README.md) for the full picture.

### System Architecture

```
[Your App] → [JavaScript Client] → [Log Save Server] → [PostgreSQL] → [Analysis Server] → [Frontend]
```

### Related Components

- **Log Save Server**: Receives logs via HTTP POST ([README](../../services/log-save-server/README.md))
- **Log Analysis Server**: Text-to-SQL with Claude Sonnet 4.5 ([README](../../services/log-analysis-server/README.md))
- **Frontend Dashboard**: Svelte 5 web interface ([README](../../frontend/README.md))
- **Python Client**: Python async log collection ([README](../python/README.md))
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

- ⚡ **비블로킹 로깅** - 앱 블로킹 < 0.01ms (Web Worker/Worker Threads)
- 🚀 **배치 전송** - 1000건 or 1초마다 자동 전송
- 📦 **자동 압축** - gzip 압축으로 네트워크 비용 절감
- 🔄 **Graceful Shutdown** - 앱 종료 시 큐 자동 flush
- 🎯 **자동 필드 수집** - 호출 위치, HTTP 컨텍스트, 사용자 컨텍스트 자동 포함
- 🌐 **웹 프레임워크 통합** - Express, Fastify, Koa 지원
- 🔍 **분산 추적** - trace_id로 마이크로서비스 간 요청 추적

## 📦 Installation

```bash
npm install log-collector-async
# or
yarn add log-collector-async
```

## 💡 Basic Usage

### Node.js

```javascript
import { createLogClient } from 'log-collector-async';

// Initialize with options
const logger = createLogClient('http://localhost:8000', {
    service: 'my-service',
    environment: 'production',
    serviceVersion: 'v1.0.0'
});

// Send logs (non-blocking, batched automatically)
logger.info('Application started');
logger.warn('High memory usage detected', { memory_mb: 512 });
logger.error('Database connection failed', { db_host: 'localhost' });

// Automatic graceful shutdown on process exit
```

### Browser

```javascript
import { WebWorkerLogClient } from 'log-collector-async/browser';

const logger = new WebWorkerLogClient('http://localhost:8000', {
    service: 'web-app',
    environment: 'production'
});

logger.info('User action', { page: '/dashboard' });
```

### Environment Variables

`.env` file or environment variables (Vite, Webpack supported):
```bash
VITE_LOG_SERVER_URL=http://localhost:8000
VITE_SERVICE_NAME=payment-api
VITE_ENVIRONMENT=production
VITE_SERVICE_VERSION=v1.2.3
VITE_LOG_TYPE=BACKEND
```

```javascript
// Auto-load from environment variables
const logger = createLogClient();
```

## 🎯 Feature 1: 자동 호출 위치 추적

**모든 로그에 `function_name`, `file_path` 자동 포함!**

```javascript
function processPayment(amount) {
    logger.info('Processing payment', { amount });
    // → function_name="processPayment", file_path="/app/payment.js" 자동 포함!
}

// 비활성화도 가능
logger.log('INFO', 'Manual log', { autoCaller: false });
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

### Express 통합

```javascript
import express from 'express';
import crypto from 'crypto';
import { createLogClient } from 'log-collector-async';

const app = express();
const logger = createLogClient('http://localhost:8000');

// HTTP 컨텍스트 미들웨어 - 요청마다 컨텍스트 객체 생성
app.use((req, res, next) => {
    // 요청 컨텍스트를 req 객체에 저장
    req.logContext = {
        path: req.path,
        method: req.method,
        ip: req.ip,
        trace_id: req.headers['x-trace-id'] || crypto.randomUUID().replace(/-/g, '').substring(0, 32)
    };

    // 사용자 ID가 있으면 추가
    if (req.headers['x-user-id']) {
        req.logContext.user_id = req.headers['x-user-id'];
    }

    // 요청 시작 로그
    logger.info('Request received', req.logContext);

    const startTime = Date.now();

    // 응답 완료 시 로그
    res.on('finish', () => {
        const duration_ms = Date.now() - startTime;
        logger.info('Request completed', {
            ...req.logContext,
            status_code: res.statusCode,
            duration_ms
        });
    });

    next();
});

app.get('/api/users/:userId', (req, res) => {
    // 라우트 핸들러에서 컨텍스트를 메타데이터로 전달
    logger.info(`Fetching user ${req.params.userId}`, {
        ...req.logContext,
        user_id_param: req.params.userId
    });
    // → path, method, ip, trace_id 모두 자동 포함!
    res.json({ userId: req.params.userId });
});

app.post('/api/todos', (req, res) => {
    logger.info('Creating todo', {
        ...req.logContext,
        todo_text: req.body.text
    });
    // ... handle todo creation
    res.json({ success: true });
});

app.listen(3000);
```

### Fastify 통합

```javascript
import Fastify from 'fastify';
import crypto from 'crypto';
import { createLogClient } from 'log-collector-async';

const fastify = Fastify();
const logger = createLogClient('http://localhost:8000');

// onRequest Hook: HTTP 컨텍스트 생성
fastify.addHook('onRequest', async (request, reply) => {
    // 요청 컨텍스트를 request 객체에 저장
    request.logContext = {
        path: request.url,
        method: request.method,
        ip: request.ip,
        trace_id: request.headers['x-trace-id'] || crypto.randomUUID().replace(/-/g, '').substring(0, 32)
    };

    // 사용자 ID가 있으면 추가
    if (request.headers['x-user-id']) {
        request.logContext.user_id = request.headers['x-user-id'];
    }

    // 요청 시작 시간 기록
    request.startTime = Date.now();

    // 요청 시작 로그
    logger.info('Request received', request.logContext);
});

// onResponse Hook: 응답 완료 로그
fastify.addHook('onResponse', async (request, reply) => {
    const duration_ms = Date.now() - request.startTime;
    logger.info('Request completed', {
        ...request.logContext,
        status_code: reply.statusCode,
        duration_ms
    });
});

fastify.get('/api/users/:userId', async (request, reply) => {
    // 라우트 핸들러에서 컨텍스트를 메타데이터로 전달
    logger.info(`Fetching user ${request.params.userId}`, {
        ...request.logContext,
        user_id_param: request.params.userId
    });
    // → path, method, ip, trace_id 모두 자동 포함!
    return { userId: request.params.userId };
});

fastify.post('/api/todos', async (request, reply) => {
    logger.info('Creating todo', {
        ...request.logContext,
        todo_text: request.body.text
    });
    // ... handle todo creation
    return { success: true };
});

await fastify.listen({ port: 3000 });
```

### Koa 통합

```javascript
import Koa from 'koa';
import crypto from 'crypto';
import { createLogClient } from 'log-collector-async';

const app = new Koa();
const logger = createLogClient('http://localhost:8000');

// HTTP 컨텍스트 미들웨어
app.use(async (ctx, next) => {
    // 요청 컨텍스트를 ctx.state에 저장
    ctx.state.logContext = {
        path: ctx.path,
        method: ctx.method,
        ip: ctx.ip,
        trace_id: ctx.headers['x-trace-id'] || crypto.randomUUID().replace(/-/g, '').substring(0, 32)
    };

    // 사용자 ID가 있으면 추가
    if (ctx.headers['x-user-id']) {
        ctx.state.logContext.user_id = ctx.headers['x-user-id'];
    }

    // 요청 시작 시간 기록
    const startTime = Date.now();

    // 요청 시작 로그
    logger.info('Request received', ctx.state.logContext);

    try {
        await next();

        // 응답 완료 로그
        const duration_ms = Date.now() - startTime;
        logger.info('Request completed', {
            ...ctx.state.logContext,
            status_code: ctx.status,
            duration_ms
        });
    } catch (err) {
        // 에러 발생 로그
        logger.error('Request failed', {
            ...ctx.state.logContext,
            error: err.message,
            stack_trace: err.stack
        });
        throw err;
    }
});

// 라우트 핸들러
app.use(async (ctx) => {
    if (ctx.path === '/api/users' && ctx.method === 'GET') {
        logger.info('Fetching users', ctx.state.logContext);
        // → path, method, ip, trace_id 모두 자동 포함!
        ctx.body = { users: [] };
    } else if (ctx.path === '/api/todos' && ctx.method === 'POST') {
        logger.info('Creating todo', {
            ...ctx.state.logContext,
            todo_text: ctx.request.body.text
        });
        ctx.body = { success: true };
    } else {
        ctx.body = { message: 'Hello' };
    }
});

app.listen(3000);
```

## 👤 Feature 3: 사용자 컨텍스트 관리

**`user_id`, `trace_id`, `session_id` 등을 모든 로그에 자동 포함!**

### runWithUserContext 방식 (권장)

```javascript
import { createLogClient } from 'log-collector-async';

const logger = createLogClient('http://localhost:8000');

// 특정 블록에만 컨텍스트 적용
logger.constructor.runWithUserContext({
    user_id: 'user_123',
    trace_id: 'trace_xyz',
    session_id: 'sess_abc'
}, () => {
    logger.info('User logged in');
    // → user_id, trace_id, session_id 자동 포함!

    processPayment();
    logger.info('Payment completed');
    // → 하위 함수에서도 자동으로 컨텍스트 유지!
});

// 블록 벗어나면 자동 초기화
```

### 비동기 함수와 함께 사용

```javascript
await logger.constructor.runWithUserContext({
    user_id: 'user_456',
    trace_id: 'trace_async_123'
}, async () => {
    logger.info('Async operation started');
    // → user_id, trace_id 자동 포함

    await fetchUserData();
    await processData();

    logger.info('Async operation completed');
    // → 같은 컨텍스트 유지됨
});
```

### 중첩 컨텍스트 (자동 병합)

```javascript
// 외부: tenant_id
logger.constructor.runWithUserContext({ tenant_id: 'tenant_1' }, () => {
    logger.info('Tenant operation');
    // → tenant_id="tenant_1"

    // 내부: user_id 추가
    logger.constructor.runWithUserContext({ user_id: 'user_123' }, () => {
        logger.info('User operation');
        // → tenant_id="tenant_1", user_id="user_123" 둘 다 포함!
    });
});
```

### 분산 추적 (Distributed Tracing)

```javascript
import { v4 as uuidv4 } from 'uuid';

function handleRequest() {
    // 요청마다 고유한 trace_id 생성 (32자, 대시 제거)
    const traceId = uuidv4().replace(/-/g, '');

    logger.constructor.runWithUserContext({
        trace_id: traceId,
        user_id: 'user_123'
    }, () => {
        logger.info('Request received');
        callServiceA();  // Service A 호출
        callServiceB();  // Service B 호출
        logger.info('Request completed');
        // → 모든 로그가 같은 trace_id로 추적 가능!
    });
}
```

**PostgreSQL 분석:**
```sql
-- trace_id로 전체 요청 흐름 추적
SELECT created_at, service, function_name, message, duration_ms
FROM logs
WHERE metadata->>'trace_id' = 'your-trace-id'
ORDER BY created_at;
```

### Set/Clear 방식

```javascript
// 로그인 시
logger.constructor.setUserContext({
    user_id: 'user_123',
    session_id: 'sess_abc'
});

logger.info('User action');
// → user_id, session_id 자동 포함

// 로그아웃 시
logger.constructor.clearUserContext();
```

## 🔧 고급 기능

### 타이머 측정

```javascript
// 수동 타이머
const timer = logger.startTimer();
const result = expensiveOperation();
logger.endTimer(timer, 'INFO', 'Operation completed');
// → duration_ms 자동 계산

// 함수 래퍼 (동기/비동기 자동 감지)
const result = logger.measure(() => expensiveOperation());
```

### 에러 추적

```javascript
try {
    riskyOperation();
} catch (err) {
    logger.errorWithTrace('Operation failed', err);
    // → stack_trace, error_type, function_name, file_path 자동 포함!
}
```

### 수동 Flush

```javascript
// 중요한 로그를 즉시 전송
logger.flush();
```

### 클라이언트 종료

```javascript
// Graceful shutdown
await logger.close();
```

## ⚙️ 설정 옵션

```javascript
const logger = createLogClient('http://localhost:8000', {
    service: 'payment-api',
    environment: 'production',
    serviceVersion: 'v1.2.3',
    logType: 'BACKEND',
    batchSize: 1000,          // 배치 크기 (기본: 1000)
    flushInterval: 1000,      // Flush 간격 ms (기본: 1000)
    enableCompression: true   // gzip 압축 (기본: true)
});
```

## 📊 성능

- **앱 블로킹**: < 0.01ms per log (Web Worker/Worker Threads)
- **처리량**: > 10,000 logs/sec
- **메모리**: < 10MB (1000건 큐)
- **압축률**: ~70% (100건 이상 시 자동 압축)

## 🧪 테스트

```bash
# 단위 테스트
npm test

# 통합 테스트 (로그 서버 필요)
npm run test:integration

# 커버리지
npm run test:coverage
```

## 📝 로그 레벨

```javascript
logger.trace('Trace message');    // TRACE
logger.debug('Debug message');    // DEBUG
logger.info('Info message');      // INFO
logger.warn('Warning message');   // WARN
logger.error('Error message');    // ERROR
logger.fatal('Fatal message');    // FATAL
```

## 🔍 PostgreSQL 쿼리 예제

### 사용자별 로그 조회
```sql
SELECT * FROM logs
WHERE metadata->>'user_id' = 'user_123'
ORDER BY created_at DESC
LIMIT 100;
```

### 에러 발생률
```sql
SELECT
    metadata->>'path' as path,
    metadata->>'method' as method,
    COUNT(*) as total_requests,
    COUNT(CASE WHEN level = 'ERROR' THEN 1 END) as errors,
    ROUND(100.0 * COUNT(CASE WHEN level = 'ERROR' THEN 1 END) / COUNT(*), 2) as error_rate
FROM logs
WHERE created_at > NOW() - INTERVAL '1 hour'
GROUP BY metadata->>'path', metadata->>'method'
ORDER BY error_rate DESC;
```

### 함수별 성능
```sql
SELECT
    function_name,
    COUNT(*) as calls,
    AVG((metadata->>'duration_ms')::numeric) as avg_ms,
    MAX((metadata->>'duration_ms')::numeric) as max_ms
FROM logs
WHERE metadata->>'duration_ms' IS NOT NULL
GROUP BY function_name
ORDER BY avg_ms DESC;
```

## 🚨 주의사항

1. **민감한 정보 포함 금지**
   ```javascript
   // ❌ 절대 안 됨!
   logger.info('Login', { password: 'secret' });

   // ✅ 식별자만 사용
   logger.info('Login successful', { user_id: 'user_123' });
   ```

2. **과도한 로깅 피하기**
   ```javascript
   // ❌ 루프 내부에서 과도한 로깅
   for (let i = 0; i < 10000; i++) {
       logger.debug(`Processing ${i}`);
   }

   // ✅ 주요 이벤트만 로깅
   logger.info('Batch processing started', { count: 10000 });
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
   - OR manually flush: `await logger.close()`

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
Error: connect ECONNREFUSED 127.0.0.1:8000
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

### CORS errors (browser only)

**Symptoms**:
```
Access to fetch at 'http://localhost:8000/logs' from origin 'http://localhost:3000'
has been blocked by CORS policy
```

**Cause**: Log server missing CORS configuration

**Solution**: Ensure log server has CORS middleware enabled (already configured in log-save-server)

---

### High memory usage

**Symptoms**:
- Application memory grows over time
- Eventually crashes with OOM error

**Cause**: Batch size too large or flush interval too long

**Solution**: Reduce batching parameters
```javascript
const logger = createLogClient('http://localhost:8000', {
    batchSize: 500,      // Reduce from 1000
    flushInterval: 500   // Reduce from 1000
});
```

---

### Logs delayed or not sent on app shutdown

**Symptoms**:
- Last few logs before shutdown are missing
- Queue not flushing properly

**Cause**: App exits before background worker flushes

**Solution**: Call close before exit
```javascript
// Graceful shutdown
process.on('SIGTERM', async () => {
    await logger.close();  // Flushes queue before closing
    process.exit(0);
});

// Or manually before exit
await logger.close();
```

---

### Worker thread/Web Worker not starting

**Symptoms**:
- Console warnings about worker initialization
- Logs sent synchronously instead of async

**Cause**: Worker script not found or CORS issues in browser

**Solution (Node.js)**: Ensure worker script is included in deployment
```javascript
// worker-node.js should be in node_modules/log-collector-async/dist/
```

**Solution (Browser)**: Serve worker script with correct MIME type
```javascript
// Ensure worker.js is served as application/javascript
```

## 📋 Version Compatibility

| Component | Minimum Version | Tested Version | Notes |
|-----------|----------------|----------------|-------|
| **This Client** | 1.0.0 | 1.0.0 | Current release |
| **Log Save Server** | 1.0.0 | 1.0.0 | FastAPI 0.104+ |
| **PostgreSQL** | 12 | 15 | Requires JSONB support |
| **Log Analysis Server** | 1.0.0 | 1.0.0 | Optional (for Text-to-SQL) |
| **Node.js** | 14 | 18 | Runtime environment |

### Breaking Changes

- **v1.0.0**: Initial release

### Upgrade Guide

No upgrades yet. This is the initial release.

## 📚 추가 문서

- [HTTP-CONTEXT-GUIDE.md](../HTTP-CONTEXT-GUIDE.md) - HTTP 컨텍스트 완전 가이드
- [USER-CONTEXT-GUIDE.md](../USER-CONTEXT-GUIDE.md) - 사용자 컨텍스트 완전 가이드
- [FIELD-AUTO-COLLECTION.md](../FIELD-AUTO-COLLECTION.md) - 자동 필드 수집 상세

## 🤝 기여

기여는 언제나 환영합니다!

## 📄 라이선스

MIT License - 자유롭게 사용하세요!

---

**Made with ❤️ by Log Analysis System Team**
