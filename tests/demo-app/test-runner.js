/**
 * 자동화 테스트 스크립트
 * JavaScript와 Python 백엔드의 모든 기능을 테스트
 */

const BASE_URL_JS = 'http://localhost:3001';
const BASE_URL_PY = 'http://localhost:3002';

// 테스트 결과 저장
const results = {
    javascript: { passed: 0, failed: 0, tests: [] },
    python: { passed: 0, failed: 0, tests: [] }
};

/**
 * HTTP 요청 헬퍼
 */
async function request(url, options = {}) {
    const response = await fetch(url, {
        ...options,
        headers: {
            'Content-Type': 'application/json',
            ...options.headers
        }
    });

    const data = await response.json();
    return { status: response.status, data };
}

/**
 * 테스트 실행
 */
async function runTest(backend, testName, testFn) {
    try {
        await testFn();
        results[backend].passed++;
        results[backend].tests.push({ name: testName, status: 'PASSED' });
        console.log(`✅ [${backend}] ${testName}`);
    } catch (error) {
        results[backend].failed++;
        results[backend].tests.push({ name: testName, status: 'FAILED', error: error.message });
        console.log(`❌ [${backend}] ${testName}: ${error.message}`);
    }
}

/**
 * JavaScript 백엔드 테스트
 */
async function testJavaScriptBackend() {
    console.log('\n========================================');
    console.log('JavaScript Backend Tests');
    console.log('========================================\n');

    // 1. GET /api/todos
    await runTest('javascript', 'GET /api/todos', async () => {
        const { status, data } = await request(`${BASE_URL_JS}/api/todos`);
        if (status !== 200) throw new Error(`Expected 200, got ${status}`);
        if (!data.success) throw new Error('Expected success: true');
        if (!Array.isArray(data.todos)) throw new Error('Expected todos array');
    });

    // 2. POST /api/todos
    let todoId;
    await runTest('javascript', 'POST /api/todos', async () => {
        const { status, data } = await request(`${BASE_URL_JS}/api/todos`, {
            method: 'POST',
            body: JSON.stringify({ text: 'Test Todo from automation' })
        });
        if (status !== 200 && status !== 201) throw new Error(`Expected 200/201, got ${status}`);
        if (!data.success) throw new Error('Expected success: true');
        if (!data.todo.id) throw new Error('Expected todo.id');
        todoId = data.todo.id;
    });

    // 3. PUT /api/todos/:id
    await runTest('javascript', 'PUT /api/todos/:id', async () => {
        const { status, data } = await request(`${BASE_URL_JS}/api/todos/${todoId}`, {
            method: 'PUT'
        });
        if (status !== 200) throw new Error(`Expected 200, got ${status}`);
        if (!data.success) throw new Error('Expected success: true');
    });

    // 4. DELETE /api/todos/:id
    await runTest('javascript', 'DELETE /api/todos/:id', async () => {
        const { status, data } = await request(`${BASE_URL_JS}/api/todos/${todoId}`, {
            method: 'DELETE'
        });
        if (status !== 200) throw new Error(`Expected 200, got ${status}`);
        if (!data.success) throw new Error('Expected success: true');
    });

    // 5. GET /api/error
    await runTest('javascript', 'GET /api/error (error handling)', async () => {
        const { status, data } = await request(`${BASE_URL_JS}/api/error`);
        if (status !== 500) throw new Error(`Expected 500, got ${status}`);
        if (!data.error) throw new Error('Expected error field');
    });

    // 6. GET /api/slow
    await runTest('javascript', 'GET /api/slow (timing)', async () => {
        const start = Date.now();
        const { status, data } = await request(`${BASE_URL_JS}/api/slow`);
        const duration = Date.now() - start;

        if (status !== 200) throw new Error(`Expected 200, got ${status}`);
        if (!data.success) throw new Error('Expected success: true');
        if (duration < 2000) throw new Error(`Expected >2s, took ${duration}ms`);
    });
}

/**
 * Python 백엔드 테스트
 */
async function testPythonBackend() {
    console.log('\n========================================');
    console.log('Python Backend Tests');
    console.log('========================================\n');

    // 1. GET /api/todos
    await runTest('python', 'GET /api/todos', async () => {
        const { status, data } = await request(`${BASE_URL_PY}/api/todos`);
        if (status !== 200) throw new Error(`Expected 200, got ${status}`);
        if (!data.success) throw new Error('Expected success: true');
        if (!Array.isArray(data.todos)) throw new Error('Expected todos array');
    });

    // 2. POST /api/todos
    let todoId;
    await runTest('python', 'POST /api/todos', async () => {
        const { status, data } = await request(`${BASE_URL_PY}/api/todos`, {
            method: 'POST',
            body: JSON.stringify({ text: 'Test Todo from automation' })
        });
        if (status !== 200) throw new Error(`Expected 200, got ${status}`);
        if (!data.success) throw new Error('Expected success: true');
        if (!data.todo.id) throw new Error('Expected todo.id');
        todoId = data.todo.id;
    });

    // 3. PUT /api/todos/:id
    await runTest('python', 'PUT /api/todos/:id', async () => {
        const { status, data } = await request(`${BASE_URL_PY}/api/todos/${todoId}`, {
            method: 'PUT'
        });
        if (status !== 200) throw new Error(`Expected 200, got ${status}`);
        if (!data.success) throw new Error('Expected success: true');
    });

    // 4. DELETE /api/todos/:id
    await runTest('python', 'DELETE /api/todos/:id', async () => {
        const { status, data } = await request(`${BASE_URL_PY}/api/todos/${todoId}`, {
            method: 'DELETE'
        });
        if (status !== 200) throw new Error(`Expected 200, got ${status}`);
        if (!data.success) throw new Error('Expected success: true');
    });

    // 5. GET /api/error
    await runTest('python', 'GET /api/error (error handling)', async () => {
        const { status, data } = await request(`${BASE_URL_PY}/api/error`);
        if (status !== 500) throw new Error(`Expected 500, got ${status}`);
        if (!data.detail) throw new Error('Expected detail field');
    });

    // 6. GET /api/slow
    await runTest('python', 'GET /api/slow (timing)', async () => {
        const start = Date.now();
        const { status, data } = await request(`${BASE_URL_PY}/api/slow`);
        const duration = Date.now() - start;

        if (status !== 200) throw new Error(`Expected 200, got ${status}`);
        if (!data.success) throw new Error('Expected success: true');
        if (duration < 2000) throw new Error(`Expected >2s, took ${duration}ms`);
    });
}

/**
 * 결과 출력
 */
function printResults() {
    console.log('\n========================================');
    console.log('Test Results Summary');
    console.log('========================================\n');

    console.log('JavaScript Backend:');
    console.log(`  ✅ Passed: ${results.javascript.passed}`);
    console.log(`  ❌ Failed: ${results.javascript.failed}`);
    console.log(`  Total: ${results.javascript.passed + results.javascript.failed}\n`);

    console.log('Python Backend:');
    console.log(`  ✅ Passed: ${results.python.passed}`);
    console.log(`  ❌ Failed: ${results.python.failed}`);
    console.log(`  Total: ${results.python.passed + results.python.failed}\n`);

    const totalPassed = results.javascript.passed + results.python.passed;
    const totalFailed = results.javascript.failed + results.python.failed;
    const totalTests = totalPassed + totalFailed;

    console.log('Overall:');
    console.log(`  ✅ Passed: ${totalPassed}/${totalTests}`);
    console.log(`  ❌ Failed: ${totalFailed}/${totalTests}`);
    console.log(`  Success Rate: ${((totalPassed / totalTests) * 100).toFixed(1)}%\n`);

    if (totalFailed > 0) {
        console.log('Failed Tests:');
        results.javascript.tests
            .filter(t => t.status === 'FAILED')
            .forEach(t => console.log(`  ❌ [JS] ${t.name}: ${t.error}`));
        results.python.tests
            .filter(t => t.status === 'FAILED')
            .forEach(t => console.log(`  ❌ [PY] ${t.name}: ${t.error}`));
        console.log('');
    }
}

/**
 * 메인 실행
 */
async function main() {
    console.log('🚀 Starting automated tests...\n');

    try {
        await testJavaScriptBackend();
        await testPythonBackend();
        printResults();

        const totalFailed = results.javascript.failed + results.python.failed;
        process.exit(totalFailed > 0 ? 1 : 0);
    } catch (error) {
        console.error('❌ Test runner error:', error);
        process.exit(1);
    }
}

main();
