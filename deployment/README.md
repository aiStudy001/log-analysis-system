# 프로덕션 배포 가이드

프로덕션 환경에서 서버를 분리하여 배포하는 가이드입니다.

---

## 아키텍처

```
서버 A (저장 서버)          서버 B (분석 서버)
├── PostgreSQL             └── log-analysis-server
└── log-save-server              ↓
        ↓                   (원격 DB 접속)
   (로컬 DB)                      ↓
                            Server A:5432
```

**네트워크:**
```
클라이언트 → Server A:8000 (로그 저장)
관리자     → Server B:8001 (Text-to-SQL 분석)
```

---

## Server A: 로그 저장 서버

### 배포

```bash
# 1. 서버 A에 접속
ssh user@server-a.example.com

# 2. 프로젝트 클론
git clone <repository-url>
cd log-analysis-system/deployment/server-a

# 3. 환경 변수 설정
cp .env.example .env
vim .env
# POSTGRES_PASSWORD 수정

# 4. 실행
docker-compose up -d

# 5. 확인
docker-compose ps
docker logs log-save-server
```

### 방화벽 설정

```bash
# PostgreSQL 포트 (Server B IP만 허용)
sudo ufw allow from <server-b-ip> to any port 5432

# 로그 저장 API (모든 클라이언트 허용)
sudo ufw allow 8000/tcp

# 설정 확인
sudo ufw status
```

---

## Server B: 로그 분석 서버

### 배포

```bash
# 1. 서버 B에 접속
ssh user@server-b.example.com

# 2. 프로젝트 클론
git clone <repository-url>
cd log-analysis-system/deployment/server-b

# 3. 환경 변수 설정
cp .env.example .env
vim .env
# DB_SERVER_A_HOST를 Server A IP로 변경
# LLM API 키 설정

# 4. 실행
docker-compose up -d

# 5. 확인
docker-compose ps
docker logs log-analysis-server
```

### DB 연결 테스트

```bash
# Server B에서 Server A의 DB에 연결 테스트
docker exec log-analysis-server python -c "
import asyncpg
import asyncio
asyncio.run(asyncpg.connect(
    host='<server-a-ip>',
    database='logs_db',
    user='postgres',
    password='las1092*'
))
print('✅ DB 연결 성공!')
"
```

---

## 환경 변수 설정

### Server A (.env)

```bash
POSTGRES_USER=postgres
POSTGRES_PASSWORD=las1092*
POSTGRES_DB=logs_db
```

### Server B (.env)

```bash
# Server A 정보
DB_SERVER_A_HOST=10.0.1.5           # ← Server A의 IP
DB_SERVER_A_PORT=5432

POSTGRES_USER=postgres
POSTGRES_PASSWORD=las1092*
POSTGRES_DB=logs_db

# LLM 설정
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...
LLM_PROVIDER=openai
```

---

## 테스트

### Server A 테스트 (로그 저장)

```bash
# 로그 저장 API 테스트
curl -X POST http://server-a.example.com:8000/logs \
  -H "Content-Type: application/json" \
  -d '{
    "logs": [
      {
        "level": "INFO",
        "message": "Test log from production",
        "service": "test-service"
      }
    ]
  }'

# 예상 응답:
{"status":"ok","count":1}
```

### Server B 테스트 (Text-to-SQL)

```bash
# 분석 API 테스트
curl -X POST http://server-b.example.com:8001/query \
  -H "Content-Type: application/json" \
  -d '{
    "question": "최근 1시간 에러 로그",
    "max_results": 10
  }'

# 예상 응답:
{
  "sql": "SELECT * FROM logs WHERE level='ERROR' ...",
  "results": [...],
  "count": 10,
  "execution_time_ms": 45.2
}
```

---

## 모니터링

### 헬스 체크

```bash
# Server A
curl http://server-a.example.com:8000/
# {"status":"ok","service":"log-server"}

# Server B
curl http://server-b.example.com:8001/
# {"status":"ok","service":"log-analysis-server"}
```

### 로그 확인

```bash
# Server A
docker-compose logs -f log-save-server

# Server B
docker-compose logs -f log-analysis-server
```

### 리소스 모니터링

```bash
docker stats
```

---

## 업데이트

### Server A

```bash
cd deployment/server-a
git pull
docker-compose build
docker-compose up -d
```

### Server B

```bash
cd deployment/server-b
git pull
docker-compose build
docker-compose up -d
```

---

## 백업

### PostgreSQL 백업 (Server A)

```bash
# 백업
docker exec log-analysis-db pg_dump -U postgres logs_db > backup.sql

# 복원
docker exec -i log-analysis-db psql -U postgres logs_db < backup.sql
```

---

## 문제 해결

### Server B가 DB에 연결 못 함

```bash
# 1. 방화벽 확인 (Server A)
sudo ufw status

# 2. PostgreSQL 로그 확인 (Server A)
docker logs log-analysis-db

# 3. 네트워크 연결 테스트 (Server B)
telnet <server-a-ip> 5432
```

### 성능 이슈

```bash
# DB 연결 풀 증가 (Server A)
# docker-compose.yml에서
DB_POOL_MAX_SIZE: 50  # 기본값 20
```

---

## 보안 체크리스트

- [ ] Server A 방화벽: PostgreSQL은 Server B IP만 허용
- [ ] Server B 방화벽: 8001 포트는 관리자 IP만 허용
- [ ] .env 파일 권한: `chmod 600 .env`
- [ ] PostgreSQL 인증: scram-sha-256 사용
- [ ] API Key 환경 변수로 관리 (코드에 하드코딩 금지)
- [ ] SSL/TLS 적용 (선택사항)

---

## 로컬 테스트 (배포 전)

프로덕션 배포 전에 로컬에서 분리 구조를 테스트할 수 있습니다.

### 1. Server A 시뮬레이션

```bash
cd deployment/server-a
cp .env.example .env
docker-compose up -d
```

### 2. Server B 시뮬레이션

```bash
cd deployment/server-b
cp .env.example .env

# .env 수정
DB_SERVER_A_HOST=host.docker.internal  # Mac/Windows
# 또는
DB_SERVER_A_HOST=172.17.0.1           # Linux

docker-compose up -d
```

### 3. 테스트

```bash
# Server A (저장)
curl -X POST http://localhost:8000/logs -H "Content-Type: application/json" -d '{"logs":[{"level":"INFO","message":"test"}]}'

# Server B (분석)
curl -X POST http://localhost:8001/query -H "Content-Type: application/json" -d '{"question":"최근 로그"}'
```

---

## 참고

- 개발/테스트: 루트의 `docker-compose.yml` 사용
- 프로덕션: `deployment/server-a`, `deployment/server-b` 사용
