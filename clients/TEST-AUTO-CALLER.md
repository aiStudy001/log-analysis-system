# Auto Caller 기능 테스트 가이드

호출 위치 자동 추적(`auto_caller`) 기능 테스트 방법

---

## ✅ 추가된 테스트

### Python 테스트 (`tests/test_async_client.py`)

| 테스트 함수 | 검증 내용 |
|-----------|----------|
| `test_auto_caller_enabled` | auto_caller=True 시 function_name, file_path, line_number 자동 추출 |
| `test_auto_caller_disabled` | auto_caller=False 시 자동 추출 비활성화 |
| `test_auto_caller_manual_override` | 수동으로 전달한 값이 우선 적용되는지 확인 |
| `test_convenience_methods_auto_caller` | info(), debug() 등 편의 메서드에서 자동 추출 |
| `test_nested_function_auto_caller` | 중첩 함수에서 올바른 함수명 추출 |

### JavaScript 테스트 (`__tests__/client.test.js`)

| 테스트 | 검증 내용 |
|-------|----------|
| `should not throw error with auto caller enabled` | 기본 동작 확인 |
| `should handle autoCaller disabled` | autoCaller=false 옵션 |
| `should handle manual function_name override` | 수동 재정의 |
| `all convenience methods should work with auto caller` | 편의 메서드 동작 |
| `should handle nested function calls` | 중첩 함수 |
| `should handle async functions` | async/await 지원 |
| `should handle arrow functions` | 화살표 함수 |
| `performance with auto caller should still be fast` | 성능 영향 확인 |

### Python 통합 테스트 (`tests/test_integration.py`)

| 테스트 함수 | 검증 내용 |
|-----------|----------|
| `test_auto_caller_integration` | E2E: 서버로 전송되고 에러 없이 처리됨 |
| `test_auto_caller_disabled_integration` | auto_caller=False로 전송 |
| `test_timer_with_auto_caller` | 타이머 기능과 함께 동작 |
| `test_error_with_trace_integration` | error_with_trace와 함께 동작 |

---

## 🚀 테스트 실행

### 1. Python 단위 테스트 (서버 불필요)

```bash
cd clients/python

# 개발 모드 설치
pip install -e ".[dev]"

# 모든 단위 테스트 실행
pytest tests/test_async_client.py -v

# auto_caller 관련 테스트만 실행
pytest tests/test_async_client.py -v -k "auto_caller"
```

**예상 출력:**
```
tests/test_async_client.py::test_auto_caller_enabled PASSED
tests/test_async_client.py::test_auto_caller_disabled PASSED
tests/test_async_client.py::test_auto_caller_manual_override PASSED
tests/test_async_client.py::test_convenience_methods_auto_caller PASSED
tests/test_async_client.py::test_nested_function_auto_caller PASSED
```

---

### 2. JavaScript 단위 테스트 (서버 불필요)

```bash
cd clients/javascript

# 패키지 설치
npm install

# 모든 테스트 실행
npm test

# auto caller 관련 테스트만 실행
npm test -- --testNamePattern="Auto Caller"
```

**예상 출력:**
```
 PASS  __tests__/client.test.js
  Auto Caller Feature
    ✓ should not throw error with auto caller enabled (default) (3 ms)
    ✓ should handle autoCaller disabled (2 ms)
    ✓ should handle manual function_name override (2 ms)
    ✓ all convenience methods should work with auto caller (3 ms)
    ✓ should handle nested function calls (2 ms)
    ✓ should handle async functions (5 ms)
    ✓ should handle arrow functions (2 ms)
    ✓ performance with auto caller should still be fast (45 ms)

Test Suites: 1 passed, 1 total
Tests:       8 passed, 8 total
```

---

### 3. Python 통합 테스트 (서버 필요)

#### 서버 환경 준비

```bash
# 터미널 1: Docker Compose로 환경 실행
cd ../../  # 프로젝트 루트
docker-compose up -d

# 서버 실행 확인
curl http://localhost:8000/
# 응답: {"status":"ok","service":"log-server"}
```

#### 통합 테스트 실행

```bash
# 터미널 2
cd clients/python

# 통합 테스트 실행
pytest tests/test_integration.py -v

# auto_caller 관련 통합 테스트만 실행
pytest tests/test_integration.py -v -k "auto_caller"
```

**예상 출력:**
```
tests/test_integration.py::test_auto_caller_integration PASSED
tests/test_integration.py::test_auto_caller_disabled_integration PASSED
tests/test_integration.py::test_timer_with_auto_caller PASSED
tests/test_integration.py::test_error_with_trace_integration PASSED
```

---

## 🔍 실제 DB 데이터 검증

통합 테스트 후 PostgreSQL에서 직접 확인:

```bash
# PostgreSQL 접속
psql -h localhost -p 5433 -U postgres -d logs_db
```

### 1. auto_caller 기능 검증

```sql
-- 자동 추출된 function_name, file_path, line_number 확인
SELECT
    function_name,
    file_path,
    line_number,
    message,
    created_at
FROM logs
WHERE metadata->>'test_id' = 'auto_caller_integration'
ORDER BY created_at DESC
LIMIT 10;
```

**예상 결과:**
```
 function_name              | file_path                    | line_number | message
---------------------------+------------------------------+-------------+---------------------------
 test_auto_caller_integration | /app/tests/test_integration.py | 165      | Auto caller test - line 1
 test_auto_caller_integration | /app/tests/test_integration.py | 166      | Auto caller test - line 2
 test_auto_caller_integration | /app/tests/test_integration.py | 167      | Auto caller test - line 3
 helper_function            | /app/tests/test_integration.py | 171      | Message from helper function
```

---

### 2. 편의 메서드 검증

```sql
-- 편의 메서드(info, debug 등)에서도 올바른 함수명 추출되는지 확인
SELECT
    level,
    function_name,
    message
FROM logs
WHERE metadata->>'test_id' = 'auto_caller_integration'
ORDER BY created_at;
```

**예상 결과:**
```
 level | function_name              | message
-------+---------------------------+---------------------------
 INFO  | test_auto_caller_integration | Auto caller test - line 1
 DEBUG | test_auto_caller_integration | Auto caller test - line 2
 WARN  | test_auto_caller_integration | Auto caller test - line 3
 INFO  | helper_function            | Message from helper function
```

---

### 3. error_with_trace 검증

```sql
-- stack_trace와 함께 function_name, file_path 추출되는지 확인
SELECT
    error_type,
    function_name,
    file_path,
    LEFT(stack_trace, 100) as stack_trace_preview,
    message
FROM logs
WHERE metadata->>'test_id' = 'error_trace_integration'
ORDER BY created_at DESC
LIMIT 1;
```

**예상 결과:**
```
 error_type | function_name                  | file_path                    | stack_trace_preview
-----------+-------------------------------+------------------------------+----------------------
 ValueError | test_error_with_trace_integration | /app/tests/test_integration.py | Traceback (most recent call last):
  File "/app/tests/test_integration.py"...
```

---

### 4. auto_caller=False 검증

```sql
-- auto_caller=False 시 function_name이 없는지 확인
SELECT
    function_name,
    file_path,
    message
FROM logs
WHERE metadata->>'test_id' = 'auto_caller_disabled'
ORDER BY created_at DESC
LIMIT 1;
```

**예상 결과:**
```
 function_name | file_path | message
--------------+-----------+---------------------------
              |           | Auto caller disabled test
```

(function_name과 file_path가 NULL 또는 빈 값)

---

## 📊 성능 테스트

### Python 성능 측정

```bash
cd clients/python

# 성능 테스트 실행
pytest tests/test_performance.py -v -s
```

**auto_caller 활성화 시 오버헤드 확인:**
- auto_caller=True: ~0.06ms per log
- auto_caller=False: ~0.05ms per log
- 차이: ~0.01ms (20% 증가, 절대값 매우 작음)

---

### JavaScript 성능 측정

```bash
cd clients/javascript

# 성능 테스트 포함 실행
npm test
```

**콘솔 출력에서 확인:**
```
Performance with auto caller: 0.015ms per call
```

---

## ✅ 테스트 체크리스트

### 단위 테스트 (서버 불필요)

- [ ] Python: `pytest tests/test_async_client.py -v -k "auto_caller"`
- [ ] JavaScript: `npm test -- --testNamePattern="Auto Caller"`
- [ ] 모든 테스트 PASSED 확인

### 통합 테스트 (서버 필요)

- [ ] Docker Compose 실행: `docker-compose up -d`
- [ ] 서버 확인: `curl http://localhost:8000/`
- [ ] Python 통합 테스트: `pytest tests/test_integration.py -v -k "auto_caller"`
- [ ] 모든 테스트 PASSED 확인

### DB 검증 (선택)

- [ ] PostgreSQL 접속
- [ ] `test_id='auto_caller_integration'` 데이터 조회
- [ ] function_name, file_path, line_number 확인

### 성능 테스트 (선택)

- [ ] Python 성능: `pytest tests/test_performance.py -v -s`
- [ ] JavaScript 성능: `npm test` (콘솔 출력 확인)
- [ ] 오버헤드 < 0.02ms 확인

---

## 🐛 트러블슈팅

### Q1: 테스트 실패 - "module 'log_collector' has no attribute 'AsyncLogClient'"

**원인:** 패키지가 설치되지 않음

**해결:**
```bash
cd clients/python
pip install -e ".[dev]"
```

---

### Q2: 통합 테스트 스킵 - "로그 서버가 실행되지 않았습니다"

**원인:** 로그 서버가 실행되지 않음

**해결:**
```bash
# Docker Compose 사용
docker-compose up -d

# 또는 수동 실행
cd services/log-save-server
python main.py
```

---

### Q3: PostgreSQL 접속 실패

**원인:** 포트 번호 불일치

**해결:**
```bash
# Docker Compose는 5433 포트 사용
psql -h localhost -p 5433 -U postgres -d logs_db

# 수동 실행은 5432 포트 사용
psql -h localhost -p 5432 -U postgres -d logs_db
```

---

### Q4: JavaScript 테스트 실패 - "Cannot find module"

**원인:** `node_modules` 설치 안 됨

**해결:**
```bash
cd clients/javascript
npm install
```

---

## 📝 다음 단계

테스트가 모두 통과하면:

1. **로컬 테스트 프로젝트 생성** - 실제 사용 시나리오 검증
2. **배포** - PyPI/npm에 패키지 업로드
3. **배포된 패키지 테스트** - 실제 설치 후 동작 확인

---

## 📚 관련 문서

- [AUTO-CALLER-EXAMPLE.md](./AUTO-CALLER-EXAMPLE.md) - 사용 가이드
- [FIELD-AUTO-COLLECTION.md](./FIELD-AUTO-COLLECTION.md) - 자동 수집 필드 분석
- [TESTING-GUIDE.md](./TESTING-GUIDE.md) - 전체 테스트 가이드
