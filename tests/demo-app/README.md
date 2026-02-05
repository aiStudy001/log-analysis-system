# Todo App - Log Collector Demo

간단한 Todo 앱을 통해 `log-client-async` 패키지의 모든 기능을 테스트합니다.

## 📋 테스트 기능

이 데모에서 테스트할 수 있는 기능:
- ✅ 기본 로그 전송 (INFO, WARN, ERROR)
- ✅ HTTP 컨텍스트 자동 수집 (path, method, ip)
- ✅ 사용자 컨텍스트 (user_id, trace_id)
- ✅ 분산 추적 (trace_id를 통한 요청 추적)
- ✅ 타이머 기능 (duration_ms)
- ✅ 에러 스택 추적 (errorWithTrace)
- ✅ 호출 위치 자동 추적 (function_name, file_path)
- ✅ 글로벌 에러 핸들러 (모든 에러 자동 로깅) - **NEW!**

---

## 🚀 실행 방법

### 1단계: 로그 서버 실행

```bash
# 로그 서버 디렉토리로 이동
cd services/log-save-server

# 서버 실행 (포트 8000)
python main.py
```

**확인**: `http://localhost:8000/` 접속 시 "Log Save Server is running" 메시지 확인

---

### 2단계: Backend 실행

```bash
# Backend 디렉토리로 이동
cd tests/demo-app/backend

# 패키지 설치
npm install

# 서버 실행 (포트 3001)
npm start
```

**확인**: 콘솔에 다음 메시지 출력
```
✅ 로거 초기화 완료
============================================================
✅ Todo Backend Server running on http://localhost:3001
============================================================
```

---

### 3단계: Frontend 실행

```bash
# Frontend 디렉토리로 이동
cd tests/demo-app/frontend

# 브라우저에서 index.html 열기 (빌드 불필요)
# 방법 1: 직접 브라우저로 드래그&드롭
# 방법 2: Live Server 사용 (VSCode Extension)
```

**확인**: 브라우저에서 로그인 화면 표시

---

## 🧪 테스트 시나리오

### 자동 테스트 (권장)
1. 로그인 후 "🚀 전체 기능 테스트" 버튼 클릭
2. 자동으로 모든 클라이언트 기능을 순차적으로 테스트
3. 콘솔에서 테스트 결과 확인

**테스트 항목**:
- Todo 추가
- Todo 리스트 조회
- Todo 완료 토글
- Todo 삭제
- 에러 처리
- 타이머 기능

---

### 개별 테스트 버튼

**🚀 전체 기능 테스트**: 모든 클라이언트 기능을 자동으로 테스트
**❌ 에러 테스트**: 에러 로깅 및 스택 추적 테스트
**⏱️ 타이머 테스트**: duration_ms 자동 계산 테스트
**📦 배치 로그 테스트**: 100개 로그 일괄 전송 (배치 처리 확인)
**🔍 분산 추적 테스트**: trace_id를 통한 요청 추적
**📊 로그 레벨 테스트**: INFO, WARN, ERROR 레벨 테스트

---

### 1. 로그인 테스트
1. Username: `demo`
2. Password: `demo123`
3. 로그인 버튼 클릭

**확인할 로그**:
- `Login attempt` (INFO)
- `Login successful` (INFO)
- HTTP 컨텍스트: `path=/api/login`, `method=POST`

---

### 2. Todo CRUD 테스트

**Todo 추가**:
1. "새 할 일 입력..." 필드에 텍스트 입력
2. "추가" 버튼 클릭

**Todo 완료 토글**:
1. Todo 항목의 체크박스 클릭

**Todo 삭제**:
1. Todo 항목의 "삭제" 버튼 클릭

**확인할 로그**:
- `Todo created` (INFO) - metadata에 todo_id, text 포함
- `Todo updated` (INFO) - metadata에 completed 상태 포함
- `Todo deleted` (INFO) - metadata에 삭제된 todo 정보 포함
- 모든 요청에 `user_id`와 `trace_id` 컨텍스트 포함

---

### 3. 에러 테스트
1. "❌ 에러 테스트" 버튼 클릭

**확인할 로그**:
- `Error endpoint called` (WARN)
- `Intentional error occurred` (ERROR) - stack_trace 포함
- HTTP 컨텍스트: `path=/api/error`, `method=GET`

---

### 4. 타이머 테스트 (duration_ms)
1. "⏱️ 타이머 테스트" 버튼 클릭
2. 2초 대기

**확인할 로그**:
- `Slow API called` (INFO)
- `Slow API completed` (INFO) - metadata에 `duration_ms ≈ 2000` 포함
- 요청 완료 로그에 `duration_ms` 포함

---

### 5. 배치 로그 테스트
1. "📦 배치 로그 테스트" 버튼 클릭
2. 100개의 로그가 빠르게 전송됨

**확인할 로그**:
- `Batch log 1` ~ `Batch log 100` (INFO)
- 로그 서버가 배치로 받아서 처리
- 모든 로그가 순서대로 저장됨

---

### 6. 분산 추적 테스트 (trace_id)
1. "🔍 분산 추적 테스트" 버튼 클릭
2. 여러 API가 동일한 trace_id로 호출됨

**확인할 로그**:
- 동일 trace_id를 가진 여러 요청 로그
- trace_id로 필터링하면 전체 요청 흐름 추적 가능

---

### 7. 로그 레벨 테스트
1. "📊 로그 레벨 테스트" 버튼 클릭

**확인할 로그**:
- INFO, WARN, ERROR 레벨의 로그 각각 전송
- 각 레벨에 맞는 메타데이터 포함

---

## 📊 로그 확인 방법

### PostgreSQL에서 직접 확인

```sql
-- 전체 로그 확인
SELECT
    created_at,
    level,
    message,
    function_name,
    file_path,
    metadata->>'user_id' as user_id,
    metadata->>'trace_id' as trace_id,
    metadata->>'duration_ms' as duration_ms,
    stack_trace
FROM logs
WHERE service = 'demo-todo-backend'
ORDER BY created_at DESC
LIMIT 20;
```

### 특정 기능별 로그 확인

**1. 로그인 로그**:
```sql
SELECT created_at, level, message, metadata
FROM logs
WHERE service = 'demo-todo-backend'
  AND message LIKE '%Login%'
ORDER BY created_at DESC;
```

**2. Todo 작업 로그**:
```sql
SELECT created_at, level, message,
       metadata->>'todo_id' as todo_id,
       metadata->>'text' as text
FROM logs
WHERE service = 'demo-todo-backend'
  AND message LIKE '%Todo%'
ORDER BY created_at DESC;
```

**3. 에러 로그 (스택 추적 포함)**:
```sql
SELECT created_at, level, message, stack_trace
FROM logs
WHERE service = 'demo-todo-backend'
  AND level = 'ERROR'
ORDER BY created_at DESC;
```

**4. 타이머 로그 (duration_ms)**:
```sql
SELECT created_at, message,
       metadata->>'duration_ms' as duration_ms
FROM logs
WHERE service = 'demo-todo-backend'
  AND metadata->>'duration_ms' IS NOT NULL
ORDER BY created_at DESC;
```

**5. 분산 추적 (동일 trace_id)**:
```sql
-- 특정 trace_id의 전체 요청 추적
SELECT created_at, level, message,
       metadata->>'path' as path,
       metadata->>'method' as method
FROM logs
WHERE service = 'demo-todo-backend'
  AND metadata->>'trace_id' = '여기에_trace_id_입력'
ORDER BY created_at ASC;
```

**6. HTTP 컨텍스트 확인**:
```sql
SELECT created_at, message,
       metadata->>'path' as path,
       metadata->>'method' as method,
       metadata->>'ip' as ip,
       metadata->>'status_code' as status_code
FROM logs
WHERE service = 'demo-todo-backend'
  AND metadata->>'path' IS NOT NULL
ORDER BY created_at DESC;
```

---

## 🔍 자동 수집 필드 확인

`log-client-async` 패키지가 자동으로 수집하는 필드들:

| 필드 | 설명 | 예시 값 |
|------|------|---------|
| `function_name` | 로그를 호출한 함수 이름 | `outerFunction` |
| `file_path` | 로그를 호출한 파일 경로 | `C:\...\server.js` |
| `created_at` | 로그 생성 시간 | `2025-02-03 10:30:45` |
| `service` | 서비스 이름 | `demo-todo-backend` |
| `environment` | 환경 | `development` |
| `metadata.path` | HTTP 요청 경로 | `/api/todos` |
| `metadata.method` | HTTP 메소드 | `POST` |
| `metadata.ip` | 클라이언트 IP | `::1` |
| `metadata.user_id` | 사용자 ID | `user_demo` |
| `metadata.trace_id` | 분산 추적 ID | `abc123...` |
| `metadata.duration_ms` | 실행 시간 | `2005` |
| `stack_trace` | 에러 스택 (에러 시) | `Error: This is...` |

---

## 🎯 예상 결과

### 로그 서버 콘솔
```
✅ Database connection pool created
✅ Received 1 logs (service: demo-todo-backend)
✅ Received 5 logs (service: demo-todo-backend)
✅ Received 2 logs (service: demo-todo-backend)
...
```

### Backend 콘솔
```
✅ 로거 초기화 완료
...
```

### PostgreSQL 로그 수
```sql
-- 최소 예상 로그 수
SELECT COUNT(*) FROM logs WHERE service = 'demo-todo-backend';
-- 로그인 1회 + Todo 작업 3회 + 에러 테스트 + 느린 API = 약 15~20개 로그
```

---

## ❓ 문제 해결

### Backend가 시작되지 않을 때
```bash
# 포트 확인
netstat -ano | findstr :3001

# 포트 사용 중이면 서버 종료 후 재시작
taskkill /F /PID <PID>
```

### Frontend에서 로그인이 안될 때
- Backend 서버가 실행 중인지 확인 (`http://localhost:3001`)
- CORS 에러 확인 (F12 콘솔)
- Username: `demo`, Password: `demo123` 정확히 입력

### 로그가 DB에 저장되지 않을 때
1. 로그 서버 실행 확인 (`http://localhost:8000/`)
2. PostgreSQL 실행 확인
3. Backend 콘솔에서 에러 메시지 확인

---

## 📝 테스트 체크리스트

**환경 설정**:
- [ ] 로그 서버 실행 (포트 8000)
- [ ] Backend 실행 (포트 3001 - JavaScript 또는 3002 - Python)
- [ ] Frontend 열기 (index.html 또는 index-python.html)
- [ ] 로그인 성공 (demo / demo123)

**자동 테스트**:
- [ ] "🚀 전체 기능 테스트" 버튼 클릭
- [ ] 콘솔에서 테스트 결과 확인 (통과/실패)

**개별 기능 테스트**:
- [ ] Todo 추가 (수동)
- [ ] Todo 완료 토글 (수동)
- [ ] Todo 삭제 (수동)
- [ ] "❌ 에러 테스트" 버튼 클릭
- [ ] "⏱️ 타이머 테스트" 버튼 클릭
- [ ] "📦 배치 로그 테스트" 버튼 클릭
- [ ] "🔍 분산 추적 테스트" 버튼 클릭
- [ ] "📊 로그 레벨 테스트" 버튼 클릭

**데이터베이스 검증**:
- [ ] PostgreSQL에서 로그 확인
- [ ] HTTP 컨텍스트 포함 확인 (path, method, ip)
- [ ] 사용자 컨텍스트 포함 확인 (user_id, trace_id)
- [ ] trace_id로 분산 추적 확인
- [ ] duration_ms 필드 확인
- [ ] stack_trace 필드 확인 (에러 로그)
- [ ] function_name, file_path 자동 수집 확인
- [ ] 배치 처리 확인 (100개 로그가 순서대로 저장됨)

**자동 에러 로깅 검증**:
- [ ] 브라우저 콘솔에서 임의의 에러 발생 (예: `throw new Error("test")`)
- [ ] PostgreSQL에서 해당 에러 로그 확인
- [ ] stack_trace가 자동으로 수집되었는지 확인

---

## 🔥 자동 에러 로깅 기능

Frontend에 **글로벌 에러 핸들러**가 활성화되어 있어 모든 에러가 자동으로 로깅됩니다.

이 기능은 클라이언트 라이브러리의 `enableGlobalErrorHandler` 옵션으로 제어됩니다:

```javascript
// 데모에서 사용 중인 설정
const logger = new SimpleLogger({
    enableGlobalErrorHandler: true  // 모든 에러 자동 로깅
});
```

### 자동으로 처리되는 에러 유형

**1. Uncaught Errors (동기 에러)**
```javascript
// 이런 에러들이 자동으로 로깅됨
undefined.someMethod();  // TypeError
JSON.parse('invalid');   // SyntaxError
throw new Error('test'); // Custom Error
```

**2. Unhandled Promise Rejections (비동기 에러)**
```javascript
// 이런 에러들도 자동으로 로깅됨
fetch('/invalid-url');  // Network Error
Promise.reject('error'); // Promise Rejection
async function() { throw new Error(); }  // Async Error
```

### 자동 로깅 내용

에러가 발생하면 다음 정보가 자동으로 로그 서버에 전송됩니다:
- 에러 메시지 (`message`)
- 발생 위치 (`source`, `line`, `column`)
- 스택 추적 (`stack`)
- 타임스탬프 (`created_at`)
- 서비스 정보 (`service`, `environment`)

### 테스트 방법

**브라우저 콘솔에서 테스트**:
```javascript
// 1. 동기 에러 테스트
throw new Error("Manual error test");

// 2. 비동기 에러 테스트
Promise.reject(new Error("Promise rejection test"));

// 3. 네트워크 에러 테스트
fetch('http://invalid-url-12345.com/api');
```

**확인**:
1. 브라우저 콘솔에서 에러 발생 확인
2. PostgreSQL에서 자동으로 저장된 에러 로그 확인:
```sql
SELECT created_at, level, message, metadata
FROM logs
WHERE service LIKE 'demo-todo-frontend%'
  AND level = 'ERROR'
ORDER BY created_at DESC
LIMIT 10;
```

### 기존 try-catch와의 차이

**기존 방식** (수동 로깅):
```javascript
try {
    someDangerousOperation();
} catch (err) {
    logger.error('Operation failed', { error: err.message });  // 수동 로깅
}
```

**자동 에러 로깅** (추가 코드 불필요):
```javascript
someDangerousOperation();  // 에러 발생 시 자동으로 로깅됨
```

단, 중요한 비즈니스 로직이나 특정 에러 처리가 필요한 경우에는 여전히 try-catch를 사용하고 명시적으로 로깅하는 것을 권장합니다.

---

## 🎉 완료!

모든 체크리스트가 완료되면 `log-client-async` 패키지의 모든 기능이 정상 동작하는 것입니다.

추가 질문이나 문제가 있으면 이슈를 등록해주세요.
