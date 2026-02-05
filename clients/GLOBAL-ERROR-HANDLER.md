# 글로벌 에러 핸들러

모든 클라이언트 라이브러리에 **글로벌 에러 핸들러** 기능이 추가되었습니다.

이 기능을 활성화하면 try-catch나 명시적인 에러 로깅 코드 없이도 모든 에러가 자동으로 로그 서버에 저장됩니다.

---

## 기능 개요

### 자동으로 처리되는 에러

**JavaScript (Browser)**:
- `window.onerror` - 동기 에러 (Uncaught Errors)
- `window.onunhandledrejection` - 비동기 에러 (Unhandled Promise Rejections)

**JavaScript (Node.js)**:
- `process.on('uncaughtException')` - 동기 에러
- `process.on('unhandledRejection')` - 비동기 에러

**Python**:
- `sys.excepthook` - Uncaught Exceptions

### 자동 수집되는 정보

- 에러 메시지
- 스택 트레이스 (stack_trace)
- 에러 타입 (error_type)
- 발생 위치 (source, line, column)
- 타임스탬프 (created_at)
- 서비스 정보 (service, environment)

---

## 사용 방법

### JavaScript (Node.js)

```javascript
import { createLogClient } from 'log-collector-async';

const logger = createLogClient('http://localhost:8000', {
    service: 'my-app',
    environment: 'production',
    enableGlobalErrorHandler: true  // 활성화
});

// 이제 모든 에러가 자동으로 로깅됩니다
throw new Error('This will be automatically logged!');
Promise.reject('This too!');
```

### JavaScript (Browser)

```javascript
import { WebWorkerLogClient } from 'log-collector-async/browser';

const logger = new WebWorkerLogClient('http://localhost:8000', {
    service: 'web-app',
    enableGlobalErrorHandler: true  // 활성화
});

// 모든 에러가 자동으로 로깅됩니다
undefined.someMethod();  // TypeError - 자동 로깅
fetch('/invalid').then(r => r.notExist());  // Promise rejection - 자동 로깅
```

### Python

```python
from log_collector import AsyncLogClient

logger = AsyncLogClient(
    "http://localhost:8000",
    service="my-python-app",
    enable_global_error_handler=True  # 활성화
)

# 모든 에러가 자동으로 로깅됩니다
raise ValueError("This will be automatically logged!")
```

---

## 환경 변수로 활성화

`.env` 파일에 설정하면 코드 수정 없이 활성화 가능:

```bash
# JavaScript
ENABLE_GLOBAL_ERROR_HANDLER=true

# Python
ENABLE_GLOBAL_ERROR_HANDLER=true
```

그러면 다음처럼 옵션을 생략해도 자동으로 활성화됩니다:

```javascript
// enableGlobalErrorHandler 생략 - 환경 변수에서 읽음
const logger = createLogClient('http://localhost:8000', {
    service: 'my-app'
});
```

---

## 기본값: false

**중요**: 글로벌 에러 핸들러는 기본적으로 **비활성화** 상태입니다.

명시적으로 `true`로 설정해야만 작동합니다:

```javascript
// ❌ 비활성화 (기본값)
const logger = createLogClient('http://localhost:8000', {
    service: 'my-app'
});

// ✅ 활성화
const logger = createLogClient('http://localhost:8000', {
    service: 'my-app',
    enableGlobalErrorHandler: true
});
```

---

## 비활성화 방법

클라이언트를 `close()` 하면 글로벌 에러 핸들러도 자동으로 해제됩니다:

```javascript
await logger.close();  // 핸들러 자동 해제
```

Python의 경우도 동일:

```python
logger.close()  # 핸들러 자동 해제
```

---

## 기존 에러 핸들러와의 관계

### JavaScript

글로벌 에러 핸들러는 **기존 핸들러를 대체하지 않고 추가**합니다:

```javascript
// 기존 핸들러
window.onerror = (msg) => console.log('Custom handler:', msg);

// log-collector-async 초기화
const logger = createLogClient('...', { enableGlobalErrorHandler: true });

// 결과: 에러 발생 시
// 1. log-collector-async가 로그 서버에 전송
// 2. 기존 핸들러도 여전히 실행됨
```

### Python

Python은 기존 `sys.excepthook`을 저장했다가 순차적으로 호출합니다:

```python
import sys

# 기존 핸들러
def custom_handler(exc_type, exc_value, exc_traceback):
    print(f'Custom handler: {exc_value}')

sys.excepthook = custom_handler

# log-collector 초기화
logger = AsyncLogClient('...', enable_global_error_handler=True)

# 결과: 에러 발생 시
# 1. log-collector가 로그 서버에 전송
# 2. 기존 custom_handler도 호출됨
```

---

## 프로덕션 고려사항

### 언제 사용하면 좋은가?

✅ **권장**:
- 개발/테스트 환경
- 모니터링이 중요한 프로덕션 앱
- 에러 추적이 어려운 복잡한 시스템
- 마이크로서비스 환경에서 일관된 에러 로깅

⚠️ **주의**:
- 기존 에러 핸들러가 있는 프로젝트 (충돌 가능성)
- 민감한 에러 정보를 로깅하면 안 되는 경우
- 에러 발생률이 매우 높은 시스템 (로그 폭증)

### 보안 고려사항

에러 메시지에 민감한 정보가 포함될 수 있으니 주의:

```javascript
// ⚠️ 위험: 비밀번호가 에러 메시지에 포함될 수 있음
const password = "secret123";
throw new Error(`Login failed with password: ${password}`);

// ✅ 안전: 민감한 정보를 포함하지 않음
throw new Error('Login failed: Invalid credentials');
```

### 성능 영향

- 에러 핸들러 등록: ~0.1ms (초기화 시 1회)
- 에러 발생 시 로깅: ~0.01ms (비블로킹)
- 정상 실행 시: 0ms (오버헤드 없음)

---

## 예제: Express 앱

```javascript
import express from 'express';
import { createLogClient } from 'log-collector-async';

const app = express();

// 글로벌 에러 핸들러 활성화
const logger = createLogClient('http://localhost:8000', {
    service: 'express-api',
    enableGlobalErrorHandler: true
});

app.get('/test', (req, res) => {
    // 이 에러는 자동으로 로깅됩니다
    undefined.someMethod();
});

app.listen(3000, () => {
    logger.info('Server started', { port: 3000 });
});
```

---

## 예제: FastAPI 앱

```python
from fastapi import FastAPI
from log_collector import AsyncLogClient

app = FastAPI()

# 글로벌 에러 핸들러 활성화
logger = AsyncLogClient(
    "http://localhost:8000",
    service="fastapi-api",
    enable_global_error_handler=True
)

@app.get("/test")
async def test_endpoint():
    # 이 에러는 자동으로 로깅됩니다
    raise ValueError("Something went wrong!")

if __name__ == "__main__":
    import uvicorn
    logger.info("Server started", port=8000)
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

---

## 데이터베이스에서 확인

```sql
-- 자동으로 로깅된 에러들 확인
SELECT
    created_at,
    service,
    message,
    metadata->>'error_type' as error_type,
    metadata->>'source' as source,
    metadata->>'line' as line,
    stack_trace
FROM logs
WHERE level = 'ERROR'
  AND message LIKE '%Uncaught%'
ORDER BY created_at DESC
LIMIT 20;
```

---

## FAQ

### Q1: 기본값이 왜 false인가요?

A: 기존 프로젝트와의 호환성을 위해 명시적으로 활성화하도록 했습니다. 기존 에러 핸들러와 충돌할 수 있기 때문입니다.

### Q2: 에러가 두 번 로깅될 수 있나요?

A: 네, try-catch로 명시적으로 로깅하고 동시에 uncaught exception이 발생하면 두 번 로깅될 수 있습니다. 따라서 try-catch로 처리한 에러는 rethrow하지 않는 것을 권장합니다.

```javascript
// ❌ 중복 로깅 가능
try {
    somethingDangerous();
} catch (err) {
    logger.error('Failed', { error: err.message });
    throw err;  // 다시 throw하면 글로벌 핸들러에서도 로깅됨
}

// ✅ 단일 로깅
try {
    somethingDangerous();
} catch (err) {
    logger.error('Failed', { error: err.message });
    // throw하지 않으면 글로벌 핸들러는 작동 안 함
}
```

### Q3: 테스트 환경에서만 활성화할 수 있나요?

A: 네, 환경 변수를 사용하세요:

```bash
# .env.development
ENABLE_GLOBAL_ERROR_HANDLER=true

# .env.production
ENABLE_GLOBAL_ERROR_HANDLER=false
```

### Q4: 특정 에러만 제외하고 싶은데?

A: 현재는 모든 에러를 로깅합니다. 선택적 필터링이 필요하다면 기존 방식(try-catch + 명시적 로깅)을 사용하세요.

---

## 관련 문서

- [CLIENT-LIBRARIES.md](./CLIENT-LIBRARIES.md) - 클라이언트 라이브러리 개요
- [example_global_error_handler.js](./javascript/example_global_error_handler.js) - JavaScript 예제
- [example_global_error_handler.py](./python/example_global_error_handler.py) - Python 예제
