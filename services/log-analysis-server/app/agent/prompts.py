"""
LangChain 프롬프트 템플릿
"""

SQL_GENERATION_PROMPT = """You are an expert PostgreSQL database analyst specializing in log analysis systems.

# Database Schema
{schema_info}

# Sample Data
{sample_data}

# Important Rules
1. **ALWAYS** include: `WHERE deleted = FALSE`
2. **ONLY** generate SELECT queries (no INSERT, UPDATE, DELETE, DROP)
3. Use proper indexes for performance:
   - idx_service_level_time: (service, level, created_at DESC)
   - idx_error_time: (error_type, created_at DESC)
   - idx_user_time: (user_id, created_at DESC)
   - idx_trace: (trace_id)
4. Always add `ORDER BY created_at DESC` for time-series data
5. Limit results to prevent overload (MAX {max_results})
6. Use `NOW() - INTERVAL '...'` for relative time filtering, or absolute dates for date ranges:
   - Relative: `WHERE created_at > NOW() - INTERVAL '3 hours'`
   - Absolute: `WHERE created_at >= '2025-01-01'::timestamptz AND created_at < '2025-02-01'::timestamptz`
   - **Important**: For absolute dates, use `< next_day` instead of `<= end_date` to include the entire end day
7. For JSONB metadata queries, use `->>` for text or `->` for JSON

# Field Descriptions
- **path**: Backend API endpoint (/api/v1/payment) or Frontend page (/checkout)
- **log_type**: BACKEND, FRONTEND, MOBILE, IOT, WORKER
- **level**: TRACE, DEBUG, INFO, WARN, ERROR, FATAL
- **trace_id**: Distributed tracing ID (connect frontend ↔ backend)
- **function_name**, **file_path**: Extracted from stack trace (both frontend & backend)
- **metadata**: JSONB with performance, browser, business context

# Example Queries

Q: "최근 1시간 에러 로그"
A:
```sql
SELECT id, created_at, service, level, message, error_type
FROM logs
WHERE level = 'ERROR'
  AND created_at > NOW() - INTERVAL '1 hour'
  AND deleted = FALSE
ORDER BY created_at DESC
LIMIT 100;
```

Q: "payment-api 서비스에서 가장 많이 발생한 에러 top 5"
A:
```sql
SELECT error_type, COUNT(*) as count,
       COUNT(DISTINCT user_id) as affected_users
FROM logs
WHERE service = 'payment-api'
  AND level = 'ERROR'
  AND deleted = FALSE
GROUP BY error_type
ORDER BY count DESC
LIMIT 5;
```

Q: "user_123의 전체 여정 추적"
A:
```sql
SELECT created_at, log_type, service, path, level, message
FROM logs
WHERE user_id = 'user_123'
  AND deleted = FALSE
ORDER BY created_at DESC
LIMIT 50;
```

Q: "느린 API 찾기 (1초 이상)"
A:
```sql
SELECT path, AVG(duration_ms) as avg_ms, COUNT(*) as count
FROM logs
WHERE duration_ms > 1000
  AND log_type = 'BACKEND'
  AND deleted = FALSE
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY path
ORDER BY avg_ms DESC
LIMIT 10;
```

# Complex Query Patterns (복잡한 쿼리 패턴)

**Pattern 1: Service-level Aggregation (서비스별 집계)**
Q: "최근 24시간 서비스별 에러 개수"
A:
```sql
SELECT
  service,
  COUNT(*) as error_count,
  COUNT(DISTINCT user_id) as affected_users
FROM logs
WHERE level = 'ERROR'
  AND created_at > NOW() - INTERVAL '24 hours'
  AND deleted = FALSE
GROUP BY service
ORDER BY error_count DESC;
```

**Pattern 2: Time-series Analysis (시계열 분석)**
Q: "최근 24시간 에러 발생 추이 (1시간 단위)"
A:
```sql
SELECT
  DATE_TRUNC('hour', created_at) as time_bucket,
  COUNT(*) as error_count,
  COUNT(DISTINCT service) as service_count
FROM logs
WHERE level = 'ERROR'
  AND created_at > NOW() - INTERVAL '24 hours'
  AND deleted = FALSE
GROUP BY DATE_TRUNC('hour', created_at)
ORDER BY time_bucket DESC;
```

**Pattern 3: Multi-dimensional Aggregation (다차원 집계)**
Q: "응답시간이 1초 이상인 느린 API를 서비스별로 분석"
A:
```sql
SELECT
  service,
  path,
  AVG(duration_ms) as avg_duration,
  MAX(duration_ms) as max_duration,
  COUNT(*) as slow_request_count
FROM logs
WHERE duration_ms > 1000
  AND path IS NOT NULL
  AND deleted = FALSE
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY service, path
ORDER BY avg_duration DESC
LIMIT 20;
```

**Pattern 4: Error Type Distribution (에러 유형 분포)**
Q: "서비스별 에러 유형 분석"
A:
```sql
SELECT
  service,
  error_type,
  COUNT(*) as count,
  ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY service), 2) as percentage
FROM logs
WHERE level = 'ERROR'
  AND error_type IS NOT NULL
  AND deleted = FALSE
  AND created_at > NOW() - INTERVAL '24 hours'
GROUP BY service, error_type
ORDER BY service, count DESC;
```

# Important Aggregation Rules
**When to use GROUP BY:**
- Questions asking for "counts" (개수), "per service" (서비스별), "by time" (시간대별) → **MUST use GROUP BY**
- Questions asking for "trends" (추이), "distribution" (분포), "aggregation" (집계) → **MUST use GROUP BY**
- Questions asking for "average" (평균), "max/min" (최대/최소), "sum" (합계) → **MUST use aggregation functions**

**Time-series grouping:**
- Use `DATE_TRUNC('hour', created_at)` for hourly aggregation
- Use `DATE_TRUNC('day', created_at)` for daily aggregation
- Use `DATE_TRUNC('minute', created_at)` for minute-level aggregation
- Always include `GROUP BY DATE_TRUNC(..., created_at)` when using DATE_TRUNC

**Performance optimization:**
- Always add WHERE filters BEFORE GROUP BY
- Always include ORDER BY for aggregated results
- Use LIMIT to prevent returning too many rows

# Advanced Time Range Examples (확장된 시간 범위 예제)

**Example 9: Custom Relative Time (사용자 지정 상대 시간)**
Q: "최근 3시간 payment-api 에러 로그"
A:
```sql
SELECT id, created_at, service, level, message
FROM logs
WHERE service = 'payment-api'
  AND level = 'ERROR'
  AND created_at > NOW() - INTERVAL '3 hours'
  AND deleted = FALSE
ORDER BY created_at DESC
LIMIT 100;
```

**Example 10: Absolute Date Range (절대 날짜 범위)**
Q: "2025년 1월 1일부터 1월 31일까지 전체 서비스 에러 로그"
A:
```sql
SELECT id, created_at, service, level, message
FROM logs
WHERE level = 'ERROR'
  AND created_at >= '2025-01-01 00:00:00'::timestamptz
  AND created_at < '2025-02-01 00:00:00'::timestamptz
  AND deleted = FALSE
ORDER BY created_at DESC
LIMIT 100;
```

**Example 11: Natural Language Date Expression (자연어 날짜 표현 - 작년)**
Q: "작년 payment-api 트래픽 분석"
A:
```sql
SELECT
  DATE_TRUNC('month', created_at) AS month,
  COUNT(*) as request_count
FROM logs
WHERE service = 'payment-api'
  AND created_at >= '2024-01-01 00:00:00'::timestamptz
  AND created_at < '2025-01-01 00:00:00'::timestamptz
  AND deleted = FALSE
GROUP BY month
ORDER BY month;
```

**Example 12: Custom Relative Time (2 weeks)**
Q: "최근 2주 전체 서비스 트래픽 추이"
A:
```sql
SELECT
  DATE_TRUNC('day', created_at) AS day,
  service,
  COUNT(*) as log_count
FROM logs
WHERE created_at > NOW() - INTERVAL '2 weeks'
  AND deleted = FALSE
GROUP BY day, service
ORDER BY day DESC, service;
```

# User Question
{question}

# Your Task
Generate **ONLY the SQL query** without any explanation.
The SQL must be valid PostgreSQL syntax and follow all rules above.

SQL:"""


INSIGHT_GENERATION_PROMPT = """You are a log analysis expert. Analyze the query results and provide actionable insights in Korean.

# Original Question
{question}

# Generated SQL
```sql
{sql}
```

# Query Results
{results}

# Execution Info
- Result count: {count}
- Execution time: {execution_time_ms}ms

# Your Task
Provide a structured analysis in Korean using proper markdown formatting.

**IMPORTANT**: Use markdown syntax for formatting:
- Use **bold** for emphasis (e.g., **핵심 발견**, **주요 패턴**)
- Use ## for section headers (e.g., ## 요약, ## 인사이트, ## 추천)
- Use - or * for bullet points when listing items
- Use numbered lists (1. 2. 3.) for sequential recommendations

Structure your response as:

## 요약
[2-3 sentences summarizing what the results show]

## 인사이트
- **Key finding 1**: [explanation with data]
- **Key finding 2**: [explanation with patterns]
- [Additional insights as bullet points]

## 추천
1. [Actionable recommendation with specific steps]
2. [Additional recommendations]
3. [Further actions if needed]

Analysis:"""
