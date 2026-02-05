#!/usr/bin/env python3
"""
Test Log Generator for Log Analysis System

Generates various log scenarios for comprehensive testing of all 6 advanced features.

Usage:
    python scripts/generate_test_logs.py --scenario normal --count 100
    python scripts/generate_test_logs.py --scenario error_spike
    python scripts/generate_test_logs.py --scenario slow_api
    python scripts/generate_test_logs.py --scenario service_down
    python scripts/generate_test_logs.py --scenario multi_step
    python scripts/generate_test_logs.py --scenario all

Scenarios:
    normal       - Normal operational logs (INFO/WARNING/ERROR mix)
    error_spike  - Sudden error spike for alert testing (Feature #5)
    slow_api     - Slow API requests for slow_api alert (Feature #5)
    service_down - Service downtime simulation (Feature #5)
    multi_step   - Payment failure pattern for multi-step analysis (Feature #3)
    all          - Combination of all scenarios
"""

import requests
import random
import time
from datetime import datetime, timedelta
import argparse
import sys

# Configuration
LOG_SAVE_URL = "http://localhost:8000/logs"

SERVICES = ["payment-api", "user-api", "order-api", "notification-api", "inventory-api"]

ERROR_TYPES = [
    "DatabaseConnectionError",
    "TimeoutError",
    "ValidationError",
    "AuthenticationError",
    "RateLimitError"
]

API_PATHS = [
    "/api/v1/checkout",
    "/api/v1/users",
    "/api/v1/orders",
    "/api/v1/payments",
    "/api/v1/inventory"
]


def generate_normal_logs(count=100):
    """
    Generate normal operational logs with realistic distribution

    Distribution:
    - 70% INFO
    - 20% WARNING
    - 10% ERROR
    """
    print(f"📝 Generating {count} normal operational logs...")

    success_count = 0
    error_count = 0

    for i in range(count):
        # Realistic log distribution
        level = random.choices(
            ["INFO", "WARNING", "ERROR"],
            weights=[70, 20, 10]
        )[0]

        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": level,
            "service": random.choice(SERVICES),
            "message": generate_message(level, i),
            "duration_ms": random.randint(50, 800),
            "user_id": f"user_{random.randint(1, 100)}"
        }

        # Add optional fields
        if random.random() < 0.3:  # 30% have path
            log_entry["path"] = random.choice(API_PATHS)

        if level == "ERROR":
            log_entry["error_type"] = random.choice(ERROR_TYPES)

        try:
            response = requests.post(
                LOG_SAVE_URL,
                json={"logs": [log_entry]},
                timeout=5
            )
            if response.status_code == 200:
                success_count += 1
            else:
                error_count += 1

            # Progress indicator
            if (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{count} ({success_count} success, {error_count} failed)")

        except Exception as e:
            error_count += 1
            print(f"  ❌ Error at {i + 1}: {e}")

        time.sleep(0.1)  # Rate limiting

    print(f"✅ Generated {count} normal logs ({success_count} success, {error_count} failed)")


def generate_message(level, index):
    """Generate realistic log messages"""
    messages = {
        "INFO": [
            f"Request processed successfully #{index}",
            f"Operation completed #{index}",
            f"User action recorded #{index}",
            f"Transaction committed #{index}"
        ],
        "WARNING": [
            f"Slow response detected #{index}",
            f"Retry attempt #{index}",
            f"Resource usage high #{index}",
            f"Deprecated API used #{index}"
        ],
        "ERROR": [
            f"Failed to process request #{index}",
            f"Connection error #{index}",
            f"Validation failed #{index}",
            f"Authentication error #{index}"
        ]
    }
    return random.choice(messages.get(level, [f"Log entry #{index}"]))


def generate_error_spike(count=100, service="payment-api"):
    """
    Generate sudden error spike for alert testing (Feature #5: Test 5.3)

    Creates concentrated ERROR logs to trigger error_rate_spike alert.
    Background task should detect >10% increase in error rate.
    """
    print(f"🚨 Generating {count} error spike for {service}...")
    print(f"   This should trigger 'error_rate_spike' alert in ~5 minutes")

    success_count = 0

    for i in range(count):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": "ERROR",
            "service": service,
            "message": f"Error spike test #{i}: {random.choice(['Connection refused', 'Timeout', 'Database unavailable'])}",
            "error_type": random.choice(ERROR_TYPES),
            "user_id": f"user_{random.randint(1, 50)}"
        }

        # Some errors include path
        if random.random() < 0.4:
            log_entry["path"] = random.choice(API_PATHS)

        try:
            response = requests.post(LOG_SAVE_URL, json={"logs": [log_entry]}, timeout=5)
            if response.status_code == 200:
                success_count += 1

            if (i + 1) % 10 == 0:
                print(f"  Progress: {i + 1}/{count}")

        except Exception as e:
            print(f"  ❌ Error at {i + 1}: {e}")

        time.sleep(0.05)  # Fast generation for spike effect

    print(f"✅ Generated {count} error logs ({success_count} success)")
    print(f"⏳ Wait ~5 minutes for background anomaly detection to trigger alert")


def generate_slow_api_logs(count=10, service="payment-api", path="/api/v1/checkout"):
    """
    Generate slow API logs for alert testing (Feature #5: Test 5.4)

    Creates logs with duration_ms > 2000 to trigger slow_api alert.
    """
    print(f"🐌 Generating {count} slow API logs...")
    print(f"   Service: {service}, Path: {path}")
    print(f"   This should trigger 'slow_api' alert in ~5 minutes")

    for i in range(count):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": "INFO",
            "service": service,
            "path": path,
            "message": f"Slow API request #{i}",
            "duration_ms": random.randint(2500, 5000),  # 2.5-5 seconds
            "user_id": f"user_{random.randint(1, 20)}"
        }

        try:
            response = requests.post(LOG_SAVE_URL, json={"logs": [log_entry]}, timeout=5)
            if (i + 1) % 5 == 0:
                print(f"  Progress: {i + 1}/{count}")
        except Exception as e:
            print(f"  ❌ Error at {i + 1}: {e}")

        time.sleep(0.2)

    print(f"✅ Generated {count} slow API logs")
    print(f"⏳ Wait ~5 minutes for background anomaly detection to trigger alert")


def generate_service_down_scenario(active_service="test-service", down_duration_min=6):
    """
    Simulate service downtime for alert testing (Feature #5: Test 5.5)

    Steps:
    1. Generate baseline activity for the service
    2. Stop generating logs for specified duration
    3. Background task should detect no logs for 5+ minutes
    """
    print(f"⏸️  Simulating {active_service} downtime for {down_duration_min} minutes...")

    # Step 1: Establish baseline activity
    print(f"   Step 1/2: Establishing baseline activity...")
    for i in range(20):
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "level": random.choice(["INFO", "WARNING"]),
            "service": active_service,
            "message": f"Normal operation #{i}",
            "duration_ms": random.randint(100, 500)
        }

        try:
            requests.post(LOG_SAVE_URL, json={"logs": [log_entry]}, timeout=5)
        except Exception as e:
            print(f"  ❌ Error: {e}")

        time.sleep(0.5)

    print(f"   ✅ Baseline established ({active_service} is active)")

    # Step 2: Downtime simulation
    print(f"   Step 2/2: Simulating downtime...")
    print(f"   🛑 Stopped logging for {active_service}")
    print(f"   ⏳ Waiting {down_duration_min} minutes for alert to trigger...")
    print(f"   (Background task runs every 5 minutes)")

    # Just wait - no logs for this service
    for minute in range(down_duration_min):
        time.sleep(60)
        print(f"   ⏱️  {minute + 1}/{down_duration_min} minutes elapsed...")

    print(f"✅ Downtime period complete")
    print(f"   'service_down' alert should have triggered for {active_service}")


def generate_multi_step_test_data():
    """
    Generate payment failure pattern for multi-step reasoning test (Feature #3: Test 3.2)

    Creates a realistic scenario:
    - Normal period (2 hours ago): Low failure rate
    - Spike period (recent 30 min): High failure rate

    Good test question: "결제 실패율이 왜 높아졌어?"
    Expected: Multi-step decomposition to analyze failure rate increase
    """
    print(f"🔍 Generating multi-step test scenario...")
    print(f"   Creating payment failure rate pattern for analysis")

    # Normal period (2 hours ago) - LOW failure rate (~20%)
    print(f"   Step 1/2: Creating baseline period (2 hours ago)...")
    past_time = datetime.now() - timedelta(hours=2)

    for i in range(50):
        level = random.choices(["INFO", "ERROR"], weights=[80, 20])[0]

        log_entry = {
            "timestamp": (past_time + timedelta(minutes=i // 2)).isoformat(),
            "level": level,
            "service": "payment-api",
            "message": f"Payment processing #{i}",
            "path": "/api/v1/checkout",
            "duration_ms": random.randint(200, 800),
            "user_id": f"user_{random.randint(1, 100)}"
        }

        if level == "ERROR":
            log_entry["error_type"] = random.choice(["ValidationError", "TimeoutError"])

        try:
            requests.post(LOG_SAVE_URL, json={"logs": [log_entry]}, timeout=5)
        except Exception as e:
            pass  # Silent failures ok for background data

        if (i + 1) % 10 == 0:
            print(f"     Progress: {i + 1}/50")

    print(f"   ✅ Baseline period created (20% failure rate)")

    # Spike period (recent 30 minutes) - HIGH failure rate (~70%)
    print(f"   Step 2/2: Creating spike period (recent 30 min)...")

    for i in range(100):
        minutes_ago = 30 - (i // 4)  # Spread over 30 minutes
        timestamp = datetime.now() - timedelta(minutes=minutes_ago)

        level = random.choices(["INFO", "ERROR"], weights=[30, 70])[0]

        log_entry = {
            "timestamp": timestamp.isoformat(),
            "level": level,
            "service": "payment-api",
            "message": f"Payment processing #{50 + i}",
            "path": "/api/v1/checkout",
            "duration_ms": random.randint(200, 1500) if level == "INFO" else random.randint(1000, 4000),
            "user_id": f"user_{random.randint(1, 30)}"  # Concentrated user range
        }

        if level == "ERROR":
            # Most errors are DatabaseConnectionError (concentrated failure mode)
            log_entry["error_type"] = "DatabaseConnectionError" if random.random() < 0.7 else "TimeoutError"

        try:
            requests.post(LOG_SAVE_URL, json={"logs": [log_entry]}, timeout=5)
        except Exception as e:
            pass

        if (i + 1) % 20 == 0:
            print(f"     Progress: {i + 1}/100")

        time.sleep(0.05)

    print(f"   ✅ Spike period created (70% failure rate)")
    print(f"\n✅ Multi-step test data ready!")
    print(f"   Good test question: '결제 실패율이 왜 높아졌어?'")
    print(f"   Expected: Multi-step analysis comparing baseline vs spike")


def generate_context_test_data():
    """
    Generate data for context-aware agent testing (Feature #2)

    Creates logs with specific services and error types for reference resolution testing.
    """
    print(f"🧠 Generating context-aware test data...")

    scenarios = [
        # Scenario 1: payment-api errors
        {"service": "payment-api", "error_type": "DatabaseConnectionError", "count": 20},
        # Scenario 2: user-api slow requests
        {"service": "user-api", "path": "/api/v1/users", "duration_range": (2000, 4000), "count": 15},
        # Scenario 3: order-api validation errors
        {"service": "order-api", "error_type": "ValidationError", "count": 10}
    ]

    for scenario in scenarios:
        print(f"   Creating scenario: {scenario}")

        for i in range(scenario["count"]):
            log_entry = {
                "timestamp": datetime.now().isoformat(),
                "level": "ERROR" if "error_type" in scenario else "INFO",
                "service": scenario["service"],
                "message": f"Test log #{i}",
                "user_id": f"user_{random.randint(1, 50)}"
            }

            if "error_type" in scenario:
                log_entry["error_type"] = scenario["error_type"]

            if "path" in scenario:
                log_entry["path"] = scenario["path"]

            if "duration_range" in scenario:
                log_entry["duration_ms"] = random.randint(*scenario["duration_range"])

            try:
                requests.post(LOG_SAVE_URL, json={"logs": [log_entry]}, timeout=5)
            except:
                pass

            time.sleep(0.1)

    print(f"✅ Context test data ready!")
    print(f"   Test with: '최근 payment-api 에러는?' → '그 서비스의 느린 API는?'")


def generate_all_scenarios():
    """
    Generate complete test dataset

    Runs all scenarios in sequence with appropriate delays
    """
    print("=" * 60)
    print("🎯 Generating Complete Test Dataset")
    print("=" * 60)

    # 1. Normal baseline
    print("\n[1/4] Normal Logs")
    generate_normal_logs(count=50)

    time.sleep(2)

    # 2. Context test data
    print("\n[2/4] Context Test Data")
    generate_context_test_data()

    time.sleep(2)

    # 3. Multi-step test data
    print("\n[3/4] Multi-Step Test Data")
    generate_multi_step_test_data()

    time.sleep(2)

    # 4. Instructions for alert testing
    print("\n[4/4] Alert Testing")
    print("⏳ For alert testing, wait 5+ minutes after baseline, then run:")
    print("   python scripts/generate_test_logs.py --scenario error_spike")
    print("   python scripts/generate_test_logs.py --scenario slow_api")
    print("   (Run these separately with 5-min gaps for clear alert separation)")

    print("\n" + "=" * 60)
    print("✅ Complete Test Dataset Generated!")
    print("=" * 60)


def print_test_summary():
    """Print testing instructions summary"""
    print("\n" + "=" * 60)
    print("📚 Test Scenario Summary")
    print("=" * 60)

    print("\n🧪 Feature Tests:")
    print("  Feature #1 (Cache):")
    print("    - Run any query twice to test cache hit")
    print("  Feature #2 (Context):")
    print("    - Use context test data: 'payment-api 에러' → '그 서비스'")
    print("  Feature #3 (Multi-Step):")
    print("    - Use multi-step data: '결제 실패율이 왜 높아졌어?'")
    print("  Feature #4 (Optimization):")
    print("    - Test complexity: simple vs complex queries")
    print("  Feature #5 (Alerting):")
    print("    - Generate spike: --scenario error_spike")
    print("    - Generate slow: --scenario slow_api")
    print("    - Generate down: --scenario service_down")
    print("  Feature #6 (Tool Selection):")
    print("    - Pattern query: \"'timeout' 패턴 포함된 로그\"")

    print("\n🔗 Integration Scenarios:")
    print("  Scenario A: Cache + Context + Multi-Step")
    print("    1. 'payment-api 에러' (cache miss, set context)")
    print("    2. Same query (cache hit)")
    print("    3. '그 서비스의 느린 API' (context resolution)")
    print("    4. '왜 느려졌어?' (multi-step)")

    print("\n⏱️  Alert Testing Timeline:")
    print("  T+0min:  Generate baseline (done)")
    print("  T+5min:  Generate error_spike")
    print("  T+10min: Wait for alert (background task)")
    print("  T+15min: Generate slow_api")
    print("  T+20min: Wait for alert")

    print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(
        description='Generate test logs for Log Analysis System',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/generate_test_logs.py --scenario normal --count 100
  python scripts/generate_test_logs.py --scenario error_spike
  python scripts/generate_test_logs.py --scenario all

Scenarios:
  normal       - Normal operational logs (70% INFO, 20% WARNING, 10% ERROR)
  error_spike  - Sudden ERROR spike for alert testing
  slow_api     - Slow API requests (>2s) for alert testing
  service_down - Service downtime simulation
  multi_step   - Payment failure pattern for multi-step reasoning
  context      - Specific patterns for context-aware testing
  all          - Complete test dataset (baseline + context + multi-step)
        """
    )

    parser.add_argument(
        '--scenario',
        choices=['normal', 'error_spike', 'slow_api', 'service_down', 'multi_step', 'context', 'all'],
        default='normal',
        help='Test scenario to generate'
    )

    parser.add_argument(
        '--count',
        type=int,
        default=100,
        help='Number of logs to generate (applies to normal, error_spike)'
    )

    parser.add_argument(
        '--service',
        type=str,
        default='payment-api',
        help='Target service for error_spike or slow_api scenarios'
    )

    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("🚀 Log Analysis System - Test Data Generator")
    print("=" * 60)
    print(f"Target URL: {LOG_SAVE_URL}")
    print(f"Scenario: {args.scenario}")
    print("=" * 60 + "\n")

    # Verify log-save-server is accessible
    try:
        response = requests.get("http://localhost:8000/docs", timeout=5)
        print("✅ log-save-server is accessible\n")
    except Exception as e:
        print(f"❌ Cannot connect to log-save-server: {e}")
        print(f"   Make sure Docker services are running: docker-compose up -d\n")
        sys.exit(1)

    # Execute scenario
    try:
        if args.scenario == 'normal':
            generate_normal_logs(args.count)

        elif args.scenario == 'error_spike':
            generate_error_spike(args.count, args.service)

        elif args.scenario == 'slow_api':
            generate_slow_api_logs(count=10, service=args.service)

        elif args.scenario == 'service_down':
            generate_service_down_scenario(active_service=args.service)

        elif args.scenario == 'multi_step':
            generate_multi_step_test_data()

        elif args.scenario == 'context':
            generate_context_test_data()

        elif args.scenario == 'all':
            generate_all_scenarios()

        # Print summary
        print_test_summary()

        print("\n✅ Test data generation complete!")
        print("🌐 Open frontend: http://localhost:3000")
        print("📖 See TESTING.md for detailed test scenarios\n")

    except KeyboardInterrupt:
        print("\n\n⚠️  Generation interrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Generation failed: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
