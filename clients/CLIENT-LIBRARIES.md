# 커스텀 로그 수집 라이브러리 상세 가이드

Python 및 JavaScript 로그 수집 클라이언트 라이브러리의 코드 구조와 동작 원리

---

## 📋 목차

1. [개요](#-개요)
2. [아키텍처 설계](#-아키텍처-설계)
3. [Python 클라이언트](#-python-클라이언트)
4. [JavaScript 클라이언트](#-javascript-클라이언트)
5. [API 사용법](#-api-사용법)
   - [글로벌 에러 핸들러](#글로벌-에러-핸들러-자동-에러-로깅)
6. [성능 특성](#-성능-특성)
7. [내부 동작 원리](#-내부-동작-원리)

---

## 🎯 개요

### 두 가지 클라이언트 라이브러리

| 특징 | Python | JavaScript |
|------|--------|------------|
| **환경** | Python 3.7+ | Node.js 12+ / 브라우저 |
| **비동기 방식** | Background Thread | Worker Threads / Web Worker |
| **앱 블로킹** | ~0.05ms | ~0.01ms |
| **배치 전송** | 1000건 or 1초 | 1000건 or 1초 |
| **압축** | gzip (100건 이상) | gzip (100건 이상) |
| **재시도** | Exponential backoff (3회) | 기본 재시도 |
| **글로벌 에러 핸들러** | sys.excepthook | window.onerror / process.on |

### 공통 특징

✅ **비블로킹 설계**: 앱 메인 스레드에 영향 없음
✅ **스마트 배치**: 1000건 모이거나 1초 경과 시 자동 전송
✅ **압축 전송**: 대량 로그 시 gzip으로 네트워크 절약
✅ **Graceful Shutdown**: 앱 종료 시 큐에 남은 로그 자동 전송
✅ **간단한 API**: `logger.info()`, `logger.error()` 등 직관적 메서드
✅ **글로벌 에러 핸들러**: 모든 에러를 자동으로 로깅 (옵션)

---

## 🏗️ 아키텍처 설계

### 전체 흐름

```
앱 코드
  ↓ logger.info("message")  ← 0.05ms 이내 즉시 리턴
로컬 큐 (deque/Array)
  ↓ 백그라운드 워커
배치 전송 (1000건 or 1초)
  ↓ HTTP POST (gzip)
FastAPI 로그 서버
  ↓ PostgreSQL COPY
PostgreSQL DB
```

### 핵심 설계 원칙

#### 1. 메인 스레드 격리 (Zero Blocking)

**Python:**
```python
def log(self, level, message, **kwargs):
    log_entry = {...}
    self.queue.append(log_entry)  # 큐에만 추가, 즉시 리턴!
    # HTTP 전송은 백그라운드 스레드에서
```

**JavaScript (Node.js):**
```javascript
log(level, message, metadata) {
    this.worker.postMessage({...});  // Worker로만 전달, 즉시 리턴!
    // HTTP 전송은 Worker Threads에서
}
```

#### 2. 스마트 배치 (Adaptive Batching)

```
큐 크기 >= 1000건 → 즉시 전송
큐 크기 < 1000건 → 1초 대기 후 전송
빈 큐 → 대기 (polling)
```

#### 3. 네트워크 최적화

```
로그 100건 미만 → JSON 그대로 전송
로그 100건 이상 → gzip 압축 전송 (70% 크기 감소)
```

---

## 🐍 Python 클라이언트

### 파일 구조

```
clients/python/
├── log_collector/
│   ├── __init__.py           # 패키지 진입점
│   └── async_client.py        # AsyncLogClient 구현
├── setup.py                   # 패키지 설정
└── README.md
```

### AsyncLogClient 클래스

#### 주요 컴포넌트

```python
class AsyncLogClient:
    def __init__(self, server_url, batch_size=1000, flush_interval=1.0):
        self.queue = deque(maxlen=max_queue_size)  # 로컬 큐
        self._worker_thread = Thread(target=self._flush_loop)  # 백그라운드 스레드
        self._stop_event = Event()  # 종료 신호

    def log(self, level, message, **kwargs):
        """큐에만 추가 (0.05ms)"""
        self.queue.append(log_entry)

    def _flush_loop(self):
        """백그라운드 스레드 루프"""
        while not self._stop_event.is_set():
            if len(self.queue) >= self.batch_size:
                # 1000건 모이면 즉시 전송
                batch = [self.queue.popleft() for _ in range(self.batch_size)]
                await self._send_batch(batch)
            elif len(self.queue) > 0:
                # 1초 지나면 쌓인 것만이라도 전송
                time.sleep(self.flush_interval)
                batch = [self.queue.popleft() for _ in range(len(self.queue))]
                await self._send_batch(batch)

    async def _send_batch(self, batch):
        """HTTP POST로 배치 전송"""
        payload = json.dumps({"logs": batch})
        if self.enable_compression and len(batch) >= 100:
            payload = gzip.compress(payload.encode())
            headers["Content-Encoding"] = "gzip"

        async with aiohttp.ClientSession() as session:
            async with session.post(f"{self.server_url}/logs", data=payload) as response:
                # 재시도 로직 포함
```

#### 스레드 구조

```
메인 스레드                     백그라운드 스레드
├─ log() 호출                  ├─ _flush_loop()
├─ queue.append()              ├─ 큐 모니터링
├─ 즉시 리턴 ✅                ├─ 배치 수집
│                              ├─ _send_batch()
│                              └─ HTTP POST
```

### 재시도 메커니즘

```python
async def _send_batch(self, batch, retry_count=0):
    try:
        # HTTP 전송
    except Exception as e:
        if retry_count < self.max_retries:
            await asyncio.sleep(2 ** retry_count)  # Exponential backoff
            await self._send_batch(batch, retry_count + 1)
        else:
            print(f"Final retry failed: {e}")
```

**재시도 간격:**
- 1차 실패 → 1초 후 재시도
- 2차 실패 → 2초 후 재시도
- 3차 실패 → 4초 후 재시도
- 최종 실패 → 로그 유실 (에러 출력)

### Graceful Shutdown

```python
def _graceful_shutdown(self):
    """앱 종료 시 자동 호출 (atexit)"""
    if len(self.queue) > 0:
        print(f"Flushing {len(self.queue)} remaining logs...")
        batch = [self.queue.popleft() for _ in range(len(self.queue))]
        loop = asyncio.new_event_loop()
        loop.run_until_complete(self._send_batch(batch))

atexit.register(self._graceful_shutdown)  # 자동 등록
```

---

## 📦 JavaScript 클라이언트

### 파일 구조

```
clients/javascript/
├── src/
│   ├── index.js              # 환경 감지 & 팩토리
│   ├── browser-client.js     # Web Worker 클라이언트
│   ├── browser-worker.js     # Web Worker 스크립트
│   ├── node-client.js        # Worker Threads 클라이언트
│   └── node-worker.js        # Worker Threads 스크립트
├── package.json
└── README.md
```

### 환경 자동 감지 (index.js)

```javascript
export function createLogClient(serverUrl, options = {}) {
    // 브라우저 환경
    if (typeof window !== 'undefined' && typeof Worker !== 'undefined') {
        return new WebWorkerLogClient(serverUrl, options);
    }
    // Node.js 환경
    else if (typeof process !== 'undefined') {
        return new WorkerThreadsLogClient(serverUrl, options);
    }
    else {
        throw new Error('Unsupported environment');
    }
}
```

### Node.js 구현 (Worker Threads)

#### WorkerThreadsLogClient 클래스

```javascript
class WorkerThreadsLogClient {
    constructor(serverUrl, options) {
        // Worker Threads 생성
        this.worker = new Worker(
            path.join(__dirname, 'node-worker.js'),
            { workerData: { serverUrl, ...options } }
        );

        this._setupGracefulShutdown();
    }

    log(level, message, metadata = {}) {
        // Worker로 메시지만 전달 (즉시 리턴!)
        this.worker.postMessage({
            type: 'log',
            data: { level, message, created_at: Date.now(), ...metadata }
        });
    }

    _setupGracefulShutdown() {
        process.on('exit', () => this.flush());
        process.on('SIGINT', () => this.flush());
        process.on('SIGTERM', () => this.flush());
    }
}
```

#### Worker Threads 구조

```
메인 스레드                     Worker Threads
├─ log() 호출                  ├─ 메시지 수신
├─ postMessage()               ├─ 큐에 추가
├─ 즉시 리턴 ✅                ├─ 배치 수집
│                              ├─ HTTP POST
│                              └─ 압축 전송
```

### 브라우저 구현 (Web Worker)

#### WebWorkerLogClient 클래스

```javascript
class WebWorkerLogClient {
    constructor(serverUrl, options) {
        // Web Worker 생성
        this.worker = new Worker(
            new URL('./browser-worker.js', import.meta.url),
            { type: 'module' }
        );

        this.worker.postMessage({
            type: 'init',
            serverUrl: this.serverUrl,
            ...this.options
        });

        this._setupGracefulShutdown();
    }

    log(level, message, metadata = {}) {
        // Worker로 메시지만 전달 (즉시 리턴!)
        this.worker.postMessage({
            type: 'log',
            data: { level, message, created_at: Date.now(), ...metadata }
        });
    }

    _setupGracefulShutdown() {
        // 브라우저 종료 시
        window.addEventListener('beforeunload', () => this.flush());

        // 탭 전환/모바일 백그라운드
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) this.flush();
        });
    }
}
```

#### Web Worker 구조

```
메인 스레드 (UI)               Web Worker
├─ log() 호출                  ├─ onmessage 이벤트
├─ postMessage()               ├─ 큐에 추가
├─ 즉시 리턴 ✅                ├─ 배치 수집
├─ UI 렌더링 계속              ├─ fetch() API
│   (렉 0%)                    └─ 압축 전송
```

---

## 📚 API 사용법

### Python 사용 예시

#### 기본 사용

```python
from log_collector import AsyncLogClient

# 클라이언트 생성
client = AsyncLogClient("http://localhost:8000")

# 로그 전송
client.log("INFO", "User logged in", user_id=123, action="login")
client.log("ERROR", "Database connection failed", error_code="DB_CONN_ERR")

# 편의 메서드
client.info("Application started")
client.warn("High memory usage", memory_mb=850)
client.error("Payment failed", transaction_id="tx_12345")
```

#### 옵션 설정

```python
client = AsyncLogClient(
    "http://localhost:8000",
    batch_size=500,           # 500건마다 전송
    flush_interval=2.0,       # 2초마다 전송
    enable_compression=True,  # gzip 압축 활성화
    max_retries=5             # 최대 5회 재시도
)
```

#### 수동 Flush

```python
# 중요한 로그 즉시 전송
client.error("Critical error occurred!")
client.flush()  # 큐에 있는 모든 로그 즉시 전송
```

#### Graceful Shutdown

```python
# 자동으로 처리됨 (atexit)
# 필요 시 수동 호출도 가능
client.close()
```

---

### JavaScript 사용 예시

#### Node.js 기본 사용

```javascript
import { createLogClient } from './src/index.js';

// 클라이언트 생성 (자동으로 Worker Threads 사용)
const logger = createLogClient('http://localhost:8000');

// 로그 전송
logger.info('User logged in', { user_id: 123, action: 'login' });
logger.error('Database connection failed', { error_code: 'DB_CONN_ERR' });

// 모든 로그 레벨 사용 가능
logger.trace('Detailed trace info');
logger.debug('Debug information');
logger.info('General information');
logger.warn('Warning message');
logger.error('Error occurred');
logger.fatal('Fatal error');
```

#### 브라우저 기본 사용

```html
<!DOCTYPE html>
<html>
<head><title>Log Example</title></head>
<body>
    <script type="module">
        import { createLogClient } from './src/index.js';

        // 클라이언트 생성 (자동으로 Web Worker 사용)
        const logger = createLogClient('http://localhost:8000');

        // 사용자 이벤트 로깅
        document.getElementById('loginBtn').addEventListener('click', () => {
            logger.info('Login button clicked', {
                timestamp: Date.now(),
                page: window.location.pathname
            });
        });

        // 에러 로깅
        window.addEventListener('error', (event) => {
            logger.error('JavaScript error', {
                message: event.message,
                filename: event.filename,
                lineno: event.lineno
            });
        });
    </script>
</body>
</html>
```

#### 옵션 설정

```javascript
const logger = createLogClient('http://localhost:8000', {
    batchSize: 500,           // 500건마다 전송
    flushInterval: 2000,      // 2초마다 전송
    enableCompression: true   // gzip 압축 활성화
});
```

#### 수동 Flush

```javascript
// 중요한 로그 즉시 전송
logger.error('Critical error occurred!');
logger.flush();  // 큐에 있는 모든 로그 즉시 전송
```

#### Graceful Shutdown

```javascript
// 자동으로 처리됨 (process.exit, beforeunload 이벤트)
// 필요 시 수동 호출도 가능
await logger.close();
```

#### 글로벌 에러 핸들러 (자동 에러 로깅)

모든 클라이언트에서 `enableGlobalErrorHandler` 옵션을 제공합니다.

**JavaScript (Node.js)**:
```javascript
const logger = createLogClient('http://localhost:8000', {
    service: 'my-app',
    enableGlobalErrorHandler: true  // 모든 에러 자동 로깅
});

// 이제 모든 uncaught errors가 자동으로 로깅됩니다
throw new Error('Uncaught error');  // 자동 로깅
Promise.reject('Unhandled rejection');  // 자동 로깅
```

**JavaScript (Browser)**:
```javascript
import { WebWorkerLogClient } from 'log-collector-async/browser';

const logger = new WebWorkerLogClient('http://localhost:8000', {
    service: 'web-app',
    enableGlobalErrorHandler: true  // 모든 에러 자동 로깅
});

// 모든 에러가 자동으로 로깅됩니다
undefined.someMethod();  // TypeError - 자동 로깅
```

**Python**:
```python
logger = AsyncLogClient(
    "http://localhost:8000",
    service="my-app",
    enable_global_error_handler=True  # 모든 에러 자동 로깅
)

# 모든 uncaught exceptions가 자동으로 로깅됩니다
raise ValueError("Uncaught exception")  # 자동 로깅
```

**환경 변수로 활성화**:
```bash
# .env 파일
ENABLE_GLOBAL_ERROR_HANDLER=true
```

**주의사항**:
- 기본값: `false` (명시적으로 활성화 필요)
- `close()` 호출 시 자동으로 핸들러 해제
- 기존 에러 핸들러와 충돌 가능성 있음 (테스트 필요)

자세한 내용은 [GLOBAL-ERROR-HANDLER.md](./GLOBAL-ERROR-HANDLER.md) 참고

---

## ⚡ 성능 특성

### 벤치마크 결과

| 항목 | Python | JavaScript (Node.js) | JavaScript (브라우저) |
|------|--------|---------------------|---------------------|
| **앱 블로킹 시간** | ~0.05ms | ~0.01ms | ~0.01ms |
| **처리량** | 20K+ logs/sec | 100K+ logs/sec | 50K+ logs/sec |
| **메모리 사용** | ~5MB (10K logs) | ~3MB (10K logs) | ~4MB (10K logs) |
| **압축률** | ~70% | ~70% | ~70% |
| **배치 전송 시간** | 5-10ms | 3-8ms | 5-12ms |

### 성능 측정 코드

#### Python 성능 테스트

```python
import time
from log_collector import AsyncLogClient

client = AsyncLogClient("http://localhost:8000")

# 블로킹 시간 측정
start = time.time()
client.info("test message")
elapsed = time.time() - start
print(f"Blocking time: {elapsed*1000:.3f}ms")  # ~0.05ms

# 처리량 측정
count = 10000
start = time.time()
for i in range(count):
    client.info(f"log {i}")
elapsed = time.time() - start
print(f"Throughput: {count/elapsed:.0f} logs/sec")  # ~20K logs/sec
```

#### JavaScript 성능 테스트

```javascript
import { createLogClient } from './src/index.js';

const logger = createLogClient('http://localhost:8000');

// 블로킹 시간 측정
const start = performance.now();
logger.info('test message');
const elapsed = performance.now() - start;
console.log(`Blocking time: ${elapsed.toFixed(3)}ms`);  // ~0.01ms

// 처리량 측정
const count = 10000;
const startTime = performance.now();
for (let i = 0; i < count; i++) {
    logger.info(`log ${i}`);
}
const elapsedTime = performance.now() - startTime;
console.log(`Throughput: ${(count / elapsedTime * 1000).toFixed(0)} logs/sec`);
```

---

## 🔬 내부 동작 원리

### 1. 큐 기반 비동기 처리

#### Python: collections.deque

```python
from collections import deque

self.queue = deque(maxlen=10000)  # FIFO 큐, 최대 10K

# 추가: O(1)
self.queue.append(log_entry)

# 제거: O(1)
batch = [self.queue.popleft() for _ in range(batch_size)]
```

**특징:**
- Thread-safe 지원
- 양방향 큐 (deque)
- O(1) append/popleft 성능

#### JavaScript: Array

```javascript
// Worker 내부
const queue = [];

// 추가: O(1)
queue.push(logEntry);

// 배치 수집: O(n)
const batch = queue.splice(0, batchSize);
```

**특징:**
- Worker 격리로 thread-safe
- splice()로 배치 수집
- Array 네이티브 성능

---

### 2. 백그라운드 워커 패턴

#### Python: Threading + asyncio

```python
import asyncio
from threading import Thread

def _flush_loop(self):
    """백그라운드 스레드"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        while not self._stop_event.is_set():
            # 큐 모니터링
            if len(self.queue) >= self.batch_size:
                batch = [...]
                loop.run_until_complete(self._send_batch(batch))
            time.sleep(0.1)  # Polling
    finally:
        loop.close()

# 스레드 시작
self._worker_thread = Thread(target=self._flush_loop, daemon=True)
self._worker_thread.start()
```

**동작 방식:**
1. 메인 스레드: `log()` → 큐 추가만
2. 백그라운드 스레드: 큐 모니터링 → HTTP 전송
3. GIL 영향: 네트워크 I/O는 GIL 해제되므로 성능 문제 없음

#### JavaScript (Node.js): Worker Threads

```javascript
// 메인 스레드
const { Worker } = require('worker_threads');
this.worker = new Worker('./node-worker.js', {
    workerData: { serverUrl, batchSize, flushInterval }
});

this.worker.postMessage({ type: 'log', data: {...} });

// Worker 스레드 (node-worker.js)
const { parentPort, workerData } = require('worker_threads');

const queue = [];
parentPort.on('message', (msg) => {
    if (msg.type === 'log') {
        queue.push(msg.data);
    }
});

// 배치 전송 루프
setInterval(() => {
    if (queue.length >= workerData.batchSize) {
        const batch = queue.splice(0, workerData.batchSize);
        sendBatch(batch);
    }
}, workerData.flushInterval);
```

**동작 방식:**
1. 메인 스레드: `log()` → postMessage
2. Worker 스레드: 메시지 수신 → 큐 추가 → HTTP 전송
3. 완전 격리: CPU 바운드 작업도 메인 스레드 영향 없음

#### JavaScript (브라우저): Web Worker

```javascript
// 메인 스레드
this.worker = new Worker(new URL('./browser-worker.js', import.meta.url));
this.worker.postMessage({ type: 'log', data: {...} });

// Web Worker (browser-worker.js)
let queue = [];

self.onmessage = (event) => {
    const { type, data } = event.data;
    if (type === 'log') {
        queue.push(data);
    }
};

// 배치 전송 루프
setInterval(() => {
    if (queue.length >= batchSize) {
        const batch = queue.splice(0, batchSize);
        fetch(`${serverUrl}/logs`, {
            method: 'POST',
            body: JSON.stringify({ logs: batch }),
            headers: { 'Content-Type': 'application/json' }
        });
    }
}, flushInterval);
```

**동작 방식:**
1. 메인 스레드 (UI): `log()` → postMessage
2. Web Worker: 메시지 수신 → 큐 추가 → fetch() 전송
3. UI 렌더링과 완전 분리 → 렉 0%

---

### 3. 압축 알고리즘 (gzip)

#### Python 압축

```python
import gzip

payload = json.dumps({"logs": batch})

if self.enable_compression and len(batch) >= 100:
    payload = gzip.compress(payload.encode())
    headers["Content-Encoding"] = "gzip"
```

#### JavaScript 압축 (Node.js)

```javascript
const zlib = require('zlib');

let payload = JSON.stringify({ logs: batch });

if (enableCompression && batch.length >= 100) {
    payload = zlib.gzipSync(payload);
    headers['Content-Encoding'] = 'gzip';
}
```

**압축 효과:**
```
원본 JSON: 10KB (100개 로그)
압축 후: ~3KB (70% 감소)
네트워크 절약: 7KB
```

---

### 4. 에러 복구 메커니즘

#### 재시도 로직 (Python)

```python
async def _send_batch(self, batch, retry_count=0):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(...) as response:
                if response.status != 200:
                    raise Exception(f"HTTP {response.status}")
    except Exception as e:
        if retry_count < self.max_retries:
            # Exponential backoff: 1s, 2s, 4s, 8s
            await asyncio.sleep(2 ** retry_count)
            await self._send_batch(batch, retry_count + 1)
        else:
            # 최종 실패 - 로그 유실
            print(f"[Log Client] Final retry failed: {e}")
```

**재시도 시나리오:**
1. 네트워크 일시 장애 → 1초 후 재시도 → 성공 ✅
2. 서버 과부하 → 2초 후 재시도 → 성공 ✅
3. 서버 다운 → 4초 후 재시도 → 실패 → 8초 후 재시도 → 최종 실패 ❌

#### 큐 오버플로우 방지

```python
# Python: maxlen으로 제한
self.queue = deque(maxlen=10000)
# 10,001번째 로그 추가 시 가장 오래된 로그 자동 제거

# JavaScript: 수동 체크
if (queue.length > maxQueueSize) {
    queue.shift();  // 가장 오래된 로그 제거
}
```

---

## 🎓 학습 포인트

### 비동기 패턴 이해

1. **Python Threading + asyncio**
   - GIL의 영향과 I/O bound 작업
   - Event loop와 스레드 분리
   - atexit를 통한 자동 cleanup

2. **JavaScript Worker API**
   - postMessage를 통한 스레드 간 통신
   - Transferable objects (성능 최적화)
   - Worker 생명주기 관리

3. **큐 기반 설계**
   - Producer-Consumer 패턴
   - 배치 처리의 효율성
   - 메모리 관리 전략

### 성능 최적화 기법

1. **지연 시간 최소화**
   - 큐에만 추가 (0.05ms)
   - 백그라운드 전송
   - 메인 스레드 격리

2. **네트워크 효율**
   - 배치 전송 (1000건)
   - gzip 압축 (70% 절약)
   - HTTP Keep-Alive

3. **메모리 효율**
   - 고정 큐 크기 (10K)
   - 자동 오버플로우 처리
   - 적시 배치 전송

---

## 🔍 디버깅 팁

### Python 디버깅

```python
# 큐 상태 확인
print(f"Queue size: {len(client.queue)}")

# Worker 스레드 상태
print(f"Worker alive: {client._worker_thread.is_alive()}")

# 강제 flush로 전송 확인
client.flush()
```

### JavaScript 디버깅

```javascript
// Worker 메시지 모니터링 (Node.js)
client.worker.on('message', (msg) => {
    console.log('Worker message:', msg);
});

// Worker 에러 확인
client.worker.on('error', (err) => {
    console.error('Worker error:', err);
});

// 강제 flush로 전송 확인
logger.flush();
```

---

## 📖 참고 자료

- [Python asyncio 공식 문서](https://docs.python.org/3/library/asyncio.html)
- [Worker Threads (Node.js)](https://nodejs.org/api/worker_threads.html)
- [Web Workers API](https://developer.mozilla.org/en-US/docs/Web/API/Web_Workers_API)
- [gzip 압축](https://www.gnu.org/software/gzip/)
