/**
 * log-client-async 패키지 종합 기능 테스트
 * 모든 기능을 체계적으로 테스트합니다.
 */
const { createLogClient } = require('log-client-async');
const { v4: uuidv4 } = require('uuid');

console.log('='.repeat(80));
console.log('log-client-async 종합 기능 테스트');
console.log('='.repeat(80));

// 클라이언트 생성
const logger = createLogClient('http://localhost:8000', {
    service: 'comprehensive-test-js',
    environment: 'test'
});

console.log('\n✅ 클라이언트 생성 완료');

// ============================================================================
// 테스트 1: 기본 로그 레벨
// ============================================================================
console.log('\n[테스트 1] 기본 로그 레벨');
logger.trace('TRACE 레벨 로그');
logger.debug('DEBUG 레벨 로그');
logger.info('INFO 레벨 로그');
logger.warn('WARN 레벨 로그', { warning_type: 'test_warning' });
logger.error('ERROR 레벨 로그', { error_code: 'TEST_001' });
logger.fatal('FATAL 레벨 로그', { severity: 'critical' });
console.log('✅ 모든 로그 레벨 테스트 완료');

// ============================================================================
// 테스트 2: 자동 호출 위치 추적 (function_name, file_path)
// ============================================================================
console.log('\n[테스트 2] 자동 호출 위치 추적');

function outerFunction() {
    logger.info('외부 함수에서 호출');

    function innerFunction() {
        logger.info('내부 함수에서 호출');
    }

    innerFunction();
}

outerFunction();
logger.info('전역에서 호출');
console.log('✅ 호출 위치 자동 추적 테스트 완료');

// ============================================================================
// 테스트 3: 사용자 컨텍스트
// ============================================================================
console.log('\n[테스트 3] 사용자 컨텍스트');

// runWithUserContext 방식
logger.constructor.runWithUserContext({
    user_id: 'user_001',
    session_id: 'sess_abc'
}, () => {
    logger.info('사용자 컨텍스트 포함 로그');
});

// 중첩 컨텍스트
logger.constructor.runWithUserContext({ tenant_id: 'tenant_001' }, () => {
    logger.info('테넌트 컨텍스트');

    logger.constructor.runWithUserContext({ user_id: 'user_002' }, () => {
        logger.info('테넌트 + 사용자 컨텍스트');
    });
});

// 분산 추적
const traceId = uuidv4().replace(/-/g, '').substring(0, 32);

logger.constructor.runWithUserContext({
    trace_id: traceId,
    user_id: 'user_003'
}, () => {
    logger.info('분산 추적 시작');
    setTimeout(() => {
        logger.info('분산 추적 진행 중');
    }, 100);
    setTimeout(() => {
        logger.info('분산 추적 완료');
    }, 200);
});

console.log('✅ 사용자 컨텍스트 테스트 완료');

// ============================================================================
// 테스트 4: 타이머 (duration_ms)
// ============================================================================
console.log('\n[테스트 4] 타이머 기능');

// 수동 타이머
const timer = logger.startTimer();
setTimeout(() => {
    logger.endTimer(timer, 'INFO', '수동 타이머 테스트 (약 500ms)');
    console.log('  ✓ 수동 타이머 완료');
}, 500);

// 함수 래퍼 (동기)
setTimeout(() => {
    function slowOperation() {
        const start = Date.now();
        while (Date.now() - start < 300) {} // 300ms 대기
        return '완료';
    }

    const result = logger.measure(slowOperation);
    console.log(`  결과: ${result}`);
}, 600);

// 함수 래퍼 (비동기)
setTimeout(() => {
    async function asyncOperation() {
        await new Promise(resolve => setTimeout(resolve, 200));
        return '비동기 완료';
    }

    logger.measure(asyncOperation).then(() => {
        console.log('  ✓ 비동기 타이머 완료');
    });
}, 1000);

setTimeout(() => {
    console.log('✅ 타이머 기능 테스트 완료');
}, 1500);

// ============================================================================
// 테스트 5: 에러 추적 (errorWithTrace)
// ============================================================================
setTimeout(() => {
    console.log('\n[테스트 5] 에러 추적');

    // 기본 에러
    try {
        throw new Error('의도적 에러 발생');
    } catch (err) {
        logger.errorWithTrace('기본 에러 테스트', err);
    }

    // 중첩 함수에서 에러
    function level1() {
        function level2() {
            function level3() {
                throw new TypeError('깊은 에러 발생');
            }
            level3();
        }
        level2();
    }

    try {
        level1();
    } catch (err) {
        logger.errorWithTrace('중첩 함수 에러', err, {
            error_context: 'level1->level2->level3'
        });
    }

    // 사용자 컨텍스트와 함께 에러
    logger.constructor.runWithUserContext({
        user_id: 'user_error',
        trace_id: 'trace_error'
    }, () => {
        try {
            throw new ReferenceError('사용자 작업 중 에러');
        } catch (err) {
            logger.errorWithTrace('사용자 작업 실패', err);
        }
    });

    console.log('✅ 에러 추적 테스트 완료');
}, 2000);

// ============================================================================
// 테스트 6: 메타데이터 및 커스텀 필드
// ============================================================================
setTimeout(() => {
    console.log('\n[테스트 6] 메타데이터 및 커스텀 필드');

    logger.info('주문 생성', {
        order_id: 'ORD-12345',
        user_id: 'user_999',
        amount: 99.99,
        currency: 'USD',
        items: 3
    });

    logger.info('API 요청', {
        method: 'POST',
        endpoint: '/api/orders',
        status_code: 201,
        response_time_ms: 45
    });

    console.log('✅ 메타데이터 테스트 완료');
}, 2500);

// ============================================================================
// 테스트 7: 수동 flush
// ============================================================================
setTimeout(() => {
    console.log('\n[테스트 7] 수동 Flush');
    logger.flush();
    console.log('✅ Flush 완료');
}, 3000);

// ============================================================================
// 완료
// ============================================================================
setTimeout(() => {
    console.log('\n로그 전송 대기 중...');

    setTimeout(() => {
        console.log('\n' + '='.repeat(80));
        console.log('모든 테스트 완료!');
        console.log('='.repeat(80));
        console.log('\nPostgreSQL에서 확인:');
        console.log('  SELECT');
        console.log('    created_at,');
        console.log('    level,');
        console.log('    message,');
        console.log('    function_name,');
        console.log('    file_path,');
        console.log("    metadata->>'user_id' as user_id,");
        console.log("    metadata->>'trace_id' as trace_id,");
        console.log("    metadata->>'duration_ms' as duration_ms,");
        console.log('    stack_trace');
        console.log('  FROM logs');
        console.log("  WHERE service = 'comprehensive-test-js'");
        console.log('  ORDER BY created_at DESC');
        console.log('  LIMIT 30;');
        console.log('='.repeat(80));

        logger.close();
        process.exit(0);
    }, 3000);
}, 3500);
