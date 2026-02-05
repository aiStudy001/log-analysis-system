#!/usr/bin/env python3
"""
테스트 로그 데이터 생성 스크립트
- 1000개의 다양한 로그 생성
- 실제 로그 분석 쿼리에 적합한 데이터
"""

import requests
import random
from datetime import datetime, timedelta
import time

# API 엔드포인트
API_URL = "http://13.60.221.13:8000/logs"

# 서비스 목록
SERVICES = [
    "auth-service",
    "user-service",
    "payment-service",
    "order-service",
    "notification-service",
    "inventory-service",
    "api-gateway",
    "analytics-service"
]

# 로그 레벨 분포 (실제 환경과 유사하게)
LOG_LEVELS = {
    "INFO": 0.6,      # 60%
    "WARN": 0.25,     # 25%
    "ERROR": 0.12,    # 12%
    "DEBUG": 0.03     # 3%
}

# 시나리오별 메시지 템플릿
SCENARIOS = {
    "auth-service": {
        "INFO": [
            "User login successful - user_id: {user_id}",
            "Password reset email sent to user {user_id}",
            "JWT token generated for user {user_id}",
            "OAuth authentication completed for user {user_id}",
            "Session created for user {user_id}",
        ],
        "WARN": [
            "Failed login attempt for user {user_id} - invalid password",
            "Rate limit warning for IP {ip} - {count} attempts",
            "Session timeout for user {user_id}",
            "Token refresh required for user {user_id}",
        ],
        "ERROR": [
            "Authentication failed - database connection timeout",
            "JWT token validation failed for user {user_id}",
            "OAuth provider unreachable - timeout after 30s",
            "Redis session store unavailable",
        ]
    },
    "payment-service": {
        "INFO": [
            "Payment processed successfully - order_id: {order_id}, amount: ${amount}",
            "Refund initiated for order {order_id}",
            "Payment method verified for user {user_id}",
            "Transaction {transaction_id} completed",
        ],
        "WARN": [
            "Payment gateway slow response - {duration}ms",
            "Retry payment for order {order_id} - attempt {attempt}/3",
            "Duplicate payment attempt detected for order {order_id}",
        ],
        "ERROR": [
            "Payment failed for order {order_id} - insufficient funds",
            "Payment gateway connection failed",
            "Transaction {transaction_id} rolled back due to error",
            "Card validation failed for user {user_id}",
        ]
    },
    "order-service": {
        "INFO": [
            "Order {order_id} created by user {user_id}",
            "Order {order_id} shipped - tracking: {tracking}",
            "Order {order_id} delivered successfully",
            "Order status updated to PROCESSING",
        ],
        "WARN": [
            "Low inventory warning for product {product_id}",
            "Order {order_id} delayed - estimated delay: {delay} hours",
            "Address validation issue for order {order_id}",
        ],
        "ERROR": [
            "Failed to create order - inventory service unavailable",
            "Order {order_id} cancelled due to payment failure",
            "Database deadlock detected while processing order {order_id}",
        ]
    },
    "user-service": {
        "INFO": [
            "User {user_id} registered successfully",
            "Profile updated for user {user_id}",
            "Email verified for user {user_id}",
            "User preferences saved",
        ],
        "WARN": [
            "Duplicate email registration attempt: {email}",
            "Profile image size exceeds limit for user {user_id}",
            "Inactive user cleanup scheduled for {count} users",
        ],
        "ERROR": [
            "Failed to send verification email to user {user_id}",
            "User data sync failed with external service",
            "Profile update failed - validation error",
        ]
    },
    "api-gateway": {
        "INFO": [
            "Request routed to {service} - method: {method}, path: {path}",
            "API key validated successfully",
            "Response time: {response_time}ms",
        ],
        "WARN": [
            "High latency detected - {response_time}ms for {endpoint}",
            "Rate limit approaching for API key {api_key}",
            "Circuit breaker opened for {service}",
        ],
        "ERROR": [
            "Service {service} unreachable - timeout after {timeout}s",
            "Invalid API key used - request rejected",
            "Gateway overload - request queue at {queue_size}",
        ]
    }
}

def get_weighted_level():
    """가중치 기반 로그 레벨 선택"""
    rand = random.random()
    cumulative = 0
    for level, weight in LOG_LEVELS.items():
        cumulative += weight
        if rand <= cumulative:
            return level
    return "INFO"

def generate_log_data(count=1000):
    """테스트 로그 데이터 생성"""
    logs = []

    # 시간 분산 (최근 24시간)
    now = datetime.now()

    for i in range(count):
        # 랜덤 시간 (최근 24시간 내)
        hours_ago = random.uniform(0, 24)
        timestamp = now - timedelta(hours=hours_ago)

        # 서비스 선택
        service = random.choice(SERVICES)

        # 로그 레벨 선택
        level = get_weighted_level()

        # 메시지 생성
        if service in SCENARIOS and level in SCENARIOS[service]:
            template = random.choice(SCENARIOS[service][level])

            # 플레이스홀더 치환
            message = template.format(
                service=service,
                user_id=f"user_{random.randint(1000, 9999)}",
                order_id=f"ORD-{random.randint(10000, 99999)}",
                transaction_id=f"TXN-{random.randint(100000, 999999)}",
                product_id=f"PRD-{random.randint(100, 999)}",
                tracking=f"TRK{random.randint(1000000, 9999999)}",
                amount=f"{random.uniform(10, 500):.2f}",
                duration=random.randint(500, 5000),
                attempt=random.randint(1, 3),
                ip=f"{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}.{random.randint(1, 255)}",
                count=random.randint(5, 50),
                delay=random.randint(1, 48),
                email=f"user{random.randint(1000, 9999)}@example.com",
                method=random.choice(["GET", "POST", "PUT", "DELETE"]),
                path=f"/api/v1/{random.choice(['users', 'orders', 'products', 'payments'])}",
                response_time=random.randint(50, 3000),
                endpoint=f"/api/{random.choice(['users', 'orders', 'payments'])}",
                api_key=f"key_{random.randint(1000, 9999)}",
                timeout=random.randint(10, 60),
                queue_size=random.randint(100, 1000),
            )
        else:
            message = f"{service} operation completed"

        log = {
            "timestamp": timestamp.isoformat(),
            "level": level,
            "service": service,
            "message": message
        }

        logs.append(log)

    return logs

def send_logs_batch(logs, batch_size=100):
    """배치로 로그 전송"""
    total = len(logs)
    success_count = 0

    print(f"📤 총 {total}개의 로그를 {batch_size}개씩 배치로 전송합니다...")

    for i in range(0, total, batch_size):
        batch = logs[i:i+batch_size]

        try:
            response = requests.post(
                API_URL,
                json={"logs": batch},
                timeout=10
            )

            if response.status_code == 200:
                success_count += len(batch)
                print(f"✅ 배치 {i//batch_size + 1}/{(total-1)//batch_size + 1} 완료 ({success_count}/{total})")
            else:
                print(f"❌ 배치 {i//batch_size + 1} 실패: {response.status_code}")

        except Exception as e:
            print(f"❌ 배치 {i//batch_size + 1} 전송 오류: {e}")

        # API 과부하 방지
        time.sleep(0.1)

    return success_count

def main():
    print("=" * 60)
    print("🚀 테스트 데이터 생성 시작")
    print("=" * 60)

    # 로그 생성
    print("\n📝 로그 데이터 생성 중...")
    logs = generate_log_data(count=1000)
    print(f"✅ {len(logs)}개의 로그 생성 완료")

    # 통계 출력
    level_counts = {}
    service_counts = {}

    for log in logs:
        level_counts[log["level"]] = level_counts.get(log["level"], 0) + 1
        service_counts[log["service"]] = service_counts.get(log["service"], 0) + 1

    print("\n📊 생성된 로그 통계:")
    print("\n레벨별 분포:")
    for level, count in sorted(level_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(logs)) * 100
        print(f"  {level:8s}: {count:4d}개 ({percentage:5.1f}%)")

    print("\n서비스별 분포:")
    for service, count in sorted(service_counts.items(), key=lambda x: x[1], reverse=True):
        percentage = (count / len(logs)) * 100
        print(f"  {service:20s}: {count:4d}개 ({percentage:5.1f}%)")

    # 로그 전송
    print("\n" + "=" * 60)
    success_count = send_logs_batch(logs, batch_size=100)
    print("=" * 60)

    print(f"\n✅ 완료: {success_count}/{len(logs)}개 로그 전송 성공")

    if success_count == len(logs):
        print("\n🎉 모든 테스트 데이터 생성 및 전송 완료!")
    else:
        print(f"\n⚠️  {len(logs) - success_count}개 로그 전송 실패")

    print("\n💡 테스트 쿼리 예시:")
    print("  - '최근 1시간 에러 로그 조회'")
    print("  - 'payment-service의 에러 분석'")
    print("  - '특정 사용자의 로그 추적'")
    print("  - '서비스별 에러율 비교'")
    print("  - '응답 시간이 느린 API 찾기'")

if __name__ == "__main__":
    main()
