# Log Save Server API 테스트 가이드

## 서버 정보

- **Base URL**: `http://localhost:8000`
- **Framework**: FastAPI
- **Features**: 배치 로그 수집, gzip 압축 지원, PostgreSQL 저장

---

## 엔드포인트 목록

### 1. Health Check
- **Method**: `GET`
- **Endpoint**: `/`
- **Description**: 서버 상태 확인

### 2. Batch Log Ingestion
- **Method**: `POST`
- **Endpoint**: `/logs`
- **Description**: 로그 배치 전송 (gzip 압축 지원)

### 3. Statistics
- **Method**: `GET`
- **Endpoint**: `/stats`
- **Description**: 로그 통계 조회

---

## 테스트 시나리오

### 시나리오 1: Health Check

**요청**:
```bash
curl http://localhost:8000/
```

**예상 응답**:
```json
{
  "status": "ok",
  "service": "log-server"
}
```

---

### 시나리오 2: 단일 백엔드 에러 로그

**설명**: 결제 API에서 발생한 데이터베이스 연결 타임아웃 에러

**요청**:
```bash
curl -X POST http://localhost:8000/logs \
  -H "Content-Type: application/json" \
  -d '{
  "logs": [
    {
      "level": "ERROR",
      "message": "Database connection timeout",
      "created_at": 1705305600.0,
      "log_type": "BACKEND",
      "service": "payment-api",
      "environment": "production",
      "service_version": "v2.5.3",
      "trace_id": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
      "user_id": "user_12345",
      "session_id": "sess_abc123def456",
      "error_type": "DatabaseConnectionError",
      "stack_trace": "Traceback (most recent call last):\n  File \"services/payment.py\", line 45, in process_payment\n    conn = db.connect()\nDatabaseConnectionError: Connection timeout after 5000ms",
      "path": "/api/v1/payment",
      "method": "POST",
      "function_name": "process_payment",
      "file_path": "services/payment/processor.py",
      "duration_ms": 5432.0,
      "metadata": {
        "performance": {
          "db_query_ms": 5432.0,
          "cache_hit": false
        },
        "http": {
          "request": {
            "query_params": {"user_id": "12345"},
            "body_size_bytes": 512
          },
          "response": {
            "status_code": 500
          }
        },
        "error_detail": {
          "category": "database",
          "subcategory": "connection_timeout",
          "severity": "high"
        }
      }
    }
  ]
}'
```

**예상 응답**:
```json
{
  "status": "ok",
  "count": 1
}
```

---

### 시나리오 3: 프론트엔드 에러 로그

**설명**: 체크아웃 페이지에서 발생한 JavaScript TypeError (같은 trace_id로 백엔드 에러와 연결)

**요청**:
```bash
curl -X POST http://localhost:8000/logs \
  -H "Content-Type: application/json" \
  -d '{
  "logs": [
    {
      "level": "ERROR",
      "message": "Cannot read property '\''price'\'' of undefined",
      "created_at": 1705305700.0,
      "log_type": "FRONTEND",
      "service": "web-app",
      "environment": "production",
      "service_version": "v1.2.0",
      "trace_id": "a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6",
      "user_id": "user_12345",
      "session_id": "sess_abc123def456",
      "error_type": "TypeError",
      "stack_trace": "TypeError: Cannot read property '\''price'\'' of undefined\n    at handleCheckout (checkout.js:42)\n    at onClick (Button.tsx:15)",
      "path": "/checkout",
      "action_type": "click",
      "function_name": "handleCheckout",
      "file_path": "src/pages/checkout/index.tsx",
      "metadata": {
        "client": {
          "browser": {"name": "Chrome", "version": "120.0.6099.109"},
          "device": {"type": "mobile", "model": "iPhone 15 Pro"},
          "screen": {"width": 393, "height": 852}
        },
        "action_detail": {
          "element_id": "checkout-button",
          "element_text": "결제하기"
        },
        "error_detail": {
          "category": "javascript",
          "recoverable": false
        }
      }
    }
  ]
}'
```

---

### 시나리오 4: 배치 로그 전송 (10개)

**설명**: 다양한 서비스와 로그 레벨을 포함한 배치 전송

**요청**:
```bash
curl -X POST http://localhost:8000/logs \
  -H "Content-Type: application/json" \
  -d '{
  "logs": [
    {
      "level": "INFO",
      "message": "User login successful",
      "log_type": "BACKEND",
      "service": "auth-service",
      "environment": "production",
      "service_version": "v1.0.0",
      "user_id": "user_001",
      "path": "/api/v1/auth/login",
      "method": "POST",
      "duration_ms": 45.2
    },
    {
      "level": "WARN",
      "message": "Slow database query detected",
      "log_type": "BACKEND",
      "service": "user-service",
      "environment": "production",
      "service_version": "v2.1.0",
      "path": "/api/v1/users",
      "method": "GET",
      "duration_ms": 1250.5,
      "metadata": {"performance": {"db_query_ms": 1200.0}}
    },
    {
      "level": "ERROR",
      "message": "Payment gateway timeout",
      "log_type": "BACKEND",
      "service": "payment-api",
      "environment": "production",
      "service_version": "v2.5.3",
      "error_type": "TimeoutError",
      "path": "/api/v1/payment/process",
      "method": "POST",
      "duration_ms": 30000.0
    },
    {
      "level": "INFO",
      "message": "Page view",
      "log_type": "FRONTEND",
      "service": "web-app",
      "environment": "production",
      "service_version": "v1.2.0",
      "path": "/dashboard",
      "action_type": "navigate"
    },
    {
      "level": "ERROR",
      "message": "Form validation failed",
      "log_type": "FRONTEND",
      "service": "web-app",
      "environment": "production",
      "service_version": "v1.2.0",
      "error_type": "ValidationError",
      "path": "/checkout",
      "action_type": "submit",
      "metadata": {"validation_errors": [{"field": "email", "message": "Invalid format"}]}
    },
    {
      "level": "DEBUG",
      "message": "Cache hit",
      "log_type": "BACKEND",
      "service": "product-service",
      "environment": "development",
      "service_version": "v0.5.0-dev",
      "path": "/api/v1/products/123",
      "method": "GET",
      "duration_ms": 5.1,
      "metadata": {"performance": {"cache_hit": true, "cache_time_ms": 2.3}}
    },
    {
      "level": "FATAL",
      "message": "Database connection pool exhausted",
      "log_type": "BACKEND",
      "service": "order-service",
      "environment": "production",
      "service_version": "v3.0.1",
      "error_type": "ConnectionPoolError",
      "path": "/api/v1/orders",
      "method": "POST"
    },
    {
      "level": "INFO",
      "message": "API request completed",
      "log_type": "BACKEND",
      "service": "notification-service",
      "environment": "staging",
      "service_version": "v1.5.0-rc1",
      "trace_id": "trace_xyz789",
      "path": "/api/v1/notifications/send",
      "method": "POST",
      "duration_ms": 120.8
    },
    {
      "level": "WARN",
      "message": "Rate limit approaching",
      "log_type": "BACKEND",
      "service": "api-gateway",
      "environment": "production",
      "service_version": "v4.2.0",
      "user_id": "user_999",
      "path": "/api/v1/data",
      "method": "GET",
      "metadata": {"rate_limit": {"current": 950, "max": 1000}}
    },
    {
      "level": "ERROR",
      "message": "Network request failed",
      "log_type": "FRONTEND",
      "service": "mobile-app",
      "environment": "production",
      "service_version": "v2.0.0",
      "error_type": "NetworkError",
      "path": "/profile",
      "action_type": "api_call",
      "metadata": {"client": {"network": {"type": "4g", "effective_type": "3g"}}}
    }
  ]
}'
```

**예상 응답**:
```json
{
  "status": "ok",
  "count": 10
}
```

---

### 시나리오 5: 성능 테스트 로그

**설명**: 다양한 응답 시간을 가진 API 성능 로그

**요청**:
```bash
curl -X POST http://localhost:8000/logs \
  -H "Content-Type: application/json" \
  -d '{
  "logs": [
    {
      "level": "INFO",
      "message": "API response time",
      "log_type": "BACKEND",
      "service": "payment-api",
      "environment": "production",
      "service_version": "v2.5.3",
      "path": "/api/v1/payment",
      "method": "POST",
      "duration_ms": 2500.0,
      "metadata": {
        "performance": {
          "db_query_ms": 1800.0,
          "external_api_ms": 600.0,
          "processing_ms": 100.0
        }
      }
    },
    {
      "level": "INFO",
      "message": "Fast API response",
      "log_type": "BACKEND",
      "service": "user-service",
      "environment": "production",
      "service_version": "v1.0.0",
      "path": "/api/v1/users/profile",
      "method": "GET",
      "duration_ms": 45.3,
      "metadata": {
        "performance": {
          "db_query_ms": 35.0,
          "cache_hit": true,
          "cache_time_ms": 2.1
        }
      }
    },
    {
      "level": "WARN",
      "message": "Slow query detected",
      "log_type": "BACKEND",
      "service": "order-service",
      "environment": "production",
      "service_version": "v3.0.1",
      "path": "/api/v1/orders/history",
      "method": "GET",
      "duration_ms": 5200.0,
      "metadata": {
        "performance": {
          "db_query_ms": 5000.0,
          "query": "SELECT * FROM orders WHERE user_id = $1 ORDER BY created_at DESC"
        }
      }
    }
  ]
}'
```

---

### 시나리오 6: 전체 트레이스 플로우 (Frontend → Backend)

**설명**: trace_id로 연결된 프론트엔드-백엔드 전체 흐름 추적

**요청**:
```bash
curl -X POST http://localhost:8000/logs \
  -H "Content-Type: application/json" \
  -d '{
  "logs": [
    {
      "level": "INFO",
      "message": "User clicked checkout button",
      "created_at": 1705305600.0,
      "log_type": "FRONTEND",
      "service": "web-app",
      "environment": "production",
      "service_version": "v1.2.0",
      "trace_id": "TRACE_CHECKOUT_ABC123",
      "user_id": "user_888",
      "session_id": "sess_xyz789",
      "path": "/checkout",
      "action_type": "click",
      "function_name": "handleCheckoutClick",
      "file_path": "src/components/CheckoutButton.tsx"
    },
    {
      "level": "INFO",
      "message": "Processing checkout request",
      "created_at": 1705305600.1,
      "log_type": "BACKEND",
      "service": "payment-api",
      "environment": "production",
      "service_version": "v2.5.3",
      "trace_id": "TRACE_CHECKOUT_ABC123",
      "user_id": "user_888",
      "session_id": "sess_xyz789",
      "path": "/api/v1/payment/checkout",
      "method": "POST",
      "function_name": "process_checkout",
      "file_path": "services/payment/checkout.py"
    },
    {
      "level": "ERROR",
      "message": "Payment validation failed",
      "created_at": 1705305600.5,
      "log_type": "BACKEND",
      "service": "payment-api",
      "environment": "production",
      "service_version": "v2.5.3",
      "trace_id": "TRACE_CHECKOUT_ABC123",
      "user_id": "user_888",
      "session_id": "sess_xyz789",
      "error_type": "ValidationError",
      "path": "/api/v1/payment/checkout",
      "method": "POST",
      "function_name": "validate_payment",
      "file_path": "services/payment/validator.py",
      "duration_ms": 450.0,
      "metadata": {
        "error_detail": {
          "validation_errors": [
            {"field": "card_number", "message": "Invalid card number"}
          ]
        }
      }
    },
    {
      "level": "ERROR",
      "message": "Checkout failed - invalid card",
      "created_at": 1705305600.6,
      "log_type": "FRONTEND",
      "service": "web-app",
      "environment": "production",
      "service_version": "v1.2.0",
      "trace_id": "TRACE_CHECKOUT_ABC123",
      "user_id": "user_888",
      "session_id": "sess_xyz789",
      "error_type": "CheckoutError",
      "path": "/checkout",
      "action_type": "error",
      "metadata": {
        "error_detail": {
          "message": "Payment validation failed"
        }
      }
    }
  ]
}'
```

**Text-to-SQL 질의 예시**:
```
"trace_id가 TRACE_CHECKOUT_ABC123인 전체 로그를 시간순으로 보여줘"
```

**예상 SQL**:
```sql
SELECT
  created_at,
  log_type,
  service,
  level,
  message,
  error_type
FROM logs
WHERE trace_id = 'TRACE_CHECKOUT_ABC123'
  AND deleted = FALSE
ORDER BY created_at ASC;
```

---

### 시나리오 7: 여러 서비스 에러 분석

**설명**: 동일 시간대 여러 서비스에서 발생한 에러

**요청**:
```bash
curl -X POST http://localhost:8000/logs \
  -H "Content-Type: application/json" \
  -d '{
  "logs": [
    {
      "level": "ERROR",
      "message": "Database connection failed",
      "log_type": "BACKEND",
      "service": "payment-api",
      "environment": "production",
      "service_version": "v2.5.3",
      "error_type": "DatabaseConnectionError",
      "path": "/api/v1/payment",
      "method": "POST"
    },
    {
      "level": "ERROR",
      "message": "Database connection failed",
      "log_type": "BACKEND",
      "service": "user-service",
      "environment": "production",
      "service_version": "v2.1.0",
      "error_type": "DatabaseConnectionError",
      "path": "/api/v1/users",
      "method": "GET"
    },
    {
      "level": "ERROR",
      "message": "Database connection failed",
      "log_type": "BACKEND",
      "service": "order-service",
      "environment": "production",
      "service_version": "v3.0.1",
      "error_type": "DatabaseConnectionError",
      "path": "/api/v1/orders",
      "method": "POST"
    },
    {
      "level": "FATAL",
      "message": "PostgreSQL server unreachable",
      "log_type": "BACKEND",
      "service": "auth-service",
      "environment": "production",
      "service_version": "v1.0.0",
      "error_type": "DatabaseConnectionError",
      "path": "/api/v1/auth/verify",
      "method": "POST"
    }
  ]
}'
```

**Text-to-SQL 질의 예시**:
```
"DatabaseConnectionError가 가장 많이 발생한 서비스는?"
```

**예상 SQL**:
```sql
SELECT
  service,
  COUNT(*) as error_count,
  MIN(created_at) as first_occurrence,
  MAX(created_at) as last_occurrence
FROM logs
WHERE error_type = 'DatabaseConnectionError'
  AND deleted = FALSE
GROUP BY service
ORDER BY error_count DESC;
```

---

### 시나리오 8: 통계 조회

**요청**:
```bash
curl http://localhost:8000/stats
```

**예상 응답**:
```json
{
  "total_logs": 1234,
  "level_distribution": [
    {"level": "INFO", "count": 800},
    {"level": "WARN", "count": 200},
    {"level": "ERROR", "count": 150},
    {"level": "DEBUG", "count": 50},
    {"level": "FATAL", "count": 34}
  ],
  "recent_errors_1h": 5
}
```

---

## Python으로 테스트하기

### 단일 로그 전송
```python
import requests
import time

log_data = {
    "logs": [{
        "level": "ERROR",
        "message": "Test error message",
        "log_type": "BACKEND",
        "service": "test-service",
        "environment": "development",
        "service_version": "v0.1.0",
        "created_at": time.time(),
        "path": "/api/test",
        "method": "GET"
    }]
}

response = requests.post("http://localhost:8000/logs", json=log_data)
print(response.json())
```

### 배치 로그 전송 (1000건)
```python
import requests
import time

logs = []
for i in range(1000):
    logs.append({
        "level": "INFO",
        "message": f"Test log {i}",
        "log_type": "BACKEND",
        "service": "batch-test",
        "environment": "development",
        "service_version": "v0.1.0",
        "created_at": time.time(),
        "path": "/api/test",
        "method": "GET"
    })

response = requests.post("http://localhost:8000/logs", json={"logs": logs})
print(f"Sent {response.json()['count']} logs")
```

---

## JavaScript/Node.js로 테스트하기

```javascript
const fetch = require('node-fetch');

async function sendLog() {
  const logData = {
    logs: [{
      level: "ERROR",
      message: "Test error from Node.js",
      log_type: "BACKEND",
      service: "nodejs-test",
      environment: "development",
      service_version: "v0.1.0",
      created_at: Date.now() / 1000,
      path: "/api/test",
      method: "POST"
    }]
  };

  const response = await fetch('http://localhost:8000/logs', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(logData)
  });

  const result = await response.json();
  console.log(result);
}

sendLog();
```

---

## gzip 압축 테스트

### Python
```python
import requests
import gzip
import json

log_data = {
    "logs": [{
        "level": "INFO",
        "message": "Compressed log",
        "log_type": "BACKEND",
        "service": "test-service",
        "environment": "production",
        "service_version": "v1.0.0"
    }]
}

# JSON → gzip 압축
json_data = json.dumps(log_data).encode('utf-8')
compressed_data = gzip.compress(json_data)

# 전송
response = requests.post(
    "http://localhost:8000/logs",
    data=compressed_data,
    headers={
        "Content-Type": "application/json",
        "Content-Encoding": "gzip"
    }
)

print(response.json())
```

---

## Text-to-SQL 질의 예시

### 1. 에러 분석
```
"지난 1시간 동안 발생한 에러가 몇 건이야?"
"어떤 에러가 가장 많이 발생했어? top 5 보여줘"
"DatabaseConnectionError가 어느 서비스에서 가장 많이 발생했어?"
```

### 2. 성능 분석
```
"평균 응답시간이 가장 긴 API 엔드포인트 5개 보여줘"
"/api/v1/payment 엔드포인트의 시간대별 평균 응답시간 보여줘"
"응답시간이 1초 이상인 요청들 보여줘"
```

### 3. 사용자 추적
```
"user_12345의 마지막 활동 로그 보여줘"
"user_888의 체크아웃 시도에서 무슨 일이 있었어?"
```

### 4. 분산 추적
```
"trace_id가 TRACE_CHECKOUT_ABC123인 전체 흐름 보여줘"
"특정 trace_id의 프론트엔드와 백엔드 로그를 모두 보여줘"
```

---

## 데이터베이스 직접 조회

서버 없이 PostgreSQL에서 직접 테스트:

```sql
-- 최근 에러 조회
SELECT * FROM logs
WHERE level = 'ERROR'
  AND deleted = FALSE
ORDER BY created_at DESC
LIMIT 10;

-- 서비스별 로그 개수
SELECT
  service,
  COUNT(*) as count
FROM logs
WHERE deleted = FALSE
GROUP BY service
ORDER BY count DESC;

-- 느린 요청 찾기
SELECT
  service,
  path,
  duration_ms,
  message
FROM logs
WHERE duration_ms > 1000
  AND deleted = FALSE
ORDER BY duration_ms DESC
LIMIT 20;
```

---

## 문제 해결

### 서버가 시작되지 않는 경우
```bash
# PostgreSQL 연결 확인
psql -h localhost -U postgres -d logs_db

# 환경 변수 확인
echo $DATABASE_HOST
echo $DATABASE_PORT
```

### 로그가 저장되지 않는 경우
```bash
# 서버 로그 확인
# FastAPI 콘솔 출력 확인

# PostgreSQL 로그 확인
SELECT COUNT(*) FROM logs;

# 최근 로그 확인
SELECT * FROM logs ORDER BY created_at DESC LIMIT 5;
```

---

## Postman 컬렉션

Postman MCP를 통해 생성된 컬렉션:
- **Collection ID**: `7ac39086-0af7-40c4-96a3-738c53629a07`
- **Workspace**: My Workspace

Postman에서 직접 확인하고 실행할 수 있습니다.

---

## 참고 문서

- [planning-draft.md](./planning-draft.md) - 프로젝트 전체 기획
- [docs/db-schema-analysis.md](./docs/db-schema-analysis.md) - 데이터베이스 스키마 상세
- [docs/scenarios-detailed.md](./docs/scenarios-detailed.md) - 38개 시나리오 목록
- [services/log-save-server/main.py](./services/log-save-server/main.py) - FastAPI 서버 소스
