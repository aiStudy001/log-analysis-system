# 커스텀 로그 라이브러리 테스팅 가이드

clients 폴더의 Python 및 JavaScript 로그 수집 라이브러리 테스트 방법

## ⚡ 초간단 시작 (1분)

```bash
# 1. 서버 환경 실행 (Docker Compose)
docker-compose up -d

# 2. Python 단위 테스트 (서버 불필요)
cd clients/python
pip install -e ".[dev]"
pytest tests/test_async_client.py -v

# 3. Python 통합 테스트 (서버 필요)
pytest tests/test_integration.py -v

# 4. JavaScript 단위 테스트 (서버 불필요)
cd ../javascript
npm test

# 5. 수동 테스트
python ../python/test_manual.py
node test-manual.js
```

---

## 📁 생성된 테스트 파일

### Python 테스트
```
clients/python/
├── test_manual.py              # 수동 테스트 스크립트
└── tests/
    ├── __init__.py
    ├── test_async_client.py    # 단위 테스트
    ├── test_integration.py     # 통합 테스트 (서버 필요)
    └── test_performance.py     # 성능 테스트 (서버 필요)
```

### JavaScript 테스트
```
clients/javascript/
├── test-manual.js              # 수동 테스트 스크립트
├── jest.config.js              # Jest 설정
└── __tests__/
    └── client.test.js          # 단위 테스트
```

---

## 🚀 빠른 시작

### 서버 환경 실행 (Docker Compose 사용 - 추천 ⭐)

```bash
# 프로젝트 루트에서
# .env 파일이 있는지 확인 (없으면 생성 필요)
ls .env

# 전체 환경 실행
docker-compose up -d

# 서버 실행 확인
curl http://localhost:8000/
# 응답: {"status":"ok","service":"log-server"}

# 로그 확인
docker-compose logs -f log-save-server
```

**실행되는 서비스:**
- PostgreSQL: `localhost:5433` (포트 주의! 5432 아님)
- Log Save Server: `localhost:8000`
- Log Analysis Server: `localhost:8001`

**주의:** `.env` 파일에 `POSTGRES_PASSWORD` 설정 필요!

---

### Python 테스트

#### 1. 환경 준비
```bash
cd clients/python
pip install -e ".[dev]"
```

#### 2. 단위 테스트 실행 (서버 불필요)
```bash
pytest tests/test_async_client.py -v
```

**예상 출력:**
```
tests/test_async_client.py::test_client_initialization PASSED
tests/test_async_client.py::test_log_queueing PASSED
tests/test_async_client.py::test_batch_size_option PASSED
tests/test_async_client.py::test_flush_interval_option PASSED
...
```

#### 3. 수동 테스트 (서버 필요)

**옵션 A: Docker Compose 사용 (추천)**
```bash
# 터미널 1: Docker Compose로 전체 환경 실행
docker-compose up -d

# 터미널 2: 테스트 실행
cd clients/python
python test_manual.py
```

**옵션 B: 로컬에서 서버 직접 실행**
```bash
# 터미널 1: 로그 서버 실행
cd services/log-save-server
python main.py

# 터미널 2: 테스트 실행
cd clients/python
python test_manual.py
```

**예상 출력:**
```
Sending 5 test logs...
Logs queued! Waiting for flush...
Flushing remaining logs...
Done! Check server logs.
```

#### 4. 통합 테스트 (서버 + DB 필요)
```bash
# PostgreSQL과 로그 서버 실행 상태에서
pytest tests/test_integration.py -v -s
```

#### 5. 성능 테스트 (서버 필요)
```bash
pytest tests/test_performance.py -v -s
```

**예상 출력:**
```
처리량 테스트 결과:
  총 로그: 10000개
  소요 시간: 0.850초
  처리량: 11765 logs/sec
  로그당 시간: 0.085ms

지연시간 테스트 결과:
  호출당 지연시간: 0.045ms
  목표: < 0.1ms

메모리 사용량 테스트 결과:
  현재 메모리: 2.45MB
  피크 메모리: 5.12MB
  목표: < 10MB
```

---

### JavaScript 테스트

#### 1. 환경 준비
```bash
cd clients/javascript
npm install
```

#### 2. 단위 테스트 실행 (서버 불필요)
```bash
npm test
```

**예상 출력:**
```
 PASS  __tests__/client.test.js
  createLogClient
    ✓ should create a client instance (5 ms)
    ✓ should accept options (2 ms)
    ✓ should have all log level methods (1 ms)
    ...

Performance: 0.012ms per call

Test Suites: 1 passed, 1 total
Tests:       15 passed, 15 total
```

#### 3. 수동 테스트 (서버 필요)

**옵션 A: Docker Compose 사용 (추천)**
```bash
# 터미널 1: Docker Compose로 전체 환경 실행
docker-compose up -d

# 터미널 2: 테스트 실행
cd clients/javascript
node test-manual.js
```

**옵션 B: 로컬에서 서버 직접 실행**
```bash
# 터미널 1: 로그 서버 실행
cd services/log-save-server
python main.py

# 터미널 2: 테스트 실행
cd clients/javascript
node test-manual.js
```

**예상 출력:**
```
Sending 5 test logs...
Logs sent! Check server...
Closing...
```

---

## 🧪 테스트 시나리오 상세

### Python 테스트 시나리오

#### test_async_client.py (단위 테스트)
- ✅ 클라이언트 초기화
- ✅ 로그 큐잉 블로킹 시간 < 0.001초
- ✅ 배치 크기 옵션 적용
- ✅ Flush 간격 옵션 적용
- ✅ 다양한 로그 레벨 (INFO/WARN/ERROR/DEBUG/FATAL)
- ✅ 메타데이터 전달
- ✅ 서비스 이름 설정

#### test_integration.py (통합 테스트)
- ✅ E2E: 로그 전송 → 서버 → DB 저장
- ✅ 배치 전송 (10개 로그 자동 배치)
- ✅ Flush 간격 자동 전송
- ✅ 수동 flush 호출
- ✅ 여러 서비스 동시 로그
- ✅ 에러 로그 처리

#### test_performance.py (성능 테스트)
- ✅ 처리량: > 5,000 logs/sec
- ✅ 지연시간: < 1ms per log
- ✅ 메모리: < 20MB for 10K logs
- ✅ 동시 로깅 성능
- ✅ 배치 크기별 성능 비교

---

### JavaScript 테스트 시나리오

#### client.test.js (단위 테스트)
- ✅ 클라이언트 생성
- ✅ 옵션 적용 (batchSize, flushInterval)
- ✅ 모든 로그 레벨 메서드 존재
- ✅ 커스텀 배치 크기
- ✅ 커스텀 flush 간격
- ✅ 메타데이터와 함께 로그 호출
- ✅ 연속 로그 호출 성능 (< 100ms for 10 logs)
- ✅ 독립적인 클라이언트 생성
- ✅ 성능: 1000개 로그 < 1초

---

## 📊 테스트 결과 확인

### 로그 서버 콘솔
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Application startup complete.
✅ Received 5 logs (batch)
✅ Received 10 logs (batch)
```

### PostgreSQL 직접 확인
```bash
# Windows PowerShell/CMD
# 주의: Docker Compose 사용 시 포트는 5433!
psql -h localhost -p 5433 -U postgres -d logs_db

# PostgreSQL 쿼리
SELECT COUNT(*) FROM logs WHERE metadata->>'test_id' = 'manual_test';
SELECT * FROM logs WHERE metadata->>'test_id' = 'e2e_test' ORDER BY created_at DESC;
SELECT level, COUNT(*) FROM logs GROUP BY level;
```

### HTTP API로 통계 확인
```bash
curl http://localhost:8000/stats
```

**응답 예시:**
```json
{
  "total_logs": 10245,
  "level_distribution": {
    "INFO": 8234,
    "WARN": 1245,
    "ERROR": 623,
    "DEBUG": 123,
    "FATAL": 20
  },
  "recent_errors_1h": 45
}
```

---

## 🔧 환경 설정

### 옵션 A: Docker Compose 사용 (추천 ⭐)
```bash
# 프로젝트 루트에서 전체 환경 실행
docker-compose up -d

# 로그 확인
docker-compose logs -f log-save-server

# 중지
docker-compose down
```

**장점:**
- PostgreSQL (5433) + Log Server (8000) 한 번에 실행
- 스키마 자동 생성
- 환경 변수 자동 설정

---

### 옵션 B: 개별 실행 (수동 설정 필요)

#### PostgreSQL 실행 (Docker)
```bash
docker run -d \
  --name log-postgres \
  -p 5433:5432 \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=logs_db \
  postgres:15
```

#### 스키마 생성
```bash
# database/schema.sql이 있다면
psql -h localhost -p 5433 -U postgres -d logs_db -f database/schema.sql

# 또는 로그 서버가 자동 생성할 수도 있음
```

#### 로그 서버 실행
```bash
cd services/log-save-server
python main.py
```

---

## ❓ 트러블슈팅

### Q1: pytest: command not found
```bash
pip install -e ".[dev]"
# 또는
pip install pytest pytest-asyncio requests
```

### Q2: 로그가 DB에 저장되지 않음
**체크리스트:**
1. Docker Compose 실행 중? → `docker-compose ps`
2. PostgreSQL 실행 중? → `psql -h localhost -p 5433 -U postgres -l`
3. 로그 서버 실행 중? → `curl http://localhost:8000`
4. 스키마 생성됨? → `psql -h localhost -p 5433 -U postgres -d logs_db -c "\dt"`
5. 올바른 URL 사용? → `http://localhost:8000`

### Q3: JavaScript 테스트 실패 - Cannot find module
```bash
# package.json에 "type": "module" 확인
# 없으면 추가:
npm pkg set type=module
```

### Q4: 성능 테스트 실패 (처리량 부족)
**원인:**
- 네트워크 지연
- 서버 부하
- 디스크 I/O

**해결:**
- 로컬에서 서버 실행
- 다른 프로세스 종료
- 성능 기준 완화 (코드 수정)

### Q5: Integration tests skipped
**원인:** 로그 서버가 실행되지 않음

**해결:**
```bash
# 터미널 1
cd services/log-save-server
python main.py

# 터미널 2
pytest tests/test_integration.py -v
```

---

## 📋 테스트 체크리스트

### 필수 테스트 (모두 통과해야 함)
- [ ] Python 단위 테스트: `pytest tests/test_async_client.py -v`
- [ ] JavaScript 단위 테스트: `npm test`
- [ ] Python 수동 테스트: `python test_manual.py`
- [ ] JavaScript 수동 테스트: `node test-manual.js`

### 선택 테스트 (서버 환경 필요)
- [ ] Python 통합 테스트: `pytest tests/test_integration.py -v`
- [ ] Python 성능 테스트: `pytest tests/test_performance.py -v -s`

---

## 🎯 다음 단계

### 1. CI/CD 통합
```yaml
# .github/workflows/test.yml
name: Test Log Clients
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Python Tests
        run: |
          cd clients/python
          pip install -e ".[dev]"
          pytest tests/test_async_client.py -v
      - name: JavaScript Tests
        run: |
          cd clients/javascript
          npm install
          npm test
```

### 2. 커버리지 측정
```bash
# Python
pytest tests/ --cov=log_collector --cov-report=html

# JavaScript
npm test -- --coverage
```

### 3. 브라우저 테스트 추가
```html
<!-- clients/javascript/test-browser.html -->
<!DOCTYPE html>
<html>
<head><title>Browser Test</title></head>
<body>
    <h1>Log Client Browser Test</h1>
    <button id="testBtn">Send Logs</button>
    <script type="module">
        import { createLogClient } from './src/index.js';
        const logger = createLogClient('http://localhost:8000');
        document.getElementById('testBtn').onclick = () => {
            logger.info('Browser test', { source: 'browser' });
        };
    </script>
</body>
</html>
```

---

## 📖 참고 자료

- [pytest 공식 문서](https://docs.pytest.org/)
- [Jest 공식 문서](https://jestjs.io/)
- [API 테스트 가이드](../API-TEST-GUIDE.md)
- [로그 서버 문서](../services/log-save-server/README.md)
