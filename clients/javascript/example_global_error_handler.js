/**
 * 글로벌 에러 핸들러 사용 예제
 *
 * enableGlobalErrorHandler 옵션을 활성화하면
 * 모든 uncaught errors와 unhandled rejections가 자동으로 로깅됩니다.
 */

import { createLogClient } from 'log-collector-async';

// ============================================================================
// 방법 1: 생성자 옵션으로 활성화
// ============================================================================
const logger = createLogClient('http://localhost:8000', {
    service: 'my-app',
    environment: 'production',
    enableGlobalErrorHandler: true  // 글로벌 에러 핸들러 활성화
});

console.log('✅ 글로벌 에러 핸들러가 활성화되었습니다.');
console.log('이제 모든 에러가 자동으로 로깅됩니다!\n');

// ============================================================================
// 테스트 1: Uncaught Exception (동기 에러)
// ============================================================================
setTimeout(() => {
    console.log('\n📌 테스트 1: Uncaught Exception');
    // 이 에러는 자동으로 로깅됩니다 (try-catch 없이도!)
    throw new Error('This is an uncaught error!');
}, 1000);

// ============================================================================
// 테스트 2: Unhandled Promise Rejection (비동기 에러)
// ============================================================================
setTimeout(() => {
    console.log('\n📌 테스트 2: Unhandled Promise Rejection');
    // 이 Promise rejection도 자동으로 로깅됩니다
    Promise.reject(new Error('This is an unhandled rejection!'));
}, 2000);

// ============================================================================
// 테스트 3: 일반 로깅도 여전히 작동
// ============================================================================
logger.info('Application started', { version: '1.0.0' });

setTimeout(() => {
    logger.warn('This is a warning', { custom_field: 'test' });
}, 500);

// ============================================================================
// 방법 2: 환경 변수로 활성화
// ============================================================================
// .env 파일에 추가:
//   ENABLE_GLOBAL_ERROR_HANDLER=true
//
// 그러면 명시적으로 옵션을 전달하지 않아도 자동으로 활성화됩니다:
//   const logger = createLogClient('http://localhost:8000', {
//       service: 'my-app'
//   });

// ============================================================================
// 주의사항
// ============================================================================
// 1. enableGlobalErrorHandler는 기본값이 false입니다
// 2. 프로덕션 환경에서는 신중하게 사용하세요
// 3. 기존 에러 핸들러와 충돌할 수 있으니 테스트 필요
// 4. close() 호출 시 자동으로 핸들러가 해제됩니다

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\nShutting down...');
    logger.flush();

    setTimeout(async () => {
        await logger.close();  // 글로벌 핸들러도 자동으로 해제됨
        process.exit(0);
    }, 1000);
});
