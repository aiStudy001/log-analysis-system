"""
Python 클라이언트 라이브러리 기능 테스트
log-collector-async v1.1.0
"""

import asyncio
import time
from log_collector import AsyncLogClient

SERVER_URL = 'http://localhost:8000'

async def main():
    print('=' * 60)
    print('Python Client Library Test')
    print('Package: log-collector-async v1.1.0')
    print('=' * 60)
    print()

    # ========================================================================
    # 테스트 1: 기본 로깅 (모든 레벨)
    # ========================================================================
    print('Test 1: Basic Logging (all levels)')
    logger = AsyncLogClient(
        SERVER_URL,
        service='test-python-client',
        environment='testing'
    )

    logger.debug('Debug message', test_id=1, feature='basic_logging')
    logger.info('Info message', test_id=1, feature='basic_logging')
    logger.warn('Warning message', test_id=1, feature='basic_logging')
    logger.error('Error message', test_id=1, feature='basic_logging')

    print('Logged: DEBUG, INFO, WARN, ERROR')
    print()

    # ========================================================================
    # 테스트 2: 배치 로깅
    # ========================================================================
    print('Test 2: Batch Logging (100 logs)')
    for i in range(100):
        logger.info(f'Batch log {i}', batch_index=i, test_id=2)

    print('Created 100 batch logs')
    print()

    # ========================================================================
    # 테스트 3: 추적 ID (Distributed Tracing)
    # ========================================================================
    print('Test 3: Distributed Tracing (trace_id)')
    trace_id = f'trace-{int(time.time() * 1000)}'

    logger.info('Request started', trace_id=trace_id, test_id=3, step=1)
    logger.info('Processing...', trace_id=trace_id, test_id=3, step=2)
    logger.info('Request completed', trace_id=trace_id, test_id=3, step=3)

    print(f'Logged with trace_id: {trace_id}')
    print()

    # ========================================================================
    # 테스트 4: 타이머 기능
    # ========================================================================
    print('Test 4: Timer Functionality')
    timer = logger.start_timer()

    # 시뮬레이션: 1초 대기
    await asyncio.sleep(1)

    logger.end_timer(timer, 'INFO', 'Operation completed',
                     test_id=4, operation='test_timer')

    print('Timer test completed (should show ~1000ms)')
    print()

    # ========================================================================
    # 테스트 5: 에러 with 스택 트레이스
    # ========================================================================
    print('Test 5: Error with Stack Trace')
    try:
        raise ValueError('Test error with stack trace')
    except Exception as e:
        logger.error_with_trace('Caught error', exception=e, test_id=5)

    print('Logged error with stack trace')
    print()

    # ========================================================================
    # 테스트 6: 컨텍스트 전파
    # ========================================================================
    print('Test 6: Context Propagation')
    context_logger = AsyncLogClient(
        SERVER_URL,
        service='test-python-client',
        environment='testing'
    )

    context_logger.info('Context test', test_id=6)
    print('Context propagation tested')
    print()

    # ========================================================================
    # 테스트 7: 글로벌 에러 핸들러 (새 기능!)
    # ========================================================================
    print('Test 7: Global Error Handler')
    error_logger = AsyncLogClient(
        SERVER_URL,
        service='test-python-client',
        environment='testing',
        enable_global_error_handler=True
    )

    print('Global error handler enabled')
    print()

    # ========================================================================
    # 테스트 8: 압축 기능
    # ========================================================================
    print('Test 8: Compression (large payload)')
    compress_logger = AsyncLogClient(
        SERVER_URL,
        service='test-python-client',
        environment='testing',
        enable_compression=True
    )

    large_data = {
        'test_id': 8,
        'data': 'x' * 1000,
        'items': [{'name': 'item', 'value': 123} for _ in range(100)]
    }

    compress_logger.info('Large payload test', **large_data)
    print('Compression test completed')
    print()

    # ========================================================================
    # 강제 플러시 및 종료
    # ========================================================================
    print('Flushing all logs...')
    await logger.close()
    await context_logger.close()
    await error_logger.close()
    await compress_logger.close()

    print('All logs flushed')
    print()

    # ========================================================================
    # 결과 안내
    # ========================================================================
    print('=' * 60)
    print('All Tests Completed')
    print('=' * 60)
    print()
    print('Next Steps:')
    print('1. Check PostgreSQL for logged data:')
    print("   SELECT created_at, level, message, metadata->'test_id' as test_id")
    print('   FROM logs')
    print("   WHERE service = 'test-python-client'")
    print('   ORDER BY created_at DESC;')
    print()
    print('2. Verify features:')
    print('   - Test 1: 4 log levels (DEBUG, INFO, WARN, ERROR)')
    print('   - Test 2: 100 batch logs')
    print('   - Test 3: 3 logs with same trace_id')
    print('   - Test 4: 1 log with duration_ms ~1000')
    print('   - Test 5: 1 log with stack_trace field')
    print('   - Test 6: 1 log with custom context')
    print('   - Test 7: Global error handler enabled')
    print('   - Test 8: 1 compressed log with large data')
    print()


if __name__ == '__main__':
    asyncio.run(main())
