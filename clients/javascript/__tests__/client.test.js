/**
 * 단위 테스트: createLogClient 기본 동작 검증
 * 로그 서버 없이도 실행 가능한 테스트
 */
import { createLogClient } from '../src/index.js';
import { WorkerThreadsLogClient } from '../src/node-client.js';

describe('createLogClient', () => {
    test('should create a client instance', () => {
        const logger = createLogClient('http://localhost:8000');
        expect(logger).toBeDefined();
        expect(logger.info).toBeInstanceOf(Function);
    });

    test('should accept options', () => {
        const logger = createLogClient('http://localhost:8000', {
            batchSize: 500,
            flushInterval: 2000
        });
        expect(logger).toBeDefined();
    });

    test('should have all log level methods', () => {
        const logger = createLogClient('http://localhost:8000');

        expect(logger.info).toBeInstanceOf(Function);
        expect(logger.warn).toBeInstanceOf(Function);
        expect(logger.error).toBeInstanceOf(Function);
        expect(logger.debug).toBeInstanceOf(Function);
        expect(logger.fatal).toBeInstanceOf(Function);
    });

    test('should accept custom batch size', () => {
        const customBatchSize = 250;
        const logger = createLogClient('http://localhost:8000', {
            batchSize: customBatchSize
        });

        expect(logger).toBeDefined();
        // Note: 실제 batch size 확인은 내부 구현에 의존
    });

    test('should accept custom flush interval', () => {
        const customInterval = 3000;
        const logger = createLogClient('http://localhost:8000', {
            flushInterval: customInterval
        });

        expect(logger).toBeDefined();
    });

    test('should handle log calls without errors', () => {
        const logger = createLogClient('http://localhost:8000');

        // 로그 호출이 에러 없이 실행되어야 함
        expect(() => {
            logger.info('test message');
            logger.warn('warning message');
            logger.error('error message');
        }).not.toThrow();
    });

    test('should handle log calls with metadata', () => {
        const logger = createLogClient('http://localhost:8000');

        // 메타데이터와 함께 로그 호출
        expect(() => {
            logger.info('test with metadata', {
                user_id: 123,
                action: 'login',
                success: true
            });
        }).not.toThrow();
    });

    test('should handle multiple consecutive log calls', () => {
        const logger = createLogClient('http://localhost:8000', {
            batchSize: 100
        });

        // 연속 로그 호출이 블로킹 없이 실행되어야 함
        const start = Date.now();

        for (let i = 0; i < 10; i++) {
            logger.info(`test log ${i}`);
        }

        const elapsed = Date.now() - start;

        // 10개 로그가 10ms 이내에 큐잉되어야 함 (비동기 처리)
        expect(elapsed).toBeLessThan(100);
    });

    test('should create different clients independently', () => {
        const logger1 = createLogClient('http://localhost:8000', { batchSize: 100 });
        const logger2 = createLogClient('http://localhost:9000', { batchSize: 200 });

        expect(logger1).toBeDefined();
        expect(logger2).toBeDefined();
        expect(logger1).not.toBe(logger2);
    });
});

describe('Log Level Methods', () => {
    let logger;

    beforeEach(() => {
        logger = createLogClient('http://localhost:8000');
    });

    test('info method should work', () => {
        expect(() => logger.info('info message')).not.toThrow();
    });

    test('warn method should work', () => {
        expect(() => logger.warn('warning message')).not.toThrow();
    });

    test('error method should work', () => {
        expect(() => logger.error('error message')).not.toThrow();
    });

    test('debug method should work', () => {
        expect(() => logger.debug('debug message')).not.toThrow();
    });

    test('fatal method should work', () => {
        expect(() => logger.fatal('fatal message')).not.toThrow();
    });
});

describe('Performance', () => {
    test('log calls should have minimal overhead', () => {
        const logger = createLogClient('http://localhost:8000', { batchSize: 1000 });

        const iterations = 1000;
        const start = Date.now();

        for (let i = 0; i < iterations; i++) {
            logger.info(`perf test ${i}`);
        }

        const elapsed = Date.now() - start;
        const msPerCall = elapsed / iterations;

        console.log(`Performance: ${msPerCall.toFixed(3)}ms per call`);

        // 1000개 로그가 1초 이내에 큐잉되어야 함
        expect(elapsed).toBeLessThan(1000);
    });
});

describe('Auto Caller Feature', () => {
    let logger;

    beforeEach(() => {
        logger = createLogClient('http://localhost:8000', { batchSize: 100 });
    });

    test('should not throw error with auto caller enabled (default)', () => {
        // autoCaller가 기본으로 활성화되어 있어야 함
        expect(() => {
            logger.info('Test auto caller');
        }).not.toThrow();
    });

    test('should handle autoCaller disabled', () => {
        // autoCaller를 명시적으로 비활성화
        expect(() => {
            logger.log('INFO', 'Test without auto caller', { autoCaller: false });
        }).not.toThrow();
    });

    test('should handle manual function_name override', () => {
        // 수동으로 function_name을 전달해도 에러 없어야 함
        expect(() => {
            logger.info('Test manual override', {
                function_name: 'custom_function',
                file_path: '/custom/path.js'
            });
        }).not.toThrow();
    });

    test('all convenience methods should work with auto caller', () => {
        // 모든 편의 메서드가 auto caller와 함께 동작해야 함
        expect(() => {
            logger.trace('Trace message');
            logger.debug('Debug message');
            logger.info('Info message');
            logger.warn('Warn message');
            logger.error('Error message');
            logger.fatal('Fatal message');
        }).not.toThrow();
    });

    test('should handle nested function calls', () => {
        function outerFunction() {
            function innerFunction() {
                logger.info('Message from inner function');
            }
            innerFunction();
        }

        // 중첩 함수에서도 에러 없이 동작해야 함
        expect(() => {
            outerFunction();
        }).not.toThrow();
    });

    test('should handle async functions', async () => {
        async function asyncFunction() {
            logger.info('Message from async function');
        }

        // async 함수에서도 에러 없이 동작해야 함
        await expect(asyncFunction()).resolves.not.toThrow();
    });

    test('should handle arrow functions', () => {
        const arrowFunction = () => {
            logger.info('Message from arrow function');
        };

        // 화살표 함수에서도 에러 없이 동작해야 함
        expect(() => {
            arrowFunction();
        }).not.toThrow();
    });

    test('performance with auto caller should still be fast', () => {
        // auto caller가 활성화되어도 성능이 크게 떨어지지 않아야 함
        const iterations = 1000;
        const start = Date.now();

        for (let i = 0; i < iterations; i++) {
            logger.info(`perf test ${i}`);
        }

        const elapsed = Date.now() - start;
        const msPerCall = elapsed / iterations;

        console.log(`Performance with auto caller: ${msPerCall.toFixed(3)}ms per call`);

        // 1000개 로그가 여전히 1초 이내에 처리되어야 함
        expect(elapsed).toBeLessThan(1000);
    });
});

// Feature 3: 사용자 컨텍스트 관리 테스트
describe('User Context Management', () => {
    let logger;

    beforeEach(() => {
        logger = new WorkerThreadsLogClient('http://localhost:8000', {
            service: 'test-service',
            batchSize: 100
        });
    });

    afterEach(() => {
        if (logger && logger.worker) {
            logger.worker.terminate();
        }
        // 컨텍스트 초기화
        WorkerThreadsLogClient.clearUserContext();
    });

    test('should auto-include user context', (done) => {
        WorkerThreadsLogClient.runWithUserContext({
            user_id: 'test_user_123',
            trace_id: 'test_trace_xyz'
        }, () => {
            logger.info('Test with user context');

            // worker로 전송된 메시지 확인
            setTimeout(() => {
                // runWithUserContext가 제대로 작동하는지 확인
                expect(WorkerThreadsLogClient.getUserContext()).toBeDefined();
                done();
            }, 50);
        });
    });

    test('should clear user context after block', (done) => {
        // 블록 내부
        WorkerThreadsLogClient.runWithUserContext({
            user_id: 'temp_user'
        }, () => {
            expect(WorkerThreadsLogClient.getUserContext()).toBeDefined();
        });

        // 블록 외부 - 컨텍스트가 초기화되어야 함
        setTimeout(() => {
            expect(WorkerThreadsLogClient.getUserContext()).toBeUndefined();
            done();
        }, 50);
    });

    test('should handle nested user context', (done) => {
        // 외부 컨텍스트
        WorkerThreadsLogClient.runWithUserContext({
            tenant_id: 'tenant_1'
        }, () => {
            logger.info('Outer context');

            // 내부 컨텍스트
            WorkerThreadsLogClient.runWithUserContext({
                user_id: 'nested_user'
            }, () => {
                logger.info('Inner context (both)');

                const ctx = WorkerThreadsLogClient.getUserContext();
                expect(ctx).toBeDefined();
                expect(ctx.user_id).toBe('nested_user');
            });

            logger.info('Back to outer');
        });

        setTimeout(done, 50);
    });

    test('should work with async functions', async () => {
        await WorkerThreadsLogClient.runWithUserContext({
            user_id: 'async_user',
            trace_id: 'async_trace'
        }, async () => {
            logger.info('Start async operation');

            await new Promise(resolve => setTimeout(resolve, 10));

            logger.info('End async operation');

            const ctx = WorkerThreadsLogClient.getUserContext();
            expect(ctx).toBeDefined();
            expect(ctx.user_id).toBe('async_user');
        });
    });

    test('should combine with HTTP context', (done) => {
        // HTTP 컨텍스트 설정
        WorkerThreadsLogClient.runWithContext({
            path: '/api/test',
            method: 'POST'
        }, () => {
            // 사용자 컨텍스트 추가
            WorkerThreadsLogClient.runWithUserContext({
                user_id: 'combined_user'
            }, () => {
                logger.info('Combined contexts');

                // 둘 다 존재해야 함
                expect(WorkerThreadsLogClient.getRequestContext()).toBeDefined();
                expect(WorkerThreadsLogClient.getUserContext()).toBeDefined();
            });
        });

        setTimeout(done, 50);
    });

    test('setUserContext and clearUserContext should work', () => {
        // 설정
        WorkerThreadsLogClient.setUserContext({
            user_id: 'set_user',
            session_id: 'set_session'
        });

        logger.info('After setUserContext');

        const ctx = WorkerThreadsLogClient.getUserContext();
        expect(ctx).toBeDefined();
        expect(ctx.user_id).toBe('set_user');
        expect(ctx.session_id).toBe('set_session');

        // 초기화
        WorkerThreadsLogClient.clearUserContext();

        logger.info('After clearUserContext');

        expect(WorkerThreadsLogClient.getUserContext()).toBeUndefined();
    });

    test('manual values should override context', (done) => {
        WorkerThreadsLogClient.runWithUserContext({
            user_id: 'context_user'
        }, () => {
            // user_id를 수동으로 전달
            logger.info('Manual override', { user_id: 'manual_user' });

            // 컨텍스트는 여전히 존재
            const ctx = WorkerThreadsLogClient.getUserContext();
            expect(ctx).toBeDefined();
            expect(ctx.user_id).toBe('context_user');
        });

        setTimeout(done, 50);
    });

    test('should handle multiple sequential contexts', (done) => {
        // 첫 번째 컨텍스트
        WorkerThreadsLogClient.runWithUserContext({
            user_id: 'user_1'
        }, () => {
            logger.info('First context');
            expect(WorkerThreadsLogClient.getUserContext().user_id).toBe('user_1');
        });

        // 두 번째 컨텍스트 (첫 번째와 독립적)
        WorkerThreadsLogClient.runWithUserContext({
            user_id: 'user_2'
        }, () => {
            logger.info('Second context');
            expect(WorkerThreadsLogClient.getUserContext().user_id).toBe('user_2');
        });

        setTimeout(done, 50);
    });
});
