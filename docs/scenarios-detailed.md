# 주요 사용 시나리오 상세 정의

## 목차

1. [시나리오 개요](#1-시나리오-개요)
2. [A. 장애 대응 시나리오](#2-a-장애-대응-시나리오)
3. [B. 성능 최적화 시나리오](#3-b-성능-최적화-시나리오)
4. [C. 데이터 정합성 시나리오](#4-c-데이터-정합성-시나리오)
5. [D. 비용 관리 시나리오](#5-d-비용-관리-시나리오)
6. [E. 보안 및 프라이버시 시나리오](#6-e-보안-및-프라이버시-시나리오)
7. [F. 사용자 경험 분석 시나리오](#7-f-사용자-경험-분석-시나리오)
8. [시나리오 복잡도 분석](#8-시나리오-복잡도-분석)
9. [Text-to-SQL 에이전트 검증 방법](#9-text-to-sql-에이전트-검증-방법)

---

## 1. 시나리오 개요

### 1.1 시나리오 분류 체계

| 카테고리 | 우선순위 | 시나리오 수 | 복잡도 |
|---------|---------|-----------|-------|
| A. 장애 대응 | 🔴 P0 | 10 | 중-높음 |
| B. 성능 최적화 | 🟡 P1 | 8 | 중-높음 |
| C. 데이터 정합성 | 🟡 P1 | 5 | 낮-중간 |
| D. 비용 관리 | 🟢 P2 | 4 | 낮-중간 |
| E. 보안/프라이버시 | 🔴 P0 | 6 | 중간 |
| F. 사용자 경험 | 🟢 P2 | 5 | 중간 |

**총 시나리오: 38개**

### 1.2 시나리오 구조

각 시나리오는 다음 요소를 포함합니다:

- **시나리오 ID**: 카테고리 + 번호 (예: A-01)
- **제목**: 간단한 설명
- **비즈니스 가치**: 왜 중요한가?
- **사용자 프롬프트**: 자연어 질문 (3-5가지 변형)
- **기대 SQL**: 생성되어야 하는 SQL 쿼리
- **예상 결과**: 결과 포맷 및 해석
- **복잡도**: 낮음/중간/높음
- **필수 인덱스**: 성능을 위한 필수 인덱스
- **확장 가능성**: 추가 질문 가능성

---

## 2. A. 장애 대응 시나리오

### A-01: 실시간 에러 발생 확인

**비즈니스 가치**: 장애 발생 즉시 인지하여 빠른 대응

**사용자 프롬프트:**
- "지난 1시간 동안 발생한 에러가 몇 건이야?"
- "최근 1시간 에러 수 알려줘"
- "1시간 내 에러 로그 개수는?"
- "지난 60분 동안 ERROR 레벨 로그 몇 개?"

**기대 SQL:**
```sql
SELECT COUNT(*) AS error_count
FROM logs
WHERE level IN ('ERROR', 'FATAL')
  AND created_at > NOW() - INTERVAL '1 hour';
```

**예상 결과:**
```
error_count
-----------
342
```

**복잡도**: 낮음 ⭐
**필수 인덱스**: `idx_service_level_time`
**확장 가능성**: 시간 범위 변경 (6시간, 24시간)

---

### A-02: 에러 유형별 분석

**비즈니스 가치**: 어떤 에러가 가장 문제인지 우선순위 파악

**사용자 프롬프트:**
- "어떤 에러가 가장 많이 발생했어? top 5 보여줘"
- "지난 1시간 에러 유형 순위는?"
- "가장 빈번한 에러 5가지는?"
- "에러 타입별로 몇 건씩 발생했는지 상위 5개 알려줘"

**기대 SQL:**
```sql
SELECT
    error_type,
    COUNT(*) AS error_count,
    COUNT(DISTINCT user_id) AS affected_users,
    MIN(created_at) AS first_occurrence,
    MAX(created_at) AS last_occurrence
FROM logs
WHERE level IN ('ERROR', 'FATAL')
  AND created_at > NOW() - INTERVAL '1 hour'
  AND error_type IS NOT NULL
GROUP BY error_type
ORDER BY error_count DESC
LIMIT 5;
```

**예상 결과:**
```
error_type                    | error_count | affected_users | first_occurrence     | last_occurrence
------------------------------|-------------|----------------|----------------------|--------------------
DatabaseConnectionTimeout     | 145         | 23             | 2024-01-15 10:15:32  | 2024-01-15 11:02:18
ValidationError               | 89          | 45             | 2024-01-15 10:20:11  | 2024-01-15 11:08:55
PaymentGatewayError           | 56          | 34             | 2024-01-15 10:30:44  | 2024-01-15 11:10:22
AuthenticationFailure         | 34          | 28             | 2024-01-15 10:45:19  | 2024-01-15 11:09:33
RateLimitExceeded             | 18          | 5              | 2024-01-15 10:55:07  | 2024-01-15 11:11:08
```

**복잡도**: 중간 ⭐⭐
**필수 인덱스**: `idx_error_service_time`
**확장 가능성**: 서비스별, 환경별 분석

---

### A-03: 특정 에러의 서비스별 분포

**비즈니스 가치**: 에러가 특정 서비스에 집중되는지 파악

**사용자 프롬프트:**
- "DatabaseConnectionTimeout이 어느 서비스에서 가장 많이 발생했어?"
- "DB 연결 에러가 어느 서비스에서 나와?"
- "DatabaseConnectionTimeout 서비스별 분포 보여줘"

**기대 SQL:**
```sql
SELECT
    service,
    component,
    COUNT(*) AS error_count,
    COUNT(DISTINCT user_id) AS affected_users,
    MIN(created_at) AS first_occurrence,
    MAX(created_at) AS last_occurrence,
    ROUND(AVG(EXTRACT(EPOCH FROM (MAX(created_at) - MIN(created_at)))) / 60, 2) AS duration_minutes
FROM logs
WHERE error_type = 'DatabaseConnectionTimeout'
  AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY service, component
ORDER BY error_count DESC;
```

**예상 결과:**
```
service        | component          | error_count | affected_users | first_occurrence     | last_occurrence      | duration_minutes
---------------|--------------------|-----------|--------------|--------------------|--------------------|-----------------
payment-api    | payment_processor  | 89        | 18           | 2024-01-15 10:15:32| 2024-01-15 11:02:18| 46.77
user-service   | profile_manager    | 34        | 12           | 2024-01-15 10:25:11| 2024-01-15 10:58:44| 33.55
order-api      | order_handler      | 22        | 8            | 2024-01-15 10:40:19| 2024-01-15 11:05:22| 25.05
```

**복잡도**: 중간 ⭐⭐
**필수 인덱스**: `idx_error_service_time`
**확장 가능성**: 환경별, 버전별 분석

---

### A-04: 영향받은 사용자 목록

**비즈니스 가치**: 고객 보상, 개별 연락 필요 시 사용자 식별

**사용자 프롬프트:**
- "DatabaseConnectionTimeout으로 영향받은 사용자 목록 보여줘"
- "DB 에러 때문에 문제 겪은 사용자는?"
- "이 에러로 피해 입은 사용자 ID들 알려줘"

**기대 SQL:**
```sql
SELECT
    user_id,
    COUNT(*) AS error_count,
    MIN(created_at) AS first_error,
    MAX(created_at) AS last_error,
    STRING_AGG(DISTINCT service, ', ') AS affected_services,
    ARRAY_AGG(DISTINCT trace_id) FILTER (WHERE trace_id IS NOT NULL) AS trace_ids
FROM logs
WHERE error_type = 'DatabaseConnectionTimeout'
  AND user_id IS NOT NULL
  AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY user_id
ORDER BY error_count DESC
LIMIT 50;
```

**예상 결과:**
```
user_id    | error_count | first_error          | last_error           | affected_services          | trace_ids
-----------|-------------|----------------------|----------------------|----------------------------|---------------------------
user_4523  | 12          | 2024-01-15 10:15:32  | 2024-01-15 11:02:18  | payment-api, order-api     | {trace1, trace2, trace3}
user_8891  | 8           | 2024-01-15 10:20:44  | 2024-01-15 10:58:33  | payment-api                | {trace4, trace5}
user_2341  | 6           | 2024-01-15 10:35:11  | 2024-01-15 11:05:22  | user-service, payment-api  | {trace6, trace7}
```

**복잡도**: 중간 ⭐⭐
**필수 인덱스**: `idx_user_time`
**확장 가능성**: 사용자별 상세 로그 추적

---

### A-05: 시계열 에러 발생 패턴

**비즈니스 가치**: 에러 급증 시점 파악, 장애 시작/종료 시점 확인

**사용자 프롬프트:**
- "payment-api의 에러가 시간대별로 어떻게 발생했어? 5분 단위로 보여줘"
- "에러 발생 추이를 5분 간격으로 알려줘"
- "시간별 에러 그래프 데이터 줘"

**기대 SQL:**
```sql
SELECT
    DATE_TRUNC('minute', created_at) -
    (EXTRACT(MINUTE FROM created_at)::INTEGER % 5) * INTERVAL '1 minute' AS time_bucket,
    COUNT(*) AS error_count,
    COUNT(DISTINCT user_id) AS affected_users,
    STRING_AGG(DISTINCT error_type, ', ' ORDER BY error_type) AS error_types
FROM logs
WHERE service = 'payment-api'
  AND level IN ('ERROR', 'FATAL')
  AND created_at > NOW() - INTERVAL '1 hour'
GROUP BY time_bucket
ORDER BY time_bucket;
```

**예상 결과:**
```
time_bucket          | error_count | affected_users | error_types
---------------------|-------------|----------------|-----------------------------------------------
2024-01-15 10:15:00  | 3           | 2              | DatabaseConnectionTimeout
2024-01-15 10:20:00  | 8           | 5              | DatabaseConnectionTimeout, ValidationError
2024-01-15 10:25:00  | 15          | 9              | DatabaseConnectionTimeout, PaymentGatewayError
2024-01-15 10:30:00  | 34          | 18             | DatabaseConnectionTimeout, PaymentGatewayError
2024-01-15 10:35:00  | 56          | 28             | DatabaseConnectionTimeout, PaymentGatewayError, ValidationError
```

**복잡도**: 높음 ⭐⭐⭐
**필수 인덱스**: `idx_service_level_time`
**확장 가능성**: 다양한 시간 버킷 (1분, 10분, 1시간)

---

### A-06: 연쇄 장애 추적 (Cascade Failure)

**비즈니스 가치**: 초기 장애 원인 파악, 의존성 문제 발견

**사용자 프롬프트:**
- "payment-api에서 시작된 에러가 다른 서비스에 어떻게 영향을 줬어?"
- "연쇄 장애 패턴 분석해줘"
- "trace_id로 연결된 에러들 보여줘"

**기대 SQL:**
```sql
WITH error_traces AS (
    SELECT DISTINCT trace_id
    FROM logs
    WHERE service = 'payment-api'
      AND level = 'ERROR'
      AND created_at > NOW() - INTERVAL '1 hour'
      AND trace_id IS NOT NULL
)
SELECT
    l.service,
    l.error_type,
    l.created_at,
    l.trace_id,
    l.message,
    l.endpoint,
    LEAD(l.service) OVER (PARTITION BY l.trace_id ORDER BY l.created_at) AS next_service
FROM logs l
INNER JOIN error_traces et ON l.trace_id = et.trace_id
WHERE l.level IN ('ERROR', 'WARN')
ORDER BY l.trace_id, l.created_at;
```

**예상 결과:**
```
service        | error_type                  | created_at           | trace_id  | message                      | endpoint            | next_service
---------------|----------------------------|----------------------|-----------|------------------------------|---------------------|-------------
payment-api    | DatabaseConnectionTimeout  | 2024-01-15 10:15:32  | trace123  | DB connection pool exhausted | /api/v1/payment     | order-api
order-api      | DependencyTimeout          | 2024-01-15 10:15:34  | trace123  | Payment service timeout      | /api/v1/orders      | notification-api
notification-api| QueueFullError            | 2024-01-15 10:15:36  | trace123  | Message queue at capacity    | /api/v1/notify      | NULL
```

**복잡도**: 높음 ⭐⭐⭐⭐
**필수 인덱스**: `idx_trace`
**확장 가능성**: 의존성 그래프 시각화

---

### A-07: 특정 사용자의 에러 경험 추적

**비즈니스 가치**: 고객 지원 시 전체 문맥 파악

**사용자 프롬프트:**
- "user_123이 경험한 에러들 시간순으로 보여줘"
- "이 사용자가 겪은 문제들 정리해줘"
- "user_123의 최근 1시간 에러 로그"

**기대 SQL:**
```sql
SELECT
    created_at,
    log_type,
    service,
    CASE
        WHEN log_type = 'FRONTEND' THEN page_path
        WHEN log_type = 'BACKEND' THEN endpoint
    END AS location,
    level,
    error_type,
    message,
    trace_id,
    session_id
FROM logs
WHERE user_id = 'user_123'
  AND level IN ('ERROR', 'WARN')
  AND created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC
LIMIT 50;
```

**예상 결과:**
```
created_at           | log_type  | service      | location           | level | error_type                | message                        | trace_id  | session_id
---------------------|-----------|--------------|-----------------------|-------|---------------------------|--------------------------------|-----------|------------
2024-01-15 11:05:22  | BACKEND   | payment-api  | /api/v1/payment       | ERROR | PaymentGatewayError       | Payment declined              | trace456  | sess_abc
2024-01-15 11:05:18  | FRONTEND  | web-app      | /checkout             | WARN  | NetworkError              | Request timeout               | trace456  | sess_abc
2024-01-15 10:58:44  | BACKEND   | payment-api  | /api/v1/payment/validate | ERROR | ValidationError        | Invalid card number           | trace455  | sess_abc
```

**복잡도**: 중간 ⭐⭐
**필수 인덱스**: `idx_user_time`
**확장 가능성**: 전체 사용자 여정 (로그 + 성공 요청)

---

### A-08: 에러 메시지 패턴 분석

**비즈니스 가치**: 유사 에러 그룹화, 근본 원인 파악

**사용자 프롬프트:**
- "비슷한 에러 메시지들끼리 묶어서 보여줘"
- "에러 메시지에 'timeout'이 포함된 로그 분석"
- "connection 관련 에러 패턴은?"

**기대 SQL:**
```sql
SELECT
    CASE
        WHEN message ILIKE '%timeout%' THEN 'Timeout Errors'
        WHEN message ILIKE '%connection%' THEN 'Connection Errors'
        WHEN message ILIKE '%validation%' THEN 'Validation Errors'
        WHEN message ILIKE '%authentication%' THEN 'Auth Errors'
        WHEN message ILIKE '%not found%' THEN 'Not Found Errors'
        ELSE 'Other Errors'
    END AS error_pattern,
    COUNT(*) AS occurrence,
    COUNT(DISTINCT service) AS affected_services,
    COUNT(DISTINCT user_id) AS affected_users,
    ARRAY_AGG(DISTINCT error_type) AS error_types,
    MIN(created_at) AS first_seen,
    MAX(created_at) AS last_seen
FROM logs
WHERE level = 'ERROR'
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY error_pattern
ORDER BY occurrence DESC;
```

**예상 결과:**
```
error_pattern       | occurrence | affected_services | affected_users | error_types                                    | first_seen           | last_seen
--------------------|------------|-------------------|----------------|-----------------------------------------------|----------------------|--------------------
Connection Errors   | 456        | 8                 | 123            | {DatabaseConnectionTimeout, RedisConnectionError} | 2024-01-14 12:15:32 | 2024-01-15 11:10:22
Timeout Errors      | 234        | 5                 | 89             | {RequestTimeout, GatewayTimeout}              | 2024-01-14 14:20:11 | 2024-01-15 11:08:55
Validation Errors   | 189        | 4                 | 145            | {ValidationError, SchemaValidationError}      | 2024-01-14 10:30:44 | 2024-01-15 11:05:19
```

**복잡도**: 중간 ⭐⭐⭐
**필수 인덱스**: `idx_error_logs`
**확장 가능성**: 정규 표현식 패턴 매칭

---

### A-09: 환경별 에러 비교

**비즈니스 가치**: Production 특정 이슈 발견, Staging 테스트 검증

**사용자 프롬프트:**
- "production과 staging 환경의 에러 비율 비교해줘"
- "환경별로 에러가 얼마나 다르게 나와?"
- "프로덕션에만 있는 에러는?"

**기대 SQL:**
```sql
SELECT
    environment,
    COUNT(*) AS total_logs,
    COUNT(CASE WHEN level = 'ERROR' THEN 1 END) AS error_count,
    ROUND(100.0 * COUNT(CASE WHEN level = 'ERROR' THEN 1 END) / COUNT(*), 2) AS error_rate_percent,
    COUNT(DISTINCT error_type) AS unique_errors,
    ARRAY_AGG(DISTINCT error_type ORDER BY error_type) FILTER (WHERE level = 'ERROR') AS error_types
FROM logs
WHERE created_at > NOW() - INTERVAL '24 hours'
  AND environment IN ('production', 'staging')
GROUP BY environment
ORDER BY error_rate_percent DESC;
```

**예상 결과:**
```
environment | total_logs | error_count | error_rate_percent | unique_errors | error_types
------------|------------|-------------|-------------------|---------------|--------------------------------------------------------
production  | 1,234,567  | 4,523       | 0.37              | 15            | {AuthError, DBTimeout, PaymentError, ValidationError, ...}
staging     | 345,678    | 234         | 0.07              | 8             | {AuthError, ValidationError, ...}
```

**복잡도**: 중간 ⭐⭐
**필수 인덱스**: `idx_env_service_time`
**확장 가능성**: 버전별, 릴리스별 비교

---

### A-10: 최근 배포 후 에러 증가 분석

**비즈니스 가치**: 배포 문제 빠른 발견, 롤백 판단 근거

**사용자 프롬프트:**
- "최근 배포 후 에러가 증가했어?"
- "새 버전 배포 전후 에러 비교해줘"
- "v2.3.0 배포 이후 에러 추이는?"

**기대 SQL:**
```sql
WITH deployment_time AS (
    SELECT MIN(created_at) AS deploy_time
    FROM logs
    WHERE service_version = 'v2.3.0'
      AND service = 'payment-api'
),
before_deploy AS (
    SELECT COUNT(*) AS error_count
    FROM logs, deployment_time
    WHERE service = 'payment-api'
      AND level = 'ERROR'
      AND created_at BETWEEN deploy_time - INTERVAL '1 hour' AND deploy_time
),
after_deploy AS (
    SELECT COUNT(*) AS error_count
    FROM logs, deployment_time
    WHERE service = 'payment-api'
      AND level = 'ERROR'
      AND created_at BETWEEN deploy_time AND deploy_time + INTERVAL '1 hour'
)
SELECT
    (SELECT error_count FROM before_deploy) AS errors_before,
    (SELECT error_count FROM after_deploy) AS errors_after,
    (SELECT error_count FROM after_deploy) - (SELECT error_count FROM before_deploy) AS difference,
    ROUND(
        100.0 * ((SELECT error_count FROM after_deploy)::NUMERIC - (SELECT error_count FROM before_deploy))
        / NULLIF((SELECT error_count FROM before_deploy), 0),
        2
    ) AS percent_change;
```

**예상 결과:**
```
errors_before | errors_after | difference | percent_change
--------------|--------------|------------|---------------
45            | 234          | 189        | 420.00
```

**복잡도**: 높음 ⭐⭐⭐⭐
**필수 인덱스**: `idx_service_level_time`
**확장 가능성**: 버전별 상세 분석, 에러 타입 비교

---

## 3. B. 성능 최적화 시나리오

### B-01: 느린 API 엔드포인트 식별

**비즈니스 가치**: 성능 병목 지점 발견, 최적화 우선순위 결정

**사용자 프롬프트:**
- "평균 응답시간이 가장 긴 API 엔드포인트 5개 보여줘"
- "어떤 API가 가장 느려?"
- "성능 개선이 필요한 엔드포인트는?"

**기대 SQL:**
```sql
SELECT
    endpoint,
    method,
    COUNT(*) AS request_count,
    ROUND(AVG(duration_ms), 2) AS avg_duration_ms,
    ROUND(MIN(duration_ms), 2) AS min_duration_ms,
    ROUND(MAX(duration_ms), 2) AS max_duration_ms,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY duration_ms), 2) AS p50_duration_ms,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms), 2) AS p95_duration_ms,
    ROUND(PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY duration_ms), 2) AS p99_duration_ms
FROM logs
WHERE endpoint IS NOT NULL
  AND duration_ms IS NOT NULL
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY endpoint, method
HAVING COUNT(*) >= 100  -- 충분한 샘플
ORDER BY avg_duration_ms DESC
LIMIT 5;
```

**예상 결과:**
```
endpoint                  | method | request_count | avg_duration_ms | min_duration_ms | max_duration_ms | p50 | p95   | p99
--------------------------|--------|---------------|-----------------|-----------------|-----------------|-----|-------|-------
/api/v1/reports/generate  | POST   | 1,234         | 5,678.45        | 1,234.12        | 28,345.67       | 4,500 | 15,000 | 22,000
/api/v1/analytics/query   | POST   | 2,567         | 3,456.78        | 567.89          | 18,234.56       | 2,800 | 10,000 | 15,000
/api/v1/export/data       | GET    | 890           | 2,345.67        | 890.12          | 12,345.78       | 1,900 | 8,000  | 11,000
```

**복잡도**: 중간 ⭐⭐
**필수 인덱스**: `idx_endpoint_time`, `idx_duration`
**확장 가능성**: 서비스별, 사용자별 성능 분석

---

### B-02: 응답시간 시계열 추이

**비즈니스 가치**: 성능 저하 시점 파악, 트래픽 패턴 이해

**사용자 프롬프트:**
- "/api/v1/payment 엔드포인트의 시간대별 평균 응답시간 보여줘"
- "결제 API 성능 추이 그래프 데이터 줘"
- "오늘 하루 응답시간 변화는?"

**기대 SQL:**
```sql
SELECT
    DATE_TRUNC('hour', created_at) AS hour,
    COUNT(*) AS request_count,
    ROUND(AVG(duration_ms), 2) AS avg_duration_ms,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY duration_ms), 2) AS median_duration_ms,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms), 2) AS p95_duration_ms,
    ROUND(MAX(duration_ms), 2) AS max_duration_ms,
    COUNT(CASE WHEN duration_ms > 1000 THEN 1 END) AS slow_requests
FROM logs
WHERE endpoint = '/api/v1/payment'
  AND duration_ms IS NOT NULL
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY hour
ORDER BY hour;
```

**예상 결과:**
```
hour                 | request_count | avg_duration_ms | median_duration_ms | p95_duration_ms | max_duration_ms | slow_requests
---------------------|---------------|-----------------|--------------------|-----------------|-----------------|--------------
2024-01-15 00:00:00  | 1,234         | 234.56          | 198.23             | 567.89          | 2,345.67        | 12
2024-01-15 01:00:00  | 987           | 212.34          | 187.45             | 498.76          | 1,876.54        | 8
2024-01-15 02:00:00  | 756           | 245.67          | 210.12             | 612.34          | 3,456.78        | 18
```

**복잡도**: 중간 ⭐⭐
**필수 인덱스**: `idx_endpoint_time`
**확장 가능성**: 분 단위, 일 단위 분석

---

### B-03: 데이터베이스 쿼리 성능 분석

**비즈니스 가치**: DB 최적화 필요 지점 발견

**사용자 프롬프트:**
- "데이터베이스 쿼리 시간이 긴 요청들 찾아줘"
- "DB 쿼리가 전체 응답시간의 대부분을 차지하는 API는?"
- "DB 병목이 있는 엔드포인트는?"

**기대 SQL:**
```sql
SELECT
    endpoint,
    COUNT(*) AS request_count,
    ROUND(AVG(duration_ms), 2) AS avg_total_time,
    ROUND(AVG(db_query_time_ms), 2) AS avg_db_time,
    ROUND(100.0 * AVG(db_query_time_ms) / NULLIF(AVG(duration_ms), 0), 2) AS db_time_percent,
    ROUND(MAX(db_query_time_ms), 2) AS max_db_time,
    COUNT(CASE WHEN db_query_time_ms > duration_ms * 0.7 THEN 1 END) AS db_bottleneck_count
FROM logs
WHERE endpoint IS NOT NULL
  AND duration_ms IS NOT NULL
  AND db_query_time_ms IS NOT NULL
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY endpoint
HAVING AVG(db_query_time_ms) / NULLIF(AVG(duration_ms), 0) > 0.5  -- DB가 50% 이상
ORDER BY avg_db_time DESC
LIMIT 10;
```

**예상 결과:**
```
endpoint                   | request_count | avg_total_time | avg_db_time | db_time_percent | max_db_time | db_bottleneck_count
---------------------------|---------------|----------------|-------------|-----------------|-------------|-----------------
/api/v1/users/search       | 5,678         | 1,234.56       | 1,098.23    | 88.95           | 8,765.43    | 4,123
/api/v1/orders/history     | 3,456         | 987.65         | 834.56      | 84.50           | 5,432.10    | 2,345
/api/v1/products/filter    | 2,345         | 756.34         | 612.45      | 80.98           | 4,321.76    | 1,567
```

**복잡도**: 높음 ⭐⭐⭐
**필수 인덱스**: `idx_endpoint_time`, JSONB 인덱스
**확장 가능성**: 캐시 히트율, 외부 API 시간 분석

---

### B-04: 타임아웃 발생 패턴

**비즈니스 가치**: 타임아웃 원인 파악, 임계값 조정

**사용자 프롬프트:**
- "TimeoutError가 발생한 요청들은 어느 컴포넌트에서 가장 많이 나왔어?"
- "타임아웃 에러 분석해줘"
- "어떤 서비스가 타임아웃을 많이 일으켜?"

**기대 SQL:**
```sql
SELECT
    service,
    component,
    endpoint,
    COUNT(*) AS timeout_count,
    ROUND(AVG(duration_ms), 2) AS avg_duration_before_timeout,
    ROUND(MIN(duration_ms), 2) AS min_duration,
    ROUND(MAX(duration_ms), 2) AS max_duration,
    COUNT(DISTINCT user_id) AS affected_users,
    STRING_AGG(DISTINCT error_type, ', ') AS timeout_types
FROM logs
WHERE (error_type ILIKE '%timeout%' OR message ILIKE '%timeout%')
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY service, component, endpoint
ORDER BY timeout_count DESC
LIMIT 10;
```

**예상 결과:**
```
service         | component         | endpoint               | timeout_count | avg_duration_before_timeout | min_duration | max_duration | affected_users | timeout_types
----------------|-------------------|------------------------|---------------|----------------------------|--------------|--------------|----------------|---------------------------
payment-api     | gateway_client    | /api/v1/payment/process| 234           | 30,145.67                  | 30,001.23    | 35,678.90    | 156            | GatewayTimeout, RequestTimeout
order-api       | inventory_service | /api/v1/inventory/check| 123           | 15,234.56                  | 15,002.34    | 20,123.45    | 89             | ServiceTimeout
notification-api| email_sender      | /api/v1/notify/email   | 89            | 10,567.89                  | 10,003.45    | 12,345.67    | 67             | SMTPTimeout
```

**복잡도**: 중간 ⭐⭐
**필수 인덱스**: `idx_error_service_time`
**확장 가능성**: 타임아웃 직전 리소스 사용량 분석

---

### B-05: 느린 요청의 공통 특성

**비즈니스 가치**: 느린 요청 패턴 발견, 최적화 힌트

**사용자 프롬프트:**
- "응답시간이 5초 이상인 요청들의 공통점은?"
- "느린 요청들이 특정 시간대에 집중되어 있어?"
- "5초 이상 걸린 요청들 분석해줘"

**기대 SQL:**
```sql
WITH slow_requests AS (
    SELECT *
    FROM logs
    WHERE duration_ms > 5000
      AND endpoint IS NOT NULL
      AND created_at > NOW() - INTERVAL '24 hours'
)
SELECT
    DATE_TRUNC('hour', created_at) AS hour_bucket,
    endpoint,
    COUNT(*) AS slow_count,
    ROUND(AVG(duration_ms), 2) AS avg_duration,
    COUNT(DISTINCT user_id) AS unique_users,
    ROUND(AVG(db_query_time_ms), 2) AS avg_db_time,
    ROUND(AVG(external_api_time_ms), 2) AS avg_external_api_time,
    ROUND(AVG(memory_usage_mb), 2) AS avg_memory_mb
FROM slow_requests
GROUP BY hour_bucket, endpoint
ORDER BY slow_count DESC
LIMIT 20;
```

**예상 결과:**
```
hour_bucket          | endpoint                  | slow_count | avg_duration | unique_users | avg_db_time | avg_external_api_time | avg_memory_mb
---------------------|---------------------------|------------|--------------|--------------|-------------|-----------------------|--------------
2024-01-15 10:00:00  | /api/v1/reports/generate  | 45         | 8,765.43     | 23           | 2,345.67    | 5,234.56              | 512.34
2024-01-15 14:00:00  | /api/v1/analytics/query   | 34         | 7,654.32     | 18           | 4,567.89    | 1,234.56              | 678.90
2024-01-15 09:00:00  | /api/v1/export/data       | 28         | 6,543.21     | 15           | 3,456.78    | 2,345.67              | 456.78
```

**복잡도**: 높음 ⭐⭐⭐
**필수 인덱스**: `idx_slow_requests`
**확장 가능성**: 머신러닝 기반 패턴 분석

---

### B-06: 캐시 히트율 분석

**비즈니스 가치**: 캐시 효율성 평가, 캐시 전략 개선

**사용자 프롬프트:**
- "캐시 히트율이 어떻게 돼?"
- "어떤 엔드포인트가 캐시를 잘 활용하고 있어?"
- "캐시 미스가 많은 API는?"

**기대 SQL:**
```sql
SELECT
    endpoint,
    COUNT(*) AS total_requests,
    COUNT(CASE WHEN (metadata->>'cache_hit')::BOOLEAN = true THEN 1 END) AS cache_hits,
    COUNT(CASE WHEN (metadata->>'cache_hit')::BOOLEAN = false THEN 1 END) AS cache_misses,
    ROUND(
        100.0 * COUNT(CASE WHEN (metadata->>'cache_hit')::BOOLEAN = true THEN 1 END) / COUNT(*),
        2
    ) AS cache_hit_rate,
    ROUND(AVG(CASE WHEN (metadata->>'cache_hit')::BOOLEAN = true THEN duration_ms END), 2) AS avg_cached_duration,
    ROUND(AVG(CASE WHEN (metadata->>'cache_hit')::BOOLEAN = false THEN duration_ms END), 2) AS avg_uncached_duration,
    ROUND(
        AVG(CASE WHEN (metadata->>'cache_hit')::BOOLEAN = false THEN duration_ms END) -
        AVG(CASE WHEN (metadata->>'cache_hit')::BOOLEAN = true THEN duration_ms END),
        2
    ) AS duration_improvement
FROM logs
WHERE endpoint IS NOT NULL
  AND metadata->>'cache_hit' IS NOT NULL
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY endpoint
HAVING COUNT(*) >= 100
ORDER BY cache_hit_rate ASC
LIMIT 10;
```

**예상 결과:**
```
endpoint                   | total_requests | cache_hits | cache_misses | cache_hit_rate | avg_cached_duration | avg_uncached_duration | duration_improvement
---------------------------|----------------|------------|--------------|----------------|---------------------|-----------------------|--------------------
/api/v1/products/details   | 5,678          | 4,234      | 1,444        | 74.58          | 23.45               | 456.78                | 433.33
/api/v1/users/profile      | 3,456          | 2,890      | 566          | 83.62          | 15.67               | 234.56                | 218.89
/api/v1/categories/list    | 2,345          | 2,123      | 222          | 90.53          | 12.34               | 189.23                | 176.89
```

**복잡도**: 중간 ⭐⭐
**필수 인덱스**: `idx_metadata_gin`
**확장 가능성**: 캐시 키 분포, TTL 효과 분석

---

### B-07: 동시성 문제 탐지

**비즈니스 가치**: 락 대기, 데드락 발견

**사용자 프롬프트:**
- "동시에 많은 요청이 몰려서 느려진 적 있어?"
- "특정 리소스에 대한 경합이 있는지 확인해줘"
- "락 대기 시간이 긴 요청들은?"

**기대 SQL:**
```sql
WITH concurrent_requests AS (
    SELECT
        DATE_TRUNC('minute', created_at) AS minute_bucket,
        endpoint,
        COUNT(*) AS concurrent_count,
        ROUND(AVG(duration_ms), 2) AS avg_duration,
        ROUND(AVG((metadata->>'queue_wait_time_ms')::NUMERIC), 2) AS avg_queue_wait
    FROM logs
    WHERE endpoint IS NOT NULL
      AND duration_ms IS NOT NULL
      AND created_at > NOW() - INTERVAL '24 hours'
    GROUP BY minute_bucket, endpoint
)
SELECT
    minute_bucket,
    endpoint,
    concurrent_count,
    avg_duration,
    avg_queue_wait,
    ROUND(100.0 * avg_queue_wait / NULLIF(avg_duration, 0), 2) AS queue_wait_percent
FROM concurrent_requests
WHERE concurrent_count >= 50  -- 분당 50개 이상
  AND avg_queue_wait > 100    -- 대기 시간 100ms 이상
ORDER BY avg_queue_wait DESC
LIMIT 20;
```

**예상 결과:**
```
minute_bucket        | endpoint                  | concurrent_count | avg_duration | avg_queue_wait | queue_wait_percent
---------------------|---------------------------|------------------|--------------|----------------|-------------------
2024-01-15 10:35:00  | /api/v1/payment/process   | 234              | 3,456.78     | 2,345.67       | 67.86
2024-01-15 14:22:00  | /api/v1/orders/create     | 189              | 2,345.67     | 1,567.89       | 66.85
2024-01-15 09:15:00  | /api/v1/inventory/update  | 156              | 1,987.65     | 1,234.56       | 62.11
```

**복잡도**: 높음 ⭐⭐⭐⭐
**필수 인덱스**: `idx_endpoint_time`, `idx_metadata_gin`
**확장 가능성**: 스레드 풀 사용률, 커넥션 풀 분석

---

### B-08: 외부 API 의존성 성능

**비즈니스 가치**: 외부 서비스 SLA 모니터링, 대안 검토

**사용자 프롬프트:**
- "외부 API 호출이 가장 오래 걸리는 엔드포인트는?"
- "third-party 서비스 때문에 느려지는 경우는?"
- "외부 의존성 성능 분석해줘"

**기대 SQL:**
```sql
SELECT
    endpoint,
    metadata->>'external_service' AS external_service,
    COUNT(*) AS call_count,
    ROUND(AVG(external_api_time_ms), 2) AS avg_external_time,
    ROUND(AVG(duration_ms), 2) AS avg_total_time,
    ROUND(100.0 * AVG(external_api_time_ms) / NULLIF(AVG(duration_ms), 0), 2) AS external_time_percent,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY external_api_time_ms), 2) AS p95_external_time,
    COUNT(CASE WHEN external_api_time_ms > 5000 THEN 1 END) AS timeout_risk_count
FROM logs
WHERE external_api_time_ms IS NOT NULL
  AND endpoint IS NOT NULL
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY endpoint, metadata->>'external_service'
HAVING AVG(external_api_time_ms) > 500  -- 평균 500ms 이상
ORDER BY avg_external_time DESC
LIMIT 15;
```

**예상 결과:**
```
endpoint                    | external_service    | call_count | avg_external_time | avg_total_time | external_time_percent | p95_external_time | timeout_risk_count
----------------------------|---------------------|------------|-------------------|----------------|-----------------------|-------------------|-------------------
/api/v1/payment/process     | stripe              | 2,345      | 1,567.89          | 2,345.67       | 66.86                 | 3,456.78          | 23
/api/v1/shipping/calculate  | fedex_api           | 1,234      | 1,234.56          | 1,987.65       | 62.11                 | 2,890.12          | 15
/api/v1/address/validate    | google_maps         | 3,456      | 987.65            | 1,456.78       | 67.80                 | 1,987.65          | 8
```

**복잡도**: 중간 ⭐⭐⭐
**필수 인덱스**: `idx_endpoint_time`, `idx_metadata_gin`
**확장 가능성**: 외부 서비스 에러율, 재시도 패턴

---

## 4. C. 데이터 정합성 시나리오

### C-01: 누락된 추적 ID

**비즈니스 가치**: 로그 수집 품질 검증, 분산 추적 완전성 확인

**사용자 프롬프트:**
- "trace_id가 누락된 로그가 얼마나 있어?"
- "분산 추적이 제대로 되고 있는지 확인해줘"
- "trace_id 없는 백엔드 로그는?"

**기대 SQL:**
```sql
SELECT
    service,
    log_type,
    COUNT(*) AS total_logs,
    COUNT(CASE WHEN trace_id IS NULL THEN 1 END) AS missing_trace_id,
    ROUND(100.0 * COUNT(CASE WHEN trace_id IS NULL THEN 1 END) / COUNT(*), 2) AS missing_percent,
    COUNT(CASE WHEN trace_id IS NULL AND level = 'ERROR' THEN 1 END) AS error_without_trace
FROM logs
WHERE created_at > NOW() - INTERVAL '24 hours'
  AND log_type IN ('BACKEND', 'FRONTEND')
GROUP BY service, log_type
HAVING COUNT(CASE WHEN trace_id IS NULL THEN 1 END) > 0
ORDER BY missing_percent DESC;
```

**예상 결과:**
```
service         | log_type  | total_logs | missing_trace_id | missing_percent | error_without_trace
----------------|-----------|------------|------------------|-----------------|--------------------
notification-api| BACKEND   | 12,345     | 3,456            | 28.00           | 234
legacy-api      | BACKEND   | 8,901      | 2,234            | 25.10           | 156
mobile-app      | FRONTEND  | 45,678     | 5,678            | 12.43           | 89
```

**복잡도**: 낮음 ⭐
**필수 인덱스**: `idx_service_level_time`
**확장 가능성**: 다른 필수 필드 누락 검사

---

### C-02: 프론트-백엔드 로그 매칭

**비즈니스 가치**: 로그 수집 누락 발견, 전체 흐름 추적 가능성

**사용자 프롬프트:**
- "프론트엔드 요청에 대응하는 백엔드 로그가 없는 경우는?"
- "로그가 제대로 짝지어져 있는지 확인해줘"
- "trace_id로 연결 안 된 로그는?"

**기대 SQL:**
```sql
WITH frontend_traces AS (
    SELECT DISTINCT trace_id
    FROM logs
    WHERE log_type = 'FRONTEND'
      AND trace_id IS NOT NULL
      AND created_at > NOW() - INTERVAL '1 hour'
),
backend_traces AS (
    SELECT DISTINCT trace_id
    FROM logs
    WHERE log_type = 'BACKEND'
      AND trace_id IS NOT NULL
      AND created_at > NOW() - INTERVAL '1 hour'
)
SELECT
    'Orphaned Frontend' AS category,
    COUNT(*) AS count
FROM frontend_traces ft
LEFT JOIN backend_traces bt ON ft.trace_id = bt.trace_id
WHERE bt.trace_id IS NULL

UNION ALL

SELECT
    'Orphaned Backend' AS category,
    COUNT(*) AS count
FROM backend_traces bt
LEFT JOIN frontend_traces ft ON bt.trace_id = ft.trace_id
WHERE ft.trace_id IS NULL

UNION ALL

SELECT
    'Matched Pairs' AS category,
    COUNT(*) AS count
FROM frontend_traces ft
INNER JOIN backend_traces bt ON ft.trace_id = bt.trace_id;
```

**예상 결과:**
```
category            | count
--------------------|-------
Orphaned Frontend   | 234
Orphaned Backend    | 56
Matched Pairs       | 5,678
```

**복잡도**: 중간 ⭐⭐
**필수 인덱스**: `idx_trace`
**확장 가능성**: 시간 차이 분석 (프론트→백 지연)

---

### C-03: 중복 로그 탐지

**비즈니스 가치**: 로그 수집 버그 발견, 저장 비용 절감

**사용자 프롬프트:**
- "중복된 로그가 있는지 확인해줘"
- "같은 내용이 여러 번 기록된 로그는?"
- "중복 로그 패턴 찾아줘"

**기대 SQL:**
```sql
WITH duplicate_candidates AS (
    SELECT
        service,
        trace_id,
        endpoint,
        message,
        error_type,
        COUNT(*) AS duplicate_count,
        ARRAY_AGG(id) AS log_ids,
        MIN(created_at) AS first_occurrence,
        MAX(created_at) AS last_occurrence
    FROM logs
    WHERE created_at > NOW() - INTERVAL '1 hour'
      AND trace_id IS NOT NULL
    GROUP BY service, trace_id, endpoint, message, error_type
    HAVING COUNT(*) > 1
)
SELECT
    service,
    duplicate_count,
    COUNT(*) AS unique_traces,
    SUM(duplicate_count) AS total_duplicates,
    ROUND(AVG(EXTRACT(EPOCH FROM (last_occurrence - first_occurrence))), 2) AS avg_time_span_seconds
FROM duplicate_candidates
GROUP BY service, duplicate_count
ORDER BY total_duplicates DESC;
```

**예상 결과:**
```
service         | duplicate_count | unique_traces | total_duplicates | avg_time_span_seconds
----------------|-----------------|---------------|------------------|----------------------
payment-api     | 3               | 45            | 135              | 0.23
order-api       | 2               | 89            | 178              | 0.15
user-service    | 5               | 12            | 60               | 1.45
```

**복잡도**: 중간 ⭐⭐⭐
**필수 인덱스**: `idx_trace`, `idx_service_level_time`
**확장 가능성**: 중복 원인 분석 (재시도 로직 등)

---

### C-04: 타임스탬프 순서 검증

**비즈니스 가치**: 시계 동기화 문제 발견, 로그 순서 신뢰성

**사용자 프롬프트:**
- "로그 타임스탬프가 역순으로 기록된 적 있어?"
- "서버 시계 동기화 문제가 있는지 확인해줘"
- "trace 내에서 시간 순서가 이상한 로그는?"

**기대 SQL:**
```sql
WITH trace_timings AS (
    SELECT
        trace_id,
        service,
        created_at,
        LAG(created_at) OVER (PARTITION BY trace_id ORDER BY created_at) AS prev_timestamp,
        LAG(service) OVER (PARTITION BY trace_id ORDER BY created_at) AS prev_service
    FROM logs
    WHERE trace_id IS NOT NULL
      AND created_at > NOW() - INTERVAL '24 hours'
)
SELECT
    service AS current_service,
    prev_service,
    COUNT(*) AS out_of_order_count,
    ROUND(AVG(EXTRACT(EPOCH FROM (prev_timestamp - created_at))), 2) AS avg_time_diff_seconds,
    ARRAY_AGG(DISTINCT trace_id) AS example_traces
FROM trace_timings
WHERE created_at < prev_timestamp  -- 역순
GROUP BY service, prev_service
ORDER BY out_of_order_count DESC;
```

**예상 결과:**
```
current_service  | prev_service     | out_of_order_count | avg_time_diff_seconds | example_traces
-----------------|------------------|--------------------|-----------------------|------------------------
order-api        | payment-api      | 23                 | -0.52                 | {trace1, trace2, trace3}
notification-api | order-api        | 12                 | -0.31                 | {trace4, trace5}
user-service     | auth-service     | 8                  | -0.18                 | {trace6, trace7}
```

**복잡도**: 높음 ⭐⭐⭐
**필수 인덱스**: `idx_trace`
**확장 가능성**: NTP 드리프트 패턴 분석

---

### C-05: 필수 필드 누락 검사

**비즈니스 가치**: 로그 품질 보증, 분석 신뢰성 확보

**사용자 프롬프트:**
- "필수 필드가 비어있는 로그가 있어?"
- "로그 데이터 품질 검사해줘"
- "service나 message가 NULL인 로그는?"

**기대 SQL:**
```sql
SELECT
    'Missing service' AS issue_type,
    COUNT(*) AS affected_logs,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM logs WHERE created_at > NOW() - INTERVAL '24 hours'), 4) AS percentage
FROM logs
WHERE service IS NULL
  AND created_at > NOW() - INTERVAL '24 hours'

UNION ALL

SELECT
    'Missing message' AS issue_type,
    COUNT(*) AS affected_logs,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM logs WHERE created_at > NOW() - INTERVAL '24 hours'), 4) AS percentage
FROM logs
WHERE message IS NULL OR message = ''
  AND created_at > NOW() - INTERVAL '24 hours'

UNION ALL

SELECT
    'Missing level' AS issue_type,
    COUNT(*) AS affected_logs,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM logs WHERE created_at > NOW() - INTERVAL '24 hours'), 4) AS percentage
FROM logs
WHERE level IS NULL
  AND created_at > NOW() - INTERVAL '24 hours'

UNION ALL

SELECT
    'Missing log_type' AS issue_type,
    COUNT(*) AS affected_logs,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM logs WHERE created_at > NOW() - INTERVAL '24 hours'), 4) AS percentage
FROM logs
WHERE log_type IS NULL
  AND created_at > NOW() - INTERVAL '24 hours';
```

**예상 결과:**
```
issue_type        | affected_logs | percentage
------------------|---------------|------------
Missing service   | 0             | 0.0000
Missing message   | 234           | 0.0189
Missing level     | 12            | 0.0010
Missing log_type  | 0             | 0.0000
```

**복잡도**: 낮음 ⭐
**필수 인덱스**: `idx_service_level_time`
**확장 가능성**: 데이터 타입 검증 (잘못된 형식)

---

## 5. D. 비용 관리 시나리오

### D-01: 로그 생성량 상위 서비스

**비즈니스 가치**: 로그 비용 최적화, 과도한 로깅 발견

**사용자 프롬프트:**
- "지난 달 가장 많은 로그를 생성한 서비스는?"
- "로그 생성량 top 10 보여줘"
- "어떤 서비스가 저장 공간을 가장 많이 차지해?"

**기대 SQL:**
```sql
SELECT
    service,
    environment,
    COUNT(*) AS log_count,
    ROUND(SUM(log_size_bytes) / (1024.0 * 1024.0), 2) AS total_size_mb,
    ROUND(AVG(log_size_bytes), 2) AS avg_log_size_bytes,
    COUNT(CASE WHEN level = 'DEBUG' THEN 1 END) AS debug_logs,
    COUNT(CASE WHEN level IN ('ERROR', 'FATAL') THEN 1 END) AS error_logs,
    ROUND(100.0 * COUNT(CASE WHEN level = 'DEBUG' THEN 1 END) / COUNT(*), 2) AS debug_percent
FROM logs
WHERE created_at >= DATE_TRUNC('month', NOW() - INTERVAL '1 month')
  AND created_at < DATE_TRUNC('month', NOW())
GROUP BY service, environment
ORDER BY total_size_mb DESC
LIMIT 10;
```

**예상 결과:**
```
service          | environment | log_count  | total_size_mb | avg_log_size_bytes | debug_logs | error_logs | debug_percent
-----------------|-------------|------------|---------------|--------------------|------------|------------|---------------
analytics-api    | production  | 45,678,901 | 12,345.67     | 278.45             | 38,901,234 | 234,567    | 85.17
logging-service  | production  | 34,567,890 | 9,876.54      | 293.12             | 29,345,678 | 123,456    | 84.90
data-pipeline    | production  | 23,456,789 | 7,654.32      | 335.67             | 18,765,432 | 89,012     | 79.98
```

**복잡도**: 낮음 ⭐
**필수 인덱스**: `idx_service_level_time`
**확장 가능성**: 일별 추이, 비용 추정

---

### D-02: 대용량 로그 식별

**비즈니스 가치**: 이상 로그 탐지, 로그 크기 제한 정책 수립

**사용자 프롬프트:**
- "로그 크기가 비정상적으로 큰 것들 찾아줘"
- "100KB 이상인 로그는?"
- "저장 용량 상위 1% 로그의 특징은?"

**기대 SQL:**
```sql
WITH percentile_threshold AS (
    SELECT PERCENTILE_CONT(0.99) WITHIN GROUP (ORDER BY log_size_bytes) AS p99_size
    FROM logs
    WHERE created_at > NOW() - INTERVAL '7 days'
)
SELECT
    l.id,
    l.created_at,
    l.service,
    l.log_type,
    l.level,
    ROUND(l.log_size_bytes / 1024.0, 2) AS size_kb,
    LENGTH(l.message) AS message_length,
    LENGTH(l.stack_trace) AS stack_trace_length,
    pg_column_size(l.metadata) AS metadata_size,
    CASE
        WHEN LENGTH(l.message) > 10000 THEN 'Long message'
        WHEN LENGTH(l.stack_trace) > 20000 THEN 'Long stack trace'
        WHEN pg_column_size(l.metadata) > 10000 THEN 'Large metadata'
        ELSE 'Other'
    END AS size_reason
FROM logs l, percentile_threshold pt
WHERE l.log_size_bytes > pt.p99_size
  AND l.created_at > NOW() - INTERVAL '7 days'
ORDER BY l.log_size_bytes DESC
LIMIT 100;
```

**예상 결과:**
```
id        | created_at           | service      | log_type | level | size_kb | message_length | stack_trace_length | metadata_size | size_reason
----------|----------------------|--------------|----------|-------|---------|----------------|--------------------|--------------|-----------------
12345678  | 2024-01-15 10:35:22  | data-api     | BACKEND  | ERROR | 234.56  | 123456         | 89012              | 45678        | Long message
23456789  | 2024-01-15 09:22:11  | analytics    | BACKEND  | INFO  | 189.23  | 8901           | 0                  | 187234       | Large metadata
34567890  | 2024-01-15 11:10:44  | payment-api  | BACKEND  | ERROR | 156.78  | 5678           | 152341             | 3456         | Long stack trace
```

**복잡도**: 중간 ⭐⭐
**필수 인덱스**: `idx_service_level_time`
**확장 가능성**: 자동 트리밍 정책 제안

---

### D-03: 디버그 로그 비율 분석

**비즈니스 가치**: Production 디버그 로그 최소화, 비용 절감

**사용자 프롬프트:**
- "Production 환경에서 DEBUG 로그가 많이 남고 있어?"
- "디버그 로그 비율이 높은 서비스는?"
- "로그 레벨 최적화가 필요한 곳은?"

**기대 SQL:**
```sql
SELECT
    service,
    environment,
    COUNT(*) AS total_logs,
    COUNT(CASE WHEN level = 'DEBUG' THEN 1 END) AS debug_count,
    COUNT(CASE WHEN level = 'TRACE' THEN 1 END) AS trace_count,
    COUNT(CASE WHEN level = 'INFO' THEN 1 END) AS info_count,
    COUNT(CASE WHEN level IN ('WARN', 'ERROR', 'FATAL') THEN 1 END) AS important_count,
    ROUND(100.0 * COUNT(CASE WHEN level IN ('DEBUG', 'TRACE') THEN 1 END) / COUNT(*), 2) AS verbose_percent,
    ROUND(SUM(CASE WHEN level IN ('DEBUG', 'TRACE') THEN log_size_bytes ELSE 0 END) / (1024.0 * 1024.0), 2) AS verbose_size_mb
FROM logs
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY service, environment
HAVING COUNT(CASE WHEN level IN ('DEBUG', 'TRACE') THEN 1 END) > 0
ORDER BY verbose_percent DESC
LIMIT 20;
```

**예상 결과:**
```
service          | environment | total_logs | debug_count | trace_count | info_count | important_count | verbose_percent | verbose_size_mb
-----------------|-------------|------------|-------------|-------------|------------|-----------------|-----------------|----------------
legacy-api       | production  | 1,234,567  | 987,654     | 123,456     | 98,765     | 24,692          | 90.00           | 3,456.78
analytics-worker | production  | 987,654    | 789,012     | 98,765      | 87,654     | 12,223          | 89.87           | 2,345.67
data-processor   | production  | 765,432    | 543,210     | 87,654      | 123,456    | 11,112          | 82.43           | 1,876.54
```

**복잡도**: 낮음 ⭐
**필수 인덱스**: `idx_service_level_time`
**확장 가능성**: 로그 레벨 변경 시뮬레이션 (비용 절감 예측)

---

### D-04: 보관 정책 최적화 제안

**비즈니스 가치**: 장기 보관 비용 절감, 컴플라이언스 준수

**사용자 프롬프트:**
- "오래된 로그 중 아카이빙 가능한 건?"
- "storage tier별 로그 분포는?"
- "cold storage로 옮길 수 있는 로그 용량은?"

**기대 SQL:**
```sql
WITH age_buckets AS (
    SELECT
        CASE
            WHEN created_at > NOW() - INTERVAL '7 days' THEN '0-7 days (hot)'
            WHEN created_at > NOW() - INTERVAL '30 days' THEN '8-30 days (warm)'
            WHEN created_at > NOW() - INTERVAL '90 days' THEN '31-90 days (cold)'
            ELSE '90+ days (archive)'
        END AS age_bucket,
        COUNT(*) AS log_count,
        ROUND(SUM(log_size_bytes) / (1024.0 * 1024.0 * 1024.0), 2) AS size_gb,
        storage_tier
    FROM logs
    GROUP BY age_bucket, storage_tier
)
SELECT
    age_bucket,
    storage_tier,
    log_count,
    size_gb,
    ROUND(size_gb *
        CASE storage_tier
            WHEN 'hot' THEN 0.10      -- $0.10 per GB/month
            WHEN 'warm' THEN 0.05     -- $0.05 per GB/month
            WHEN 'cold' THEN 0.01     -- $0.01 per GB/month
            WHEN 'archived' THEN 0.004 -- $0.004 per GB/month
            ELSE 0.10
        END, 2
    ) AS estimated_monthly_cost_usd
FROM age_buckets
ORDER BY
    CASE age_bucket
        WHEN '0-7 days (hot)' THEN 1
        WHEN '8-30 days (warm)' THEN 2
        WHEN '31-90 days (cold)' THEN 3
        ELSE 4
    END;
```

**예상 결과:**
```
age_bucket           | storage_tier | log_count    | size_gb  | estimated_monthly_cost_usd
---------------------|--------------|--------------|----------|---------------------------
0-7 days (hot)       | hot          | 45,678,901   | 1,234.56 | 123.46
8-30 days (warm)     | hot          | 123,456,789  | 3,456.78 | 345.68  ← 최적화 필요
31-90 days (cold)    | warm         | 234,567,890  | 6,789.01 | 339.45  ← 최적화 필요
90+ days (archive)   | cold         | 345,678,901  | 8,901.23 | 89.01   ← 최적화 필요
```

**복잡도**: 중간 ⭐⭐
**필수 인덱스**: `idx_service_level_time`
**확장 가능성**: 자동 티어링 정책 제안

---

## 6. E. 보안 및 프라이버시 시나리오

### E-01: 인증 실패 패턴

**비즈니스 가치**: 브루트포스 공격 탐지, 계정 보안

**사용자 프롬프트:**
- "인증 실패가 많이 발생한 IP 주소는?"
- "로그인 시도 공격이 있었는지 확인해줘"
- "같은 IP에서 반복된 인증 실패는?"

**기대 SQL:**
```sql
SELECT
    client_ip,
    COUNT(*) AS failed_attempts,
    COUNT(DISTINCT user_id) AS attempted_users,
    MIN(created_at) AS first_attempt,
    MAX(created_at) AS last_attempt,
    ROUND(
        EXTRACT(EPOCH FROM (MAX(created_at) - MIN(created_at))) / 60.0,
        2
    ) AS attack_duration_minutes,
    ARRAY_AGG(DISTINCT user_id ORDER BY user_id) AS targeted_users,
    geo_country,
    geo_city
FROM logs
WHERE error_type IN ('AuthenticationFailure', 'InvalidCredentials', 'LoginFailed')
  AND created_at > NOW() - INTERVAL '24 hours'
  AND client_ip IS NOT NULL
GROUP BY client_ip, geo_country, geo_city
HAVING COUNT(*) >= 10  -- 10회 이상 실패
ORDER BY failed_attempts DESC
LIMIT 20;
```

**예상 결과:**
```
client_ip       | failed_attempts | attempted_users | first_attempt        | last_attempt         | attack_duration_minutes | targeted_users        | geo_country | geo_city
----------------|-----------------|-----------------|----------------------|----------------------|------------------------|-----------------------|-------------|----------
192.168.1.100   | 456             | 123             | 2024-01-15 10:15:32  | 2024-01-15 11:45:22  | 89.83                  | {user1, user2, ...}   | US          | New York
203.0.113.45    | 234             | 1               | 2024-01-15 09:22:11  | 2024-01-15 09:35:44  | 13.55                  | {admin}               | CN          | Beijing
198.51.100.78   | 189             | 78              | 2024-01-15 14:10:33  | 2024-01-15 15:02:18  | 51.75                  | {user3, user4, ...}   | RU          | Moscow
```

**복잡도**: 중간 ⭐⭐
**필수 인덱스**: `idx_error_service_time`
**확장 가능성**: IP 블랙리스트 제안, 지역 패턴 분석

---

### E-02: PII 필터링 누락 검사

**비즈니스 가치**: GDPR/CCPA 준수, 개인정보 보호

**사용자 프롬프트:**
- "PII 필터링이 안 된 로그가 있어?"
- "개인정보가 포함된 로그 찾아줘"
- "이메일이나 전화번호가 로그에 남아있는지 확인해줘"

**기대 SQL:**
```sql
WITH pii_patterns AS (
    SELECT
        id,
        service,
        created_at,
        message,
        CASE
            WHEN message ~ '[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}' THEN 'Email'
            WHEN message ~ '\b\d{3}[-.]?\d{3}[-.]?\d{4}\b' THEN 'Phone'
            WHEN message ~ '\b\d{3}-\d{2}-\d{4}\b' THEN 'SSN'
            WHEN message ~ '\b\d{16}\b' THEN 'Credit Card'
            WHEN message ~ '\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b' THEN 'IP Address'
        END AS pii_type,
        is_pii_filtered
    FROM logs
    WHERE created_at > NOW() - INTERVAL '7 days'
      AND level IN ('ERROR', 'WARN', 'INFO')
)
SELECT
    service,
    pii_type,
    COUNT(*) AS pii_occurrences,
    COUNT(CASE WHEN NOT is_pii_filtered THEN 1 END) AS unfiltered_count,
    ROUND(
        100.0 * COUNT(CASE WHEN NOT is_pii_filtered THEN 1 END) / COUNT(*),
        2
    ) AS unfiltered_percent,
    ARRAY_AGG(id ORDER BY created_at DESC) FILTER (WHERE NOT is_pii_filtered) AS example_log_ids
FROM pii_patterns
WHERE pii_type IS NOT NULL
GROUP BY service, pii_type
ORDER BY unfiltered_count DESC;
```

**예상 결과:**
```
service         | pii_type     | pii_occurrences | unfiltered_count | unfiltered_percent | example_log_ids
----------------|--------------|-----------------|------------------|--------------------|-------------------------
user-service    | Email        | 1,234           | 456              | 36.95              | {12345, 23456, 34567}
payment-api     | Credit Card  | 234             | 89               | 38.03              | {45678, 56789}
notification    | Phone        | 567             | 123              | 21.69              | {67890, 78901}
```

**복잡도**: 중간 ⭐⭐⭐
**필수 인덱스**: `idx_service_level_time`
**확장 가능성**: 자동 PII 탐지 및 마스킹

---

### E-03: 권한 상승 시도 탐지

**비즈니스 가치**: 내부 위협 탐지, 권한 관리 검증

**사용자 프롬프트:**
- "권한 없는 리소스 접근 시도가 있었어?"
- "Forbidden 에러가 많이 발생한 사용자는?"
- "권한 상승 공격 패턴 찾아줘"

**기대 SQL:**
```sql
SELECT
    user_id,
    COUNT(*) AS forbidden_attempts,
    COUNT(DISTINCT endpoint) AS attempted_endpoints,
    COUNT(DISTINCT service) AS attempted_services,
    ARRAY_AGG(DISTINCT endpoint ORDER BY endpoint) AS endpoints,
    MIN(created_at) AS first_attempt,
    MAX(created_at) AS last_attempt,
    STRING_AGG(DISTINCT client_ip, ', ') AS source_ips
FROM logs
WHERE (
    http_status_code = 403
    OR error_type IN ('Forbidden', 'Unauthorized', 'AccessDenied')
)
  AND user_id IS NOT NULL
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY user_id
HAVING COUNT(*) >= 10
ORDER BY forbidden_attempts DESC
LIMIT 20;
```

**예상 결과:**
```
user_id    | forbidden_attempts | attempted_endpoints | attempted_services | endpoints                             | first_attempt        | last_attempt         | source_ips
-----------|--------------------|--------------------|-------------------|---------------------------------------|----------------------|----------------------|------------------
user_5678  | 156                | 23                 | 5                 | {/admin, /api/v1/users, ...}          | 2024-01-15 10:15:32  | 2024-01-15 11:45:22  | 192.168.1.50
user_9012  | 89                 | 12                 | 3                 | {/api/v1/payments/all, ...}           | 2024-01-15 09:22:11  | 2024-01-15 10:05:44  | 10.0.0.123
user_3456  | 67                 | 8                  | 2                 | {/api/internal, /metrics}             | 2024-01-15 14:10:33  | 2024-01-15 15:22:18  | 172.16.0.45
```

**복잡도**: 중간 ⭐⭐
**필수 인덱스**: `idx_user_time`, `idx_error_service_time`
**확장 가능성**: 비정상 행동 패턴 분석

---

### E-04: SQL 인젝션 시도 탐지

**비즈니스 가치**: 애플리케이션 보안 강화

**사용자 프롬프트:**
- "SQL 인젝션 공격이 있었는지 확인해줘"
- "의심스러운 쿼리 패턴 찾아줘"
- "ValidationError 중에 SQL 관련된 거는?"

**기대 SQL:**
```sql
WITH sql_injection_patterns AS (
    SELECT
        id,
        created_at,
        service,
        endpoint,
        client_ip,
        user_id,
        message,
        metadata,
        CASE
            WHEN message ~* '(union|select|insert|update|delete|drop|create|alter)\s' THEN 'SQL Keywords'
            WHEN message ~ '(--|#|/\*|\*/|;)' THEN 'SQL Comments'
            WHEN message ~ '(''\s*or\s*''|''\s*=\s*'')' THEN 'Always True'
            WHEN message ~ '(\bor\b.*=|\band\b.*=)' THEN 'Boolean Logic'
        END AS injection_pattern
    FROM logs
    WHERE created_at > NOW() - INTERVAL '24 hours'
      AND (
        error_type IN ('ValidationError', 'SQLSyntaxError', 'DatabaseError')
        OR message ~* '(union|select|insert|update|delete|drop|create|alter|--|#|/\*|\*/)'
      )
)
SELECT
    injection_pattern,
    COUNT(*) AS attempt_count,
    COUNT(DISTINCT client_ip) AS unique_ips,
    COUNT(DISTINCT endpoint) AS affected_endpoints,
    ARRAY_AGG(DISTINCT client_ip) AS attacker_ips,
    ARRAY_AGG(DISTINCT endpoint) AS vulnerable_endpoints,
    MIN(created_at) AS first_attempt,
    MAX(created_at) AS last_attempt
FROM sql_injection_patterns
WHERE injection_pattern IS NOT NULL
GROUP BY injection_pattern
ORDER BY attempt_count DESC;
```

**예상 결과:**
```
injection_pattern | attempt_count | unique_ips | affected_endpoints | attacker_ips              | vulnerable_endpoints           | first_attempt        | last_attempt
------------------|---------------|------------|--------------------|---------------------------|--------------------------------|----------------------|--------------------
SQL Keywords      | 234           | 12         | 5                  | {192.168.1.100, ...}      | {/api/v1/search, /api/users}   | 2024-01-15 10:15:32  | 2024-01-15 11:45:22
Always True       | 156           | 8          | 3                  | {203.0.113.45, ...}       | {/login, /api/v1/auth}         | 2024-01-15 09:22:11  | 2024-01-15 10:05:44
SQL Comments      | 89            | 5          | 2                  | {198.51.100.78, ...}      | {/api/v1/products}             | 2024-01-15 14:10:33  | 2024-01-15 15:22:18
```

**복잡도**: 높음 ⭐⭐⭐
**필수 인덱스**: `idx_error_service_time`
**확장 가능성**: WAF 룰 생성, 자동 차단 정책

---

### E-05: 비정상적 접근 패턴

**비즈니스 가치**: 봇, 스크래퍼 탐지

**사용자 프롬프트:**
- "너무 빠른 속도로 요청을 보내는 IP는?"
- "봇 공격이 있었는지 확인해줘"
- "비정상적인 트래픽 패턴 찾아줘"

**기대 SQL:**
```sql
WITH request_rates AS (
    SELECT
        client_ip,
        DATE_TRUNC('minute', created_at) AS minute_bucket,
        COUNT(*) AS requests_per_minute,
        COUNT(DISTINCT endpoint) AS unique_endpoints,
        COUNT(DISTINCT user_agent) AS unique_user_agents,
        ARRAY_AGG(DISTINCT endpoint ORDER BY endpoint) AS endpoints
    FROM logs
    WHERE created_at > NOW() - INTERVAL '1 hour'
      AND client_ip IS NOT NULL
      AND log_type IN ('BACKEND', 'FRONTEND')
    GROUP BY client_ip, minute_bucket
)
SELECT
    client_ip,
    MAX(requests_per_minute) AS peak_rpm,
    ROUND(AVG(requests_per_minute), 2) AS avg_rpm,
    COUNT(*) AS active_minutes,
    MAX(unique_endpoints) AS max_endpoints_per_minute,
    MAX(unique_user_agents) AS user_agent_variations,
    STRING_AGG(DISTINCT endpoints::TEXT, ' | ') AS endpoint_patterns
FROM request_rates
WHERE requests_per_minute > 60  -- 분당 60회 이상
GROUP BY client_ip
HAVING MAX(requests_per_minute) > 100
ORDER BY peak_rpm DESC
LIMIT 20;
```

**예상 결과:**
```
client_ip       | peak_rpm | avg_rpm | active_minutes | max_endpoints_per_minute | user_agent_variations | endpoint_patterns
----------------|----------|---------|----------------|-------------------------|-----------------------|------------------------------------
192.168.1.200   | 1,234    | 987.45  | 58             | 45                      | 1                     | {/api/v1/products, /api/v1/search}
203.0.113.90    | 856      | 678.23  | 45             | 23                      | 2                     | {/api/v1/listings, /api/v1/items}
198.51.100.120  | 567      | 456.78  | 38             | 12                      | 1                     | {/api/v1/data}
```

**복잡도**: 높음 ⭐⭐⭐
**필수 인덱스**: `idx_service_level_time`
**확장 가능성**: Rate limiting 임계값 제안

---

### E-06: 데이터 유출 시도 탐지

**비즈니스 가치**: 민감 데이터 보호

**사용자 프롬프트:**
- "대량의 데이터를 조회한 사용자는?"
- "데이터 유출 가능성이 있는 패턴 찾아줘"
- "한 번에 많은 레코드를 가져간 요청은?"

**기대 SQL:**
```sql
SELECT
    user_id,
    endpoint,
    COUNT(*) AS large_query_count,
    ROUND(AVG((metadata->>'result_count')::NUMERIC), 0) AS avg_result_count,
    MAX((metadata->>'result_count')::NUMERIC) AS max_result_count,
    ROUND(SUM(response_size_bytes) / (1024.0 * 1024.0), 2) AS total_data_mb,
    MIN(created_at) AS first_occurrence,
    MAX(created_at) AS last_occurrence,
    ARRAY_AGG(DISTINCT client_ip) AS source_ips
FROM logs
WHERE (metadata->>'result_count')::NUMERIC > 1000  -- 결과 1000건 이상
  AND endpoint IS NOT NULL
  AND user_id IS NOT NULL
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY user_id, endpoint
HAVING COUNT(*) >= 5  -- 5회 이상
ORDER BY total_data_mb DESC
LIMIT 20;
```

**예상 결과:**
```
user_id    | endpoint                  | large_query_count | avg_result_count | max_result_count | total_data_mb | first_occurrence     | last_occurrence      | source_ips
-----------|---------------------------|-------------------|-----------------|--------------------|---------------|----------------------|----------------------|------------------
user_7890  | /api/v1/users/export      | 23                | 8,765           | 25,000             | 3,456.78      | 2024-01-15 10:15:32  | 2024-01-15 11:45:22  | {192.168.1.75}
user_1234  | /api/v1/transactions/list | 18                | 5,432           | 15,000             | 2,345.67      | 2024-01-15 09:22:11  | 2024-01-15 10:05:44  | {10.0.0.89}
user_5678  | /api/v1/orders/all        | 12                | 3,456           | 10,000             | 1,876.54      | 2024-01-15 14:10:33  | 2024-01-15 15:22:18  | {172.16.0.90}
```

**복잡도**: 중간 ⭐⭐⭐
**필수 인덱스**: `idx_user_time`, `idx_metadata_gin`
**확장 가능성**: 이상 탐지 머신러닝 모델

---

## 7. F. 사용자 경험 분석 시나리오

### F-01: 프론트엔드 에러 발생 페이지

**비즈니스 가치**: UX 개선 우선순위, 사용자 이탈 방지

**사용자 프롬프트:**
- "프론트엔드에서 에러가 가장 많이 발생하는 페이지는?"
- "사용자들이 어디서 문제를 겪어?"
- "클라이언트 에러 top 5 페이지는?"

**기대 SQL:**
```sql
SELECT
    page_path,
    COUNT(*) AS error_count,
    COUNT(DISTINCT user_id) AS affected_users,
    COUNT(DISTINCT session_id) AS affected_sessions,
    STRING_AGG(DISTINCT error_type, ', ' ORDER BY error_type) AS error_types,
    ROUND(AVG(EXTRACT(EPOCH FROM (MAX(created_at) - MIN(created_at)))) / 60, 2) AS avg_session_duration_minutes,
    MIN(created_at) AS first_error,
    MAX(created_at) AS last_error
FROM logs
WHERE log_type = 'FRONTEND'
  AND level = 'ERROR'
  AND page_path IS NOT NULL
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY page_path
ORDER BY error_count DESC
LIMIT 10;
```

**예상 결과:**
```
page_path        | error_count | affected_users | affected_sessions | error_types                         | avg_session_duration_minutes | first_error          | last_error
-----------------|-------------|----------------|-------------------|-------------------------------------|------------------------------|----------------------|--------------------
/checkout        | 1,234       | 567            | 789               | NetworkError, ValidationError       | 3.45                         | 2024-01-08 10:15:32  | 2024-01-15 11:45:22
/payment         | 987         | 456            | 567               | PaymentError, TimeoutError          | 2.78                         | 2024-01-08 09:22:11  | 2024-01-15 10:05:44
/search          | 789         | 345            | 456               | APIError, RenderError               | 5.12                         | 2024-01-08 14:10:33  | 2024-01-15 15:22:18
```

**복잡도**: 낮음 ⭐
**필수 인덱스**: `idx_frontend_errors`
**확장 가능성**: 디바이스별, 브라우저별 분석

---

### F-02: 브라우저별 호환성 이슈

**비즈니스 가치**: 브라우저 지원 정책, 테스트 우선순위

**사용자 프롬프트:**
- "특정 브라우저에서만 발생하는 에러는?"
- "브라우저 호환성 문제가 있는지 확인해줘"
- "Safari에서 에러가 많이 나와?"

**기대 SQL:**
```sql
SELECT
    browser_name,
    browser_version,
    COUNT(*) AS error_count,
    COUNT(DISTINCT user_id) AS affected_users,
    ROUND(
        100.0 * COUNT(*) / SUM(COUNT(*)) OVER (),
        2
    ) AS error_percentage,
    STRING_AGG(DISTINCT error_type, ', ' ORDER BY error_type) AS error_types,
    ARRAY_AGG(DISTINCT page_path ORDER BY page_path) AS affected_pages
FROM logs
WHERE log_type = 'FRONTEND'
  AND level = 'ERROR'
  AND browser_name IS NOT NULL
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY browser_name, browser_version
HAVING COUNT(*) >= 10
ORDER BY error_count DESC
LIMIT 15;
```

**예상 결과:**
```
browser_name | browser_version | error_count | affected_users | error_percentage | error_types                    | affected_pages
-------------|-----------------|-------------|----------------|------------------|--------------------------------|----------------------------------
Safari       | 14.0.0          | 456         | 234            | 25.43            | RenderError, CSSError          | {/checkout, /dashboard, /profile}
IE           | 11.0            | 234         | 123            | 13.05            | ScriptError, PolyfillError     | {/search, /products}
Firefox      | 120.0.0         | 189         | 98             | 10.54            | NetworkError, LocalStorageError| {/payment, /cart}
```

**복잡도**: 낮음 ⭐
**필수 인덱스**: `idx_frontend_errors`
**확장 가능성**: 버전별 세부 분석

---

### F-03: 모바일 vs 데스크탑 에러 비교

**비즈니스 가치**: 모바일 최적화 우선순위

**사용자 프롬프트:**
- "모바일과 데스크탑 중 어디서 에러가 많아?"
- "디바이스별 에러 비율 비교해줘"
- "모바일 사용자 경험 문제는?"

**기대 SQL:**
```sql
WITH device_stats AS (
    SELECT
        device_type,
        COUNT(*) AS total_logs,
        COUNT(CASE WHEN level = 'ERROR' THEN 1 END) AS error_count,
        COUNT(DISTINCT user_id) AS unique_users,
        COUNT(DISTINCT error_type) AS unique_error_types,
        ROUND(AVG(duration_ms), 2) AS avg_page_load_ms
    FROM logs
    WHERE log_type = 'FRONTEND'
      AND created_at > NOW() - INTERVAL '7 days'
      AND device_type IS NOT NULL
    GROUP BY device_type
)
SELECT
    device_type,
    total_logs,
    error_count,
    ROUND(100.0 * error_count / total_logs, 2) AS error_rate_percent,
    unique_users,
    unique_error_types,
    avg_page_load_ms
FROM device_stats
ORDER BY error_rate_percent DESC;
```

**예상 결과:**
```
device_type | total_logs | error_count | error_rate_percent | unique_users | unique_error_types | avg_page_load_ms
------------|------------|-------------|--------------------|--------------|--------------------|------------------
mobile      | 456,789    | 12,345      | 2.70               | 23,456       | 18                 | 3,456.78
tablet      | 123,456    | 2,345       | 1.90               | 8,901        | 12                 | 2,890.12
desktop     | 789,012    | 8,901       | 1.13               | 45,678       | 15                 | 1,987.65
```

**복잡도**: 낮음 ⭐
**필수 인덱스**: `idx_frontend_errors`
**확장 가능성**: 화면 크기별 분석

---

### F-04: 사용자 여정 분석

**비즈니스 가치**: 이탈 지점 발견, 전환율 개선

**사용자 프롬프트:**
- "결제까지 가는 여정에서 어디서 에러가 나?"
- "checkout 플로우 중 이탈이 많은 지점은?"
- "회원가입 과정의 문제점은?"

**기대 SQL:**
```sql
WITH checkout_funnel AS (
    SELECT
        session_id,
        user_id,
        page_path,
        level,
        error_type,
        created_at,
        ROW_NUMBER() OVER (PARTITION BY session_id ORDER BY created_at) AS step_order
    FROM logs
    WHERE log_type = 'FRONTEND'
      AND created_at > NOW() - INTERVAL '24 hours'
      AND (
        page_path IN ('/cart', '/checkout', '/payment', '/confirmation')
        OR page_path LIKE '/checkout%'
      )
)
SELECT
    page_path,
    COUNT(DISTINCT session_id) AS sessions,
    COUNT(CASE WHEN level = 'ERROR' THEN 1 END) AS errors,
    ROUND(100.0 * COUNT(CASE WHEN level = 'ERROR' THEN 1 END) / COUNT(*), 2) AS error_rate,
    STRING_AGG(DISTINCT error_type, ', ') FILTER (WHERE level = 'ERROR') AS error_types,
    COUNT(DISTINCT user_id) AS unique_users,
    ROUND(AVG(step_order), 2) AS avg_step_position
FROM checkout_funnel
GROUP BY page_path
ORDER BY avg_step_position;
```

**예상 결과:**
```
page_path      | sessions | errors | error_rate | error_types                  | unique_users | avg_step_position
---------------|----------|--------|------------|------------------------------|--------------|------------------
/cart          | 5,678    | 89     | 1.57       | ValidationError              | 4,567        | 1.23
/checkout      | 4,123    | 234    | 5.68       | NetworkError, AddressError   | 3,456        | 2.45
/payment       | 2,890    | 456    | 15.78      | PaymentError, TimeoutError   | 2,345        | 3.67
/confirmation  | 1,234    | 12     | 0.97       | NULL                         | 1,234        | 4.89
```

**복잡도**: 높음 ⭐⭐⭐⭐
**필수 인덱스**: `idx_frontend_errors`
**확장 가능성**: 이탈 원인 분석, 전환율 계산

---

### F-05: 페이지 로드 성능 이슈

**비즈니스 가치**: 로딩 속도 개선, SEO 향상

**사용자 프롬프트:**
- "페이지 로딩이 느린 경우는?"
- "3초 이상 걸린 페이지는?"
- "프론트엔드 성능 문제 분석해줘"

**기대 SQL:**
```sql
SELECT
    page_path,
    COUNT(*) AS slow_load_count,
    COUNT(DISTINCT user_id) AS affected_users,
    ROUND(AVG(duration_ms), 2) AS avg_load_time_ms,
    ROUND(PERCENTILE_CONT(0.50) WITHIN GROUP (ORDER BY duration_ms), 2) AS median_load_time,
    ROUND(PERCENTILE_CONT(0.95) WITHIN GROUP (ORDER BY duration_ms), 2) AS p95_load_time,
    ROUND(MAX(duration_ms), 2) AS max_load_time,
    ROUND(AVG((metadata->>'dom_content_loaded_ms')::NUMERIC), 2) AS avg_dom_ready_time,
    device_type
FROM logs
WHERE log_type = 'FRONTEND'
  AND page_path IS NOT NULL
  AND duration_ms > 3000  -- 3초 이상
  AND created_at > NOW() - INTERVAL '7 days'
GROUP BY page_path, device_type
HAVING COUNT(*) >= 10
ORDER BY avg_load_time_ms DESC
LIMIT 20;
```

**예상 결과:**
```
page_path        | slow_load_count | affected_users | avg_load_time_ms | median_load_time | p95_load_time | max_load_time | avg_dom_ready_time | device_type
-----------------|-----------------|----------------|------------------|------------------|---------------|---------------|--------------------|-------------
/dashboard       | 1,234           | 567            | 8,765.43         | 6,543.21         | 15,678.90     | 28,901.23     | 3,456.78           | mobile
/reports         | 987             | 456            | 7,654.32         | 5,678.90         | 12,345.67     | 23,456.78     | 2,987.65           | desktop
/analytics       | 789             | 345            | 6,543.21         | 4,987.65         | 10,234.56     | 19,876.54     | 2,345.67           | mobile
```

**복잡도**: 중간 ⭐⭐
**필수 인덱스**: `idx_frontend_errors`, `idx_duration`
**확장 가능성**: 리소스별 로딩 시간 분석

---

## 8. 시나리오 복잡도 분석

### 복잡도 기준

| 복잡도 | SQL 특징 | 예상 실행 시간 | Text-to-SQL 난이도 |
|-------|----------|--------------|-------------------|
| ⭐ 낮음 | 단순 필터, 집계 | < 100ms | 쉬움 (정확도 95%+) |
| ⭐⭐ 중간 | JOIN, 윈도우 함수 | 100-500ms | 보통 (정확도 85-95%) |
| ⭐⭐⭐ 높음 | CTE, 복잡한 집계 | 500ms-2s | 어려움 (정확도 70-85%) |
| ⭐⭐⭐⭐ 매우 높음 | 다중 CTE, 재귀 | 2s+ | 매우 어려움 (정확도 60-70%) |

### 카테고리별 평균 복잡도

```
A. 장애 대응:       ⭐⭐⭐   (2.7 / 4.0)
B. 성능 최적화:     ⭐⭐⭐   (2.9 / 4.0)
C. 데이터 정합성:   ⭐⭐     (2.2 / 4.0)
D. 비용 관리:       ⭐⭐     (1.8 / 4.0)
E. 보안/프라이버시: ⭐⭐⭐   (2.7 / 4.0)
F. 사용자 경험:     ⭐⭐     (2.3 / 4.0)
```

---

## 9. Text-to-SQL 에이전트 검증 방법

### 9.1 검증 프레임워크

```python
# tests/test_text_to_sql.py

import pytest
from text_to_sql_agent import generate_sql

@pytest.mark.parametrize("scenario_id,prompt,expected_sql", [
    ("A-01", "지난 1시간 동안 발생한 에러가 몇 건이야?", "SELECT COUNT(*) FROM logs WHERE level = 'ERROR'..."),
    # 38개 시나리오 모두 포함
])
def test_scenario(scenario_id, prompt, expected_sql):
    generated_sql = generate_sql(prompt)

    # SQL 구문 검증
    assert is_valid_sql(generated_sql)

    # 핵심 키워드 검증
    assert check_keywords(generated_sql, expected_sql)

    # 실행 검증
    result = execute_sql(generated_sql)
    assert result is not None

    # 결과 구조 검증
    assert validate_result_schema(result, scenario_id)
```

### 9.2 성능 메트릭

```python
# 정확도 측정
def calculate_accuracy():
    metrics = {
        'syntax_accuracy': 0,      # SQL 문법 정확도
        'logic_accuracy': 0,        # 쿼리 로직 정확도
        'result_accuracy': 0,       # 결과 정확도
        'performance': 0            # 실행 성능
    }

    for scenario in scenarios:
        result = test_scenario(scenario)
        metrics['syntax_accuracy'] += result.syntax_score
        metrics['logic_accuracy'] += result.logic_score
        metrics['result_accuracy'] += result.result_score
        metrics['performance'] += result.execution_time

    return {
        k: v / len(scenarios)
        for k, v in metrics.items()
    }
```

### 9.3 에이전트 개선 로드맵

**Phase 1: 기본 시나리오 (낮음 복잡도)**
- 목표: 95% 정확도
- 기간: 1-2주
- 시나리오: A-01, A-02, C-01, D-01, F-01

**Phase 2: 중간 시나리오**
- 목표: 85% 정확도
- 기간: 2-3주
- 시나리오: A-03~A-05, B-01~B-04

**Phase 3: 고급 시나리오**
- 목표: 75% 정확도
- 기간: 3-4주
- 시나리오: A-06~A-10, B-05~B-08

**Phase 4: 최적화 및 엣지 케이스**
- 목표: 전체 80% 이상 정확도
- 기간: 2-3주
- 모든 시나리오 재검증

---

**문서 버전**: 1.0
**최종 수정일**: 2024-01-15
**작성자**: Log Analysis System Team
**총 시나리오 수**: 38개
