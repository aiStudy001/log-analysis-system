# 환경 변수 자동 설정 가이드

클라이언트 라이브러리의 환경 변수 자동 로드 기능 사용법

---

## 🎯 개요

**문제점:**
- 매번 클라이언트 초기화 시 `service`, `environment`, `serviceVersion` 등을 수동 입력
- 환경별로 설정을 변경하기 어려움
- 코드에 하드코딩된 설정 값

**해결책:**
- `.env` 파일에서 자동으로 읽기
- `package.json`에서 서비스 정보 자동 추출 (JavaScript)
- 환경 변수 우선순위 시스템

---

## 📋 환경 변수 우선순위

### Python

```
1. 코드에서 명시적으로 전달한 값
2. 환경 변수 (.env 파일 또는 시스템 환경 변수)
3. 기본값
```

### JavaScript (Node.js)

```
1. 코드에서 명시적으로 전달한 값
2. 환경 변수 (process.env)
3. package.json (name, version 필드)
4. 기본값
```

### JavaScript (브라우저)

```
1. 코드에서 명시적으로 전달한 값
2. 빌드 시점 환경 변수 (REACT_APP_*, VUE_APP_*, VITE_*)
3. 기본값
```

---

## 🐍 Python 사용법

### 1. 환경 변수 설정

**`.env` 파일 생성:**

```bash
cd clients/python
cp .env.example .env
```

**`.env` 파일 내용:**

```env
LOG_SERVER_URL=http://localhost:8000
SERVICE_NAME=payment-api
ENVIRONMENT=production
SERVICE_VERSION=v1.2.3
LOG_TYPE=BACKEND
```

---

### 2. 사용 예시

#### 기본 사용 (환경 변수에서 자동 로드)

```python
from log_collector import AsyncLogClient

# .env 파일에서 모든 설정 자동 로드
client = AsyncLogClient()

# 다음과 동일:
# client = AsyncLogClient(
#     server_url="http://localhost:8000",  # ← LOG_SERVER_URL에서 읽음
#     service="payment-api",                # ← SERVICE_NAME에서 읽음
#     environment="production",             # ← ENVIRONMENT에서 읽음
#     service_version="v1.2.3",             # ← SERVICE_VERSION에서 읽음
#     log_type="BACKEND"                    # ← LOG_TYPE에서 읽음
# )

# 로그 전송 시 자동으로 service, environment 등이 포함됨
client.info("Payment processed", amount=100.50)
```

#### 부분 재정의 (환경 변수 + 명시적 값)

```python
# .env의 대부분 설정을 사용하되, 일부만 재정의
client = AsyncLogClient(
    environment="staging",  # ← .env의 ENVIRONMENT 무시하고 staging 사용
    batch_size=500          # ← 배치 크기만 변경
)

# 다른 설정은 .env에서 자동 로드됨:
# - server_url: LOG_SERVER_URL
# - service: SERVICE_NAME
# - service_version: SERVICE_VERSION
# - log_type: LOG_TYPE
```

#### 모든 값 명시적 지정 (환경 변수 무시)

```python
# 환경 변수를 완전히 무시하고 모든 값 지정
client = AsyncLogClient(
    server_url="https://logs.company.com",
    service="special-service",
    environment="test",
    service_version="v2.0.0",
    log_type="WORKER"
)
```

---

### 3. 환경별 설정 관리

#### 개발 환경

```bash
# .env.development
LOG_SERVER_URL=http://localhost:8000
ENVIRONMENT=development
SERVICE_VERSION=v0.0.0-dev
```

#### 프로덕션 환경

```bash
# .env.production
LOG_SERVER_URL=https://logs.company.com
ENVIRONMENT=production
SERVICE_VERSION=v1.2.3
```

#### 사용 방법

```bash
# 개발 환경
cp .env.development .env
python app.py

# 프로덕션 환경
cp .env.production .env
python app.py
```

또는 환경 변수로 직접 지정:

```bash
# 프로덕션 배포
export ENVIRONMENT=production
export LOG_SERVER_URL=https://logs.company.com
python app.py
```

---

## 🌐 JavaScript 사용법

### Node.js 환경

#### 1. 환경 변수 설정

**`.env` 파일 생성:**

```bash
cd clients/javascript
cp .env.example .env
```

**`.env` 파일 내용:**

```env
LOG_SERVER_URL=http://localhost:8000
SERVICE_NAME=payment-api
NODE_ENV=production
SERVICE_VERSION=v1.2.3
LOG_TYPE=BACKEND
```

#### 2. package.json 활용

**`package.json`:**

```json
{
  "name": "my-awesome-api",
  "version": "2.1.0",
  "description": "My API service"
}
```

#### 3. 사용 예시

##### 자동 로드 (환경 변수 + package.json)

```javascript
import { createLogClient } from 'log-collector';

// 자동으로 다음 순서로 읽음:
// 1. .env의 LOG_SERVER_URL
// 2. .env의 SERVICE_NAME (없으면 package.json의 name)
// 3. .env의 NODE_ENV
// 4. .env의 SERVICE_VERSION (없으면 package.json의 version)
const logger = createLogClient();

// 결과:
// {
//   serverUrl: "http://localhost:8000",      // ← LOG_SERVER_URL
//   service: "payment-api",                  // ← SERVICE_NAME (또는 package.json name)
//   environment: "production",               // ← NODE_ENV
//   serviceVersion: "v1.2.3",                // ← SERVICE_VERSION (또는 package.json version)
//   logType: "BACKEND"                       // ← LOG_TYPE
// }
```

##### 부분 재정의

```javascript
// 대부분은 자동 로드, 일부만 변경
const logger = createLogClient(null, {
    environment: 'staging',  // ← NODE_ENV 무시
    batchSize: 500
});
```

##### .env가 없을 때 (package.json만 사용)

```javascript
// .env 파일이 없어도 package.json에서 자동으로 읽음
const logger = createLogClient('http://localhost:8000');

// 자동으로 적용:
// - service: package.json의 name
// - serviceVersion: package.json의 version
```

---

### 브라우저 환경

#### 1. 빌드 도구별 환경 변수 설정

##### Vite (추천)

**`.env` 파일:**

```env
VITE_LOG_SERVER_URL=http://localhost:8000
VITE_SERVICE_NAME=web-app
VITE_ENVIRONMENT=production
VITE_SERVICE_VERSION=v2.1.0
VITE_LOG_TYPE=FRONTEND
```

**사용:**

```javascript
import { createLogClient } from 'log-collector';

// 자동으로 import.meta.env에서 읽음
const logger = createLogClient();
```

##### React (Create React App)

**`.env` 파일:**

```env
REACT_APP_LOG_SERVER_URL=http://localhost:8000
REACT_APP_SERVICE_NAME=web-app
REACT_APP_ENVIRONMENT=production
REACT_APP_SERVICE_VERSION=v2.1.0
REACT_APP_LOG_TYPE=FRONTEND
```

**사용:**

```javascript
import { createLogClient } from 'log-collector';

// 자동으로 process.env에서 읽음
const logger = createLogClient();
```

##### Vue CLI

**`.env` 파일:**

```env
VUE_APP_LOG_SERVER_URL=http://localhost:8000
VUE_APP_SERVICE_NAME=web-app
VUE_APP_ENVIRONMENT=production
VUE_APP_SERVICE_VERSION=v2.1.0
VUE_APP_LOG_TYPE=FRONTEND
```

**사용:**

```javascript
import { createLogClient } from 'log-collector';

// 자동으로 process.env에서 읽음
const logger = createLogClient();
```

---

#### 2. 환경별 빌드

##### Vite

```bash
# 개발 환경 (.env.development)
npm run dev

# 프로덕션 환경 (.env.production)
npm run build

# 스테이징 환경 (.env.staging)
vite build --mode staging
```

##### React

```bash
# 개발 환경
npm start

# 프로덕션 빌드
npm run build

# 커스텀 환경
REACT_APP_ENVIRONMENT=staging npm run build
```

---

## 📊 환경 변수 매핑표

### Python

| 환경 변수 | 파라미터 | 기본값 | 설명 |
|----------|---------|--------|------|
| `LOG_SERVER_URL` | `server_url` | `http://localhost:8000` | 로그 서버 URL |
| `SERVICE_NAME` | `service` | `None` | 서비스 이름 |
| `ENVIRONMENT` | `environment` | `development` | 환경 (production, staging 등) |
| `SERVICE_VERSION` | `service_version` | `v0.0.0-dev` | 서비스 버전 |
| `LOG_TYPE` | `log_type` | `BACKEND` | 로그 타입 |

---

### JavaScript (Node.js)

| 환경 변수 | 파라미터 | Fallback | 기본값 | 설명 |
|----------|---------|----------|--------|------|
| `LOG_SERVER_URL` | `serverUrl` | - | `http://localhost:8000` | 로그 서버 URL |
| `SERVICE_NAME` | `service` | `package.json` name | `null` | 서비스 이름 |
| `NODE_ENV` | `environment` | - | `development` | 환경 |
| `SERVICE_VERSION` | `serviceVersion` | `package.json` version | `v0.0.0-dev` | 서비스 버전 |
| `LOG_TYPE` | `logType` | - | `BACKEND` | 로그 타입 |

---

### JavaScript (브라우저)

| 환경 변수 (Vite) | 환경 변수 (React) | 환경 변수 (Vue) | 파라미터 | 기본값 |
|-----------------|------------------|----------------|---------|--------|
| `VITE_LOG_SERVER_URL` | `REACT_APP_LOG_SERVER_URL` | `VUE_APP_LOG_SERVER_URL` | `serverUrl` | `http://localhost:8000` |
| `VITE_SERVICE_NAME` | `REACT_APP_SERVICE_NAME` | `VUE_APP_SERVICE_NAME` | `service` | `null` |
| `VITE_ENVIRONMENT` | `REACT_APP_ENVIRONMENT` | `VUE_APP_ENVIRONMENT` | `environment` | `development` |
| `VITE_SERVICE_VERSION` | `REACT_APP_SERVICE_VERSION` | `VUE_APP_SERVICE_VERSION` | `serviceVersion` | `v0.0.0-dev` |
| `VITE_LOG_TYPE` | `REACT_APP_LOG_TYPE` | `VUE_APP_LOG_TYPE` | `logType` | `FRONTEND` |

---

## 🚀 실전 예시

### Python - FastAPI 서비스

**`.env`:**

```env
LOG_SERVER_URL=https://logs.company.com
SERVICE_NAME=payment-api
ENVIRONMENT=production
SERVICE_VERSION=v1.2.3
LOG_TYPE=BACKEND
```

**`app.py`:**

```python
from fastapi import FastAPI
from log_collector import AsyncLogClient

app = FastAPI()

# 환경 변수에서 자동 로드 - 설정 불필요!
logger = AsyncLogClient()

@app.post("/charge")
async def charge_payment(amount: float):
    with logger.timer("Payment processing"):
        result = process_payment(amount)
        logger.info("Payment successful", amount=amount, transaction_id=result.id)
        return result
```

---

### JavaScript - Express 서비스

**`package.json`:**

```json
{
  "name": "user-api",
  "version": "2.1.0"
}
```

**`.env`:**

```env
LOG_SERVER_URL=http://localhost:8000
NODE_ENV=production
LOG_TYPE=BACKEND
```

**`server.js`:**

```javascript
import express from 'express';
import { createLogClient } from 'log-collector';

const app = express();

// 자동으로 package.json과 .env에서 로드
// service: "user-api" (← package.json name)
// serviceVersion: "2.1.0" (← package.json version)
// environment: "production" (← NODE_ENV)
const logger = createLogClient();

app.post('/users', async (req, res) => {
    const timer = logger.startTimer();

    try {
        const user = await createUser(req.body);
        logger.endTimer(timer, 'INFO', 'User created', { user_id: user.id });
        res.json(user);
    } catch (err) {
        logger.errorWithTrace('User creation failed', err);
        res.status(500).json({ error: err.message });
    }
});
```

---

### React - 웹 앱

**`.env.production`:**

```env
REACT_APP_LOG_SERVER_URL=https://logs.company.com
REACT_APP_SERVICE_NAME=web-app
REACT_APP_ENVIRONMENT=production
REACT_APP_SERVICE_VERSION=v3.0.0
REACT_APP_LOG_TYPE=FRONTEND
```

**`src/logger.js`:**

```javascript
import { createLogClient } from 'log-collector';

// 빌드 시점에 .env.production에서 자동 주입
export const logger = createLogClient();
```

**`src/App.jsx`:**

```javascript
import { logger } from './logger';
import { useEffect } from 'react';

function App() {
    useEffect(() => {
        logger.info('App mounted', { page: '/' });
    }, []);

    const handleLogin = async () => {
        const timer = logger.startTimer();

        try {
            await login(username, password);
            logger.endTimer(timer, 'INFO', 'Login successful', { username });
        } catch (err) {
            logger.errorWithTrace('Login failed', err, { username });
        }
    };

    return <div>...</div>;
}
```

---

## 🔧 트러블슈팅

### Q1: 환경 변수가 로드되지 않음 (Python)

**원인:**
- `python-dotenv` 패키지가 설치되지 않음
- `.env` 파일 위치가 잘못됨

**해결:**

```bash
# python-dotenv 설치
pip install python-dotenv

# .env 파일 위치 확인 (프로젝트 루트)
ls .env
```

---

### Q2: package.json을 읽지 못함 (Node.js)

**원인:**
- `package.json`이 현재 디렉토리에 없음
- 읽기 권한 문제

**해결:**

```bash
# package.json 확인
cat package.json

# 명시적으로 서비스 정보 제공
const logger = createLogClient('http://localhost:8000', {
    service: 'my-service',
    serviceVersion: 'v1.0.0'
});
```

---

### Q3: 브라우저에서 환경 변수가 적용되지 않음

**원인:**
- 빌드 도구별 prefix가 틀림 (`REACT_APP_`, `VUE_APP_`, `VITE_`)
- `.env` 파일 수정 후 재빌드 안 함

**해결:**

```bash
# Vite
VITE_LOG_SERVER_URL=... (O)
LOG_SERVER_URL=... (X)

# React
REACT_APP_LOG_SERVER_URL=... (O)
LOG_SERVER_URL=... (X)

# .env 수정 후 반드시 재빌드
npm run build
```

---

### Q4: 환경 변수 우선순위 확인

**Python:**

```python
import os
from log_collector import AsyncLogClient

# 환경 변수 확인
print(f"LOG_SERVER_URL: {os.getenv('LOG_SERVER_URL')}")
print(f"SERVICE_NAME: {os.getenv('SERVICE_NAME')}")

# 클라이언트 설정 확인
client = AsyncLogClient()
print(f"server_url: {client.server_url}")
print(f"service: {client.service}")
```

**JavaScript:**

```javascript
// 환경 변수 확인
console.log('LOG_SERVER_URL:', process.env.LOG_SERVER_URL);
console.log('package.json name:', require('./package.json').name);

// 클라이언트 설정 확인
const logger = createLogClient();
console.log('serverUrl:', logger.serverUrl);
console.log('service:', logger.service);
```

---

## 📝 권장 사항

### 1. 프로덕션 배포

- ✅ 환경 변수는 시스템 환경 변수로 설정 (`.env` 파일 제외)
- ✅ `.env` 파일은 `.gitignore`에 추가
- ✅ `.env.example`은 Git에 포함

**`.gitignore`:**

```
.env
.env.local
.env.*.local
```

---

### 2. 개발 환경

- ✅ `.env.example`을 복사해서 `.env` 생성
- ✅ 로컬 설정은 `.env.local` 사용 (Git 제외)

---

### 3. CI/CD

**GitHub Actions 예시:**

```yaml
env:
  LOG_SERVER_URL: ${{ secrets.LOG_SERVER_URL }}
  SERVICE_NAME: my-service
  ENVIRONMENT: production
  SERVICE_VERSION: ${{ github.ref_name }}
```

---

## 🎯 다음 단계

- [CLIENT-LIBRARIES.md](./CLIENT-LIBRARIES.md) - API 사용법 및 예제
- [CODE-EXPLANATION.md](./CODE-EXPLANATION.md) - 코드 상세 설명
- [TESTING-GUIDE.md](./TESTING-GUIDE.md) - 테스트 방법
- [DEPLOYMENT-GUIDE.md](./DEPLOYMENT-GUIDE.md) - 배포 가이드
