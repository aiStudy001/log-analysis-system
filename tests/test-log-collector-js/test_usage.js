/**
 * 배포된 log-client-async 패키지 사용 테스트
 */
const { createLogClient } = require('log-client-async');

console.log('='.repeat(60));
console.log('log-client-async 패키지 테스트');
console.log('='.repeat(60));

// 클라이언트 생성
const logger = createLogClient('http://localhost:8000', {
    service: 'test-service-js',
    environment: 'development'
});

console.log('\n✅ 클라이언트 생성 완료');

// 기본 로그 전송
logger.info('테스트 로그 1');
logger.warn('경고 로그', { warning_type: 'test' });
logger.error('에러 로그', { error_code: 'TEST_ERROR' });

console.log('✅ 로그 3개 전송 완료');

// 자동 호출 위치 추적 테스트
function testFunction() {
    logger.info('함수에서 호출한 로그');
    // function_name과 file_path가 자동으로 포함됨
}

testFunction();
console.log('✅ 자동 호출 위치 추적 테스트 완료');

// 사용자 컨텍스트 테스트
logger.constructor.runWithUserContext({
    user_id: 'user_123',
    trace_id: 'trace_xyz'
}, () => {
    logger.info('컨텍스트 포함 로그');
    // user_id와 trace_id가 자동으로 포함됨
});

console.log('✅ 사용자 컨텍스트 테스트 완료');

// Flush 대기
console.log('\n로그 전송 대기 중...');
setTimeout(() => {
    logger.flush();
    console.log('✅ 모든 로그 전송 완료!');

    setTimeout(() => {
        console.log('\n' + '='.repeat(60));
        console.log('테스트 완료! 로그 서버에서 확인하세요.');
        console.log('='.repeat(60));

        logger.close();
        process.exit(0);
    }, 1000);
}, 2000);
