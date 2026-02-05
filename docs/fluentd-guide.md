# Fluentd 기술 가이드

## 목차

1. [Fluentd 소개](#1-fluentd-소개)
2. [Fluentd vs Fluent Bit](#2-fluentd-vs-fluent-bit)
3. [Docker Logging Driver 통합](#3-docker-logging-driver-통합)
4. [Fluentd 설정 파일 구조](#4-fluentd-설정-파일-구조)
5. [파싱 및 필터링 패턴](#5-파싱-및-필터링-패턴)
6. [HTTP 엔드포인트 전송 설정](#6-http-엔드포인트-전송-설정)
7. [성능 튜닝 가이드](#7-성능-튜닝-가이드)
8. [트러블슈팅 가이드](#8-트러블슈팅-가이드)

---

## 1. Fluentd 소개

### 1.1 Fluentd란?

**Fluentd**는 통합 로그 수집 레이어(unified logging layer)를 제공하는 오픈소스 데이터 수집 도구입니다.

**핵심 개념:**
```
[Input] → [Filter] → [Output]
  수집      변환      전송
```

**주요 특징:**
- 📦 **플러그인 생태계**: 500+ 플러그인 (input, filter, output)
- 🔄 **유연한 라우팅**: 태그 기반 로그 라우팅
- 💾 **버퍼링**: 메모리/파일 버퍼로 데이터 손실 방지
- 🚀 **성능**: Ruby + C로 작성, 비동기 I/O
- 🐳 **Docker 친화적**: Docker logging driver 지원

### 1.2 왜 Fluentd인가?

| 요구사항 | Fluentd 해결책 |
|---------|----------------|
| Docker stdout 로그 수집 | Docker logging driver 플러그인 |
| 로그 포맷 통일 | Parser와 Filter 플러그인 |
| 대용량 로그 처리 | 버퍼링 및 배치 전송 |
| 다양한 출력 지원 | HTTP, Elasticsearch, S3 등 |
| 장애 복구 | 재시도 로직, Dead Letter Queue |

### 1.3 로그 분석 시스템에서의 역할

```
[Docker Container]
        │
        │ stdout/stderr
        ▼
[Docker Logging Driver]
        │
        │ json-file format
        ▼
[Fluentd]
  ├─ Tail input plugin (Docker 로그 파일 읽기)
  ├─ Parser plugin (JSON 파싱)
  ├─ Filter plugin (필드 추가, 변환)
  └─ HTTP output plugin (로그 서버로 전송)
        │
        ▼
[Log Server (FastAPI)]
```

---

## 2. Fluentd vs Fluent Bit

### 2.1 비교표

| 항목 | Fluentd | Fluent Bit |
|-----|---------|-----------|
| **언어** | Ruby + C | C |
| **메모리** | ~40MB | ~450KB |
| **플러그인** | 500+ | 50+ (핵심만) |
| **성능** | 중간 (10K-50K events/sec) | 높음 (100K+ events/sec) |
| **확장성** | 매우 높음 (커스텀 플러그인 쉬움) | 제한적 |
| **설정 복잡도** | 중간 | 낮음 |
| **사용 사례** | 중앙 aggregator, 복잡한 변환 | 경량 forwarder, edge 수집 |

### 2.2 선택 가이드

**Fluentd를 선택하는 경우:**
- ✅ 복잡한 로그 파싱 및 변환 필요
- ✅ 다양한 출력 대상 (Elasticsearch, S3, Kafka 등)
- ✅ 커스텀 플러그인 개발 가능성
- ✅ 중앙 집중식 로그 aggregation
- ✅ Ruby에 익숙한 팀

**Fluent Bit를 선택하는 경우:**
- ✅ 경량 footprint 필요 (IoT, edge devices)
- ✅ 단순한 로그 전달 (forwarding)
- ✅ 극도의 성능 최적화 필요
- ✅ Kubernetes sidecar 패턴
- ✅ C에 익숙한 팀

### 2.3 하이브리드 아키텍처

```
[Application Containers]
        │
        │ stdout
        ▼
[Fluent Bit (Forwarder)]  ← 경량, 각 노드에 배포
  - 빠른 수집
  - 기본 필터링
        │
        │ forward protocol
        ▼
[Fluentd (Aggregator)]    ← 중앙, 강력한 처리
  - 복잡한 파싱
  - 라우팅
  - 변환
        │
        ▼
[다양한 Output]
  - Log Server (HTTP)
  - Elasticsearch
  - S3 (아카이브)
```

**권장:** 로그 분석 시스템에서는 **Fluentd**를 권장합니다.
- 이유: 복잡한 로그 변환 필요, HTTP output 필수, 향후 확장성

---

## 3. Docker Logging Driver 통합

### 3.1 Docker Logging Driver 설정

#### 방법 1: Docker Compose

**파일**: `docker-compose.yml`

```yaml
version: '3.8'

services:
  # Fluentd 서비스
  fluentd:
    image: fluent/fluentd:v1.16-1
    ports:
      - "24224:24224"
      - "24224:24224/udp"
    volumes:
      - ./fluentd/fluent.conf:/fluentd/etc/fluent.conf
      - ./fluentd/plugins:/fluentd/plugins
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
    networks:
      - log-network

  # 애플리케이션 서비스 (Fluentd logging driver 사용)
  payment-api:
    build: ./services/payment-api
    logging:
      driver: fluentd
      options:
        fluentd-address: localhost:24224
        fluentd-async: "true"
        fluentd-max-retries: "5"
        fluentd-retry-wait: "1s"
        tag: docker.payment-api
    networks:
      - log-network

  order-api:
    build: ./services/order-api
    logging:
      driver: fluentd
      options:
        fluentd-address: localhost:24224
        tag: docker.order-api
    networks:
      - log-network

  web-app:
    build: ./services/web-app
    logging:
      driver: fluentd
      options:
        fluentd-address: localhost:24224
        tag: docker.web-app
    networks:
      - log-network

networks:
  log-network:
    driver: bridge
```

#### 방법 2: Docker Daemon 전역 설정

**파일**: `/etc/docker/daemon.json`

```json
{
  "log-driver": "fluentd",
  "log-opts": {
    "fluentd-address": "localhost:24224",
    "fluentd-async": "true",
    "tag": "docker.{{.Name}}"
  }
}
```

**적용**:
```bash
sudo systemctl restart docker
```

#### 방법 3: json-file + Fluentd tail (권장)

Fluentd가 다운되어도 로그 손실 방지를 위해 json-file을 사용하고 Fluentd가 파일을 tail하는 방식:

```yaml
services:
  payment-api:
    build: ./services/payment-api
    logging:
      driver: json-file
      options:
        max-size: "10m"
        max-file: "3"
        labels: "service=payment-api,env=production"

  fluentd:
    image: fluent/fluentd:v1.16-1
    volumes:
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
```

**장점:**
- Fluentd 다운 시에도 로그가 Docker에 저장됨
- Fluentd 재시작 후 누락된 로그 복구 가능

### 3.2 Logging Driver 옵션

| 옵션 | 설명 | 기본값 | 권장값 |
|-----|------|-------|-------|
| `fluentd-address` | Fluentd 주소 | localhost:24224 | - |
| `fluentd-async` | 비동기 전송 | false | true |
| `fluentd-buffer-limit` | 버퍼 크기 | 8MB | 64MB |
| `fluentd-retry-wait` | 재시도 대기 시간 | 1s | 1s |
| `fluentd-max-retries` | 최대 재시도 횟수 | unlimited | 5 |
| `tag` | 로그 태그 | - | docker.{{.Name}} |
| `labels` | 컨테이너 라벨 | - | service,env |
| `env` | 환경 변수 | - | - |

### 3.3 로그 포맷

Docker logging driver가 Fluentd로 전송하는 로그 포맷:

```json
{
  "container_id": "abc123...",
  "container_name": "/payment-api",
  "source": "stdout",
  "log": "{\"level\":\"ERROR\",\"message\":\"Payment failed\",\"timestamp\":\"2024-01-15T10:30:22Z\"}",
  "partial_id": "",
  "partial_ordinal": "",
  "partial_last": false
}
```

---

## 4. Fluentd 설정 파일 구조

### 4.1 기본 구조

**파일**: `fluent.conf`

```
<source>
  # 로그 수집 소스
</source>

<filter>
  # 로그 변환 및 필터링
</filter>

<match>
  # 로그 출력 대상
</match>
```

### 4.2 완전한 설정 예시

**파일**: `infrastructure/docker/fluentd/fluent.conf`

```ruby
# ========================================
# Input Sources
# ========================================

# Docker Fluentd logging driver로부터 수신
<source>
  @type forward
  port 24224
  bind 0.0.0.0
</source>

# Docker json-file 로그를 tail로 읽기 (fallback)
<source>
  @type tail
  path /var/lib/docker/containers/*/*.log
  pos_file /fluentd/log/docker-containers.pos
  tag docker.container.*
  read_from_head true
  <parse>
    @type json
    time_key time
    time_format %Y-%m-%dT%H:%M:%S.%NZ
    keep_time_key true
  </parse>
</source>

# ========================================
# Filters
# ========================================

# Docker 메타데이터에서 서비스명 추출
<filter docker.**>
  @type record_transformer
  enable_ruby true
  <record>
    # 컨테이너명에서 서비스명 추출 (/payment-api → payment-api)
    service ${record["container_name"].sub(/^\//, '')}
    environment "#{ENV['ENVIRONMENT'] || 'development'}"
    log_type BACKEND
    hostname "#{Socket.gethostname}"
  </record>
</filter>

# 애플리케이션 로그 JSON 파싱
<filter docker.**>
  @type parser
  key_name log
  reserve_data true
  remove_key_name_field true
  <parse>
    @type json
    time_key timestamp
    time_format %Y-%m-%dT%H:%M:%S.%NZ
  </parse>
</filter>

# 필드 매핑 및 정규화
<filter docker.**>
  @type record_transformer
  enable_ruby true
  <record>
    # timestamp를 created_at으로 변경
    created_at ${record["timestamp"] || Time.now.utc.iso8601}

    # trace_id가 없으면 request_id 사용
    trace_id ${record["trace_id"] || record["request_id"]}

    # level 정규화 (debug → DEBUG)
    level ${record["level"]&.upcase || "INFO"}

    # 메타데이터 구조화
    metadata ${record.select { |k, v| !%w[timestamp level message service].include?(k) }.to_json}
  </record>
  remove_keys timestamp,request_id
</filter>

# 에러 로그만 Slack 알림 (optional)
<filter docker.** tag=docker.**>
  @type grep
  <regexp>
    key level
    pattern /ERROR|FATAL/
  </regexp>
</filter>

# 민감 정보 필터링 (PII masking)
<filter docker.**>
  @type record_modifier
  <replace>
    key message
    expression /\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b/
    replace [EMAIL_REDACTED]
  </replace>
  <replace>
    key message
    expression /\b\d{3}-\d{2}-\d{4}\b/
    replace [SSN_REDACTED]
  </replace>
  <replace>
    key message
    expression /\b\d{16}\b/
    replace [CARD_REDACTED]
  </replace>
</filter>

# ========================================
# Outputs
# ========================================

# 메인: 로그 서버로 HTTP POST
<match docker.**>
  @type http
  endpoint http://log-server:8000/api/v1/logs/batch
  open_timeout 5
  read_timeout 10
  <format>
    @type json
  </format>
  json_array true
  <buffer>
    @type file
    path /fluentd/buffer/http
    flush_mode interval
    flush_interval 5s
    flush_at_shutdown true
    retry_type exponential_backoff
    retry_wait 1s
    retry_max_interval 60s
    retry_max_times 10
    chunk_limit_size 10M
    total_limit_size 1G
    overflow_action drop_oldest_chunk
  </buffer>
  <secondary>
    # 전송 실패 시 로컬 파일 백업
    @type file
    path /fluentd/log/failed/${tag}
    <format>
      @type json
    </format>
    <buffer tag, time>
      @type file
      path /fluentd/buffer/failed
      timekey 3600  # 1시간 단위 파일
      timekey_wait 10m
    </buffer>
  </secondary>
</match>

# 에러 로그는 추가로 Slack 알림
<match docker.** tag=docker.** level=ERROR>
  @type copy
  <store>
    @type slack
    webhook_url "#{ENV['SLACK_WEBHOOK_URL']}"
    channel alerts
    username Fluentd
    icon_emoji :warning:
    message "Error in %s: %s"
    message_keys service,message
  </store>
  <store>
    # 메인 output으로도 전송
    @type relabel
    @label @MAIN
  </store>
</match>

# ========================================
# System Config
# ========================================

<system>
  # Fluentd 자체 로그 레벨
  log_level info

  # Worker 수
  workers 2

  # 프로세스명
  process_name fluentd

  # RPC 서버 (모니터링용)
  rpc_endpoint 0.0.0.0:24444
</system>

# ========================================
# Monitoring
# ========================================

# Prometheus 메트릭 노출
<source>
  @type prometheus
  bind 0.0.0.0
  port 24231
  metrics_path /metrics
</source>

<source>
  @type prometheus_monitor
</source>

<source>
  @type prometheus_output_monitor
</source>
```

---

## 5. 파싱 및 필터링 패턴

### 5.1 JSON 로그 파싱

**시나리오**: 애플리케이션이 JSON 형식으로 로그 출력

**입력 로그**:
```json
{"level":"ERROR","timestamp":"2024-01-15T10:30:22Z","message":"Payment failed","user_id":"user123","error_code":"PAYMENT_DECLINED"}
```

**Fluentd 설정**:
```ruby
<filter docker.**>
  @type parser
  key_name log
  reserve_data true  # 원본 필드 유지
  <parse>
    @type json
    time_key timestamp
    time_format %Y-%m-%dT%H:%M:%S.%NZ
  </parse>
</filter>
```

**출력**:
```json
{
  "level": "ERROR",
  "timestamp": "2024-01-15T10:30:22Z",
  "message": "Payment failed",
  "user_id": "user123",
  "error_code": "PAYMENT_DECLINED",
  "container_name": "/payment-api",
  "source": "stdout"
}
```

### 5.2 구조화되지 않은 로그 파싱

**시나리오**: Plain text 로그를 구조화

**입력 로그**:
```
2024-01-15 10:30:22 ERROR [payment-api] Payment failed for user user123: PAYMENT_DECLINED
```

**Fluentd 설정**:
```ruby
<filter docker.**>
  @type parser
  key_name log
  <parse>
    @type regexp
    expression /^(?<created_at>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (?<level>\w+) \[(?<service>[\w-]+)\] (?<message>.*)$/
    time_key created_at
    time_format %Y-%m-%d %H:%M:%S
  </parse>
</filter>
```

### 5.3 멀티라인 로그 처리

**시나리오**: 스택 트레이스 같은 멀티라인 로그

**입력 로그**:
```
2024-01-15 10:30:22 ERROR Exception occurred
Traceback (most recent call last):
  File "payment.py", line 45, in process_payment
    raise PaymentError("Card declined")
PaymentError: Card declined
```

**Fluentd 설정**:
```ruby
<source>
  @type tail
  path /var/log/app/*.log
  pos_file /fluentd/log/app.pos
  tag app.log
  <parse>
    @type multiline
    format_firstline /^\d{4}-\d{2}-\d{2}/
    format1 /^(?<created_at>\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}) (?<level>\w+) (?<message>.*)/
  </parse>
</source>
```

### 5.4 조건부 필터링

**시나리오**: 특정 조건의 로그만 전송

```ruby
# DEBUG 로그 제외
<filter docker.**>
  @type grep
  <exclude>
    key level
    pattern /DEBUG|TRACE/
  </exclude>
</filter>

# 특정 서비스만 포함
<filter docker.**>
  @type grep
  <regexp>
    key service
    pattern /payment-api|order-api/
  </regexp>
</filter>

# 에러만 포함
<filter docker.**>
  @type grep
  <regexp>
    key level
    pattern /ERROR|FATAL/
  </regexp>
</filter>
```

### 5.5 필드 변환 및 추가

```ruby
<filter docker.**>
  @type record_transformer
  enable_ruby true
  <record>
    # 환경 변수 추가
    environment "#{ENV['ENVIRONMENT']}"
    region "#{ENV['AWS_REGION']}"

    # 계산된 필드
    log_size ${record.to_json.bytesize}
    hour ${Time.parse(record["timestamp"]).hour}

    # 조건부 필드
    is_error ${record["level"] == "ERROR"}

    # 중첩 필드 평탄화
    user_id ${record.dig("metadata", "user", "id")}

    # 필드 이름 변경
    endpoint ${record["path"]}
  </record>
  remove_keys path
</filter>
```

### 5.6 GeoIP 조회

**플러그인 설치**:
```bash
fluent-gem install fluent-plugin-geoip
```

**설정**:
```ruby
<filter docker.**>
  @type geoip
  geoip_lookup_keys client_ip
  <record>
    geo_country   ${country_code["client_ip"]}
    geo_city      ${city["client_ip"]}
    geo_latitude  ${latitude["client_ip"]}
    geo_longitude ${longitude["client_ip"]}
  </record>
</filter>
```

---

## 6. HTTP 엔드포인트 전송 설정

### 6.1 기본 HTTP Output

```ruby
<match docker.**>
  @type http
  endpoint http://log-server:8000/api/v1/logs/batch
  open_timeout 5
  read_timeout 10
  <format>
    @type json
  </format>
  json_array true  # 배치를 JSON 배열로
  <buffer>
    flush_interval 5s
  </buffer>
</match>
```

### 6.2 고급 버퍼링 설정

```ruby
<match docker.**>
  @type http
  endpoint http://log-server:8000/api/v1/logs/batch
  <buffer>
    # 버퍼 타입
    @type file
    path /fluentd/buffer/http

    # Flush 전략
    flush_mode interval
    flush_interval 5s           # 5초마다
    flush_at_shutdown true      # 종료 시 flush

    # 재시도 전략
    retry_type exponential_backoff
    retry_wait 1s               # 초기 대기 시간
    retry_max_interval 60s      # 최대 대기 시간
    retry_max_times 10          # 최대 재시도 횟수
    retry_forever false         # 무한 재시도 비활성화

    # 성능 튜닝
    chunk_limit_size 10M        # 청크 최대 크기
    total_limit_size 1G         # 전체 버퍼 크기
    overflow_action drop_oldest_chunk  # 버퍼 가득 시 동작

    # 배치 크기
    chunk_limit_records 1000    # 청크당 최대 레코드 수
  </buffer>
</match>
```

### 6.3 인증 헤더 추가

```ruby
<match docker.**>
  @type http
  endpoint http://log-server:8000/api/v1/logs/batch
  <headers>
    Authorization Bearer ${ENV['API_TOKEN']}
    Content-Type application/json
  </headers>
</match>
```

### 6.4 다중 Output (Copy)

```ruby
<match docker.**>
  @type copy

  # 메인: Log Server
  <store>
    @type http
    endpoint http://log-server:8000/api/v1/logs/batch
    <buffer>
      flush_interval 5s
    </buffer>
  </store>

  # 백업: S3
  <store>
    @type s3
    s3_bucket my-log-backup
    s3_region us-east-1
    path logs/%Y/%m/%d/
    <buffer time>
      timekey 3600  # 1시간 단위
      timekey_wait 10m
    </buffer>
  </store>

  # 실시간 알림: Elasticsearch
  <store ignore_error>
    @type elasticsearch
    host elasticsearch
    port 9200
    index_name fluentd-${tag}-%Y.%m.%d
  </store>
</match>
```

### 6.5 Secondary Output (Fallback)

```ruby
<match docker.**>
  @type http
  endpoint http://log-server:8000/api/v1/logs/batch
  <buffer>
    flush_interval 5s
  </buffer>

  # 전송 실패 시 로컬 파일에 백업
  <secondary>
    @type file
    path /fluentd/log/failed/${tag}
    <format>
      @type json
    </format>
    <buffer tag, time>
      @type file
      path /fluentd/buffer/failed
      timekey 3600
    </buffer>
  </secondary>
</match>
```

---

## 7. 성능 튜닝 가이드

### 7.1 성능 병목 지점

| 병목 지점 | 증상 | 해결 방법 |
|----------|------|----------|
| **CPU** | Fluentd 프로세스 CPU 사용률 높음 | Worker 수 증가, 파싱 최적화 |
| **메모리** | OOM 에러, 메모리 부족 | 버퍼 크기 감소, chunk 크기 조정 |
| **디스크 I/O** | 버퍼 파일 쓰기 느림 | SSD 사용, 버퍼 경로 변경 |
| **네트워크** | Output 전송 지연 | 배치 크기 증가, 동시 전송 수 증가 |

### 7.2 Worker 설정

```ruby
<system>
  # CPU 코어 수에 맞춰 조정
  workers 4

  # Worker당 메모리 제한
  root_dir /var/log/fluentd
</system>

# Worker별 부하 분산
<match docker.**>
  @type forward
  <buffer>
    flush_thread_count 4  # Worker당 flush 스레드 수
  </buffer>
</match>
```

### 7.3 버퍼 최적화

**시나리오별 권장 설정:**

#### 고처리량 (High Throughput)
```ruby
<buffer>
  @type file
  path /fluentd/buffer/high-throughput

  # 큰 청크, 빈번한 flush
  chunk_limit_size 50M
  flush_interval 10s
  flush_thread_count 8

  # 큰 버퍼
  total_limit_size 10G
</buffer>
```

#### 저지연 (Low Latency)
```ruby
<buffer>
  @type memory

  # 작은 청크, 빠른 flush
  chunk_limit_size 1M
  flush_interval 1s
  flush_thread_count 2

  # 작은 버퍼 (메모리 절약)
  total_limit_size 256M
</buffer>
```

#### 안정성 우선 (Reliability)
```ruby
<buffer>
  @type file
  path /fluentd/buffer/reliable

  # 재시도 강화
  retry_type exponential_backoff
  retry_max_times 20
  retry_max_interval 300s
  retry_forever true

  # Secondary output 필수
  <secondary>
    @type file
    path /fluentd/log/backup
  </secondary>
</buffer>
```

### 7.4 파싱 성능 최적화

```ruby
# ❌ 비효율적: Ruby eval 사용
<filter docker.**>
  @type record_transformer
  enable_ruby true
  <record>
    processed_at ${Time.now.iso8601}
    complex_calc ${record["value"].to_i * 1000 + rand(100)}
  </record>
</filter>

# ✅ 효율적: 플러그인 내장 기능 사용
<filter docker.**>
  @type record_transformer
  auto_typecast true
  <record>
    processed_at ${time}
  </record>
</filter>
```

### 7.5 모니터링 메트릭

**Prometheus 메트릭 수집:**

```ruby
<source>
  @type prometheus
  bind 0.0.0.0
  port 24231
  metrics_path /metrics
</source>

<source>
  @type prometheus_monitor
  <labels>
    host ${hostname}
  </labels>
</source>

<source>
  @type prometheus_output_monitor
  <labels>
    host ${hostname}
  </labels>
</source>
```

**주요 메트릭:**
- `fluentd_buffer_queue_length`: 버퍼 큐 길이
- `fluentd_buffer_total_queued_size`: 버퍼 총 크기
- `fluentd_output_status_emit_count`: 전송 성공 수
- `fluentd_output_status_retry_count`: 재시도 횟수
- `fluentd_output_status_rollback_count`: 롤백 수

**Grafana 대시보드 쿼리 예시:**
```promql
# 초당 로그 처리량
rate(fluentd_output_status_emit_count[5m])

# 버퍼 사용률
fluentd_buffer_total_queued_size / fluentd_buffer_stage_byte_size * 100

# 에러율
rate(fluentd_output_status_rollback_count[5m]) / rate(fluentd_output_status_emit_count[5m])
```

### 7.6 성능 벤치마크

**테스트 도구**: `fluent-cat`

```bash
# 100,000개 로그 전송
for i in {1..100000}; do
  echo '{"level":"INFO","message":"Test log '$i'"}' | \
  fluent-cat docker.test
done

# 시간 측정
time for i in {1..10000}; do
  echo '{"message":"test"}' | fluent-cat docker.test
done
```

**기대 성능:**
- **Throughput**: 10,000 - 50,000 events/sec (워커 4개 기준)
- **Latency**: < 100ms (버퍼링 포함)
- **메모리**: 40MB - 500MB (버퍼 크기에 따라)

---

## 8. 트러블슈팅 가이드

### 8.1 일반적인 문제

#### 문제 1: Fluentd가 시작되지 않음

**증상**:
```
2024-01-15 10:30:22 +0000 [error]: config error file="/fluentd/etc/fluent.conf" error_class=Fluent::ConfigError error="Unknown output plugin 'http'"
```

**원인**: 플러그인 미설치

**해결**:
```bash
# 필요한 플러그인 설치
docker exec fluentd fluent-gem install fluent-plugin-http-out

# 또는 Dockerfile에 추가
FROM fluent/fluentd:v1.16-1
USER root
RUN fluent-gem install fluent-plugin-http-out
USER fluent
```

#### 문제 2: 로그가 전송되지 않음

**증상**: Log Server에 로그 도착하지 않음

**디버깅 단계**:

```bash
# 1. Fluentd 로그 확인
docker logs fluentd

# 2. 버퍼 상태 확인
docker exec fluentd ls -lh /fluentd/buffer/

# 3. Fluentd health check
curl http://localhost:24231/metrics | grep buffer_queue_length

# 4. Log Server 연결 테스트
docker exec fluentd curl -v http://log-server:8000/health

# 5. 수동 로그 전송 테스트
echo '{"message":"test"}' | docker exec -i fluentd fluent-cat docker.test
```

**일반적 원인**:
- Log Server down → Secondary output 확인
- 네트워크 문제 → DNS/방화벽 확인
- 버퍼 가득참 → `total_limit_size` 증가

#### 문제 3: 메모리 사용량 증가

**증상**: Fluentd OOM killed

**디버깅**:
```bash
# 메모리 사용량 확인
docker stats fluentd

# 버퍼 크기 확인
du -sh /fluentd/buffer/
```

**해결**:
```ruby
<buffer>
  # 파일 버퍼로 변경 (메모리 절약)
  @type file
  path /fluentd/buffer/disk

  # 버퍼 크기 제한
  total_limit_size 1G
  chunk_limit_size 10M

  # 오래된 청크 삭제
  overflow_action drop_oldest_chunk
</buffer>
```

#### 문제 4: 로그 누락

**증상**: 일부 로그가 DB에 없음

**원인**:
1. Fluentd 버퍼 오버플로우
2. 재시도 실패
3. Log Server 에러

**해결**:
```ruby
# Secondary output으로 백업
<match docker.**>
  @type http
  endpoint http://log-server:8000/api/v1/logs/batch
  <buffer>
    overflow_action block  # 버퍼 가득 시 블록 (누락 방지)
  </buffer>
  <secondary>
    @type file
    path /fluentd/log/backup/${tag}
  </secondary>
</match>

# 백업 로그 재전송 스크립트
# scripts/resend_failed_logs.py
```

### 8.2 성능 문제

#### 문제 5: 높은 CPU 사용률

**원인**:
- 복잡한 정규식 파싱
- Ruby eval 남용
- Worker 수 부족

**해결**:
```ruby
# Worker 수 증가
<system>
  workers 8
</system>

# 파싱 최적화 (정규식 단순화)
<parse>
  @type regexp
  # ❌ 복잡: /^(?<time>\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d+Z) .../
  # ✅ 단순: /^(?<time>[^ ]+) .../
  expression /^(?<time>[^ ]+) (?<level>\w+) (?<message>.*)$/
</parse>

# Ruby eval 제거
<filter>
  @type record_transformer
  # enable_ruby true  # 제거
  <record>
    processed_at ${time}  # 내장 변수 사용
  </record>
</filter>
```

#### 문제 6: 느린 출력 속도

**원인**: 배치 크기 작음, 동시 전송 수 부족

**해결**:
```ruby
<match docker.**>
  @type http
  endpoint http://log-server:8000/api/v1/logs/batch
  <buffer>
    # 배치 크기 증가
    chunk_limit_records 5000  # 1000 → 5000
    flush_interval 10s         # 5s → 10s

    # 동시 전송 증가
    flush_thread_count 8       # 기본 1 → 8
  </buffer>
</match>
```

### 8.3 디버깅 도구

#### 로그 레벨 조정

```ruby
<system>
  log_level debug  # info → debug
</system>
```

#### 특정 태그 디버깅

```ruby
# stdout으로 출력
<match docker.payment-api>
  @type stdout
</match>
```

#### 로그 샘플링

```ruby
# 10개 중 1개만 처리 (디버깅용)
<filter docker.**>
  @type sampling
  interval 10
  sample_unit tag
</filter>
```

### 8.4 체크리스트

**배포 전 체크리스트:**
- [ ] Fluentd 플러그인 모두 설치됨
- [ ] 설정 파일 문법 검증 (`fluentd --dry-run`)
- [ ] Log Server 연결 테스트
- [ ] 버퍼 디렉토리 권한 확인
- [ ] Secondary output 설정됨
- [ ] 모니터링 메트릭 수집 설정

**운영 중 체크리스트:**
- [ ] 버퍼 사용률 < 80%
- [ ] 재시도 횟수 낮음
- [ ] Log Server 응답 시간 정상
- [ ] 메모리 사용량 안정적
- [ ] 로그 누락 없음

---

## 부록 A: 유용한 플러그인

| 플러그인 | 용도 | 설치 |
|---------|------|-----|
| `fluent-plugin-geoip` | GeoIP 조회 | `fluent-gem install fluent-plugin-geoip` |
| `fluent-plugin-elasticsearch` | Elasticsearch 출력 | `fluent-gem install fluent-plugin-elasticsearch` |
| `fluent-plugin-s3` | S3 백업 | `fluent-gem install fluent-plugin-s3` |
| `fluent-plugin-kafka` | Kafka 연동 | `fluent-gem install fluent-plugin-kafka` |
| `fluent-plugin-prometheus` | Prometheus 메트릭 | `fluent-gem install fluent-plugin-prometheus` |
| `fluent-plugin-slack` | Slack 알림 | `fluent-gem install fluent-plugin-slack` |
| `fluent-plugin-rewrite-tag-filter` | 동적 태그 변경 | `fluent-gem install fluent-plugin-rewrite-tag-filter` |

## 부록 B: 참고 자료

- **공식 문서**: https://docs.fluentd.org/
- **플러그인 검색**: https://www.fluentd.org/plugins/all
- **GitHub**: https://github.com/fluent/fluentd
- **커뮤니티**: https://groups.google.com/g/fluentd

---

**문서 버전**: 1.0
**최종 수정일**: 2024-01-15
**작성자**: Log Analysis System Team
