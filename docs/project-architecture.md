# 프로젝트 구조 및 아키텍처

## 목차

1. [시스템 아키텍처 개요](#1-시스템-아키텍처-개요)
2. [컴포넌트 상세 설명](#2-컴포넌트-상세-설명)
3. [데이터 파이프라인 흐름](#3-데이터-파이프라인-흐름)
4. [디렉토리 구조](#4-디렉토리-구조)
5. [에러 처리 및 복구 전략](#5-에러-처리-및-복구-전략)
6. [확장성 고려사항](#6-확장성-고려사항)
7. [배포 아키텍처](#7-배포-아키텍처)

---

## 1. 시스템 아키텍처 개요

### 1.1 전체 시스템 다이어그램

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           APPLICATION LAYER                                     │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐             │
│  │  Python Backend  │  │  Node.js Backend │  │  Svelte Frontend │             │
│  │  (FastAPI/Flask) │  │  (Express)       │  │  (SPA)           │             │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘             │
│           │                     │                     │                         │
│           │ ┌───────────────────┴─────────────────────┴──────────┐             │
│           │ │          Common Logging Strategy                   │             │
│           │ └────────────────────────────────────────────────────┘             │
│           │                                                                     │
│           │  Option 1: Library         Option 2: Docker stdout                 │
│           ▼                                   ▼                                 │
│  ┌─────────────────┐                ┌─────────────────┐                        │
│  │  log_collector  │                │  console.log()  │                        │
│  │  (Python pkg)   │                │  print()        │                        │
│  │  log-helper.js  │                │  logging.info() │                        │
│  └────────┬────────┘                └────────┬────────┘                        │
│           │                                  │                                  │
└───────────┼──────────────────────────────────┼──────────────────────────────────┘
            │                                  │
            │ HTTP POST                        │ Docker logging
            │ /api/v1/logs                     │ driver (json-file)
            ▼                                  ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          COLLECTION LAYER                                       │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────────────────┐       ┌─────────────────────────────┐        │
│  │    FastAPI Log Server        │       │         Fluentd             │        │
│  │  - HTTP endpoint receiver    │       │  - Docker stdout capture    │        │
│  │  - Validation & enrichment   │◄──────┤  - Log parsing              │        │
│  │  - Async batch insertion     │       │  - Format transformation    │        │
│  └──────────┬───────────────────┘       └─────────────────────────────┘        │
│             │                                                                   │
│             │ Async writes (asyncpg)                                            │
│             ▼                                                                   │
└─────────────────────────────────────────────────────────────────────────────────┘
              │
              │ PostgreSQL protocol (5432)
              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                           STORAGE LAYER                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐      │
│  │                    PostgreSQL 15 (Partitioned)                       │      │
│  │                                                                      │      │
│  │  ├─ logs (parent table)                                             │      │
│  │  │   ├─ logs_2024_01 (partition: Jan 2024)                          │      │
│  │  │   ├─ logs_2024_02 (partition: Feb 2024)                          │      │
│  │  │   ├─ logs_2024_03 (partition: Mar 2024)                          │      │
│  │  │   └─ ...                                                          │      │
│  │  │                                                                   │      │
│  │  ├─ Indexes                                                          │      │
│  │  │   ├─ idx_service_level_time (B-tree)                             │      │
│  │  │   ├─ idx_error_service_time (B-tree)                             │      │
│  │  │   ├─ idx_user_time (B-tree)                                      │      │
│  │  │   ├─ idx_metadata_gin (GIN)                                      │      │
│  │  │   └─ ...                                                          │      │
│  │  │                                                                   │      │
│  │  └─ Materialized Views                                              │      │
│  │      ├─ daily_log_summary                                           │      │
│  │      ├─ error_patterns                                              │      │
│  │      └─ performance_metrics                                         │      │
│  └──────────────────────────────────────────────────────────────────────┘      │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
              │
              │ SQL queries
              ▼
┌─────────────────────────────────────────────────────────────────────────────────┐
│                          ANALYSIS LAYER                                         │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                 │
│  ┌──────────────────────────────────────────────────────────────────────┐      │
│  │                  Text-to-SQL Agent (LangChain)                       │      │
│  │                                                                      │      │
│  │  ┌────────────────────┐    ┌────────────────────┐                  │      │
│  │  │  Claude Sonnet 4.5 │    │   Schema Context   │                  │      │
│  │  │  - Natural language│    │   - Table schema   │                  │      │
│  │  │    understanding   │◄───┤   - Relationships  │                  │      │
│  │  │  - SQL generation  │    │   - Indexes        │                  │      │
│  │  └─────────┬──────────┘    └────────────────────┘                  │      │
│  │            │                                                         │      │
│  │            │ Generated SQL                                           │      │
│  │            ▼                                                         │      │
│  │  ┌────────────────────┐    ┌────────────────────┐                  │      │
│  │  │  SQL Validator     │    │  Query Executor    │                  │      │
│  │  │  - Syntax check    │───►│  - Execute query   │                  │      │
│  │  │  - Security check  │    │  - Result format   │                  │      │
│  │  │  - Performance est │    │  - Explanation     │                  │      │
│  │  └────────────────────┘    └─────────┬──────────┘                  │      │
│  │                                       │                             │      │
│  │                                       │ Results                     │      │
│  │                                       ▼                             │      │
│  │  ┌────────────────────────────────────────────────────┐            │      │
│  │  │           Result Interpreter                       │            │      │
│  │  │  - Format results for human consumption           │            │      │
│  │  │  - Generate insights and recommendations           │            │      │
│  │  │  - Create visualizations (optional)                │            │      │
│  │  └────────────────────────────────────────────────────┘            │      │
│  └──────────────────────────────────────────────────────────────────────┘      │
│                                                                                 │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 아키텍처 레이어 설명

| 레이어 | 책임 | 주요 기술 | 확장 포인트 |
|-------|------|----------|-----------|
| **Application** | 로그 생성 | Python, Node.js, Svelte | 다른 언어/프레임워크 추가 |
| **Collection** | 로그 수집 및 전처리 | FastAPI, Fluentd | Kafka, Logstash 연동 |
| **Storage** | 로그 저장 및 인덱싱 | PostgreSQL 15 | ClickHouse, TimescaleDB 마이그레이션 |
| **Analysis** | 자연어 질의 및 분석 | LangChain, Claude API | 다른 LLM, 커스텀 에이전트 |

### 1.3 핵심 설계 원칙

1. **유연성**: 두 가지 로그 수집 방법 지원 (라이브러리 vs stdout)
2. **확장성**: 파티셔닝, 인덱스 최적화로 대용량 처리
3. **신뢰성**: 비동기 배치 처리, 에러 복구
4. **분석 용이성**: Text-to-SQL로 진입 장벽 낮춤
5. **비용 효율**: 단일 통합 테이블, 파티션 아카이빙

---

## 2. 컴포넌트 상세 설명

### 2.1 로그 수집 라이브러리 (Option 1)

#### Python 로그 수집 클라이언트

**파일**: `clients/python/log_collector/__init__.py`

```python
import httpx
import asyncio
from typing import Optional, Dict, Any
from datetime import datetime

class LogCollector:
    """비동기 로그 수집 클라이언트"""

    def __init__(
        self,
        log_server_url: str,
        service: str,
        environment: str = "development",
        batch_size: int = 10,
        flush_interval: float = 5.0
    ):
        self.log_server_url = log_server_url
        self.service = service
        self.environment = environment
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._buffer = []
        self._lock = asyncio.Lock()
        self._client = httpx.AsyncClient(timeout=10.0)

    async def log(
        self,
        level: str,
        message: str,
        **kwargs
    ):
        """로그 전송 (배치 처리)"""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "log_type": "BACKEND",
            "service": self.service,
            "environment": self.environment,
            "message": message,
            **kwargs
        }

        async with self._lock:
            self._buffer.append(log_entry)
            if len(self._buffer) >= self.batch_size:
                await self._flush()

    async def _flush(self):
        """버퍼의 로그를 서버로 전송"""
        if not self._buffer:
            return

        batch = self._buffer.copy()
        self._buffer.clear()

        try:
            response = await self._client.post(
                f"{self.log_server_url}/api/v1/logs/batch",
                json={"logs": batch}
            )
            response.raise_for_status()
        except Exception as e:
            # 실패 시 로컬 파일에 백업
            self._save_to_local(batch, error=str(e))

    async def close(self):
        """종료 시 남은 로그 flush"""
        await self._flush()
        await self._client.aclose()
```

**사용 예시**:

```python
# FastAPI 애플리케이션
from log_collector import LogCollector

logger = LogCollector(
    log_server_url="http://log-server:8000",
    service="payment-api",
    environment="production"
)

@app.post("/api/v1/payment")
async def process_payment(payment: Payment):
    try:
        result = await payment_processor.process(payment)
        await logger.log(
            "INFO",
            "Payment processed successfully",
            user_id=payment.user_id,
            trace_id=request.state.trace_id,
            endpoint="/api/v1/payment",
            duration_ms=request.state.duration,
            metadata={"order_id": payment.order_id, "amount": payment.amount}
        )
        return result
    except Exception as e:
        await logger.log(
            "ERROR",
            str(e),
            user_id=payment.user_id,
            trace_id=request.state.trace_id,
            error_type=type(e).__name__,
            stack_trace=traceback.format_exc()
        )
        raise
```

#### JavaScript/TypeScript 로그 수집 클라이언트

**파일**: `clients/javascript/log-helper.js`

```javascript
class LogHelper {
  constructor(config) {
    this.logServerUrl = config.logServerUrl;
    this.service = config.service;
    this.environment = config.environment || 'development';
    this.batchSize = config.batchSize || 10;
    this.buffer = [];
    this.flushInterval = setInterval(() => this.flush(), 5000);
  }

  async log(level, message, metadata = {}) {
    const logEntry = {
      timestamp: new Date().toISOString(),
      level,
      log_type: typeof window !== 'undefined' ? 'FRONTEND' : 'BACKEND',
      service: this.service,
      environment: this.environment,
      message,
      ...metadata
    };

    // 프론트엔드 특화 정보 자동 수집
    if (typeof window !== 'undefined') {
      logEntry.page_path = window.location.pathname;
      logEntry.page_url = window.location.href;
      logEntry.browser_name = this.detectBrowser();
      logEntry.device_type = this.detectDevice();
      logEntry.screen_width = window.screen.width;
      logEntry.screen_height = window.screen.height;
    }

    this.buffer.push(logEntry);

    if (this.buffer.length >= this.batchSize) {
      await this.flush();
    }
  }

  async flush() {
    if (this.buffer.length === 0) return;

    const batch = [...this.buffer];
    this.buffer = [];

    try {
      await fetch(`${this.logServerUrl}/api/v1/logs/batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ logs: batch })
      });
    } catch (error) {
      console.error('Failed to send logs:', error);
      // Fallback: localStorage에 저장
      this.saveToLocalStorage(batch);
    }
  }

  detectBrowser() {
    const ua = navigator.userAgent;
    if (ua.includes('Chrome')) return 'Chrome';
    if (ua.includes('Firefox')) return 'Firefox';
    if (ua.includes('Safari')) return 'Safari';
    if (ua.includes('Edge')) return 'Edge';
    return 'Unknown';
  }

  detectDevice() {
    const width = window.screen.width;
    if (width < 768) return 'mobile';
    if (width < 1024) return 'tablet';
    return 'desktop';
  }

  destroy() {
    clearInterval(this.flushInterval);
    this.flush();
  }
}

export default LogHelper;
```

**Svelte 사용 예시**:

```svelte
<script>
  import LogHelper from '$lib/log-helper';
  import { onDestroy } from 'svelte';

  const logger = new LogHelper({
    logServerUrl: 'http://log-server:8000',
    service: 'web-app',
    environment: 'production'
  });

  async function handleCheckout() {
    const startTime = performance.now();
    try {
      const result = await checkout(cart);
      const duration = performance.now() - startTime;

      logger.log('INFO', 'Checkout successful', {
        user_id: $user.id,
        trace_id: generateTraceId(),
        action_type: 'button_click',
        action_target: 'button#checkout',
        metadata: {
          cart_items: cart.items.length,
          total_amount: cart.total,
          duration_ms: duration
        }
      });
    } catch (error) {
      logger.log('ERROR', error.message, {
        user_id: $user.id,
        trace_id: generateTraceId(),
        error_type: error.name,
        stack_trace: error.stack
      });
    }
  }

  onDestroy(() => {
    logger.destroy();
  });
</script>

<button on:click={handleCheckout}>결제하기</button>
```

### 2.2 FastAPI 로그 서버

**파일**: `services/log-server/main.py`

```python
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
import asyncpg
import asyncio
from contextlib import asynccontextmanager

# Database connection pool
db_pool: Optional[asyncpg.Pool] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """애플리케이션 생명주기 관리"""
    global db_pool
    # Startup: DB connection pool 생성
    db_pool = await asyncpg.create_pool(
        host="postgres",
        port=5432,
        database="logs",
        user="loguser",
        password="logpass",
        min_size=10,
        max_size=50
    )
    yield
    # Shutdown: pool 종료
    await db_pool.close()

app = FastAPI(title="Log Collection Server", lifespan=lifespan)

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# Pydantic 모델
class LogEntry(BaseModel):
    timestamp: datetime
    level: str
    log_type: str
    service: str
    environment: str = "development"
    message: str

    # 추적 정보
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    trace_id: Optional[str] = None
    span_id: Optional[str] = None

    # 에러 정보
    error_type: Optional[str] = None
    application_error_code: Optional[str] = None
    http_status_code: Optional[int] = None
    stack_trace: Optional[str] = None

    # 백엔드 특화
    module: Optional[str] = None
    component: Optional[str] = None
    endpoint: Optional[str] = None
    method: Optional[str] = None
    duration_ms: Optional[float] = None

    # 프론트엔드 특화
    page_path: Optional[str] = None
    browser_name: Optional[str] = None
    device_type: Optional[str] = None
    screen_width: Optional[int] = None

    # 메타데이터
    metadata: Optional[Dict[str, Any]] = None

class LogBatch(BaseModel):
    logs: List[LogEntry]

# 단일 로그 수신
@app.post("/api/v1/logs")
async def receive_log(log: LogEntry):
    """단일 로그 저장"""
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("""
                INSERT INTO logs (
                    created_at, level, log_type, service, environment, message,
                    user_id, session_id, trace_id, span_id,
                    error_type, application_error_code, http_status_code, stack_trace,
                    module, component, endpoint, method, duration_ms,
                    page_path, browser_name, device_type, screen_width,
                    metadata
                ) VALUES (
                    $1, $2, $3, $4, $5, $6,
                    $7, $8, $9, $10,
                    $11, $12, $13, $14,
                    $15, $16, $17, $18, $19,
                    $20, $21, $22, $23,
                    $24
                )
            """,
                log.timestamp, log.level, log.log_type, log.service, log.environment, log.message,
                log.user_id, log.session_id, log.trace_id, log.span_id,
                log.error_type, log.application_error_code, log.http_status_code, log.stack_trace,
                log.module, log.component, log.endpoint, log.method, log.duration_ms,
                log.page_path, log.browser_name, log.device_type, log.screen_width,
                log.metadata
            )
        return {"status": "success", "id": "generated_id"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# 배치 로그 수신
@app.post("/api/v1/logs/batch")
async def receive_log_batch(batch: LogBatch):
    """배치 로그 저장 (성능 최적화)"""
    try:
        async with db_pool.acquire() as conn:
            # 배치 삽입 (executemany 사용)
            await conn.executemany("""
                INSERT INTO logs (
                    created_at, level, log_type, service, environment, message,
                    user_id, session_id, trace_id, span_id,
                    error_type, application_error_code, http_status_code, stack_trace,
                    module, component, endpoint, method, duration_ms,
                    page_path, browser_name, device_type, screen_width,
                    metadata
                ) VALUES (
                    $1, $2, $3, $4, $5, $6,
                    $7, $8, $9, $10,
                    $11, $12, $13, $14,
                    $15, $16, $17, $18, $19,
                    $20, $21, $22, $23,
                    $24
                )
            """, [
                (
                    log.timestamp, log.level, log.log_type, log.service, log.environment, log.message,
                    log.user_id, log.session_id, log.trace_id, log.span_id,
                    log.error_type, log.application_error_code, log.http_status_code, log.stack_trace,
                    log.module, log.component, log.endpoint, log.method, log.duration_ms,
                    log.page_path, log.browser_name, log.device_type, log.screen_width,
                    log.metadata
                )
                for log in batch.logs
            ])
        return {"status": "success", "count": len(batch.logs)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Health check
@app.get("/health")
async def health_check():
    """서버 상태 확인"""
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}
```

### 2.3 Fluentd 구성 (Option 2)

**파일**: `infrastructure/docker/fluentd/fluent.conf`

```
<source>
  @type forward
  port 24224
  bind 0.0.0.0
</source>

# Docker stdout 수신
<source>
  @type tail
  path /var/lib/docker/containers/*/*.log
  pos_file /fluentd/log/docker-containers.pos
  tag docker.*
  <parse>
    @type json
    time_key time
    time_format %Y-%m-%dT%H:%M:%S.%NZ
  </parse>
</source>

# 로그 파싱 및 변환
<filter docker.**>
  @type parser
  key_name log
  <parse>
    @type json
  </parse>
</filter>

# 서비스별 태그 추가
<filter docker.**>
  @type record_transformer
  <record>
    service ${tag_parts[1]}
    log_type BACKEND
    environment ${ENV['ENVIRONMENT'] || 'development'}
  </record>
</filter>

# 로그 서버로 전송
<match docker.**>
  @type http
  endpoint http://log-server:8000/api/v1/logs/batch
  open_timeout 2
  <format>
    @type json
  </format>
  <buffer>
    flush_interval 5s
    flush_at_shutdown true
  </buffer>
</match>

# 전송 실패 시 로컬 파일 백업
<match **>
  @type file
  path /fluentd/log/backup
  compress gzip
</match>
```

### 2.4 Text-to-SQL 에이전트

**파일**: `services/text-to-sql-agent/agent.py`

```python
from langchain_anthropic import ChatAnthropic
from langchain.agents import create_sql_agent
from langchain.agents.agent_toolkits import SQLDatabaseToolkit
from langchain.sql_database import SQLDatabase
from langchain.prompts import PromptTemplate
from typing import Dict, Any
import sqlalchemy

class TextToSQLAgent:
    """자연어를 SQL로 변환하는 에이전트"""

    def __init__(
        self,
        db_url: str,
        anthropic_api_key: str,
        model: str = "claude-sonnet-4-5-20250929"
    ):
        # 데이터베이스 연결
        self.db = SQLDatabase.from_uri(db_url)

        # Claude LLM 초기화
        self.llm = ChatAnthropic(
            model=model,
            anthropic_api_key=anthropic_api_key,
            temperature=0
        )

        # SQL 툴킷 생성
        toolkit = SQLDatabaseToolkit(db=self.db, llm=self.llm)

        # 커스텀 프롬프트
        prefix = """You are an expert SQL analyst for a log analysis system.
        You have access to a PostgreSQL database with a table called 'logs'.

        Schema details:
        - created_at: timestamp of log entry
        - level: log level (INFO, WARN, ERROR, FATAL)
        - log_type: source type (BACKEND, FRONTEND)
        - service: service name
        - error_type: error class name
        - trace_id: distributed tracing ID
        - duration_ms: request duration
        - metadata: JSONB field with additional data

        Important:
        - Use created_at for time filtering, not timestamp
        - Use appropriate indexes: idx_service_level_time, idx_error_service_time
        - For time ranges, use NOW() - INTERVAL syntax
        - For JSONB queries, use -> or ->> operators
        - Always include LIMIT for large result sets
        - Use EXPLAIN ANALYZE for performance-critical queries
        """

        suffix = """Begin!
        Question: {input}
        Thought: {agent_scratchpad}
        """

        # 에이전트 생성
        self.agent = create_sql_agent(
            llm=self.llm,
            toolkit=toolkit,
            verbose=True,
            prefix=prefix,
            suffix=suffix,
            agent_type="openai-tools"
        )

    async def query(self, natural_language_query: str) -> Dict[str, Any]:
        """
        자연어 질의를 SQL로 변환하고 실행

        Args:
            natural_language_query: 자연어 질문

        Returns:
            {
                "query": "생성된 SQL 쿼리",
                "result": "쿼리 실행 결과",
                "explanation": "결과 설명",
                "performance": "쿼리 성능 정보"
            }
        """
        try:
            # 에이전트 실행
            response = await self.agent.ainvoke({"input": natural_language_query})

            # SQL 추출 및 실행
            sql_query = self._extract_sql(response)
            result = self.db.run(sql_query)

            # 성능 분석
            explain_result = self.db.run(f"EXPLAIN ANALYZE {sql_query}")

            return {
                "query": sql_query,
                "result": result,
                "explanation": self._generate_explanation(result, natural_language_query),
                "performance": self._parse_explain(explain_result)
            }
        except Exception as e:
            return {
                "error": str(e),
                "query": None,
                "result": None
            }

    def _extract_sql(self, response: Dict) -> str:
        """에이전트 응답에서 SQL 추출"""
        # 구현 로직
        pass

    def _generate_explanation(self, result: Any, query: str) -> str:
        """결과를 자연어로 설명"""
        explanation_prompt = f"""
        Given the query: "{query}"
        And the result: {result}

        Provide a clear, concise explanation of what the data shows.
        Include key insights and actionable recommendations.
        """
        explanation = self.llm.invoke(explanation_prompt)
        return explanation.content

    def _parse_explain(self, explain_result: str) -> Dict:
        """EXPLAIN ANALYZE 결과 파싱"""
        # 실행 시간, 비용, 스캔 방식 등 추출
        pass
```

**사용 예시**:

```python
# CLI 도구
import asyncio
from agent import TextToSQLAgent

async def main():
    agent = TextToSQLAgent(
        db_url="postgresql://loguser:logpass@localhost:5432/logs",
        anthropic_api_key="sk-ant-..."
    )

    while True:
        query = input("\n질문: ")
        if query.lower() in ['exit', 'quit']:
            break

        result = await agent.query(query)

        print(f"\n생성된 SQL:\n{result['query']}\n")
        print(f"결과:\n{result['result']}\n")
        print(f"설명:\n{result['explanation']}\n")
        print(f"성능:\n{result['performance']}\n")

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 3. 데이터 파이프라인 흐름

### 3.1 로그 수집 흐름 (Option 1: Library)

```
[Application Code]
        │
        │ log_collector.log("ERROR", "Payment failed", ...)
        │
        ▼
[In-Memory Buffer]
  - 배치 크기: 10개
  - 플러시 간격: 5초
        │
        │ HTTP POST /api/v1/logs/batch
        │ Content-Type: application/json
        │ Body: {"logs": [...]}
        │
        ▼
[Log Server: FastAPI]
  ├─ 입력 검증 (Pydantic)
  ├─ 데이터 보강 (타임스탬프, 서버 IP 등)
  ├─ 배치 삽입 준비
  │
  └─► [PostgreSQL]
       ├─ asyncpg.executemany()
       ├─ 트랜잭션 처리
       └─ 파티션 자동 선택
```

### 3.2 로그 수집 흐름 (Option 2: Docker stdout)

```
[Application Code]
        │
        │ console.log({level: "ERROR", message: "..."})
        │ print(json.dumps({...}))
        │
        ▼
[Docker Container stdout]
        │
        │ JSON 형식 로그
        │
        ▼
[Fluentd: Docker Logging Driver]
  ├─ 로그 캡처
  ├─ JSON 파싱
  ├─ 필터링 및 변환
  │   ├─ 서비스명 태그 추가
  │   ├─ 환경 정보 추가
  │   └─ 타임스탬프 정규화
  │
  └─► HTTP POST to Log Server
       (Option 1과 동일한 엔드포인트)
```

### 3.3 분석 질의 흐름

```
[User]
  │ "지난 1시간 에러가 몇 건?"
  │
  ▼
[Text-to-SQL Agent]
  │
  ├─ [1] Schema Context 로드
  │     - 테이블 구조
  │     - 인덱스 정보
  │     - 샘플 데이터
  │
  ├─ [2] LangChain Agent
  │     ├─ Claude LLM 호출
  │     ├─ SQL 생성
  │     │   SELECT COUNT(*) FROM logs
  │     │   WHERE level = 'ERROR'
  │     │   AND created_at > NOW() - INTERVAL '1 hour'
  │     │
  │     └─ SQL 검증
  │           ├─ 문법 체크
  │           ├─ 보안 체크 (DROP, DELETE 방지)
  │           └─ 성능 예측 (EXPLAIN)
  │
  ├─ [3] Query Execution
  │     ├─ PostgreSQL 실행
  │     ├─ 결과 가져오기
  │     └─ 성능 메트릭 수집
  │
  ├─ [4] Result Interpretation
  │     ├─ Claude LLM으로 설명 생성
  │     ├─ 인사이트 추출
  │     └─ 추천 사항 제시
  │
  └─► [User]
       "지난 1시간 동안 342건의 에러가 발생했습니다.
        이는 평소 대비 230% 증가한 수치입니다.
        주요 원인은 DatabaseConnectionTimeout (78%)입니다.
        추천: payment-api 서비스의 DB 커넥션 풀 설정을 확인하세요."
```

---

## 4. 디렉토리 구조

```
log-analysis-system/
│
├── services/                          # 마이크로서비스
│   ├── log-server/                    # 로그 수집 서버
│   │   ├── main.py                    # FastAPI 엔트리포인트
│   │   ├── models/                    # Pydantic 모델
│   │   │   ├── __init__.py
│   │   │   └── log_entry.py
│   │   ├── routes/                    # API 라우트
│   │   │   ├── __init__.py
│   │   │   ├── logs.py
│   │   │   └── health.py
│   │   ├── database/                  # DB 관련
│   │   │   ├── __init__.py
│   │   │   ├── connection.py          # Connection pool
│   │   │   └── queries.py             # SQL 쿼리 정의
│   │   ├── middleware/                # 미들웨어
│   │   │   ├── __init__.py
│   │   │   ├── error_handler.py
│   │   │   └── rate_limiter.py
│   │   ├── requirements.txt
│   │   ├── Dockerfile
│   │   └── README.md
│   │
│   ├── text-to-sql-agent/             # 분석 에이전트
│   │   ├── agent.py                   # LangChain 에이전트
│   │   ├── prompts/                   # 프롬프트 템플릿
│   │   │   ├── __init__.py
│   │   │   ├── system_prompt.py
│   │   │   └── few_shot_examples.py
│   │   ├── tools/                     # 커스텀 도구
│   │   │   ├── __init__.py
│   │   │   ├── sql_validator.py
│   │   │   └── performance_analyzer.py
│   │   ├── cli.py                     # CLI 인터페이스
│   │   ├── web_ui.py                  # 웹 UI (Streamlit)
│   │   ├── requirements.txt
│   │   └── README.md
│   │
│   └── sample-services/               # 테스트용 샘플 서비스
│       ├── python-backend/            # Python 백엔드 예시
│       │   ├── main.py                # FastAPI 앱
│       │   ├── requirements.txt
│       │   └── Dockerfile
│       ├── nodejs-backend/            # Node.js 백엔드 예시
│       │   ├── index.js               # Express 앱
│       │   ├── package.json
│       │   └── Dockerfile
│       └── svelte-frontend/           # Svelte 프론트엔드 예시
│           ├── src/
│           │   ├── App.svelte
│           │   └── lib/
│           │       └── logger.js
│           ├── package.json
│           ├── vite.config.js
│           └── Dockerfile
│
├── clients/                           # 로그 수집 라이브러리
│   ├── python/                        # Python 클라이언트
│   │   ├── log_collector/
│   │   │   ├── __init__.py
│   │   │   ├── collector.py
│   │   │   ├── buffer.py
│   │   │   └── fallback.py           # 로컬 백업 로직
│   │   ├── setup.py
│   │   ├── requirements.txt
│   │   └── README.md
│   │
│   └── javascript/                    # JS/TS 클라이언트
│       ├── src/
│       │   ├── index.ts
│       │   ├── logger.ts
│       │   ├── buffer.ts
│       │   └── browser.ts            # 브라우저 정보 감지
│       ├── package.json
│       ├── tsconfig.json
│       └── README.md
│
├── infrastructure/                    # 인프라 설정
│   ├── docker/
│   │   ├── docker-compose.yml         # 전체 스택
│   │   ├── docker-compose.dev.yml     # 개발 환경
│   │   ├── docker-compose.prod.yml    # 프로덕션 환경
│   │   ├── fluentd/
│   │   │   ├── Dockerfile
│   │   │   ├── fluent.conf
│   │   │   └── plugins/              # 커스텀 플러그인
│   │   └── postgres/
│   │       ├── init.sql              # 초기 스키마
│   │       ├── create_partitions.sql
│   │       ├── create_indexes.sql
│   │       └── create_views.sql
│   │
│   ├── terraform/                     # AWS 인프라 코드
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── modules/
│   │   │   ├── ec2/                  # EC2 인스턴스
│   │   │   ├── rds/                  # RDS PostgreSQL
│   │   │   ├── vpc/                  # 네트워크
│   │   │   └── security/             # 보안 그룹
│   │   └── README.md
│   │
│   └── kubernetes/                    # K8s 배포 (선택)
│       ├── namespace.yaml
│       ├── log-server/
│       │   ├── deployment.yaml
│       │   ├── service.yaml
│       │   └── hpa.yaml              # Horizontal Pod Autoscaler
│       ├── postgres/
│       │   ├── statefulset.yaml
│       │   ├── service.yaml
│       │   └── pvc.yaml              # Persistent Volume Claim
│       └── fluentd/
│           ├── daemonset.yaml
│           └── configmap.yaml
│
├── docs/                              # 문서
│   ├── db-schema-analysis.md          # 스키마 분석
│   ├── scenarios-detailed.md          # 시나리오 정의
│   ├── project-architecture.md        # 아키텍처 (이 문서)
│   ├── fluentd-guide.md              # Fluentd 가이드
│   ├── aws-deployment-guide.md       # AWS 배포 가이드
│   ├── api-reference.md              # API 문서
│   └── troubleshooting.md            # 트러블슈팅
│
├── scripts/                           # 유틸리티 스크립트
│   ├── setup.sh                       # 초기 설정
│   ├── seed-data.py                   # 샘플 데이터 생성
│   ├── benchmark.py                   # 성능 벤치마크
│   ├── migrate.py                     # DB 마이그레이션
│   ├── backup.sh                      # 백업 스크립트
│   └── monitoring/
│       ├── check_log_server.sh
│       └── check_postgres.sh
│
├── tests/                             # 테스트
│   ├── unit/                          # 단위 테스트
│   │   ├── test_log_collector.py
│   │   ├── test_log_server.py
│   │   └── test_agent.py
│   ├── integration/                   # 통합 테스트
│   │   ├── test_end_to_end.py
│   │   ├── test_fluentd_integration.py
│   │   └── test_agent_scenarios.py
│   ├── e2e/                           # E2E 테스트
│   │   ├── test_full_pipeline.py
│   │   └── test_web_ui.py
│   ├── performance/                   # 성능 테스트
│   │   ├── load_test.py              # Locust 스크립트
│   │   └── stress_test.sh
│   └── fixtures/                      # 테스트 데이터
│       ├── sample_logs.json
│       └── expected_queries.json
│
├── .github/                           # GitHub Actions
│   └── workflows/
│       ├── ci.yml                     # CI 파이프라인
│       ├── cd.yml                     # CD 파이프라인
│       └── test.yml                   # 테스트 자동화
│
├── .env.example                       # 환경 변수 예시
├── .gitignore
├── README.md                          # 프로젝트 개요
├── CONTRIBUTING.md                    # 기여 가이드
└── LICENSE
```

---

## 5. 에러 처리 및 복구 전략

### 5.1 로그 수집 실패 처리

#### 클라이언트 측 재시도 로직

```python
# clients/python/log_collector/fallback.py

import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict

class FallbackStorage:
    """로그 전송 실패 시 로컬 저장"""

    def __init__(self, backup_dir: str = "/var/log/app/backup"):
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def save(self, logs: List[Dict]):
        """로컬 파일에 저장"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = self.backup_dir / f"logs_{timestamp}.json"

        with open(filename, 'w') as f:
            json.dump(logs, f, indent=2)

    def retry_pending(self, log_server_url: str):
        """저장된 로그 재전송"""
        for log_file in self.backup_dir.glob("logs_*.json"):
            try:
                with open(log_file, 'r') as f:
                    logs = json.load(f)

                # 로그 서버로 재전송
                response = httpx.post(
                    f"{log_server_url}/api/v1/logs/batch",
                    json={"logs": logs},
                    timeout=30
                )
                response.raise_for_status()

                # 성공 시 파일 삭제
                log_file.unlink()
                print(f"Retried {log_file}: success")
            except Exception as e:
                print(f"Retry failed for {log_file}: {e}")
```

#### 서버 측 배치 처리 재시도

```python
# services/log-server/database/batch_writer.py

import asyncio
from typing import List
import asyncpg

class BatchWriter:
    """배치 삽입 실패 시 재시도"""

    def __init__(self, pool: asyncpg.Pool, max_retries: int = 3):
        self.pool = pool
        self.max_retries = max_retries

    async def insert_batch(self, logs: List[Dict]) -> bool:
        """배치 삽입 with exponential backoff"""
        for attempt in range(self.max_retries):
            try:
                async with self.pool.acquire() as conn:
                    async with conn.transaction():
                        await conn.executemany(INSERT_SQL, logs)
                return True
            except asyncpg.DeadlockDetectedError:
                # 데드락 발생 시 재시도
                await asyncio.sleep(2 ** attempt)  # Exponential backoff
                continue
            except asyncpg.PostgresError as e:
                # 다른 DB 에러는 기록하고 넘어감
                logging.error(f"DB error: {e}")
                # Dead Letter Queue로 이동
                await self.send_to_dlq(logs)
                return False

        # 최대 재시도 횟수 초과
        await self.send_to_dlq(logs)
        return False

    async def send_to_dlq(self, logs: List[Dict]):
        """실패한 로그를 Dead Letter Queue로"""
        # Redis, Kafka, 또는 로컬 파일에 저장
        pass
```

### 5.2 데이터베이스 장애 복구

#### 읽기 전용 모드

```python
# services/log-server/database/failover.py

class DatabaseFailover:
    """DB 장애 시 읽기 전용 replica로 전환"""

    def __init__(self, primary_url: str, replica_urls: List[str]):
        self.primary_pool = None
        self.replica_pools = []
        self.is_primary_healthy = True

    async def get_connection(self, read_only: bool = False):
        """상태에 따라 적절한 커넥션 반환"""
        if read_only or not self.is_primary_healthy:
            # Replica 사용 (round-robin)
            return await self._get_replica_connection()
        else:
            # Primary 사용
            try:
                return await self.primary_pool.acquire()
            except Exception:
                self.is_primary_healthy = False
                # 알림 발송
                await self.send_alert("Primary DB down")
                # Replica로 폴백
                return await self._get_replica_connection()

    async def health_check(self):
        """정기적 health check"""
        while True:
            await asyncio.sleep(30)
            try:
                async with self.primary_pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                if not self.is_primary_healthy:
                    self.is_primary_healthy = True
                    await self.send_alert("Primary DB recovered")
            except Exception:
                self.is_primary_healthy = False
```

### 5.3 Text-to-SQL 에이전트 에러 처리

```python
# services/text-to-sql-agent/tools/sql_validator.py

class SQLValidator:
    """생성된 SQL의 안전성 검증"""

    DANGEROUS_KEYWORDS = ['DROP', 'DELETE', 'TRUNCATE', 'UPDATE', 'INSERT', 'ALTER']
    MAX_RESULT_SIZE = 10000

    def validate(self, sql: str) -> Dict[str, Any]:
        """SQL 안전성 검증"""
        validation_result = {
            "is_safe": True,
            "errors": [],
            "warnings": []
        }

        # 1. 위험한 키워드 체크
        sql_upper = sql.upper()
        for keyword in self.DANGEROUS_KEYWORDS:
            if keyword in sql_upper:
                validation_result["is_safe"] = False
                validation_result["errors"].append(
                    f"Dangerous operation: {keyword}"
                )

        # 2. LIMIT 절 체크
        if 'LIMIT' not in sql_upper:
            validation_result["warnings"].append(
                f"No LIMIT clause. Adding LIMIT {self.MAX_RESULT_SIZE}"
            )
            sql += f" LIMIT {self.MAX_RESULT_SIZE}"

        # 3. 구문 검증
        try:
            import sqlparse
            parsed = sqlparse.parse(sql)
            if not parsed:
                validation_result["is_safe"] = False
                validation_result["errors"].append("Invalid SQL syntax")
        except Exception as e:
            validation_result["is_safe"] = False
            validation_result["errors"].append(f"Parse error: {e}")

        # 4. 성능 예측 (EXPLAIN)
        estimated_cost = self.estimate_cost(sql)
        if estimated_cost > 10000:
            validation_result["warnings"].append(
                f"High cost query: {estimated_cost}"
            )

        return validation_result
```

---

## 6. 확장성 고려사항

### 6.1 수평 확장

#### 로그 서버 스케일 아웃

```yaml
# infrastructure/kubernetes/log-server/hpa.yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: log-server-hpa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: log-server
  minReplicas: 3
  maxReplicas: 20
  metrics:
  - type: Resource
    resource:
      name: cpu
      target:
        type: Utilization
        averageUtilization: 70
  - type: Resource
    resource:
      name: memory
      target:
        type: Utilization
        averageUtilization: 80
  - type: Pods
    pods:
      metric:
        name: http_requests_per_second
      target:
        type: AverageValue
        averageValue: "1000"
```

#### PostgreSQL 샤딩 전략

```sql
-- 서비스별 샤딩 (향후 확장)
CREATE TABLE logs_payment_api PARTITION OF logs
FOR VALUES IN ('payment-api');

CREATE TABLE logs_order_api PARTITION OF logs
FOR VALUES IN ('order-api');

-- 또는 시간 + 서비스 복합 파티셔닝
CREATE TABLE logs_2024_01_payment PARTITION OF logs_2024_01
FOR VALUES IN ('payment-api');
```

### 6.2 캐싱 전략

```python
# services/text-to-sql-agent/cache.py

import redis
import hashlib
from typing import Optional, Dict

class QueryCache:
    """빈번한 질의 캐싱"""

    def __init__(self, redis_url: str):
        self.redis = redis.from_url(redis_url)
        self.ttl = 300  # 5분

    def get_cached_result(self, query: str) -> Optional[Dict]:
        """캐시된 결과 조회"""
        cache_key = self._generate_key(query)
        cached = self.redis.get(cache_key)
        if cached:
            return json.loads(cached)
        return None

    def cache_result(self, query: str, result: Dict):
        """결과 캐싱"""
        cache_key = self._generate_key(query)
        self.redis.setex(
            cache_key,
            self.ttl,
            json.dumps(result)
        )

    def _generate_key(self, query: str) -> str:
        """쿼리의 해시 키 생성"""
        return f"query:{hashlib.md5(query.encode()).hexdigest()}"
```

### 6.3 비동기 처리

```python
# services/log-server/async_processor.py

from celery import Celery
from typing import List, Dict

app = Celery('log-processor', broker='redis://localhost:6379/0')

@app.task
def enrich_logs(logs: List[Dict]):
    """로그 보강 작업 (비동기)"""
    enriched = []
    for log in logs:
        # GeoIP 조회
        if log.get('client_ip'):
            geo_info = geoip_lookup(log['client_ip'])
            log.update(geo_info)

        # PII 필터링
        log = filter_pii(log)

        enriched.append(log)

    return enriched

@app.task
def aggregate_metrics():
    """집계 메트릭 계산 (주기적)"""
    # Materialized View 갱신
    db.execute("REFRESH MATERIALIZED VIEW CONCURRENTLY daily_log_summary")

# Celery Beat 스케줄링
app.conf.beat_schedule = {
    'aggregate-every-hour': {
        'task': 'aggregate_metrics',
        'schedule': 3600.0,  # 1시간
    },
}
```

---

## 7. 배포 아키텍처

### 7.1 개발 환경

```yaml
# infrastructure/docker/docker-compose.dev.yml
version: '3.8'
services:
  postgres:
    image: postgres:15
    environment:
      POSTGRES_DB: logs
      POSTGRES_USER: loguser
      POSTGRES_PASSWORD: logpass
    ports:
      - "5432:5432"
    volumes:
      - ./infrastructure/docker/postgres:/docker-entrypoint-initdb.d

  log-server:
    build: ./services/log-server
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: postgresql://loguser:logpass@postgres:5432/logs
    depends_on:
      - postgres

  text-to-sql-agent:
    build: ./services/text-to-sql-agent
    ports:
      - "8501:8501"
    environment:
      DATABASE_URL: postgresql://loguser:logpass@postgres:5432/logs
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
    depends_on:
      - postgres

  # 샘플 서비스들
  python-backend:
    build: ./services/sample-services/python-backend
    environment:
      LOG_SERVER_URL: http://log-server:8000

  nodejs-backend:
    build: ./services/sample-services/nodejs-backend
    environment:
      LOG_SERVER_URL: http://log-server:8000

  svelte-frontend:
    build: ./services/sample-services/svelte-frontend
    ports:
      - "5173:5173"
    environment:
      VITE_LOG_SERVER_URL: http://log-server:8000
```

### 7.2 프로덕션 환경 (AWS)

```
┌─────────────────────────────────────────────────────────────┐
│                        AWS Cloud                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌────────────────────────────────────────┐                │
│  │         VPC (10.0.0.0/16)              │                │
│  │                                        │                │
│  │  ┌──────────────────────────────────┐ │                │
│  │  │  Public Subnet (10.0.1.0/24)     │ │                │
│  │  │                                  │ │                │
│  │  │  ┌──────────────────┐            │ │                │
│  │  │  │  Application     │            │ │                │
│  │  │  │  Load Balancer   │            │ │                │
│  │  │  └────────┬─────────┘            │ │                │
│  │  │           │                      │ │                │
│  │  └───────────┼──────────────────────┘ │                │
│  │              │                        │                │
│  │  ┌───────────┼──────────────────────┐ │                │
│  │  │  Private Subnet (10.0.2.0/24)    │ │                │
│  │  │           │                      │ │                │
│  │  │  ┌────────▼──────────┐           │ │                │
│  │  │  │  Auto Scaling     │           │ │                │
│  │  │  │  Group            │           │ │                │
│  │  │  │  (Log Servers)    │           │ │                │
│  │  │  │  - EC2 x 3-10     │           │ │                │
│  │  │  └───────────────────┘           │ │                │
│  │  │                                  │ │                │
│  │  └──────────────────────────────────┘ │                │
│  │                                        │                │
│  │  ┌──────────────────────────────────┐ │                │
│  │  │  Private Subnet (10.0.3.0/24)    │ │                │
│  │  │                                  │ │                │
│  │  │  ┌──────────────────┐            │ │                │
│  │  │  │  RDS PostgreSQL  │            │ │                │
│  │  │  │  - Multi-AZ      │            │ │                │
│  │  │  │  - Read Replica  │            │ │                │
│  │  │  └──────────────────┘            │ │                │
│  │  │                                  │ │                │
│  │  └──────────────────────────────────┘ │                │
│  │                                        │                │
│  └────────────────────────────────────────┘                │
│                                                             │
│  ┌────────────────────────────────────────┐                │
│  │         Additional Services            │                │
│  │  - S3 (로그 아카이브)                   │                │
│  │  - CloudWatch (모니터링)               │                │
│  │  - Route53 (DNS)                      │                │
│  │  - ElastiCache (Redis - 캐싱)          │                │
│  └────────────────────────────────────────┘                │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

**문서 버전**: 1.0
**최종 수정일**: 2024-01-15
**작성자**: Log Analysis System Team
