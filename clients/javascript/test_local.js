/**
 * 로컬 수정 버전 테스트
 */
import { createLogClient } from './src/index.js';

console.log('=== 로컬 수정 버전 테스트 ===\n');

const logger = createLogClient('http://localhost:8000', {
    service: 'local-test',
    environment: 'development'
});

console.log('✅ 클라이언트 생성');

// 기본 로그
logger.info('테스트 로그 1');
console.log('✅ info 호출');

// 함수에서 호출
function testFunction() {
    logger.info('함수에서 호출한 로그');
    console.log('✅ 함수에서 info 호출');
}

testFunction();

// 컨텍스트 테스트
logger.constructor.runWithUserContext({
    user_id: 'user_test',
    trace_id: 'trace_test'
}, () => {
    logger.info('컨텍스트 로그');
    console.log('✅ 컨텍스트 포함 로그');
});

setTimeout(() => {
    logger.flush();
    console.log('\n✅ Flush 완료');

    setTimeout(() => {
        console.log('\n=== 테스트 완료! PostgreSQL에서 확인하세요 ===');
        logger.close();
        process.exit(0);
    }, 1000);
}, 2000);
