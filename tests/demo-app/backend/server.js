import express from 'express';
import cors from 'cors';
import { v4 as uuidv4 } from 'uuid';
import { createLogClient } from 'log-collector-async';

const app = express();
const PORT = 3001;

// ============================================================================
// 로거 초기화
// ============================================================================
const logger = createLogClient('http://localhost:8000', {
    service: 'demo-todo-backend',
    environment: 'development'
});

console.log('✅ 로거 초기화 완료');

// ============================================================================
// 미들웨어
// ============================================================================
app.use(cors());
app.use(express.json());

// HTTP 컨텍스트 자동 수집 미들웨어
app.use((req, res, next) => {
    // 요청 시작 시간
    req.startTime = Date.now();

    // trace_id 생성 (클라이언트에서 전달되거나 새로 생성)
    req.traceId = req.headers['x-trace-id'] || uuidv4().replace(/-/g, '').substring(0, 32);

    // HTTP 컨텍스트를 req 객체에 저장
    req.logContext = {
        path: req.path,
        method: req.method,
        ip: req.ip,
        trace_id: req.traceId
    };

    // 사용자 컨텍스트 추가 (로그인된 경우)
    if (req.headers['x-user-id']) {
        req.logContext.user_id = req.headers['x-user-id'];
    }

    logger.info('Request received', req.logContext);

    // 응답 완료 시
    res.on('finish', () => {
        const duration = Date.now() - req.startTime;
        logger.info('Request completed', {
            ...req.logContext,
            status_code: res.statusCode,
            duration_ms: duration
        });
    });

    next();
});

// ============================================================================
// 인메모리 데이터 저장소
// ============================================================================
let todos = [
    { id: '1', text: '첫 번째 할 일', completed: false, userId: 'user_demo' },
    { id: '2', text: '두 번째 할 일', completed: true, userId: 'user_demo' },
];

let users = {
    'demo': { id: 'user_demo', username: 'demo', password: 'demo123' }
};

// ============================================================================
// API 엔드포인트
// ============================================================================

// 로그인
app.post('/api/login', (req, res) => {
    const { username, password } = req.body;

    logger.info('Login attempt', { ...req.logContext, username });

    if (!username || !password) {
        logger.warn('Login failed: missing credentials', req.logContext);
        return res.status(400).json({ error: 'Username and password required' });
    }

    const user = users[username];
    if (!user || user.password !== password) {
        logger.warn('Login failed: invalid credentials', { ...req.logContext, username });
        return res.status(401).json({ error: 'Invalid credentials' });
    }

    logger.info('Login successful', { ...req.logContext, user_id: user.id, username });

    res.json({
        success: true,
        user: { id: user.id, username: user.username },
        traceId: req.traceId
    });
});

// Todo 리스트 조회
app.get('/api/todos', (req, res) => {
    const userId = req.headers['x-user-id'] || 'user_demo';

    logger.info('Fetching todos', { ...req.logContext, count: todos.length });

    const userTodos = todos.filter(todo => todo.userId === userId);

    res.json({
        success: true,
        todos: userTodos
    });
});

// Todo 생성
app.post('/api/todos', (req, res) => {
    const { text } = req.body;
    const userId = req.headers['x-user-id'] || 'user_demo';

    if (!text) {
        logger.warn('Todo creation failed: missing text', req.logContext);
        return res.status(400).json({ error: 'Text is required' });
    }

    const newTodo = {
        id: uuidv4(),
        text,
        completed: false,
        userId
    };

    todos.push(newTodo);

    logger.info('Todo created', {
        ...req.logContext,
        todo_id: newTodo.id,
        text: newTodo.text
    });

    res.status(201).json({
        success: true,
        todo: newTodo
    });
});

// Todo 완료 토글
app.put('/api/todos/:id', (req, res) => {
    const { id } = req.params;
    const userId = req.headers['x-user-id'] || 'user_demo';

    const todo = todos.find(t => t.id === id && t.userId === userId);

    if (!todo) {
        logger.warn('Todo not found', { ...req.logContext, todo_id: id });
        return res.status(404).json({ error: 'Todo not found' });
    }

    todo.completed = !todo.completed;

    logger.info('Todo updated', {
        ...req.logContext,
        todo_id: id,
        completed: todo.completed
    });

    res.json({
        success: true,
        todo
    });
});

// Todo 삭제
app.delete('/api/todos/:id', (req, res) => {
    const { id } = req.params;
    const userId = req.headers['x-user-id'] || 'user_demo';

    const index = todos.findIndex(t => t.id === id && t.userId === userId);

    if (index === -1) {
        logger.warn('Todo not found for deletion', { ...req.logContext, todo_id: id });
        return res.status(404).json({ error: 'Todo not found' });
    }

    const deletedTodo = todos.splice(index, 1)[0];

    logger.info('Todo deleted', {
        ...req.logContext,
        todo_id: id,
        text: deletedTodo.text
    });

    res.json({
        success: true,
        todo: deletedTodo
    });
});

// 의도적 에러 (테스트용)
app.get('/api/error', (req, res) => {
    logger.warn('Error endpoint called', req.logContext);

    try {
        // 의도적으로 에러 발생
        throw new Error('This is a test error!');
    } catch (err) {
        logger.errorWithTrace('Intentional error occurred', err, {
            ...req.logContext,
            test: true
        });

        res.status(500).json({
            error: 'Internal server error',
            message: err.message
        });
    }
});

// 느린 API (타이머 테스트)
app.get('/api/slow', async (req, res) => {
    const timer = logger.startTimer();

    logger.info('Slow API called', req.logContext);

    // 2초 대기
    await new Promise(resolve => setTimeout(resolve, 2000));

    logger.endTimer(timer, 'INFO', 'Slow API completed', req.logContext);

    res.json({
        success: true,
        message: 'This took 2 seconds'
    });
});

// ============================================================================
// 서버 시작
// ============================================================================
app.listen(PORT, () => {
    console.log('='.repeat(60));
    console.log(`✅ Todo Backend Server running on http://localhost:${PORT}`);
    console.log('='.repeat(60));

    logger.info('Server started', { port: PORT });
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\nShutting down gracefully...');
    logger.info('Server shutting down');
    logger.flush();

    setTimeout(async () => {
        await logger.close();
        process.exit(0);
    }, 1000);
});
