# Text-to-SQL 로그 분석 시스템 - 기획 초안

## 1. 프로젝트 개요

### 목적

- Text-to-SQL 에이전트를 활용한 로그 분석 시스템 구축
- 자연어 질문으로 로그 데이터를 쉽게 조회하고 분석
- 향후 데이터 파이프라인 과제와 연계 가능한 구조

### 핵심 기능

1. **로그 수집**: 다양한 서비스에서 발생하는 로그 자동 수집
2. **로그 저장**: PostgreSQL에 구조화된 형태로 저장
3. **자연어 조회**: Text-to-SQL 에이전트를 통한 로그 분석
4. **다중 언어 지원**: Python, JavaScript/TypeScript 서비스 모두 지원

### 주요 분석 시나리오

- **A. 장애 대응**: 에러 모니터링, 원인 분석, 영향도 파악
- **C. 성능 최적화**: 느린 API 찾기, 응답시간 추이, 병목 지점 파악
- **(B. 비즈니스 분석은 향후 확장 고려사항)**

---

## 2. 시스템 아키텍처

### 커스텀 라이브러리 기반 로그 수집

```
┌─────────────────────────────────────────────────┐
│           서비스 계층                            │
├─────────────────────────────────────────────────┤
│  Python 서비스:                                 │
│  - log_collector 패키지                        │
│  - 구조화된 로깅 (structlog)                    │
│  - 비동기 배치 전송                             │
│                                                 │
│  JavaScript/TypeScript 서비스:                 │
│  - log-client.js 라이브러리                    │
│  - 브라우저/Node.js 환경 모두 지원              │
│  - 자동 배치 처리                               │
│                                                 │
│  Svelte 프론트엔드:                             │
│  - log-client.js 통합                          │
│  - Error Boundary 자동 로깅                    │
│  - Stack trace 자동 파싱                       │
└─────────────────────────────────────────────────┘
                    ↓ HTTP POST (비동기 배치)
┌─────────────────────────────────────────────────┐
│           FastAPI 로그 서버                      │
├─────────────────────────────────────────────────┤
│  - POST /logs (배치 전송 지원)                  │
│  - 검증 및 정규화                               │
│  - Connection Pool (asyncpg)                   │
│  - PostgreSQL COPY (고성능)                    │
└─────────────────────────────────────────────────┘
                    ↓ Bulk INSERT
┌─────────────────────────────────────────────────┐
│           PostgreSQL Database                   │
│  - logs 테이블 (통합 스키마, 21개 필드)          │
│  - 프론트/백엔드 로그 모두 포함                  │
│  - 핵심 4개 인덱스 (성능 최적화)                 │
│  - Soft delete (deleted 플래그)                │
└─────────────────────────────────────────────────┘
                    ↓
┌─────────────────────────────────────────────────┐
│       Text-to-SQL Agent (LangChain)             │
│  - Claude Sonnet 4.5 사용                       │
│  - 자연어 → SQL 변환                            │
│  - 분석 결과 제공                               │
└─────────────────────────────────────────────────┘
```

### 커스텀 라이브러리 장점

| 항목 | 설명 |
|-----|------|
| **성능** | 50K logs/sec 처리 가능, PostgreSQL COPY 활용 |
| **완전한 필드 수집** | 21개 필드 모두 수집 (trace_id, user_id 등) |
| **단순한 구조** | 중간 단계 없음 (앱 → DB 직통) |
| **낮은 리소스** | Fluentd 없이 50-100MB 메모리 |
| **언어 지원** | Python, JavaScript/TypeScript |
| **비동기 처리** | 앱 블로킹 없음 (~0.1ms) |
| **배치 최적화** | 1000건씩 모아서 전송 |

---

## 3. 데이터베이스 스키마

### 통합 로그 테이블 (최적화 완료, 21개 필드)

```sql
-- ENUM 타입 정의 (저장 공간 최적화)
CREATE TYPE log_level AS ENUM ('TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL');
CREATE TYPE source_type AS ENUM ('BACKEND', 'FRONTEND', 'MOBILE', 'IOT', 'WORKER');
CREATE TYPE env_type AS ENUM ('production', 'staging', 'development', 'test', 'local');
CREATE TYPE http_method AS ENUM ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS');

-- 메인 테이블
CREATE TABLE logs (
    -- 기본 정보 (4)
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level log_level NOT NULL DEFAULT 'INFO',
    log_type source_type NOT NULL,

    -- 서비스 식별 (3)
    service VARCHAR(100) NOT NULL,
    environment env_type NOT NULL DEFAULT 'development',
    service_version VARCHAR(50) NOT NULL DEFAULT 'v0.0.0-dev',

    -- 분산 추적 (3)
    trace_id VARCHAR(32),               -- OpenTelemetry 표준
    user_id VARCHAR(255),
    session_id VARCHAR(100),

    -- 에러 정보 (3)
    error_type VARCHAR(200),
    message TEXT NOT NULL,
    stack_trace TEXT,

    -- 위치 정보 (3) - 통합 및 공통화
    path VARCHAR(500),                  -- 백엔드: /api/v1/payment, 프론트: /checkout
    method http_method,                 -- 백엔드 전용: HTTP 메서드
    action_type VARCHAR(50),            -- 프론트엔드 전용: click, submit, navigate

    -- 코드 위치 (2) - 프론트/백 공통
    function_name VARCHAR(300),         -- 함수명 (stack trace에서 추출)
    file_path VARCHAR(1000),            -- 파일 경로 (stack trace에서 추출)

    -- 성능 (1)
    duration_ms DECIMAL(10, 3),

    -- 관리 (1)
    deleted BOOLEAN NOT NULL DEFAULT FALSE,

    -- 확장 메타데이터 (1)
    metadata JSONB
);

-- 필드 설명 (COMMENT)
COMMENT ON TABLE logs IS '통합 로그 테이블 (프론트엔드 + 백엔드)';
COMMENT ON COLUMN logs.path IS '경로: 백엔드는 API endpoint, 프론트엔드는 page path';
COMMENT ON COLUMN logs.function_name IS '함수명: stack trace에서 추출 (프론트/백 공통)';
COMMENT ON COLUMN logs.file_path IS '파일 경로: stack trace에서 추출 (프론트/백 공통)';
COMMENT ON COLUMN logs.deleted IS 'Soft delete 플래그 (true = 삭제됨)';
COMMENT ON COLUMN logs.metadata IS '확장 데이터: 성능 메트릭, 브라우저 정보, 비즈니스 컨텍스트 등';

-- 핵심 4개 인덱스 (성능 최적화)
CREATE INDEX idx_service_level_time
ON logs(service, level, created_at DESC)
WHERE deleted = FALSE;

CREATE INDEX idx_error_time
ON logs(error_type, created_at DESC)
WHERE error_type IS NOT NULL AND deleted = FALSE;

CREATE INDEX idx_user_time
ON logs(user_id, created_at DESC)
WHERE user_id IS NOT NULL AND deleted = FALSE;

CREATE INDEX idx_trace
ON logs(trace_id)
WHERE trace_id IS NOT NULL AND deleted = FALSE;
```

### 스키마 설계 원칙

**단순화 완료:**
- ✅ 27개 → 21개 필드로 축소
- ✅ endpoint + page_path → path 통합 (log_type으로 구분)
- ✅ function_name, file_path → 프론트/백 공통 사용
- ✅ browser, device 등 → metadata로 이동
- ✅ ENUM 타입으로 저장 공간 90% 절감

**Text-to-SQL 최적화:**
- ✅ 단일 스키마 = AI 이해 용이
- ✅ 명확한 필드명 = 쿼리 정확도 향상
- ✅ 통합 path 필드 = CASE 문 불필요

**성능 최적화:**
- ✅ 4개 부분 인덱스 (deleted = FALSE 조건)
- ✅ TIMESTAMPTZ로 타임존 지원
- ✅ Soft delete (deleted 플래그)

---

## 4. 주요 시나리오 및 예상 프롬프트

### A. 장애 대응 시나리오

#### 1) 에러 발생 확인

**프롬프트**: "지난 1시간 동안 발생한 에러가 몇 건이야?"

**기대 SQL**:

```sql
SELECT COUNT(*) as error_count
FROM logs
WHERE level = 'ERROR'
  AND created_at > NOW() - INTERVAL '1 hour'
  AND deleted = FALSE;
```

#### 2) 에러 유형 분석

**프롬프트**: "어떤 에러가 가장 많이 발생했어? top 5 보여줘"

**기대 SQL**:

```sql
SELECT
  error_type,
  COUNT(*) as count,
  COUNT(DISTINCT user_id) as affected_users
FROM logs
WHERE level = 'ERROR'
  AND created_at > NOW() - INTERVAL '1 hour'
  AND deleted = FALSE
GROUP BY error_type
ORDER BY count DESC
LIMIT 5;
```

#### 3) 특정 에러 상세 분석

**프롬프트**: "DatabaseConnectionError가 어느 서비스에서 가장 많이 발생했어?"

**기대 SQL**:

```sql
SELECT
  service,
  function_name,
  COUNT(*) as error_count,
  MIN(created_at) as first_occurrence,
  MAX(created_at) as last_occurrence
FROM logs
WHERE error_type = 'DatabaseConnectionError'
  AND created_at > NOW() - INTERVAL '1 hour'
  AND deleted = FALSE
GROUP BY service, function_name
ORDER BY error_count DESC;
```

#### 4) 영향받은 사용자 파악

**프롬프트**: "DatabaseConnectionError로 영향받은 사용자 목록 보여줘"

**기대 SQL**:

```sql
SELECT
  user_id,
  COUNT(*) as error_count,
  MIN(created_at) as first_error,
  MAX(created_at) as last_error
FROM logs
WHERE error_type = 'DatabaseConnectionError'
  AND user_id IS NOT NULL
  AND created_at > NOW() - INTERVAL '1 hour'
  AND deleted = FALSE
GROUP BY user_id
ORDER BY error_count DESC
LIMIT 20;
```

#### 5) 시계열 분석

**프롬프트**: "payment-api의 에러가 시간대별로 어떻게 발생했어? 5분 단위로 보여줘"

**기대 SQL**:

```sql
SELECT
  DATE_TRUNC('minute', created_at) -
  (EXTRACT(MINUTE FROM created_at)::int % 5) * INTERVAL '1 minute' as time_bucket,
  COUNT(*) as error_count
FROM logs
WHERE service = 'payment-api'
  AND level = 'ERROR'
  AND created_at > NOW() - INTERVAL '1 hour'
  AND deleted = FALSE
GROUP BY time_bucket
ORDER BY time_bucket;
```

### C. 성능 최적화 시나리오

#### 1) 느린 엔드포인트 찾기

**프롬프트**: "평균 응답시간이 가장 긴 API 엔드포인트 5개 보여줘"

**전제**: duration_ms 필드 사용 (또는 metadata에 저장 가능)

**기대 SQL**:

```sql
SELECT
  path,
  COUNT(*) as request_count,
  AVG(duration_ms) as avg_duration_ms,
  MAX(duration_ms) as max_duration_ms,
  PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms) as p95_duration_ms
FROM logs
WHERE path IS NOT NULL
  AND duration_ms IS NOT NULL
  AND log_type = 'BACKEND'
  AND created_at > NOW() - INTERVAL '24 hours'
  AND deleted = FALSE
GROUP BY path
ORDER BY avg_duration_ms DESC
LIMIT 5;
```

#### 2) 응답시간 추이

**프롬프트**: "/api/v1/payment 엔드포인트의 시간대별 평균 응답시간 보여줘"

**기대 SQL**:

```sql
SELECT
  DATE_TRUNC('hour', created_at) as hour,
  COUNT(*) as request_count,
  AVG(duration_ms) as avg_duration_ms
FROM logs
WHERE path = '/api/v1/payment'
  AND duration_ms IS NOT NULL
  AND created_at > NOW() - INTERVAL '24 hours'
  AND deleted = FALSE
GROUP BY hour
ORDER BY hour;
```

#### 3) 타임아웃 분석

**프롬프트**: "TimeoutError가 발생한 요청들은 어느 서비스에서 가장 많이 나왔어?"

**기대 SQL**:

```sql
SELECT
  service,
  path,
  COUNT(*) as timeout_count,
  AVG(duration_ms) as avg_duration_before_timeout
FROM logs
WHERE error_type = 'TimeoutError'
  AND created_at > NOW() - INTERVAL '24 hours'
  AND deleted = FALSE
GROUP BY service, path
ORDER BY timeout_count DESC;
```

#### 4) 전체 흐름 추적 (프론트-백엔드 연계)

**프롬프트**: "user_123의 마지막 결제 시도에서 무슨 일이 있었어?"

**기대 SQL**:

```sql
SELECT
  created_at,
  log_type,
  service,
  path,
  level,
  message,
  error_type
FROM logs
WHERE user_id = 'user_123'
  AND (path LIKE '%checkout%' OR path LIKE '%payment%')
  AND created_at > NOW() - INTERVAL '1 hour'
  AND deleted = FALSE
ORDER BY created_at DESC
LIMIT 20;
```

**참고**: path 통합으로 CASE 문 불필요! ✅

---

## 5. 기술 스택

### 로그 수집 및 저장

- **로그 서버**: FastAPI (Python 3.11+)
  - asyncpg (비동기 PostgreSQL 클라이언트)
  - Connection Pool
  - PostgreSQL COPY (bulk insert)
- **데이터베이스**: PostgreSQL 15
  - JSONB 지원
  - 부분 인덱스
  - ENUM 타입

### 커스텀 로그 라이브러리

- **Python 패키지**: `log-collector`
  - structlog (구조화된 로깅)
  - aiohttp (비동기 HTTP 클라이언트)
  - 백그라운드 배치 전송
- **JavaScript/TypeScript**: `log-client.js`
  - fetch API (브라우저/Node.js)
  - 자동 배치 처리
  - Error Boundary 통합

### Text-to-SQL 에이전트

- **LLM**: Claude Sonnet 4.5 (Anthropic API)
- **프레임워크**: LangChain
- **DB 연결**: asyncpg (직접 연결)
- **프롬프트 엔지니어링**: 스키마 컨텍스트 최적화

### 샘플 서비스

- **Python 백엔드**: Flask/FastAPI
- **Node.js 백엔드**: Express
- **프론트엔드**: Svelte + Vite

### 인프라

- **개발 환경**: Docker Compose (PostgreSQL만)
- **프로덕션**: AWS RDS 또는 EC2 (선택사항)

---

## 6. 참고사항

### 로그 데이터 특성

- **프론트엔드 로그**: `log_type='FRONTEND'`, path는 page 경로, action_type 사용
- **백엔드 로그**: `log_type='BACKEND'`, path는 API endpoint, method 사용
- **공통 필드**: function_name, file_path는 stack trace에서 자동 추출
- **연결**: `trace_id`로 프론트-백엔드 로그 연결

### 중요 설계 원칙

- **단순화**: 27개 → 21개 필드로 축소, Text-to-SQL 최적화
- **통합**: endpoint + page_path → path 단일 필드
- **공통화**: function_name, file_path는 프론트/백 모두 사용
- **trace_id 필수**: 전체 요청 흐름 추적의 핵심
- **metadata 활용**: 브라우저, 디바이스 등 확장 정보는 JSONB
- **Soft delete**: deleted 플래그로 삭제 관리

### 커스텀 라이브러리 사용 가이드

**Python 서비스:**
```python
from log_collector import Logger

logger = Logger(
    service="payment-api",
    environment="production",
    log_server_url="http://localhost:8000"
)

logger.info(
    "payment_success",
    trace_id=request.trace_id,
    user_id=user.id,
    path="/api/v1/payment",
    duration_ms=123.45
)
```

**JavaScript 서비스:**
```javascript
import { LogClient } from 'log-client';

const logger = new LogClient({
    service: 'web-app',
    environment: 'production',
    logServerUrl: 'http://localhost:8000'
});

logger.info({
    message: 'checkout_completed',
    traceId: request.traceId,
    userId: user.id,
    path: '/checkout',
    actionType: 'submit'
});
```

**장점:**
- ✅ 21개 필드 모두 완벽 수집
- ✅ 구조화된 로그 강제
- ✅ 비동기 배치 전송 (~0.1ms)
- ✅ 중간 단계 없음 (앱 → DB)
- ✅ 50K logs/sec 처리 가능

### 향후 확장성

**로그 규모 증가 대응:**
- Kafka 추가: 로그 서버 앞단에 Kafka 배치 → 초당 100K+ 처리
- 파티셔닝: 월별/주별 파티션으로 쿼리 성능 10배 향상
- ClickHouse 마이그레이션: OLAP DB로 실시간 대시보드 구축

**분석 고도화:**
- Airflow: 배치 집계 작업 (일일/주간 리포트)
- Elasticsearch: 전문 검색 (full-text search)
- Grafana: 실시간 모니터링 대시보드

**데이터 파이프라인 연계:**
- 로그 → Kafka → Flink → ClickHouse (실시간 스트림 처리)
- 로그 → S3 → Spark → 데이터 웨어하우스 (배치 분석)
- Text-to-SQL 에이전트는 어떤 DB든 연결 가능

---

## 7. 예상 결과물

### 과제 발표 시 시연

**1. 로그 수집 데모:**
- Python 백엔드: 결제 API 에러 발생 시나리오
- Svelte 프론트엔드: 버튼 클릭 → 백엔드 호출 → 에러 발생
- 커스텀 라이브러리로 구조화된 로그 자동 전송
- trace_id로 프론트-백 연결 확인

**2. Text-to-SQL 에이전트:**
- 자연어 질문: "지난 1시간 에러 분석해줘"
- AI가 SQL 자동 생성 (21개 필드 스키마 이해)
- 결과 해석 및 인사이트 제공

**3. 실시간 분석:**
- "payment-api에서 가장 많이 발생한 에러는?"
- "응답시간이 가장 긴 API는?"
- "user_123의 전체 여정 추적"

**4. 성능 증명:**
- 1000건 로그 배치 전송 → < 100ms
- 복잡한 쿼리 실행 → < 50ms (인덱스 활용)
- Text-to-SQL 정확도 측정

### 어필 포인트

**실무 중심:**
- ✅ 실무적 문제 해결 (장애 대응, 성능 최적화)
- ✅ 38개 시나리오 기반 설계 (에러 분석, 사용자 추적, 성능 분석)

**기술적 깊이:**
- ✅ 최적화된 DB 스키마 (27개 → 21개 필드, ENUM 타입, 4개 인덱스)
- ✅ 고성능 로그 수집 (50K logs/sec, PostgreSQL COPY, 비동기 배치)
- ✅ Text-to-SQL 최적화 (단일 스키마, 통합 필드, 명확한 네이밍)

**확장성:**
- ✅ 다중 언어 지원 (Python, JavaScript/TypeScript)
- ✅ 프론트엔드/백엔드 통합 추적 (trace_id)
- ✅ 확장 가능한 설계 (metadata JSONB, 데이터 파이프라인 연계)

**최신 기술:**
- ✅ LLM 활용 (Claude Sonnet 4.5, LangChain)
- ✅ 모던 스택 (FastAPI, asyncpg, Svelte)
- ✅ 분산 추적 표준 (trace_id, OpenTelemetry 호환)

---

## 시작하기

### 개발 환경 설정

```bash
# 1. PostgreSQL 실행 (Docker)
docker run -d -p 5432:5432 \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=logs_db \
  postgres:15

# 2. 스키마 생성
psql -h localhost -U postgres -d logs_db -f schema.sql

# 3. 로그 서버 실행 (FastAPI)
cd services/log-server
pip install -r requirements.txt
python main.py
# → http://localhost:8000 에서 실행

# 4. 커스텀 라이브러리 설치
# Python
cd clients/python
pip install -e .

# JavaScript
cd clients/javascript
npm install
npm run build

# 5. 샘플 서비스 실행 (로그 생성)
cd sample-services/payment-api
python main.py

cd sample-services/web-app
npm run dev

# 6. Text-to-SQL 에이전트 실행
cd services/text-to-sql-agent
pip install -r requirements.txt
python agent.py
```

### Docker Compose 사용 (선택사항)

```bash
# PostgreSQL + 로그 서버 + 샘플 서비스 한 번에 실행
docker-compose up -d

# Text-to-SQL 에이전트는 로컬에서 실행
cd services/text-to-sql-agent
python agent.py
```

### 자연어 질문 예시

```
"지난 1시간 동안 에러가 몇 건 발생했어?"
"payment-api에서 가장 많이 발생한 에러는 뭐야?"
"응답시간이 가장 긴 API는?"
```
