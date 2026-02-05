# 호출 위치 자동 추적 사용 가이드

일반 로그에서 `function_name`, `file_path`, `line_number` 자동 수집 기능

---

## ✅ 구현 완료

### 자동 수집되는 필드

| 필드 | 설명 | 예시 |
|-----|------|------|
| `function_name` | 로그를 호출한 함수 이름 | `"process_payment"` |
| `file_path` | 로그를 호출한 파일 경로 | `"/app/api.py"` |
| `line_number` | 로그를 호출한 라인 번호 | `45` |

---

## 🐍 Python 사용 예시

### Before (수동 전달)

```python
from log_collector import AsyncLogClient

client = AsyncLogClient("http://localhost:8000")

def process_payment(user_id, amount):
    # 수동으로 function_name, file_path 전달 필요
    client.info(
        "Payment processing started",
        function_name="process_payment",  # ← 수동
        file_path="/app/api.py",          # ← 수동
        user_id=user_id,
        amount=amount
    )

    # ... 결제 처리 로직
```

---

### After (자동 추적) ⭐

```python
from log_collector import AsyncLogClient

client = AsyncLogClient("http://localhost:8000")

def process_payment(user_id, amount):
    # 자동으로 function_name, file_path, line_number 추출!
    client.info("Payment processing started", user_id=user_id, amount=amount)

    # 전송되는 로그:
    # {
    #   "level": "INFO",
    #   "message": "Payment processing started",
    #   "function_name": "process_payment",     ← 자동!
    #   "file_path": "/app/api.py",             ← 자동!
    #   "line_number": 7,                       ← 자동!
    #   "user_id": "user123",
    #   "amount": 100.50,
    #   "service": "payment-api",
    #   "environment": "production"
    # }

    # ... 결제 처리 로직
```

---

### 편의 메서드 사용

```python
def create_user(username, email):
    # 모든 편의 메서드에서 자동 추적
    client.debug("Creating user", username=username)
    # ← function_name="create_user", file_path="/app/users.py", line_number=12

    user = User(username=username, email=email)
    user.save()

    client.info("User created successfully", user_id=user.id)
    # ← function_name="create_user", file_path="/app/users.py", line_number=17

    return user
```

---

### 비활성화 (성능 최적화)

```python
# 고빈도 로그에서 성능이 중요한 경우
def high_frequency_operation():
    for i in range(100000):
        # auto_caller=False로 자동 추적 비활성화
        client.log("DEBUG", f"Processing {i}", auto_caller=False)
```

---

## 🌐 JavaScript 사용 예시

### Node.js

#### Before (수동 전달)

```javascript
import { createLogClient } from 'log-collector';

const logger = createLogClient('http://localhost:8000');

function processPayment(userId, amount) {
    // 수동으로 전달 필요
    logger.info('Payment processing started', {
        function_name: 'processPayment',  // ← 수동
        file_path: '/app/api.js',          // ← 수동
        user_id: userId,
        amount: amount
    });

    // ... 결제 처리 로직
}
```

---

#### After (자동 추적) ⭐

```javascript
import { createLogClient } from 'log-collector';

const logger = createLogClient('http://localhost:8000');

function processPayment(userId, amount) {
    // 자동으로 function_name, file_path, line_number 추출!
    logger.info('Payment processing started', {
        user_id: userId,
        amount: amount
    });

    // 전송되는 로그:
    // {
    //   level: "INFO",
    //   message: "Payment processing started",
    //   function_name: "processPayment",      ← 자동!
    //   file_path: "/app/api.js",             ← 자동!
    //   line_number: 7,                       ← 자동!
    //   user_id: "user123",
    //   amount: 100.50,
    //   service: "payment-api",
    //   environment: "production"
    // }

    // ... 결제 처리 로직
}
```

---

#### async 함수에서도 동작

```javascript
async function fetchUserData(userId) {
    logger.debug('Fetching user data', { user_id: userId });
    // ← function_name="fetchUserData", file_path="/app/users.js", line_number=12

    const user = await db.users.findById(userId);

    logger.info('User data fetched', { user_id: userId, username: user.name });
    // ← function_name="fetchUserData", file_path="/app/users.js", line_number=16

    return user;
}
```

---

#### 비활성화 (성능 최적화)

```javascript
function highFrequencyOperation() {
    for (let i = 0; i < 100000; i++) {
        // autoCaller: false로 자동 추적 비활성화
        logger.log('DEBUG', `Processing ${i}`, { autoCaller: false });
    }
}
```

---

### 브라우저

```javascript
import { createLogClient } from 'log-collector';

const logger = createLogClient('http://localhost:8000');

function handleButtonClick() {
    logger.info('Button clicked');
    // 자동 포함:
    // {
    //   function_name: "handleButtonClick",
    //   file_path: "http://localhost:3000/static/js/main.js",
    //   line_number: 45
    // }

    // ... 클릭 처리 로직
}

// React 컴포넌트에서
function LoginForm() {
    const handleSubmit = (e) => {
        e.preventDefault();

        logger.info('Login form submitted', { username: e.target.username.value });
        // 자동 포함:
        // {
        //   function_name: "handleSubmit",
        //   file_path: "http://localhost:3000/static/js/LoginForm.js",
        //   line_number: 12
        // }
    };

    return <form onSubmit={handleSubmit}>...</form>;
}
```

---

## 📊 성능 영향

### 오버헤드 측정

**Python:**
- auto_caller=True: ~0.06ms per log
- auto_caller=False: ~0.05ms per log
- 차이: ~0.01ms (20% 증가, 절대값 매우 작음)

**JavaScript:**
- autoCaller=true: ~0.015ms per log
- autoCaller=false: ~0.010ms per log
- 차이: ~0.005ms (50% 증가, 절대값 매우 작음)

### 권장 사항

✅ **대부분의 경우 활성화 유지 (기본값)**
- 디버깅 편의성이 성능 손실보다 훨씬 큼
- 절대 시간이 매우 작아서 실질적 영향 미미

⚠️ **다음 경우에만 비활성화 고려**
- 초당 10,000+ 로그를 생성하는 고빈도 로깅
- 마이크로초 단위 성능이 중요한 실시간 시스템
- 프로파일링 결과 로깅이 병목으로 확인된 경우

---

## 🎯 실전 활용

### 1. 에러 디버깅

```python
def calculate_discount(price, discount_rate):
    logger.debug("Calculating discount", price=price, rate=discount_rate)
    # ← function_name="calculate_discount", file_path="/app/pricing.py", line_number=123

    if discount_rate > 1.0:
        logger.error("Invalid discount rate", rate=discount_rate)
        # ← function_name="calculate_discount", file_path="/app/pricing.py", line_number=126
        # 에러 발생 위치를 정확히 알 수 있음!
        raise ValueError("Discount rate must be <= 1.0")

    return price * (1 - discount_rate)
```

**로그 분석 시:**
```sql
-- 에러가 발생한 함수와 파일을 즉시 파악
SELECT function_name, file_path, line_number, message, COUNT(*)
FROM logs
WHERE level = 'ERROR'
GROUP BY function_name, file_path, line_number, message
ORDER BY COUNT(*) DESC;

-- 결과:
-- calculate_discount | /app/pricing.py | 126 | Invalid discount rate | 1523
-- process_payment    | /app/api.py     | 45  | Payment failed       | 234
```

---

### 2. 성능 프로파일링

```python
def slow_operation():
    logger.info("Starting slow operation")
    # ← function_name="slow_operation", line_number=10

    with client.timer("Database query"):
        # ← function_name="slow_operation", line_number=13
        result = db.query("SELECT * FROM large_table")

    logger.info("Finished slow operation")
    # ← function_name="slow_operation", line_number=17

    return result
```

**분석:**
```sql
-- 어느 함수에서 가장 많은 시간을 소비하는지 확인
SELECT function_name, file_path, AVG(duration_ms) as avg_duration
FROM logs
WHERE duration_ms IS NOT NULL
GROUP BY function_name, file_path
ORDER BY avg_duration DESC;

-- 결과:
-- slow_operation | /app/tasks.py | 1523.45
-- process_batch  | /app/batch.py | 892.12
```

---

### 3. 호출 흐름 추적

```python
def create_order(user_id, items):
    logger.info("Creating order", user_id=user_id)
    # ← function_name="create_order"

    order = Order.create(user_id=user_id)

    for item in items:
        add_order_item(order.id, item)
        # ← 내부에서 logger.info() 호출 시 function_name="add_order_item"

    send_confirmation_email(user_id, order.id)
    # ← 내부에서 logger.info() 호출 시 function_name="send_confirmation_email"

    logger.info("Order created", order_id=order.id)
    # ← function_name="create_order"

    return order

def add_order_item(order_id, item):
    logger.debug("Adding order item", order_id=order_id, item_id=item['id'])
    # ← function_name="add_order_item" (자동으로 올바른 함수명)
    OrderItem.create(order_id=order_id, **item)

def send_confirmation_email(user_id, order_id):
    logger.info("Sending confirmation email", user_id=user_id, order_id=order_id)
    # ← function_name="send_confirmation_email" (자동으로 올바른 함수명)
    email_service.send(user_id, "order_confirmation", order_id=order_id)
```

**로그 분석:**
```sql
-- 특정 주문의 호출 흐름 확인
SELECT created_at, function_name, message
FROM logs
WHERE metadata->>'order_id' = '12345'
ORDER BY created_at;

-- 결과:
-- 2024-01-15 10:30:00 | create_order              | Creating order
-- 2024-01-15 10:30:01 | add_order_item            | Adding order item
-- 2024-01-15 10:30:02 | add_order_item            | Adding order item
-- 2024-01-15 10:30:03 | send_confirmation_email   | Sending confirmation email
-- 2024-01-15 10:30:04 | create_order              | Order created
```

---

## 🔍 비교: 에러 로깅 vs 일반 로깅

### 에러 로깅 (error_with_trace)

```python
try:
    result = risky_operation()
except Exception as e:
    client.error_with_trace("Operation failed", exception=e)
    # 자동 포함:
    # - stack_trace: 전체 스택 추적 (여러 함수 호출 경로)
    # - error_type: Exception 타입
    # - function_name: 에러 발생 함수
    # - file_path: 에러 발생 파일
    # - line_number: 에러 발생 라인 (stack trace 내)
```

---

### 일반 로깅 (info, debug 등)

```python
def my_function():
    client.info("Normal operation")
    # 자동 포함:
    # - function_name: 로그 호출 함수 (my_function)
    # - file_path: 로그 호출 파일
    # - line_number: 로그 호출 라인 (현재 라인)
    # stack_trace는 포함되지 않음 (에러가 아니므로)
```

---

## 📝 주의사항

### 1. 익명 함수

```javascript
// 익명 함수는 function_name이 "anonymous"로 표시됨
setTimeout(() => {
    logger.info('Timeout completed');
    // function_name: "anonymous" 또는 빈 문자열
}, 1000);

// 이름 있는 함수 사용 권장
setTimeout(function handleTimeout() {
    logger.info('Timeout completed');
    // function_name: "handleTimeout"
}, 1000);
```

---

### 2. 압축/난독화된 코드

```javascript
// 프로덕션 빌드 (압축된 코드)
function a(){logger.info("Test")}  // ← function_name: "a"

// 개발 빌드 (원본 코드)
function processPayment(){logger.info("Test")}  // ← function_name: "processPayment"
```

**권장:** source map을 사용하거나 개발 모드에서 디버깅

---

### 3. 수동 재정의

```python
# 자동 추적된 값을 수동으로 재정의 가능
def internal_helper():
    client.info(
        "Helper called",
        function_name="main_function",  # ← 수동 재정의
        custom_field="value"
    )
    # function_name이 "main_function"으로 저장됨 (실제는 internal_helper)
```

---

## 🎓 권장 사항

### ✅ 활성화 유지 (기본값)

- 대부분의 애플리케이션
- 디버깅이 자주 필요한 환경
- 개발 및 스테이징 환경

### 🟡 선택적 비활성화

- 초고빈도 로깅 (10K+ logs/sec)
- 성능이 매우 중요한 실시간 시스템
- 프로파일링으로 병목 확인된 경우만

### ❌ 비활성화 불필요

- 일반적인 웹 애플리케이션
- 마이크로서비스 (평균 100-1000 logs/sec)
- 배치 작업

---

## 🚀 다음 단계

1. ✅ **호출 위치 자동 추적** (완료)
2. 🔜 **HTTP 경로 자동 수집** (Flask, FastAPI, Express 통합)
3. 🔜 **사용자 컨텍스트 관리** (user_id, trace_id)

---

## 📚 관련 문서

- [CODE-EXPLANATION.md](./CODE-EXPLANATION.md) - 코드 상세 설명
- [FIELD-AUTO-COLLECTION.md](./FIELD-AUTO-COLLECTION.md) - 자동 수집 필드 분석
- [ENV-CONFIG-GUIDE.md](./ENV-CONFIG-GUIDE.md) - 환경 변수 설정
- [CLIENT-LIBRARIES.md](./CLIENT-LIBRARIES.md) - API 사용법
