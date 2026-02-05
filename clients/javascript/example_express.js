/**
 * Express HTTP 컨텍스트 자동 수집 예제
 *
 * 실행 방법:
 *     npm install express
 *     node example_express.js
 *
 * 테스트:
 *     curl http://localhost:3000/api/users/123
 *     curl -X POST http://localhost:3000/api/users -H "Content-Type: application/json" -d '{"name":"John"}'
 */
const express = require('express');
const { WorkerThreadsLogClient } = require('./src/node-client');

const app = express();
app.use(express.json());

// 로그 클라이언트 초기화
const logger = new WorkerThreadsLogClient('http://localhost:8000', {
    service: 'express-example',
    environment: 'development'
});

// HTTP 컨텍스트 미들웨어
app.use((req, res, next) => {
    WorkerThreadsLogClient.runWithContext({
        path: req.path,
        method: req.method,
        ip: req.ip
    }, () => {
        const startTime = Date.now();

        // 요청 시작 로그
        logger.info(`Request started: ${req.method} ${req.path}`);

        // 응답 후킹
        res.on('finish', () => {
            const durationMs = Date.now() - startTime;
            logger.info(`Request completed: ${res.statusCode}`, {
                status_code: res.statusCode,
                duration_ms: durationMs
            });
        });

        next();
    });
});

// 라우트
app.get('/api/users/:userId', (req, res) => {
    const { userId } = req.params;

    logger.info('Fetching user from database', { user_id: userId });
    // 자동으로 포함됨: path="/api/users/123", method="GET", ip="::1"

    // 가짜 데이터
    const user = { id: userId, name: `User ${userId}` };

    logger.info('User fetched successfully', { user_id: userId });
    res.json({ user });
});

app.post('/api/users', (req, res) => {
    const { name } = req.body;

    logger.info('Creating new user', { username: name });
    // 자동으로 포함됨: path="/api/users", method="POST", ip="::1"

    // 가짜 생성
    const newUser = { id: 999, name };

    logger.info('User created successfully', { user_id: newUser.id });
    res.status(201).json({ user: newUser });
});

app.get('/api/error', (req, res) => {
    logger.warn('About to trigger an error');

    try {
        throw new Error('This is a test error');
    } catch (err) {
        logger.errorWithTrace('Error occurred', err);
        // HTTP 컨텍스트도 에러 로그에 포함됨
        res.status(500).json({ error: err.message });
    }
});

// 서버 시작
const PORT = 3000;
app.listen(PORT, () => {
    logger.info('Server started', { port: PORT });
    console.log(`Starting Express server on port ${PORT}...`);
    console.log('Test with:');
    console.log(`  curl http://localhost:${PORT}/api/users/123`);
    console.log(`  curl -X POST http://localhost:${PORT}/api/users -H "Content-Type: application/json" -d '{"name":"John"}'`);
    console.log(`  curl http://localhost:${PORT}/api/error`);
    console.log('\nCheck logs in PostgreSQL:');
    console.log('  SELECT path, method, ip, function_name, message FROM logs ORDER BY created_at DESC LIMIT 10;');
});
