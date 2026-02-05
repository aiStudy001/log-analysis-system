const { createLogClient } = require('./src/index.js');

// 로그 서버 실행 필요 (http://localhost:8000)
const logger = createLogClient('http://localhost:8000', {
    batchSize: 10,  // 작은 배치로 빠른 확인
    flushInterval: 1000
});

console.log('Sending 5 test logs...');
for (let i = 0; i < 5; i++) {
    logger.info(`Test log ${i}`, {
        test_id: 'manual_test',
        iteration: i
    });
}

console.log('Logs sent! Check server...');

// Graceful shutdown 테스트
setTimeout(() => {
    console.log('Closing...');
    if (logger.close) {
        logger.close();
    }
    console.log('\nTo verify in PostgreSQL:');
    console.log('  psql -h localhost -p 5433 -U postgres -d logs_db');
    console.log('  SELECT * FROM logs WHERE metadata->>\'test_id\' = \'manual_test\';');
    process.exit(0);
}, 3000);
