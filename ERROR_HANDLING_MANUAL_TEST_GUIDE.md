# 에러 핸들링 수동 테스트 가이드

**목적**: 10개 에러 핸들링 개선사항을 실제로 테스트하여 사용자 피드백 확인
**난이도**: ⭐ 쉬움 | ⭐⭐ 보통 | ⭐⭐⭐ 어려움
**예상 시간**: 약 30분

---

## 사전 준비

### 1. 애플리케이션 실행
```bash
# 터미널 1: 백엔드 실행
cd services/log-analysis-server
python -m uvicorn app.main:app --reload

# 터미널 2: 프론트엔드 실행
cd frontend
pnpm dev
```

### 2. 브라우저 준비
- **Chrome/Edge 권장** (DevTools 사용)
- http://localhost:3000 접속
- F12로 DevTools 열기

---

## 프론트엔드 에러 테스트 (5개)

### Test 1: localStorage 저장 실패 ⭐

**목적**: localStorage 에러 시 사용자에게 alert 표시

**방법 1 - 브라우저 저장소 제한**
1. **Chrome 시크릿 모드** (Ctrl+Shift+N) 열기
2. http://localhost:3000 접속
3. F12 → Console 탭
4. 다음 코드 실행:
   ```javascript
   // localStorage를 무효화
   Object.defineProperty(window, 'localStorage', {
     get: function() {
       throw new Error('QuotaExceededError');
     }
   });
   ```
5. 질문 입력: "최근 1시간 에러 로그"
6. 전송 버튼 클릭

**방법 2 - Private 브라우저**
1. Firefox Private Window에서 about:config
2. `dom.storage.enabled` → false
3. http://localhost:3000 접속
4. 질문 제출

**예상 결과**:
- ✅ Console에 "Failed to save history" 에러 표시
- ✅ 화면 우상단에 **빨간색 alert**: "히스토리 저장 실패. 브라우저 저장 공간을 확인해주세요."
- ⏱️ 5초 후 자동으로 사라짐

**스크린샷 위치**: 우상단 alert 영역

---

### Test 2: WebSocket 연결 끊김 ⭐⭐

**목적**: WebSocket 끊김 시 쿼리 전송 차단 및 에러 메시지

**방법 1 - DevTools Network 차단**
1. F12 → Network 탭
2. Filter에서 "WS" 선택 (WebSocket만 표시)
3. WebSocket 연결 확인 (ws://localhost:8001/ws 또는 유사)
4. **Offline** 체크박스 활성화 (또는 Throttling → Offline)
5. 질문 입력: "payment-api 에러"
6. 전송 버튼 클릭

**방법 2 - 백엔드 중지**
1. 터미널에서 Ctrl+C로 log-analysis-server 중지
2. 페이지는 새로고침하지 않음 (WebSocket 끊어짐)
3. 질문 입력 후 전송

**예상 결과**:
- ✅ 채팅창에 **빨간색 에러 메시지**: "WebSocket이 연결되지 않았습니다. 페이지를 새로고침해주세요."
- ✅ 로딩 인디케이터가 즉시 멈춤
- ❌ 쿼리가 전송되지 않음

**스크린샷 위치**: 채팅 메시지 영역

---

### Test 3: 페이지 라우팅 에러 ⭐

**목적**: 라우팅 실패 시 alert 표시 (정상 작동 시에는 발생 안 함)

**방법 1 - History 페이지 정상 동작 확인**
1. 좌측 메뉴에서 "📜 히스토리" 클릭
2. 저장된 쿼리 중 하나의 "재실행" 버튼 클릭
3. 홈으로 돌아오는지 확인

**방법 2 - 라우팅 강제 에러 (고급)**
1. Console에서 svelte-spa-router의 push 함수를 모킹:
   ```javascript
   // 이 방법은 실제로는 작동 안 할 수 있음 (Svelte 내부 스코프)
   window.history.pushState = function() {
     throw new Error('Routing failed');
   };
   ```
2. 히스토리 페이지에서 재실행 클릭

**예상 결과**:
- ✅ 정상: 홈으로 이동, 대화 로드됨
- ⚠️ 에러 시: "페이지 이동 실패. 새로고침 후 다시 시도해주세요." alert

**참고**: 라우팅 에러는 매우 드물어서 정상 작동 확인이면 충분

---

### Test 4: Markdown 파싱 에러 ⭐⭐⭐

**목적**: 잘못된 Markdown 시 1회 알림 표시

**주의**: 백엔드에서 잘못된 markdown을 보내야 함 (테스트 어려움)

**방법 1 - 백엔드 응답 수정 (임시)**
1. `services/log-analysis-server/app/agent/nodes.py` 열기
2. `generate_insight_node` 함수에서 응답에 잘못된 markdown 추가:
   ```python
   # 임시 테스트용
   insight = "**잘못된 markdown [미완성 링크("
   ```
3. 서버 재시작 후 쿼리 제출

**방법 2 - Console 주입 (권장)**
1. 쿼리를 정상적으로 실행
2. 응답이 오면 Console에서:
   ```javascript
   // marked.parse에 잘못된 입력
   marked.parse('**bold [broken link(');
   ```
3. 에러 발생 확인

**예상 결과**:
- ✅ 화면 우상단에 **파란색 info alert**: "일부 텍스트 서식을 표시할 수 없습니다."
- ✅ **1회만** 표시됨 (이후 동일 에러 발생해도 alert 안 뜸)
- ✅ 텍스트는 평문으로 fallback 표시

**스크린샷 위치**: 우상단 alert 영역

---

### Test 5: 새 이벤트 타입 처리 ⭐⭐

**목적**: clarification_failed와 anomaly_check_error 이벤트 처리 확인

#### 5-1. clarification_failed 이벤트

**방법 - DB 에러 시뮬레이션**
1. PostgreSQL 서비스 중지:
   ```bash
   # Windows
   net stop postgresql-x64-13

   # 또는 Docker
   docker-compose stop postgres
   ```
2. 프론트엔드에서 질문 입력: "에러 로그 조회" (서비스 없이)
3. 재질문이 필요한 쿼리 → 서비스 목록 조회 실패

**예상 결과**:
- ✅ 채팅창에 **빨간색 에러**: "❌ 재질문 생성 실패: 서비스 목록 조회 실패..."
- ✅ 로딩 멈춤

#### 5-2. anomaly_check_error 이벤트

**방법 - 백그라운드 이상 탐지 에러**
1. PostgreSQL 중지 (위와 동일)
2. 5분 대기 (백그라운드 작업 실행 주기)
3. 또는 서버 로그 확인:
   ```bash
   # 서버 터미널에서
   # "Anomaly check failed" 에러 확인
   ```

**예상 결과**:
- ✅ 화면 우상단에 **노란색 warning alert**: "이상 탐지 실패: 데이터베이스 연결 오류"
- ✅ 백그라운드에서 자동으로 발생 (사용자 액션 필요 없음)

**참고**: PostgreSQL 다시 시작:
```bash
net start postgresql-x64-13
# 또는
docker-compose start postgres
```

---

## 백엔드 에러 테스트 (5개)

### Test 6: alerting_service 에러 → Alert 전환 ⭐⭐

**목적**: 이상 탐지 실패 시 alert 이벤트 반환 (None 대신)

**방법**:
1. PostgreSQL 중지
2. 5분 대기 또는 alerting_service를 강제로 트리거
3. 서버 로그 확인

**예상 결과**:
- ✅ 서버 로그: "Anomaly check failed: ..." (ERROR 레벨)
- ✅ WebSocket으로 alert 전송
- ✅ 프론트엔드에 alert 표시

**서버 로그 예시**:
```
ERROR: Anomaly check failed: connection to server failed
```

---

### Test 7: retrieve_schema_node 예외 처리 ⭐⭐

**목적**: 스키마 조회 실패 시 에러 이벤트 반환

**방법**:
1. PostgreSQL 중지
2. 새 쿼리 제출: "최근 에러 로그"
3. 스키마 조회 단계에서 실패

**예상 결과**:
- ✅ 서버 로그: "Schema retrieval failed: ..." (ERROR 레벨)
- ✅ 프론트엔드 채팅창: **에러 메시지** (스키마 조회 실패 관련)
- ✅ 작업 히스토리에서 "retrieve_schema" 단계 실패 표시

**프론트엔드 예상 메시지**:
```
❌ 에러가 발생했습니다: 스키마 조회 실패...
```

---

### Test 8: clarifier DB 에러 처리 ⭐⭐

**목적**: 재질문 생성 시 DB 에러 발생 → clarification_failed 이벤트

**방법**:
1. PostgreSQL 중지
2. 재질문이 필요한 쿼리 제출: "에러 로그 조회" (서비스 명시 안 함)
3. 서비스 목록 조회 실패

**예상 결과**:
- ✅ 서버 로그: "Clarification failed: 서비스 목록 조회 실패..." (ERROR 레벨)
- ✅ 프론트엔드: "❌ 재질문 생성 실패: 서비스 목록 조회 실패..."
- ✅ 쿼리 진행 중단

---

### Test 9: broadcast_alert 로깅 개선 ⭐

**목적**: Alert 브로드캐스트 통계 로깅 확인

**방법**:
1. 여러 브라우저 탭에서 http://localhost:3000 열기 (3~4개)
2. PostgreSQL 중지
3. 5분 대기 (백그라운드 anomaly check)
4. 또는 한 탭에서 에러 유발

**예상 결과**:
- ✅ 서버 로그에 브로드캐스트 통계:
  ```
  INFO: Alert broadcast complete: 3 success, 0 failed, 3 active connections
  ```
- ✅ 각 탭에서 alert 수신 확인

**확인 방법**:
- 서버 터미널에서 "Alert broadcast complete" 로그 검색

---

### Test 10: cache_service 로깅 추가 ⭐

**목적**: 캐시 실패 시 warning 로그 기록

**방법 1 - 캐시 에러 강제 발생 (어려움)**
1. 코드 임시 수정:
   ```python
   # cache_service.py의 get() 또는 set()에 임시로 에러 추가
   async def get(self, key: str) -> Optional[dict]:
       raise Exception("Test cache error")
   ```
2. 쿼리 제출
3. 서버 로그 확인

**방법 2 - 정상 동작 확인**
1. 동일한 쿼리를 2번 연속 실행:
   - "payment-api 최근 1시간 에러"
2. 서버 로그에서 캐시 관련 로그 확인

**예상 결과**:
- ✅ 정상: 로그 없음 (캐시 정상 작동)
- ⚠️ 에러 시: "Cache get failed for key '...': ..." (WARNING 레벨)
- ✅ LRU 제거 시: "Cache evicted oldest entry: ..." (DEBUG 레벨)

---

## SQL 검증 에러 테스트 (보너스) ⭐

**목적**: 위험한 SQL 키워드 차단 확인

### 위험한 쿼리 테스트

각 쿼리를 순서대로 테스트:

1. **DELETE 차단**
   - 입력: `DELETE FROM logs WHERE id = 1`
   - 예상: "❌ SQL 검증 실패: Dangerous keyword detected: DELETE"

2. **UPDATE 차단**
   - 입력: `UPDATE logs SET level = 'INFO'`
   - 예상: "❌ SQL 검증 실패: Dangerous keyword detected: UPDATE"

3. **DROP 차단**
   - 입력: `DROP TABLE logs`
   - 예상: "❌ SQL 검증 실패: Dangerous keyword detected: DROP"

4. **INSERT 차단**
   - 입력: `INSERT INTO logs VALUES (1, 'test')`
   - 예상: "❌ SQL 검증 실패: Dangerous keyword detected: INSERT"

5. **ALTER 차단**
   - 입력: `ALTER TABLE logs ADD COLUMN test VARCHAR`
   - 예상: "❌ SQL 검증 실패: Dangerous keyword detected: ALTER"

6. **비-SELECT 시작 차단**
   - 입력: `TRUNCATE TABLE logs`
   - 예상: "❌ SQL 검증 실패: Only SELECT queries are allowed"

### 안전한 쿼리 테스트

1. **정상 SELECT**
   - 입력: `SELECT * FROM logs WHERE level = 'ERROR' LIMIT 10`
   - 예상: ✅ 정상 실행

2. **deleted 필터 누락 (옛날 검증)**
   - 입력: `SELECT * FROM logs WHERE service = 'payment-api'`
   - 예상: 현재는 자동으로 deleted = FALSE 추가됨 (검증 통과)

---

## 테스트 체크리스트

### 프론트엔드 (5개)

- [ ] **Test 1**: localStorage 에러 → alert 표시
- [ ] **Test 2**: WebSocket 끊김 → 에러 메시지
- [ ] **Test 3**: 라우팅 정상 동작 확인
- [ ] **Test 4**: Markdown 파싱 에러 → 1회 alert
- [ ] **Test 5-1**: clarification_failed 이벤트 처리
- [ ] **Test 5-2**: anomaly_check_error 이벤트 처리

### 백엔드 (5개)

- [ ] **Test 6**: alerting_service 에러 → alert 반환
- [ ] **Test 7**: schema 조회 실패 → 에러 이벤트
- [ ] **Test 8**: clarifier DB 에러 → 에러 이벤트
- [ ] **Test 9**: broadcast_alert 통계 로깅
- [ ] **Test 10**: cache 실패 로깅

### SQL 검증 (보너스)

- [ ] DELETE 키워드 차단
- [ ] UPDATE 키워드 차단
- [ ] DROP 키워드 차단
- [ ] INSERT 키워드 차단
- [ ] ALTER 키워드 차단
- [ ] 정상 SELECT 통과

---

## 팁 & 트러블슈팅

### Alert가 안 보이는 경우
1. **너무 빨리 사라짐**: 화면을 계속 주시하거나 스크린 녹화
2. **위치 확인**: 화면 **우상단** 고정 위치
3. **Console 확인**: alert 생성 로그 확인

### WebSocket 에러가 안 나는 경우
1. **재연결 확인**: WebSocket은 자동 재연결 시도 (3회)
2. **완전 차단**: Network 탭에서 WS 연결을 직접 차단
3. **백엔드 중지**: 가장 확실한 방법

### PostgreSQL 중지/시작
```bash
# Windows 서비스
net stop postgresql-x64-13
net start postgresql-x64-13

# Docker
docker-compose stop postgres
docker-compose start postgres

# 상태 확인
docker-compose ps
```

### 로그 확인 방법
```bash
# 백엔드 로그 실시간 확인
# 터미널에서 uvicorn 실행 시 자동으로 표시됨

# 특정 에러 검색
# Ctrl+F로 "ERROR", "WARNING", "failed" 검색
```

---

## 예상 소요 시간

| 테스트 그룹 | 예상 시간 |
|------------|----------|
| 프론트엔드 5개 | 15분 |
| 백엔드 5개 | 10분 |
| SQL 검증 보너스 | 5분 |
| **총합** | **30분** |

---

## 테스트 성공 기준

✅ **통과**:
- 모든 에러 시나리오에서 **사용자에게 보이는 피드백** 확인
- Console이 아닌 **UI에 표시**되는 메시지/alert
- 서버 로그에 적절한 레벨(ERROR/WARNING)로 기록

⚠️ **주의**:
- Alert는 5초 후 자동으로 사라짐 (놓치지 않도록)
- PostgreSQL 중지 후 반드시 다시 시작
- 테스트 중 브라우저 캐시가 영향 줄 수 있음 (Ctrl+Shift+R로 새로고침)

---

## 문제 발생 시

1. **에러가 표시 안 됨**: 코드 재확인, 브라우저 새로고침
2. **서버 크래시**: 코드 문법 에러 확인, 서버 재시작
3. **WebSocket 끊김 안 됨**: 완전히 서버 중지 또는 Network 차단

모든 테스트를 완료하면 **MANUAL_TEST_RESULTS.md** 파일을 작성하여 결과를 기록하세요!
