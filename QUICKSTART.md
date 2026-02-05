# 빠른 시작 가이드

로그 수집 시스템 전체 스택 구축 및 테스트

## 📋 순서

1. PostgreSQL 실행
2. 스키마 생성
3. 로그 서버 실행
4. 클라이언트 테스트

---

## 1️⃣ PostgreSQL 실행

```bash
# Docker로 PostgreSQL 실행
docker run -d \
  --name logs-db \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=logs_db \
  -p 5432:5432 \
  postgres:15

# 실행 확인
docker ps | grep logs-db
```

---

## 2️⃣ 스키마 생성

```bash
# psql로 스키마 생성
docker exec -i logs-db psql -U postgres -d logs_db < schema.sql

# 또는 Windows에서
type schema.sql | docker exec -i logs-db psql -U postgres -d logs_db

# 테이블 확인
docker exec -it logs-db psql -U postgres -d logs_db -c "\dt"
docker exec -it logs-db psql -U postgres -d logs_db -c "\d logs"
```

**예상 출력:**
```
             List of relations
 Schema | Name | Type  |  Owner
--------+------+-------+----------
 public | logs | table | postgres

Table "public.logs"
    Column     |          Type          | Nullable | Default
---------------+------------------------+----------+---------
 id            | bigint                 | not null | nextval(...)
 created_at    | timestamp with time zone | not null | now()
 level         | log_level              | not null | 'INFO'
 ...
```

---

## 3️⃣ 로그 서버 실행

```bash
# 의존성 설치
cd services/log-server
pip install -r requirements.txt

# 서버 실행
python main.py
```

**예상 출력:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
✅ Database connection pool created
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

**헬스 체크:**
```bash
curl http://localhost:8000/
# {"status":"ok","service":"log-server"}
```

---

## 4️⃣ 클라이언트 테스트

### Python 테스트

```bash
# 라이브러리 설치
cd clients/python
pip install -e .

# 테스트 스크립트 실행
python << 'EOF'
from log_collector import AsyncLogClient
import time

# 클라이언트 생성
client = AsyncLogClient("http://localhost:8000")

print("🚀 로그 전송 시작...")

# 성능 테스트: 10000건 로깅
start = time.time()
for i in range(10000):
    client.log(
        level="INFO",
        message=f"Test log {i}",
        service="test-service",
        log_type="BACKEND",
        trace_id=f"trace_{i % 100}"
    )
elapsed = time.time() - start

print(f"✅ 10000건 로깅 완료")
print(f"   총 시간: {elapsed:.2f}초")
print(f"   처리량: {10000/elapsed:.0f} logs/sec")
print(f"   평균: {elapsed/10000*1000:.3f}ms per log")

# 큐 비우기
print("\n⏳ 큐 비우는 중...")
client.flush()
time.sleep(2)

print("✅ 완료!")
EOF
```

**예상 출력:**
```
🚀 로그 전송 시작...
✅ 10000건 로깅 완료
   총 시간: 0.52초
   처리량: 19231 logs/sec
   평균: 0.052ms per log

⏳ 큐 비우는 중...
[Log Client] Flushing 0 remaining logs...
✅ 완료!
```

---

### JavaScript 테스트 (Node.js)

```bash
# 라이브러리 설치
cd clients/javascript
npm install node-fetch

# 테스트 스크립트 실행
node << 'EOF'
const { createLogClient } = require('./src/index.js');

(async () => {
    const logger = createLogClient('http://localhost:8000');

    console.log('🚀 로그 전송 시작...');

    // 성능 테스트: 10000건 로깅
    const start = Date.now();
    for (let i = 0; i < 10000; i++) {
        logger.info(`Test log ${i}`, {
            service: 'test-service',
            log_type: 'BACKEND',
            trace_id: `trace_${i % 100}`
        });
    }
    const elapsed = (Date.now() - start) / 1000;

    console.log(`✅ 10000건 로깅 완료`);
    console.log(`   총 시간: ${elapsed.toFixed(2)}초`);
    console.log(`   처리량: ${(10000/elapsed).toFixed(0)} logs/sec`);
    console.log(`   평균: ${(elapsed/10000*1000).toFixed(3)}ms per log`);

    // 큐 비우기
    console.log('\n⏳ 큐 비우는 중...');
    logger.flush();
    await new Promise(resolve => setTimeout(resolve, 2000));

    console.log('✅ 완료!');
    await logger.close();
})();
EOF
```

---

## 5️⃣ 결과 확인

### 데이터베이스에서 로그 확인

```bash
# 로그 개수 확인
docker exec -it logs-db psql -U postgres -d logs_db -c \
  "SELECT COUNT(*) FROM logs;"

# 레벨별 개수
docker exec -it logs-db psql -U postgres -d logs_db -c \
  "SELECT level, COUNT(*) FROM logs GROUP BY level;"

# 최근 10개 로그
docker exec -it logs-db psql -U postgres -d logs_db -c \
  "SELECT created_at, level, service, message FROM logs ORDER BY created_at DESC LIMIT 10;"
```

**예상 출력:**
```
 count
-------
 20000
(1 row)

 level | count
-------+-------
 INFO  | 20000
(1 row)
```

### API 통계 확인

```bash
curl http://localhost:8000/stats
```

**예상 출력:**
```json
{
  "total_logs": 20000,
  "level_distribution": [
    {"level": "INFO", "count": 20000}
  ],
  "recent_errors_1h": 0
}
```

---

## 🎉 성공!

전체 시스템이 정상 작동합니다:

- ✅ PostgreSQL: 로그 저장
- ✅ FastAPI 서버: 로그 수신 + gzip 처리
- ✅ Python 클라이언트: 앱 블로킹 < 0.1ms
- ✅ JavaScript 클라이언트: 메인 스레드 렉 0%

---

## 🧹 정리

```bash
# PostgreSQL 중지 및 삭제
docker stop logs-db
docker rm logs-db

# 서버 중지
# Ctrl+C로 FastAPI 서버 종료
```

---

## 🔍 문제 해결

### PostgreSQL 연결 실패

```bash
# PostgreSQL 로그 확인
docker logs logs-db

# 연결 테스트
docker exec -it logs-db psql -U postgres -c "SELECT version();"
```

### 로그 서버 에러

```bash
# 서버 로그 확인
# FastAPI 터미널 출력 확인

# DB 연결 테스트
python -c "import asyncpg; import asyncio; asyncio.run(asyncpg.connect(host='localhost', database='logs_db', user='postgres', password='password'))"
```

### 클라이언트 에러

```bash
# Python: aiohttp 설치 확인
pip list | grep aiohttp

# JavaScript: node-fetch 설치 확인
npm list node-fetch
```
