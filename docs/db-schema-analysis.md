# 데이터베이스 스키마 상세 분석

## 목차

1. [현재 스키마 분석](#1-현재-스키마-분석)
2. [필드별 상세 분석](#2-필드별-상세-분석)
3. [문제점 및 개선안](#3-문제점-및-개선안)
4. [인덱스 최적화 전략](#4-인덱스-최적화-전략)
5. [파티셔닝 전략](#5-파티셔닝-전략)
6. [개선된 최종 스키마](#6-개선된-최종-스키마)
7. [마이그레이션 계획](#7-마이그레이션-계획)

---

## 1. 현재 스키마 분석

### 1.1 전체 구조

현재 스키마는 **단일 통합 테이블 방식**으로 프론트엔드와 백엔드 로그를 모두 수용합니다.

**장점:**
- ✅ 쿼리 간소화: JOIN 불필요
- ✅ 일관된 데이터 모델
- ✅ 프론트-백엔드 연계 분석 용이 (trace_id 기반)
- ✅ 스키마 관리 단순화

**단점:**
- ⚠️ NULL 필드 다수 발생 (저장 공간 비효율)
- ⚠️ 특화된 인덱스 설계 어려움
- ⚠️ 대용량 처리 시 성능 저하 가능성
- ⚠️ 필드 용도 혼재로 유지보수 복잡도 증가

### 1.2 필드 분류

현재 스키마의 필드를 기능별로 분류:

| 분류 | 필드 개수 | 필드 목록 |
|-----|---------|----------|
| **기본 정보** | 4 | id, timestamp, level, log_type |
| **서비스 식별** | 3 | service, environment, version |
| **추적 정보** | 3 | trace_id, user_id, session_id |
| **에러 정보** | 3 | error_type, message, stack_trace |
| **위치** | 3 | path, method, action_type |
| **코드 위치** | 2 | function_name, file_path |
| **성능** | 1 | duration_ms |
| **관리** | 1 | deleted |
| **확장** | 1 | metadata (JSONB) |

**총 필드 수: 21개 (더 심플!)**

**참고:**
- `path`: 백엔드 endpoint 또는 프론트엔드 page path (log_type으로 구분)
- 세부 성능, 브라우저, 디바이스, 비즈니스 컨텍스트는 metadata에 저장
- 로그 삭제는 soft delete (deleted 플래그)

---

## 2. 필드별 상세 분석

### 2.1 기본 정보 필드

#### `id` (BIGSERIAL PRIMARY KEY)
- **용도**: 로그 고유 식별자
- **적절성**: ✅ BIGSERIAL은 대용량 로그에 적합
- **분석**:
  - BIGSERIAL 범위: -9,223,372,036,854,775,808 ~ 9,223,372,036,854,775,807
  - 초당 1만 건 기준: 약 2,900만 년 사용 가능
- **개선 제안**: 없음 (현재 최적)

#### `timestamp` (TIMESTAMP NOT NULL)
- **용도**: 로그 발생 시각
- **적절성**: ⚠️ 타임존 고려 필요
- **분석**:
  - 현재: `TIMESTAMP` (타임존 없음)
  - 글로벌 서비스 고려 시 `TIMESTAMP WITH TIME ZONE` 권장
- **개선 제안**:
  ```sql
  timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW()
  ```
- **근거**:
  - 글로벌 서비스 확장 시 타임존 혼란 방지
  - 서버 타임존 변경 시에도 일관성 유지
  - 약 8바이트로 동일한 저장 공간

#### `level` (VARCHAR(10))
- **용도**: 로그 레벨 (INFO, WARN, ERROR, DEBUG)
- **적절성**: ✅ 표준 로그 레벨 수용
- **분석**:
  - 일반적 로그 레벨: DEBUG(5자), INFO(4자), WARN(4자), ERROR(5자), FATAL(5자), TRACE(5자)
  - VARCHAR(10) 충분
- **개선 제안**: ENUM 타입으로 변경 고려
  ```sql
  CREATE TYPE log_level AS ENUM ('TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL');
  level log_level NOT NULL DEFAULT 'INFO'
  ```
- **근거**:
  - 저장 공간 절약 (VARCHAR(10) → 1바이트)
  - 데이터 무결성 강화 (잘못된 값 입력 방지)
  - 인덱스 효율 향상

#### `log_type` (VARCHAR(20) NOT NULL)
- **용도**: 로그 출처 구분 (BACKEND, FRONTEND)
- **적절성**: ✅ 기본 구분에 충분
- **분석**:
  - 현재 값: BACKEND(7자), FRONTEND(8자)
  - 향후 확장: MOBILE(6자), IOT(3자) 추가 가능
- **개선 제안**: ENUM 타입 + 확장 가능성 고려
  ```sql
  CREATE TYPE source_type AS ENUM ('BACKEND', 'FRONTEND', 'MOBILE', 'IOT', 'WORKER', 'CRONJOB');
  log_type source_type NOT NULL
  ```

### 2.2 서비스 식별 필드

#### `service` (VARCHAR(50))
- **용도**: 서비스 이름 (payment-api, user-service 등)
- **적절성**: ✅ 마이크로서비스 이름 수용 충분
- **분석**:
  - 일반적 서비스명 길이: 10-30자
  - 예시: payment-api(11자), user-authentication-service(28자)
- **개선 제안**:
  ```sql
  service VARCHAR(100) NOT NULL  -- NULL 허용 제거
  ```
- **근거**:
  - 모든 로그는 출처 서비스 필수
  - 긴 서비스명 수용 (kubernetes deployment name 등)
  - NOT NULL 제약으로 데이터 품질 향상

#### `environment` (VARCHAR(20))
- **용도**: 실행 환경 (production, staging, development)
- **적절성**: ✅ 표준 환경 구분 충분
- **개선 제안**: ENUM + NOT NULL
  ```sql
  CREATE TYPE env_type AS ENUM ('production', 'staging', 'development', 'test', 'local');
  environment env_type NOT NULL DEFAULT 'development'
  ```
- **근거**:
  - 표준화된 환경 구분
  - 오타 방지 (producton → production)
  - 환경별 필터링 성능 향상

#### `service_version` (VARCHAR(50))
- **용도**: 서비스 버전 (Semantic Versioning)
- **적절성**: ✅ 버전 추적에 충분
- **분석**:
  - Semantic Versioning 형식: v1.2.3, v2.0.0-beta.1
  - Git tag와 1:1 매핑 가능
  - 배포 추적 및 에러 분석에 활용
- **개선 제안**: NOT NULL + DEFAULT
  ```sql
  service_version VARCHAR(50) NOT NULL DEFAULT 'v0.0.0-dev'
  ```
- **근거**:
  - 심플하고 명확한 버전 관리
  - pyproject.toml, package.json에서 자동 읽기 가능
  - Git tag와 완벽한 매핑
  - 복잡한 build_id, git hash 불필요 (오버엔지니어링 방지)

### 2.3 추적 정보 필드

#### `user_id` (VARCHAR(100))
- **용도**: 사용자 식별자
- **적절성**: ✅ UUID, 이메일, 숫자 ID 모두 수용
- **분석**:
  - UUID: 36자
  - 이메일: 평균 25자, 최대 254자
  - 숫자 ID: 1-20자
- **개선 제안**: 길이 확장 고려
  ```sql
  user_id VARCHAR(255)  -- 이메일 전체 수용
  ```
- **인덱스 고려**:
  ```sql
  CREATE INDEX idx_user_id ON logs(user_id) WHERE user_id IS NOT NULL;
  ```

#### `session_id` (VARCHAR(100))
- **용도**: 세션 식별자 (웹 세션, 모바일 앱 세션)
- **적절성**: ✅ UUID 기반 세션 ID 수용
- **개선 제안**: 없음 (현재 적절)

#### `trace_id` (VARCHAR(100))
- **용도**: 분산 추적 ID (프론트-백엔드 연결)
- **적절성**: ✅ OpenTelemetry 표준 수용
- **분석**:
  - OpenTelemetry Trace ID: 32자 (16바이트 hex)
  - Jaeger Trace ID: 32자
  - AWS X-Ray Trace ID: 35자
- **개선 제안**: 없음 (현재 충분)
- **중요도**: ⭐⭐⭐⭐⭐ (프론트-백엔드 연계 필수)

#### `request_id` (VARCHAR(100))
- **용도**: 요청 고유 식별자
- **적절성**: ⚠️ trace_id와 중복
- **분석**:
  - `trace_id`: 전체 분산 추적 (여러 서비스 걸쳐)
  - `request_id`: 단일 서비스 내 요청 식별
- **개선 제안**: trace_id로 통합
  - request_id 제거하고 trace_id만 사용
  - 서비스 내 세부 추적은 function_name, file_path로 충분
- **권장**: **trace_id 단일 사용** - 심플하고 실용적

### 2.4 에러 정보 필드

#### `error_type` (VARCHAR(100))
- **용도**: 에러 클래스명 (DatabaseConnectionError, ValidationError)
- **적절성**: ✅ 대부분의 에러 클래스명 수용
- **분석**:
  - 일반적 에러명: 20-50자
  - 예시: DatabaseConnectionTimeoutError(32자)
- **개선 제안**: 길이 확장
  ```sql
  error_type VARCHAR(200)  -- 중첩 에러명 수용
  ```

#### `error_code` (VARCHAR(50))
- **용도**: 에러 코드 (DB_CONN_TIMEOUT, AUTH_FAILED)
- **적절성**: ✅ 표준 에러 코드 수용
- **분석**:
  - 일반적 에러 코드: 10-30자
  - HTTP 상태 코드: 3자
  - 커스텀 코드: 평균 20자
- **개선 제안**: 네이밍 명확화
  ```sql
  application_error_code VARCHAR(100)  -- 애플리케이션 정의 에러 코드
  ```
- **추가 필드 제안**:
  ```sql
  http_status_code INTEGER  -- HTTP 응답 코드 (200, 404, 500)
  ```

#### `message` (TEXT)
- **용도**: 에러 메시지 또는 로그 메시지
- **적절성**: ✅ TEXT 타입으로 제한 없음
- **개선 제안**: 없음 (현재 최적)
- **주의사항**:
  - 민감 정보 포함 가능성 (PII 필터링 필요)
  - 과도한 길이 로그 제한 (max 10KB 등)

#### `stack_trace` (TEXT)
- **용도**: 에러 스택 트레이스
- **적절성**: ✅ TEXT 타입 적절
- **분석**:
  - 일반적 스택 트레이스: 1-20KB
  - 깊은 재귀: 100KB+
- **개선 제안**: 저장 전략 고려
  ```sql
  stack_trace TEXT,                           -- 짧은 스택 (< 10KB)
  stack_trace_storage_url VARCHAR(500)        -- S3 등 외부 저장소 URL (큰 스택)
  ```
- **근거**: 대용량 스택 트레이스는 DB 외부 저장으로 비용 절감

### 2.5 코드 위치 필드

#### `function_name` (VARCHAR(300))
- **용도**: 에러 발생 함수명 (프론트엔드, 백엔드 공통)
- **적절성**: ✅ 대부분의 함수명 수용
- **예시**:
  - 백엔드: `process_payment`, `validate_user`, `handle_webhook`
  - 프론트엔드: `handleSubmit`, `onButtonClick`, `fetchUserData`
- **분석**:
  - JavaScript 람다: `() => { ... }` (익명 함수는 `<anonymous>`)
  - Python 데코레이터: `@decorator` 적용된 함수명
  - 길이: 대부분 50자 이내, 긴 경우 300자 수용
- **추출 방법**: Stack trace 파싱

#### `file_path` (VARCHAR(1000))
- **용도**: 소스 파일 경로 (프론트엔드, 백엔드 공통)
- **적절성**: ✅ 깊은 디렉토리 구조 수용
- **예시**:
  - 백엔드: `services/payment/processor.py`, `api/v1/handlers/user.go`
  - 프론트엔드: `src/components/auth/LoginForm.tsx`, `pages/checkout/index.js`
- **분석**:
  - Unix 경로 최대: 4096자
  - 일반적 경로: 50-200자
  - 프로젝트 루트부터 상대 경로 권장
- **참고**: line_number는 제외
  - 코드 수정 시마다 변경되어 과거 로그와 매칭 불가
  - file_path + function_name으로 충분
- **추출 방법**: Stack trace 파싱

### 2.6 위치 정보 (통합)

#### `path` (VARCHAR(500))
- **용도**: 경로 - 백엔드 API endpoint 또는 프론트엔드 page path
- **적절성**: ✅ 통합으로 심플화
- **분석**:
  - 백엔드 예시: `/api/v1/payment`, `/users/123`
  - 프론트엔드 예시: `/checkout`, `/dashboard`
  - log_type으로 구분 가능
- **장점**:
  - 필드 1개 절약
  - Text-to-SQL 단순화 (CASE 문 불필요)
  - 쿼리 심플: `WHERE path LIKE '%payment%'`
- **개선 제안**: 전체 URL은 metadata로
  ```sql
  path VARCHAR(500),                          -- /api/v1/payment 또는 /checkout
  metadata JSONB                              -- {"full_url": "https://...", "query_params": {...}}
  ```

#### `method` (VARCHAR(10))
- **용도**: HTTP 메서드 (GET, POST, PUT, DELETE) - 백엔드 전용
- **적절성**: ✅ 표준 메서드 수용
- **개선 제안**: ENUM 타입
  ```sql
  CREATE TYPE http_method AS ENUM ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS');
  method http_method
  ```

### 2.7 프론트엔드 특화 필드

#### `action_type` (VARCHAR(50))
- **용도**: 사용자 액션 (click, submit, navigate) - 프론트엔드 전용
- **적절성**: ✅ 일반적 액션 수용
- **개선 제안**: 표준화된 액션 타입
  ```sql
  action_type VARCHAR(50),                    -- click, submit, navigate, error
  ```
- **상세 정보**: metadata로
  ```json
  {
    "action_detail": {
      "element_id": "checkout-button",
      "element_text": "결제하기"
    }
  }
  ```

#### browser, device, screen 정보
- **권장**: metadata로 이동
- **근거**:
  - 모든 프론트엔드 로그에 필수는 아님
  - 필요할 때만 수집 (브라우저 호환성 이슈 추적 시)
  - JSONB로 유연하게 저장
- **metadata 예시**:
  ```json
  {
    "browser": {
      "name": "Chrome",
      "version": "120.0.0",
      "engine": "Blink"
    },
    "device": {
      "type": "mobile",
      "model": "iPhone 15 Pro"
    },
    "screen": {
      "width": 1920,
      "height": 1080,
      "viewport_width": 1340,
      "viewport_height": 768
    },
    "user_agent": "Mozilla/5.0 ..."
  }
  ```

### 2.8 확장 메타데이터 필드

#### `metadata` (JSONB)
- **용도**: 유연한 확장 데이터 저장
- **적절성**: ✅ PostgreSQL JSONB 최적
- **분석**:
  - 성능: JSONB는 바이너리 포맷으로 빠른 검색
  - 인덱스: 필요시 GIN 인덱스 지원
  - 유연성: 스키마 변경 없이 필드 추가
  - 필요한 정보만 선택적 저장

---

#### metadata 표준 구조 (상세)

**1. 성능 메트릭 (performance)**
```json
{
  "performance": {
    // 백엔드 타이밍
    "db_query_ms": 120.5,           // DB 쿼리 시간
    "db_connection_ms": 5.2,        // DB 커넥션 획득 시간
    "cache_query_ms": 10.3,         // 캐시 조회 시간
    "cache_hit": true,              // 캐시 히트 여부
    "external_api_ms": 450.0,       // 외부 API 호출 시간
    "external_api_name": "payment-gateway",  // 호출한 API 이름
    "queue_wait_ms": 15.0,          // 큐 대기 시간
    "serialization_ms": 8.5,        // 직렬화 시간

    // 리소스 사용량
    "memory_mb": 256,               // 메모리 사용량
    "cpu_percent": 45.2,            // CPU 사용률
    "thread_count": 4,              // 스레드 수
    "goroutine_count": 128,         // Go 루틴 수 (Go)

    // 프론트엔드 타이밍
    "dom_load_ms": 1200,            // DOM 로드 시간
    "render_ms": 350,               // 렌더링 시간
    "api_call_ms": 800,             // API 호출 시간
    "first_paint_ms": 500,          // First Paint
    "first_contentful_paint_ms": 650  // FCP
  }
}
```

**2. HTTP 요청/응답 상세 (http)**
```json
{
  "http": {
    "request": {
      "headers": {
        "content-type": "application/json",
        "authorization": "Bearer [REDACTED]"
      },
      "query_params": {
        "page": "1",
        "limit": "20",
        "filter": "active"
      },
      "body_size_bytes": 1024,
      "ip": "203.0.113.42",         // 필요시 (프라이버시 주의)
      "user_agent": "Mozilla/5.0 ..."
    },
    "response": {
      "status_code": 200,
      "headers": {
        "content-type": "application/json"
      },
      "body_size_bytes": 8192
    }
  }
}
```

**3. 브라우저/디바이스 정보 (client)**
```json
{
  "client": {
    "browser": {
      "name": "Chrome",
      "version": "120.0.6099.109",
      "major_version": 120,
      "engine": "Blink"
    },
    "device": {
      "type": "mobile",             // desktop, mobile, tablet
      "vendor": "Apple",
      "model": "iPhone 15 Pro",
      "os": "iOS",
      "os_version": "17.2"
    },
    "screen": {
      "width": 1920,
      "height": 1080,
      "pixel_ratio": 2.0,           // Retina 등
      "orientation": "portrait"     // portrait, landscape
    },
    "viewport": {
      "width": 393,
      "height": 852
    },
    "network": {
      "type": "4g",                 // wifi, 4g, 5g, slow-2g
      "effective_type": "4g",
      "downlink": 10.5,             // Mbps
      "rtt": 50                     // Round Trip Time (ms)
    }
  }
}
```

**4. 비즈니스 컨텍스트 (business)**
```json
{
  "business": {
    // 주문/결제
    "order_id": "ORD-2024-12345",
    "transaction_id": "TXN-ABC123",
    "payment_method": "credit_card",
    "amount": 99.99,
    "currency": "USD",

    // 상품
    "product_ids": ["P001", "P002"],
    "product_names": ["Product A", "Product B"],
    "category": "electronics",

    // 사용자 행동
    "referrer": "https://google.com",
    "campaign": "summer_sale_2024",
    "utm_source": "facebook",
    "utm_medium": "cpc",
    "utm_campaign": "retargeting"
  }
}
```

**5. 에러 상세 정보 (error_detail)**
```json
{
  "error_detail": {
    "error_id": "ERR-20240115-001",  // 에러 추적 ID
    "category": "database",           // database, network, validation, auth
    "subcategory": "connection_timeout",
    "severity": "high",               // low, medium, high, critical
    "recoverable": false,             // 복구 가능 여부
    "retry_count": 3,                 // 재시도 횟수
    "retry_after_ms": [100, 200, 400], // 재시도 간격

    // 에러 컨텍스트
    "query": "SELECT * FROM users WHERE id = $1",  // 실패한 쿼리 (민감정보 제거)
    "params": ["[REDACTED]"],
    "constraint_name": "users_email_unique",  // DB 제약 조건
    "validation_errors": [
      {"field": "email", "message": "Invalid format"},
      {"field": "age", "message": "Must be >= 18"}
    ],

    // 원인 체인
    "caused_by": {
      "error_type": "ConnectionError",
      "message": "Connection refused",
      "service": "postgres"
    }
  }
}
```

**6. 기술 컨텍스트 (tech)**
```json
{
  "tech": {
    // 프로세스 정보
    "process_id": 12345,
    "thread_id": "thread-42",
    "worker_id": "worker-3",
    "container_id": "abc123def456",
    "pod_name": "payment-api-7d9f8b-xyz",
    "node_name": "k8s-node-2",

    // 런타임
    "runtime": "Node.js",
    "runtime_version": "20.10.0",
    "framework": "Express",
    "framework_version": "4.18.2",

    // 데이터베이스
    "db_pool_size": 10,
    "db_pool_available": 7,
    "db_connection_id": "conn-789",

    // 인프라
    "region": "us-west-2",
    "availability_zone": "us-west-2a",
    "instance_type": "t3.medium"
  }
}
```

**7. 사용자 액션 상세 (action_detail)**
```json
{
  "action_detail": {
    // 클릭 이벤트
    "element_id": "checkout-button",
    "element_class": "btn btn-primary",
    "element_text": "결제하기",
    "element_xpath": "/html/body/div[1]/button",

    // 폼 제출
    "form_id": "payment-form",
    "form_fields": ["email", "card_number", "cvv"],  // 값은 제외!
    "form_validation_errors": ["Invalid card number"],

    // 페이지 전환
    "previous_page": "/cart",
    "navigation_type": "link",        // link, back, forward, reload

    // 사용자 입력
    "input_length": 15,                // 입력 길이 (내용은 제외)
    "keyboard_shortcut": "Ctrl+S"
  }
}
```

**8. 보안/프라이버시 (security)**
```json
{
  "security": {
    "auth_method": "jwt",              // jwt, oauth, session
    "auth_provider": "google",         // google, github, email
    "token_type": "access_token",
    "token_expires_at": "2024-01-15T12:00:00Z",
    "permission_level": "user",        // admin, user, guest
    "scopes": ["read:profile", "write:posts"],

    // 보안 이벤트
    "failed_login_attempts": 2,
    "last_failed_at": "2024-01-15T11:55:00Z",
    "suspicious_activity": false,
    "rate_limit_exceeded": false,

    // PII 처리
    "pii_redacted": true,
    "redacted_fields": ["email", "phone", "address"],
    "data_classification": "internal"  // public, internal, confidential
  }
}
```

**9. 실험/기능 플래그 (experiments)**
```json
{
  "experiments": {
    "ab_tests": {
      "checkout_flow_v2": "variant_b",
      "new_payment_ui": "control"
    },
    "feature_flags": {
      "new_dashboard": true,
      "beta_features": false,
      "dark_mode": true
    },
    "cohort": "power_users",
    "segment": "premium_subscribers"
  }
}
```

**10. 커스텀/기타 (custom)**
```json
{
  "custom": {
    // 프로젝트별 커스텀 데이터
    "deployment_id": "deploy-2024-01-15-001",
    "release_version": "v2.5.3",
    "build_number": "1234",

    // 태그
    "tags": ["critical", "payment", "needs-review"],

    // 알림
    "alert_sent": true,
    "alert_channels": ["slack", "email"],
    "oncall_engineer": "john@example.com",

    // 기타
    "notes": "Customer reported issue during checkout",
    "ticket_id": "JIRA-12345"
  }
}
```

---

#### 사용 예시

**백엔드 API 에러:**
```json
{
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
    "subcategory": "query_timeout",
    "severity": "high",
    "query": "SELECT * FROM orders WHERE user_id = $1"
  }
}
```

**프론트엔드 클릭 에러:**
```json
{
  "client": {
    "browser": {"name": "Safari", "version": "17.2"},
    "device": {"type": "mobile", "model": "iPhone 15"}
  },
  "action_detail": {
    "element_id": "payment-button",
    "element_text": "결제하기"
  },
  "error_detail": {
    "category": "javascript",
    "message": "Cannot read property 'price' of undefined",
    "recoverable": false
  }
}
```

---

#### 쿼리 예시

```sql
-- 특정 브라우저 에러
SELECT * FROM logs
WHERE metadata->'client'->'browser'->>'name' = 'Safari'
  AND level = 'ERROR';

-- 느린 DB 쿼리
SELECT * FROM logs
WHERE (metadata->'performance'->>'db_query_ms')::float > 1000
ORDER BY created_at DESC;

-- 실험 그룹별 에러율
SELECT
    metadata->'experiments'->'ab_tests'->>'checkout_flow_v2' as variant,
    COUNT(*) FILTER (WHERE level = 'ERROR') as errors,
    COUNT(*) as total
FROM logs
WHERE metadata->'experiments'->'ab_tests' ? 'checkout_flow_v2'
GROUP BY variant;
```

---

## 3. 문제점 및 개선안

### 3.1 중복 필드 문제

#### 문제 1: `request_id` vs `trace_id` 중복

**현재 상황:**
- 둘 다 요청 추적 용도
- 차이점 불명확

**해결 방안:**
```sql
-- trace_id만 사용 (request_id 제거)
trace_id VARCHAR(32),                       -- 전체 분산 추적 ID
```

**근거:**
- trace_id로 프론트엔드 → 백엔드 전체 흐름 추적 가능
- 서비스 내 세부 추적은 기존 필드로 충분:
  - service: 어느 서비스
  - function_name: 어느 함수
  - file_path: 정확한 위치
- OpenTelemetry의 span_id는 오버엔지니어링 (function_name이 대체 가능)

#### 문제 2: `error_code` vs HTTP 상태 코드 혼재

**현재 상황:**
- error_code: 애플리케이션 에러 코드
- HTTP 상태 코드 저장 필드 없음

**해결 방안:**
```sql
http_status_code INTEGER,                   -- HTTP 응답 코드 (200, 404, 500)
application_error_code VARCHAR(100),        -- 앱 정의 에러 (DB_CONN_TIMEOUT)
grpc_status_code INTEGER,                   -- gRPC 상태 코드
error_category VARCHAR(50)                  -- 에러 분류 (network, database, auth)
```

### 3.2 누락 필드 문제

#### 누락 1: 응답 크기 및 비용 관리

**필요성:**
- 대용량 로그 식별
- 저장 비용 최적화
- 비정상적 크기 로그 탐지

**추가 필드:**
```sql
-- 크기 정보
request_size_bytes INTEGER,                 -- 요청 크기
response_size_bytes INTEGER,                -- 응답 크기
log_size_bytes INTEGER,                     -- 로그 자체 크기

-- 비용 관리
storage_tier VARCHAR(20),                   -- hot, warm, cold
retention_days INTEGER DEFAULT 90,          -- 보관 일수
archived_at TIMESTAMP,                      -- 아카이브 시각
archive_location VARCHAR(500)               -- S3 bucket path
```

#### 누락 2: 민감 정보 처리

**필요성:**
- GDPR, CCPA 등 규제 준수
- PII 필터링 추적
- 데이터 거버넌스

**추가 필드:**
```sql
-- 프라이버시
is_pii_filtered BOOLEAN DEFAULT FALSE,      -- PII 필터링 여부
redacted_fields TEXT[],                     -- 삭제된 필드 목록
data_classification VARCHAR(20),            -- public, internal, confidential, restricted
consent_granted BOOLEAN,                    -- 사용자 동의 여부
gdpr_applicable BOOLEAN                     -- GDPR 적용 대상 여부
```

#### 누락 3: 성능 메트릭 구조화

**현재 문제:**
- metadata JSONB에 비정형으로 저장
- 쿼리 성능 저하

**해결 방안:**
```sql
-- 성능 메트릭 (자주 조회되는 항목은 별도 컬럼)
duration_ms DECIMAL(10, 3),                 -- 전체 처리 시간
db_query_time_ms DECIMAL(10, 3),            -- DB 쿼리 시간
cache_time_ms DECIMAL(10, 3),               -- 캐시 조회 시간
external_api_time_ms DECIMAL(10, 3),        -- 외부 API 호출 시간
queue_wait_time_ms DECIMAL(10, 3),          -- 큐 대기 시간

-- 리소스 사용량
memory_usage_mb INTEGER,                    -- 메모리 사용량
cpu_usage_percent DECIMAL(5, 2),            -- CPU 사용률
thread_count INTEGER,                       -- 스레드 수
connection_pool_size INTEGER                -- DB 커넥션 풀 크기
```

### 3.3 데이터 타입 개선

#### VARCHAR → ENUM 변환

**변환 대상:**
```sql
-- 기존
level VARCHAR(10)
log_type VARCHAR(20)
environment VARCHAR(20)
method VARCHAR(10)

-- 개선 (ENUM)
CREATE TYPE log_level AS ENUM ('TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL');
CREATE TYPE source_type AS ENUM ('BACKEND', 'FRONTEND', 'MOBILE', 'IOT', 'WORKER', 'CRONJOB');
CREATE TYPE env_type AS ENUM ('production', 'staging', 'development', 'test', 'local');
CREATE TYPE http_method AS ENUM ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS');

level log_level NOT NULL DEFAULT 'INFO',
log_type source_type NOT NULL,
environment env_type NOT NULL DEFAULT 'development',
method http_method
```

**효과:**
- 저장 공간: VARCHAR(10) 10바이트 → ENUM 1바이트 (90% 절감)
- 성능: 인덱스 크기 감소, 정렬 속도 향상
- 무결성: 잘못된 값 입력 방지

#### TIMESTAMP → TIMESTAMPTZ

```sql
-- 기존
timestamp TIMESTAMP NOT NULL

-- 개선
created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
indexed_at TIMESTAMPTZ,                     -- 로그 인덱싱 시각
processed_at TIMESTAMPTZ                    -- 로그 처리 시각
```

### 3.4 NOT NULL 제약 추가

**현재 문제:**
- 대부분의 필드가 NULL 허용
- 데이터 품질 저하

**개선 방안:**
```sql
-- 필수 필드 (NOT NULL 추가)
timestamp TIMESTAMPTZ NOT NULL DEFAULT NOW(),
level log_level NOT NULL DEFAULT 'INFO',
log_type source_type NOT NULL,
service VARCHAR(100) NOT NULL,              -- 서비스는 필수
environment env_type NOT NULL DEFAULT 'development',
message TEXT NOT NULL                       -- 로그 메시지는 필수

-- 선택 필드 (NULL 허용)
user_id VARCHAR(255),
session_id VARCHAR(100),
trace_id VARCHAR(32),
error_type VARCHAR(200),
-- 기타 특화 필드들...
```

---

## 4. 인덱스 최적화 전략

### 4.1 현재 인덱스 분석

```sql
CREATE INDEX idx_timestamp ON logs(timestamp DESC);
CREATE INDEX idx_log_type ON logs(log_type);
CREATE INDEX idx_service_level ON logs(service, level);
CREATE INDEX idx_trace_id ON logs(trace_id) WHERE trace_id IS NOT NULL;
CREATE INDEX idx_user_session ON logs(user_id, session_id);
CREATE INDEX idx_error_type ON logs(error_type) WHERE error_type IS NOT NULL;
```

**문제점:**
- ⚠️ 단일 컬럼 인덱스 위주 (복합 쿼리 비효율)
- ⚠️ 시계열 특성 미반영 (최신 로그 조회 최적화 부족)
- ⚠️ JSONB 인덱스 없음 (metadata 검색 느림)

### 4.2 쿼리 패턴 분석

**일반적 쿼리 패턴:**
1. 시간 범위 + 서비스 + 레벨 필터
2. 에러 분석 (error_type + service + 시간)
3. 사용자 추적 (user_id + 시간)
4. 성능 분석 (path + duration_ms)
5. 분산 추적 (trace_id)

### 4.3 최적화된 인덱스 전략

#### 4.3.1 복합 인덱스 (Composite Index)

```sql
-- 시계열 + 서비스 + 레벨 (가장 빈번한 쿼리)
CREATE INDEX idx_service_level_time
ON logs(service, level, created_at DESC)
WHERE level IN ('ERROR', 'WARN');

-- 에러 분석 (에러 타입 + 서비스 + 시간)
CREATE INDEX idx_error_service_time
ON logs(error_type, service, created_at DESC)
WHERE error_type IS NOT NULL;

-- 사용자 추적 (user_id + 시간)
CREATE INDEX idx_user_time
ON logs(user_id, created_at DESC)
WHERE user_id IS NOT NULL;

-- 엔드포인트 성능 (endpoint + 시간)
CREATE INDEX idx_endpoint_time
ON logs(endpoint, created_at DESC)
WHERE endpoint IS NOT NULL;

-- 환경별 필터링 (environment + service + 시간)
CREATE INDEX idx_env_service_time
ON logs(environment, service, created_at DESC);
```

#### 4.3.2 부분 인덱스 (Partial Index)

**목적**: 특정 조건의 로그만 인덱싱하여 크기 절감

```sql
-- 에러 로그만 (전체의 ~5%)
CREATE INDEX idx_error_logs
ON logs(service, created_at DESC)
WHERE level IN ('ERROR', 'FATAL');

-- 느린 요청만 (duration > 1000ms)
CREATE INDEX idx_slow_requests
ON logs(endpoint, duration_ms, created_at DESC)
WHERE duration_ms > 1000;

-- 특정 환경만 (production)
CREATE INDEX idx_production_logs
ON logs(service, level, created_at DESC)
WHERE environment = 'production';

-- 프론트엔드 에러만
CREATE INDEX idx_frontend_errors
ON logs(page_path, created_at DESC)
WHERE log_type = 'FRONTEND' AND level = 'ERROR';
```

#### 4.3.3 JSONB 인덱스

```sql
-- GIN 인덱스 (전체 metadata 검색)
CREATE INDEX idx_metadata_gin
ON logs USING GIN (metadata);

-- 특정 키 인덱스 (자주 조회되는 키)
CREATE INDEX idx_metadata_duration
ON logs ((metadata->>'duration_ms'))
WHERE metadata->>'duration_ms' IS NOT NULL;

CREATE INDEX idx_metadata_order_id
ON logs ((metadata->>'order_id'))
WHERE metadata->>'order_id' IS NOT NULL;

-- JSONB 경로 인덱스
CREATE INDEX idx_metadata_tags
ON logs USING GIN ((metadata->'tags'));
```

#### 4.3.4 표현식 인덱스 (Expression Index)

```sql
-- 날짜 기반 집계 (일별, 시간별)
CREATE INDEX idx_date_trunc_day
ON logs (DATE_TRUNC('day', created_at), service);

CREATE INDEX idx_date_trunc_hour
ON logs (DATE_TRUNC('hour', created_at), service, level);

-- 대소문자 무관 검색
CREATE INDEX idx_service_lower
ON logs (LOWER(service));

-- 도메인 추출 (URL에서)
CREATE INDEX idx_endpoint_domain
ON logs ((split_part(endpoint, '/', 1)));
```

### 4.4 인덱스 우선순위

| 우선순위 | 인덱스 | 예상 크기 | 활용도 |
|--------|-------|----------|-------|
| 🔴 P0 | idx_service_level_time | 큼 | 매우 높음 |
| 🔴 P0 | idx_error_service_time | 중간 | 매우 높음 |
| 🔴 P0 | idx_user_time | 큼 | 높음 |
| 🟡 P1 | idx_endpoint_time | 큼 | 높음 |
| 🟡 P1 | idx_metadata_gin | 매우 큼 | 중간 |
| 🟢 P2 | idx_slow_requests | 작음 | 중간 |
| 🟢 P2 | idx_date_trunc_hour | 큼 | 낮음 |

### 4.5 인덱스 유지보수

```sql
-- 인덱스 사용 통계 조회
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE schemaname = 'public'
ORDER BY idx_scan ASC;

-- 사용되지 않는 인덱스 찾기
SELECT
    schemaname,
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexrelid)) as index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND schemaname = 'public'
ORDER BY pg_relation_size(indexrelid) DESC;

-- 인덱스 재구축 (주기적 실행)
REINDEX TABLE logs;

-- 통계 정보 업데이트
ANALYZE logs;
```

---

## 5. 파티셔닝 전략

### 5.1 파티셔닝 필요성

**로그 데이터 특성:**
- 시계열 데이터 (시간순 삽입)
- 최신 데이터 집중 조회
- 오래된 데이터 아카이빙

**기대 효과:**
- 쿼리 성능 향상 (파티션 프루닝)
- 유지보수 간소화 (파티션 단위 삭제/아카이브)
- 인덱스 크기 감소

### 5.2 파티셔닝 전략 선택

#### 옵션 1: 월별 파티셔닝 (권장)

**적합한 경우:**
- 월간 로그 볼륨: 1억 건 미만
- 쿼리 범위: 일반적으로 최근 1-7일

**구현:**
```sql
-- 부모 테이블 (파티션 기준: created_at)
CREATE TABLE logs (
    id BIGSERIAL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    -- 기타 필드들...
    PRIMARY KEY (id, created_at)
) PARTITION BY RANGE (created_at);

-- 월별 파티션 생성
CREATE TABLE logs_2024_01 PARTITION OF logs
FOR VALUES FROM ('2024-01-01') TO ('2024-02-01');

CREATE TABLE logs_2024_02 PARTITION OF logs
FOR VALUES FROM ('2024-02-01') TO ('2024-03-01');

CREATE TABLE logs_2024_03 PARTITION OF logs
FOR VALUES FROM ('2024-03-01') TO ('2024-04-01');

-- 자동 파티션 생성 (pg_partman 확장 사용)
CREATE EXTENSION pg_partman;

SELECT create_parent(
    'public.logs',
    'created_at',
    'native',
    'monthly',
    p_premake := 3,                         -- 3개월 미리 생성
    p_start_partition := '2024-01-01'
);
```

#### 옵션 2: 주별 파티셔닝

**적합한 경우:**
- 주간 로그 볼륨: 1천만 ~ 1억 건
- 빠른 아카이빙 필요 (주 단위)

```sql
CREATE TABLE logs_2024_w01 PARTITION OF logs
FOR VALUES FROM ('2024-01-01') TO ('2024-01-08');

CREATE TABLE logs_2024_w02 PARTITION OF logs
FOR VALUES FROM ('2024-01-08') TO ('2024-01-15');
```

#### 옵션 3: 일별 파티셔닝

**적합한 경우:**
- 일간 로그 볼륨: 1억 건 이상
- 실시간 아카이빙 필요

```sql
CREATE TABLE logs_2024_01_01 PARTITION OF logs
FOR VALUES FROM ('2024-01-01') TO ('2024-01-02');

CREATE TABLE logs_2024_01_02 PARTITION OF logs
FOR VALUES FROM ('2024-01-02') TO ('2024-01-03');
```

### 5.3 파티션별 인덱스

```sql
-- 각 파티션에 자동으로 인덱스 생성
CREATE INDEX ON logs (service, level, created_at DESC);
CREATE INDEX ON logs (error_type, created_at DESC) WHERE error_type IS NOT NULL;

-- 파티션별로 idx_logs_2024_01_service_level_created_at,
-- idx_logs_2024_02_service_level_created_at 자동 생성
```

### 5.4 파티션 관리 자동화

```sql
-- 자동 파티션 생성 함수
CREATE OR REPLACE FUNCTION create_monthly_partitions()
RETURNS void AS $$
DECLARE
    partition_date DATE;
    partition_name TEXT;
    start_date TEXT;
    end_date TEXT;
BEGIN
    -- 다음 3개월 파티션 생성
    FOR i IN 0..2 LOOP
        partition_date := DATE_TRUNC('month', CURRENT_DATE + (i || ' months')::INTERVAL);
        partition_name := 'logs_' || TO_CHAR(partition_date, 'YYYY_MM');
        start_date := TO_CHAR(partition_date, 'YYYY-MM-DD');
        end_date := TO_CHAR(partition_date + INTERVAL '1 month', 'YYYY-MM-DD');

        EXECUTE format('
            CREATE TABLE IF NOT EXISTS %I PARTITION OF logs
            FOR VALUES FROM (%L) TO (%L)
        ', partition_name, start_date, end_date);
    END LOOP;
END;
$$ LANGUAGE plpgsql;

-- 매월 1일 자동 실행 (pg_cron 사용)
CREATE EXTENSION pg_cron;

SELECT cron.schedule(
    'create-partitions',
    '0 0 1 * *',                            -- 매월 1일 00:00
    'SELECT create_monthly_partitions()'
);
```

### 5.5 파티션 아카이빙 및 삭제

```sql
-- 오래된 파티션 분리 (detach)
ALTER TABLE logs DETACH PARTITION logs_2023_01;

-- S3 등으로 백업
COPY logs_2023_01 TO PROGRAM 'gzip > /backup/logs_2023_01.csv.gz' WITH CSV HEADER;

-- 또는 외부 테이블로 변환 (aws_s3 확장)
SELECT aws_s3.query_export_to_s3(
    'SELECT * FROM logs_2023_01',
    aws_commons.create_s3_uri(
        'my-bucket',
        'logs/2023/01/logs.csv.gz',
        'us-east-1'
    )
);

-- 파티션 삭제
DROP TABLE logs_2023_01;

-- 자동 아카이빙 스크립트 (Python 예시)
-- scripts/archive_old_partitions.py
```

### 5.6 파티션 프루닝 검증

```sql
-- EXPLAIN으로 파티션 프루닝 확인
EXPLAIN (ANALYZE, BUFFERS)
SELECT COUNT(*)
FROM logs
WHERE created_at >= '2024-03-01'
  AND created_at < '2024-03-02'
  AND level = 'ERROR';

-- 결과 예시:
-- Aggregate  (cost=... rows=1)
--   ->  Append  (cost=...)
--         ->  Seq Scan on logs_2024_03  (actual rows=...)
--               Filter: (level = 'ERROR')
--
-- 파티션 프루닝 작동: logs_2024_01, logs_2024_02는 스캔 안 함
```

---

## 6. 개선된 최종 스키마

### 6.1 완전한 스키마 정의

```sql
-- ENUM 타입 정의
CREATE TYPE log_level AS ENUM ('TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL');
CREATE TYPE source_type AS ENUM ('BACKEND', 'FRONTEND', 'MOBILE', 'IOT', 'WORKER', 'CRONJOB');
CREATE TYPE env_type AS ENUM ('production', 'staging', 'development', 'test', 'local');
CREATE TYPE http_method AS ENUM ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS', 'TRACE', 'CONNECT');

-- 메인 로그 테이블
CREATE TABLE logs (
    -- 기본 정보
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level log_level NOT NULL DEFAULT 'INFO',
    log_type source_type NOT NULL,

    -- 서비스 식별
    service VARCHAR(100) NOT NULL,
    environment env_type NOT NULL DEFAULT 'development',
    service_version VARCHAR(50) NOT NULL DEFAULT 'v0.0.0-dev',

    -- 분산 추적
    trace_id VARCHAR(32),
    user_id VARCHAR(255),
    session_id VARCHAR(100),

    -- 에러 정보
    error_type VARCHAR(200),
    message TEXT NOT NULL,
    stack_trace TEXT,

    -- 위치 정보 (통합)
    path VARCHAR(500),              -- 백엔드: /api/v1/payment, 프론트엔드: /checkout
    method http_method,             -- 백엔드 전용: GET, POST, PUT, DELETE
    action_type VARCHAR(50),        -- 프론트엔드 전용: click, submit, navigate

    -- 코드 위치
    function_name VARCHAR(300),     -- 함수명 (프론트: handleSubmit, 백: process_payment)
    file_path VARCHAR(1000),        -- 파일 경로 (프론트: src/LoginForm.tsx, 백: services/payment.py)

    -- 성능
    duration_ms DECIMAL(10, 3),

    -- 관리
    deleted BOOLEAN NOT NULL DEFAULT FALSE,

    -- 확장 메타데이터 (상세 정보는 여기에)
    metadata JSONB
);

-- 코멘트
COMMENT ON TABLE logs IS '통합 로그 테이블 (프론트엔드 + 백엔드)';
COMMENT ON COLUMN logs.path IS '경로: 백엔드는 API endpoint, 프론트엔드는 page path';
COMMENT ON COLUMN logs.function_name IS '함수명: stack trace에서 추출 (프론트/백 공통)';
COMMENT ON COLUMN logs.file_path IS '파일 경로: stack trace에서 추출 (프론트/백 공통)';
COMMENT ON COLUMN logs.deleted IS 'Soft delete 플래그 (true = 삭제됨)';
COMMENT ON COLUMN logs.metadata IS '확장 데이터: 성능 메트릭, 브라우저 정보, 비즈니스 컨텍스트 등';
```

### 6.2 핵심 인덱스 (4개만!)

```sql
-- 1. 서비스/레벨/시간 (가장 빈번한 쿼리)
CREATE INDEX idx_service_level_time
ON logs(service, level, created_at DESC)
WHERE deleted = FALSE;

-- 2. 에러 추적
CREATE INDEX idx_error_time
ON logs(error_type, created_at DESC)
WHERE error_type IS NOT NULL AND deleted = FALSE;

-- 3. 사용자 추적
CREATE INDEX idx_user_time
ON logs(user_id, created_at DESC)
WHERE user_id IS NOT NULL AND deleted = FALSE;

-- 4. 분산 추적 (trace_id)
CREATE INDEX idx_trace
ON logs(trace_id)
WHERE trace_id IS NOT NULL AND deleted = FALSE;
```

**참고:**
- 모든 인덱스에 `WHERE deleted = FALSE` 조건 포함
- metadata 검색이 필요하면 나중에 GIN 인덱스 추가 가능
- 성능 문제가 실제로 발생하면 그때 인덱스 추가

### 6.3 로그 관리

#### Soft Delete (삭제된 로그 처리)
```sql
-- 로그 "삭제" (실제로는 플래그만 설정)
UPDATE logs
SET deleted = TRUE
WHERE created_at < NOW() - INTERVAL '90 days';

-- 삭제된 로그 제외하고 조회 (기본)
SELECT * FROM logs
WHERE deleted = FALSE
  AND level = 'ERROR';

-- 영구 삭제 (필요시에만, 주기적으로 배치 실행)
DELETE FROM logs
WHERE deleted = TRUE
  AND created_at < NOW() - INTERVAL '1 year';
```

#### 유용한 쿼리 예시
```sql
-- 에러 로그만 조회
SELECT * FROM logs
WHERE level IN ('ERROR', 'FATAL')
  AND deleted = FALSE
ORDER BY created_at DESC
LIMIT 100;

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
LIMIT 50;

-- 시간대별 에러 집계
SELECT
    DATE_TRUNC('hour', created_at) as hour,
    service,
    COUNT(*) as error_count
FROM logs
WHERE level = 'ERROR'
  AND deleted = FALSE
  AND created_at >= NOW() - INTERVAL '24 hours'
GROUP BY hour, service
ORDER BY hour DESC;
```

---

## 7. 구현 가이드

### 7.1 초기 설정

```sql
-- 1. ENUM 타입 생성
CREATE TYPE log_level AS ENUM ('TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL');
CREATE TYPE source_type AS ENUM ('BACKEND', 'FRONTEND', 'MOBILE', 'IOT', 'WORKER', 'CRONJOB');
CREATE TYPE env_type AS ENUM ('production', 'staging', 'development', 'test', 'local');
CREATE TYPE http_method AS ENUM ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS', 'TRACE', 'CONNECT');

-- 2. 테이블 생성 (위의 스키마 사용)

-- 3. 인덱스 생성 (위의 4개 인덱스)

-- 4. 완료!
```

### 7.2 애플리케이션 통합

```python
# Python 예시
import logging
from datetime import datetime

def log_to_db(conn, log_data):
    """로그를 DB에 삽입"""
    conn.execute("""
        INSERT INTO logs (
            level, log_type, service, environment,
            message, trace_id, metadata, deleted
        ) VALUES (
            $1, $2, $3, $4, $5, $6, $7, FALSE
        )
    """,
    log_data['level'],
    log_data['log_type'],
    log_data['service'],
    log_data['environment'],
    log_data['message'],
    log_data.get('trace_id'),
    log_data.get('metadata', {}))

# 사용 예시
log_to_db(conn, {
    'level': 'ERROR',
    'log_type': 'BACKEND',
    'service': 'payment-api',
    'environment': 'production',
    'message': 'Payment gateway timeout',
    'trace_id': 'abc123',
    'metadata': {
        'performance': {'duration_ms': 5000},
        'error_detail': {'category': 'timeout'}
    }
})
```

### 7.3 기존 시스템에서 마이그레이션 (필요시)

```sql
-- 간단한 마이그레이션 (기존 시스템이 있는 경우만)
INSERT INTO logs (
    created_at, level, log_type, service,
    message, trace_id, deleted
)
SELECT
    timestamp,
    level::text::log_level,
    log_type::text::source_type,
    service,
    message,
    trace_id,
    FALSE
FROM old_logs
WHERE timestamp >= NOW() - INTERVAL '30 days';  -- 최근 데이터만
```

---

## 부록 A: 필드 요약

### 필수 필드 (NOT NULL)
- `id`, `created_at`, `level`, `log_type`
- `service`, `environment`, `service_version`
- `message`, `deleted`

### 선택 필드 (NULL 허용)
- `trace_id`, `user_id`, `session_id` - 추적 정보
- `error_type`, `stack_trace` - 에러 시에만
- `path` - 위치 (백엔드: /api/v1/payment, 프론트: /checkout)
- `method` - HTTP 메서드 (백엔드 전용)
- `action_type` - 사용자 액션 (프론트엔드 전용)
- `function_name`, `file_path` - 코드 위치 (stack trace에서 추출, 프론트/백 공통)
- `duration_ms` - 성능 측정 시에만
- `metadata` - 추가 정보 필요 시

## 부록 B: 성능 가이드

### 예상 성능
| 작업 | 목표 | 참고 |
|-----|-----|------|
| 단일 로그 삽입 | < 10ms | 일반적인 경우 |
| 배치 삽입 (1000건) | < 200ms | 권장 방식 |
| 에러 로그 조회 | < 50ms | 인덱스 활용 |
| 집계 쿼리 | < 500ms | 복잡도에 따라 |

### 최적화 팁
```sql
-- 1. 배치 삽입 사용
INSERT INTO logs VALUES (...), (...), (...);  -- 1000건씩

-- 2. deleted 필드 활용
WHERE deleted = FALSE  -- 모든 쿼리에 포함

-- 3. 시간 범위 제한
WHERE created_at >= NOW() - INTERVAL '7 days'

-- 4. 필요한 컬럼만 조회
SELECT id, message, created_at  -- SELECT * 지양
```

---

## 최종 요약

### 핵심 설계 원칙
1. **심플함**: 정말 필요한 필드만 (21개)
2. **유연성**: metadata JSONB로 확장
3. **실용성**: soft delete, 핵심 인덱스 4개
4. **표준**: ENUM 타입, OpenTelemetry trace_id
5. **통합**: path 필드로 endpoint/page_path 통합

### 주요 특징
- ✅ 통합 테이블 (프론트엔드 + 백엔드)
- ✅ 통합 경로 필드 (path)
- ✅ Soft delete (deleted 플래그)
- ✅ 유연한 metadata 구조 (10개 카테고리)
- ✅ 최소한의 인덱스 (4개)
- ✅ 복잡한 자동화 제거 (수동 관리)

### 제거된 오버엔지니어링
- ❌ 복잡한 아카이빙 시스템 (storage_tier, pg_cron)
- ❌ 과도한 성능 메트릭 필드 (metadata로 이동)
- ❌ 프라이버시 필드 5개 (PII 아예 안 담기)
- ❌ 불필요한 인덱스 6개 이상
- ❌ Materialized View, 트리거
- ❌ 복잡한 마이그레이션 계획
- ❌ endpoint/page_path 분리 (path로 통합)

---

**문서 버전**: 2.0 (심플화)
**최종 수정일**: 2024-01-15
**작성자**: Log Analysis System Team
