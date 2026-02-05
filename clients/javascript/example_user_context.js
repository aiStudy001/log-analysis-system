/**
 * 사용자 컨텍스트 자동 수집 예제 (JavaScript/Node.js)
 *
 * 실행 방법:
 *     node example_user_context.js
 *
 * 테스트 시나리오:
 *     1. runWithUserContext 방식 (권장)
 *     2. Promise와 함께 사용
 *     3. 중첩 컨텍스트
 *     4. 분산 추적 (trace_id)
 */
import { WorkerThreadsLogClient } from './src/node-client.js';
import { v4 as uuidv4 } from 'uuid';

// 로그 클라이언트 초기화
const logger = new WorkerThreadsLogClient('http://localhost:8000', {
    service: 'user-context-example-js',
    environment: 'development'
});

/**
 * 예제 1: runWithUserContext 방식 (권장)
 */
function example1_runWithUserContext() {
    console.log('\n=== 예제 1: runWithUserContext 방식 ===');

    // 컨텍스트 없이 로그
    logger.info('Operation without context');
    // → user_id 없음

    // 컨텍스트 있이 로그
    WorkerThreadsLogClient.runWithUserContext({
        user_id: 'user_123',
        trace_id: 'trace_xyz',
        session_id: 'sess_abc'
    }, () => {
        logger.info('User logged in');
        // → user_id, trace_id, session_id 자동 포함!

        logger.info('User viewing dashboard');
        // → 같은 컨텍스트 정보 포함

        simulatePayment();
    });

    // 블록 벗어나면 컨텍스트 자동 초기화
    logger.info('Operation after context cleared');
    // → user_id 없음
}

/**
 * 결제 시뮬레이션 (컨텍스트 자동 전파)
 */
function simulatePayment() {
    logger.info('Processing payment');
    // → 상위 컨텍스트의 user_id, trace_id 자동 포함!

    setTimeout(() => {
        logger.info('Payment completed', { amount: 99.99, currency: 'USD' });
        // → user_id, trace_id + 추가 필드
    }, 100);
}

/**
 * 예제 2: Promise와 함께 사용
 */
async function example2_withPromises() {
    console.log('\n=== 예제 2: Promise와 함께 사용 ===');

    await WorkerThreadsLogClient.runWithUserContext({
        user_id: 'user_456',
        trace_id: 'trace_async_123'
    }, async () => {
        logger.info('Async operation started');
        // → user_id, trace_id 자동 포함

        await fetchUserData();
        await processData();

        logger.info('Async operation completed');
        // → 같은 컨텍스트 유지됨
    });
}

/**
 * 사용자 데이터 조회 (비동기)
 */
async function fetchUserData() {
    logger.info('Fetching user data from database');
    // → 상위 컨텍스트의 user_id, trace_id 자동 포함!

    return new Promise(resolve => {
        setTimeout(() => {
            logger.info('User data fetched successfully');
            resolve({ name: 'John Doe', email: 'john@example.com' });
        }, 50);
    });
}

/**
 * 데이터 처리 (비동기)
 */
async function processData() {
    logger.info('Processing user data');

    return new Promise(resolve => {
        setTimeout(() => {
            logger.info('Data processed successfully');
            resolve();
        }, 80);
    });
}

/**
 * 예제 3: 중첩 컨텍스트
 */
function example3_nestedContext() {
    console.log('\n=== 예제 3: 중첩 컨텍스트 ===');

    // 외부 컨텍스트: tenant_id
    WorkerThreadsLogClient.runWithUserContext({ tenant_id: 'tenant_acme' }, () => {
        logger.info('Tenant operation started');
        // → tenant_id="tenant_acme"

        // 내부 컨텍스트: user_id 추가
        WorkerThreadsLogClient.runWithUserContext({ user_id: 'user_789' }, () => {
            logger.info('User operation in tenant');
            // → tenant_id="tenant_acme", user_id="user_789" 둘 다 포함!

            logger.info('Fetching tenant data for user');
            // → 같은 컨텍스트
        });

        logger.info('Back to tenant-only context');
        // → tenant_id="tenant_acme" (user_id 없음)
    });
}

/**
 * 예제 4: 분산 추적 (trace_id)
 */
function example4_distributedTracing() {
    console.log('\n=== 예제 4: 분산 추적 ===');

    // 요청마다 고유한 trace_id 생성 (32자, 대시 제거)
    const traceId = uuidv4().replace(/-/g, '');

    WorkerThreadsLogClient.runWithUserContext({
        trace_id: traceId,
        user_id: 'user_999'
    }, () => {
        logger.info('Request received');
        // → trace_id, user_id 포함

        // 여러 서비스 호출 (시뮬레이션)
        callServiceA();
        callServiceB();
        callServiceC();

        logger.info('Request completed');
        // → 같은 trace_id로 전체 흐름 추적 가능!
    });
}

/**
 * Service A 호출 시뮬레이션
 */
function callServiceA() {
    logger.info('Calling Service A');
    // → 상위 컨텍스트의 trace_id 자동 포함!
    setTimeout(() => {
        logger.info('Service A responded');
    }, 50);
}

/**
 * Service B 호출 시뮬레이션
 */
function callServiceB() {
    logger.info('Calling Service B');
    setTimeout(() => {
        logger.info('Service B responded');
    }, 80);
}

/**
 * Service C 호출 시뮬레이션
 */
function callServiceC() {
    logger.info('Calling Service C');
    setTimeout(() => {
        logger.info('Service C responded');
    }, 60);
}

/**
 * 예제 5: 에러 추적 with Context
 */
function example5_errorTracking() {
    console.log('\n=== 예제 5: 에러 추적 ===');

    WorkerThreadsLogClient.runWithUserContext({
        user_id: 'user_error_test',
        trace_id: 'trace_error_123'
    }, () => {
        logger.info('Starting risky operation');

        try {
            // 의도적으로 에러 발생
            throw new Error('Simulated error for testing');

        } catch (err) {
            logger.errorWithTrace('Operation failed', err);
            // → user_id, trace_id, stack_trace, error_type 모두 포함!
            // 어떤 사용자의 작업이 실패했는지 즉시 파악 가능
        }
    });
}

/**
 * 예제 6: Set/Clear 방식 (주의사항 있음)
 */
function example6_setCleanStyle() {
    console.log('\n=== 예제 6: Set/Clear 방식 (주의) ===');

    // ⚠️ 주의: 동기 코드에서만 안전
    WorkerThreadsLogClient.setUserContext({
        user_id: 'user_set_clear',
        session_id: 'sess_123'
    });

    logger.info('User logged in (set/clear style)');
    // → user_id, session_id 포함

    logger.info('Browsing products');
    // → 계속 포함됨

    // 컨텍스트 초기화
    WorkerThreadsLogClient.clearUserContext();

    logger.info('User logged out');
    // → user_id 없음
}

/**
 * 모든 예제 실행
 */
async function main() {
    console.log('='.repeat(60));
    console.log('사용자 컨텍스트 자동 수집 예제 (JavaScript)');
    console.log('='.repeat(60));

    example1_runWithUserContext();
    await sleep(500);

    await example2_withPromises();
    await sleep(500);

    example3_nestedContext();
    await sleep(500);

    example4_distributedTracing();
    await sleep(500);

    example5_errorTracking();
    await sleep(500);

    example6_setCleanStyle();
    await sleep(500);

    // Flush 대기
    console.log('\n=== Flushing logs... ===');
    logger.flush();
    await sleep(2000);

    console.log('\n=== 완료! ===');
    console.log('\nPostgreSQL에서 확인:');
    console.log('  SELECT');
    console.log("    created_at,");
    console.log("    metadata->>'user_id' as user_id,");
    console.log("    metadata->>'trace_id' as trace_id,");
    console.log("    message");
    console.log("  FROM logs");
    console.log("  WHERE service = 'user-context-example-js'");
    console.log("  ORDER BY created_at DESC");
    console.log("  LIMIT 20;");

    // 종료
    await logger.close();
    process.exit(0);
}

/**
 * Sleep 헬퍼
 */
function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// 실행
main().catch(err => {
    console.error('Error:', err);
    process.exit(1);
});
