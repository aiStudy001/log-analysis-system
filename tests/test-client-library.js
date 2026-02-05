/**
 * JavaScript 클라이언트 라이브러리 기능 테스트
 * log-collector-async v1.1.0
 */

import { createLogClient } from '../clients/javascript/src/index.js';

const SERVER_URL = 'http://localhost:8000';

console.log('========================================');
console.log('JavaScript Client Library Test');
console.log('Package: log-collector-async v1.1.0');
console.log('========================================\n');

// ============================================================================
// 테스트 1: 기본 로깅 (모든 레벨)
// ============================================================================
console.log('Test 1: Basic Logging (all levels)');
const logger = createLogClient(SERVER_URL, {
    service: 'test-js-client',
    environment: 'testing',
    userId: 'test-user-123'
});

logger.debug('Debug message', { test_id: 1, feature: 'basic_logging' });
logger.info('Info message', { test_id: 1, feature: 'basic_logging' });
logger.warn('Warning message', { test_id: 1, feature: 'basic_logging' });
logger.error('Error message', { test_id: 1, feature: 'basic_logging' });

console.log('✅ Logged: DEBUG, INFO, WARN, ERROR\n');

// ============================================================================
// 테스트 2: 배치 로깅
// ============================================================================
console.log('Test 2: Batch Logging (100 logs)');
for (let i = 0; i < 100; i++) {
    logger.info(`Batch log ${i}`, { batch_index: i, test_id: 2 });
}
console.log('✅ Created 100 batch logs\n');

// ============================================================================
// 테스트 3: 추적 ID (Distributed Tracing)
// ============================================================================
console.log('Test 3: Distributed Tracing (trace_id)');
const traceId = 'trace-' + Date.now();

logger.info('Request started', { trace_id: traceId, test_id: 3, step: 1 });
logger.info('Processing...', { trace_id: traceId, test_id: 3, step: 2 });
logger.info('Request completed', { trace_id: traceId, test_id: 3, step: 3 });

console.log(`✅ Logged with trace_id: ${traceId}\n`);

// ============================================================================
// 테스트 4: 타이머 기능
// ============================================================================
console.log('Test 4: Timer Functionality');
const timer = logger.startTimer();

// 시뮬레이션: 1초 대기
await new Promise(resolve => setTimeout(resolve, 1000));

logger.endTimer(timer, 'INFO', 'Operation completed', {
    test_id: 4,
    operation: 'test_timer'
});

console.log('✅ Timer test completed (should show ~1000ms)\n');

// ============================================================================
// 테스트 5: 에러 with 스택 트레이스
// ============================================================================
console.log('Test 5: Error with Stack Trace');
try {
    throw new Error('Test error with stack trace');
} catch (error) {
    logger.errorWithTrace('Caught error', error, {
        test_id: 5,
        error_type: 'intentional'
    });
}
console.log('✅ Logged error with stack trace\n');

// ============================================================================
// 테스트 6: 컨텍스트 전파
// ============================================================================
console.log('Test 6: Context Propagation');
const contextLogger = createLogClient(SERVER_URL, {
    service: 'test-js-client',
    environment: 'testing',
    userId: 'context-user',
    metadata: {
        version: '1.0.0',
        region: 'us-east-1'
    }
});

contextLogger.info('Context test', { test_id: 6 });
console.log('✅ Context propagation tested\n');

// ============================================================================
// 테스트 7: 글로벌 에러 핸들러 (새 기능!)
// ============================================================================
console.log('Test 7: Global Error Handler');
const errorLogger = createLogClient(SERVER_URL, {
    service: 'test-js-client',
    environment: 'testing',
    enableGlobalErrorHandler: true
});

console.log('✅ Global error handler enabled\n');

// ============================================================================
// 테스트 8: 압축 기능
// ============================================================================
console.log('Test 8: Compression (large payload)');
const compressLogger = createLogClient(SERVER_URL, {
    service: 'test-js-client',
    environment: 'testing',
    enableCompression: true
});

const largeData = {
    test_id: 8,
    data: Array(1000).fill('x').join(''),
    items: Array(100).fill({ name: 'item', value: 123 })
};

compressLogger.info('Large payload test', largeData);
console.log('✅ Compression test completed\n');

// ============================================================================
// 강제 플러시 및 종료
// ============================================================================
console.log('Flushing all logs...');
await logger.flush();
await contextLogger.flush();
await errorLogger.flush();
await compressLogger.flush();

console.log('✅ All logs flushed\n');

// ============================================================================
// 결과 안내
// ============================================================================
console.log('========================================');
console.log('All Tests Completed');
console.log('========================================\n');
console.log('Next Steps:');
console.log('1. Check PostgreSQL for logged data:');
console.log('   SELECT created_at, level, message, metadata->\'test_id\' as test_id');
console.log('   FROM logs');
console.log('   WHERE service = \'test-js-client\'');
console.log('   ORDER BY created_at DESC;');
console.log('');
console.log('2. Verify features:');
console.log('   - Test 1: 4 log levels (DEBUG, INFO, WARN, ERROR)');
console.log('   - Test 2: 100 batch logs');
console.log('   - Test 3: 3 logs with same trace_id');
console.log('   - Test 4: 1 log with duration_ms ~1000');
console.log('   - Test 5: 1 log with stack_trace field');
console.log('   - Test 6: 1 log with custom context');
console.log('   - Test 7: Global error handler enabled');
console.log('   - Test 8: 1 compressed log with large data');
console.log('');

process.exit(0);
