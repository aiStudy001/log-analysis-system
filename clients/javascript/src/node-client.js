/**
 * Node.js 로그 클라이언트 (Worker Threads 사용)
 *
 * 특징:
 * - 메인 이벤트 루프 영향 없음
 * - 앱 블로킹 < 0.01ms
 * - Graceful shutdown (process.exit)
 */

import { Worker } from 'worker_threads';
import { AsyncLocalStorage } from 'async_hooks';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import { dirname } from 'path';

// ES 모듈에서 __dirname 대체
const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// HTTP 요청 컨텍스트 저장용 (웹 프레임워크 통합용)
const asyncLocalStorage = new AsyncLocalStorage();

// 사용자 컨텍스트 저장용 (user_id, trace_id, session_id 등)
const userContextStorage = new AsyncLocalStorage();

// package.json에서 서비스 정보 자동 로드
let packageInfo = { name: null, version: null };
try {
    // 현재 프로젝트의 package.json 찾기
    const cwd = process.cwd();
    const packagePath = path.join(cwd, 'package.json');
    if (fs.existsSync(packagePath)) {
        packageInfo = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
    }
} catch (err) {
    // package.json 읽기 실패 시 무시
}

class WorkerThreadsLogClient {
    /**
     * @param {string} serverUrl - 로그 서버 URL (기본: 환경 변수 LOG_SERVER_URL)
     * @param {Object} options - 옵션
     * @param {string} options.service - 서비스 이름 (기본: package.json name 또는 환경 변수 SERVICE_NAME)
     * @param {string} options.environment - 환경 (기본: 환경 변수 NODE_ENV 또는 'development')
     * @param {string} options.serviceVersion - 서비스 버전 (기본: package.json version 또는 환경 변수 SERVICE_VERSION)
     * @param {string} options.logType - 로그 타입 (기본: 환경 변수 LOG_TYPE 또는 'BACKEND')
     * @param {number} options.batchSize - 배치 크기
     * @param {number} options.flushInterval - Flush 간격 (ms)
     * @param {boolean} options.enableCompression - 압축 활성화
     * @param {boolean} options.enableGlobalErrorHandler - 글로벌 에러 핸들러 활성화 (기본: false)
     *
     * 환경 변수 우선순위: 명시적 파라미터 > 환경 변수 > package.json > 기본값
     *
     * .env 파일 예시:
     *   LOG_SERVER_URL=http://localhost:8000
     *   SERVICE_NAME=payment-api
     *   NODE_ENV=production
     *   SERVICE_VERSION=v1.2.3
     *   LOG_TYPE=BACKEND
     *   ENABLE_GLOBAL_ERROR_HANDLER=true
     */
    constructor(serverUrl = null, options = {}) {
        // 환경 변수 및 package.json에서 자동 로드
        this.serverUrl = (serverUrl || process.env.LOG_SERVER_URL || 'http://localhost:8000').replace(/\/$/, '');
        this.service = options.service || process.env.SERVICE_NAME || packageInfo.name || null;
        this.environment = options.environment || process.env.NODE_ENV || 'development';
        this.serviceVersion = options.serviceVersion || process.env.SERVICE_VERSION || packageInfo.version || 'v0.0.0-dev';
        this.logType = options.logType || process.env.LOG_TYPE || 'BACKEND';

        this.options = {
            batchSize: options.batchSize || 1000,
            flushInterval: options.flushInterval || 1000,
            enableCompression: options.enableCompression !== false,
            enableGlobalErrorHandler: options.enableGlobalErrorHandler || process.env.ENABLE_GLOBAL_ERROR_HANDLER === 'true'
        };

        this._originalExceptionHandlers = null;

        // Worker Threads 생성
        this._createWorker();

        // Graceful shutdown 설정
        this._setupGracefulShutdown();

        // 글로벌 에러 핸들러 설정 (옵션)
        if (this.options.enableGlobalErrorHandler) {
            this._setupGlobalErrorHandler();
        }
    }

    _createWorker() {
        try {
            this.worker = new Worker(
                path.join(__dirname, 'node-worker.js'),
                {
                    workerData: {
                        serverUrl: this.serverUrl,
                        ...this.options
                    }
                }
            );

            // Worker 에러 핸들링
            this.worker.on('error', (error) => {
                console.error('[Log Client] Worker error:', error);
            });

            // Worker 종료 처리
            this.worker.on('exit', (code) => {
                if (code !== 0) {
                    console.error(`[Log Client] Worker stopped with exit code ${code}`);
                }
            });

        } catch (error) {
            console.error('[Log Client] Failed to create worker:', error);
            throw error;
        }
    }

    _setupGracefulShutdown() {
        // 프로세스 종료 시 큐 비우기
        const shutdownHandler = () => {
            this.flush();
            setTimeout(() => {
                if (this.worker) {
                    this.worker.terminate();
                }
            }, 100);
        };

        process.on('exit', shutdownHandler);
        process.on('SIGINT', shutdownHandler);
        process.on('SIGTERM', shutdownHandler);
    }

    /**
     * 로그 추가 (비블로킹, ~0.01ms)
     * @param {string} level - 로그 레벨
     * @param {string} message - 로그 메시지
     * @param {Object} metadata - 추가 메타데이터
     * @param {boolean} metadata.autoCaller - 호출 위치 자동 추적 활성화 (기본: true)
     */
    log(level, message, metadata = {}) {
        if (!this.worker) {
            console.warn('[Log Client] Worker not initialized');
            return;
        }

        // 공통 필드 자동 추가
        const logEntry = {
            level,
            message,
            created_at: Date.now() / 1000,  // Unix timestamp (초 단위)
            ...metadata
        };

        // 호출 위치 자동 추적 (function_name, file_path) - V8 structured stack trace 사용
        if (metadata.autoCaller !== false && !metadata.function_name) {
            try {
                const originalPrepareStackTrace = Error.prepareStackTrace;
                Error.prepareStackTrace = (err, stack) => stack;

                const err = new Error();
                const stack = err.stack;

                Error.prepareStackTrace = originalPrepareStackTrace;

                // stack[0] = 현재 함수 (log)
                // stack[1] = 호출자 (실제 사용자 코드 또는 편의 메서드)
                // stack[2] = 편의 메서드의 경우 실제 사용자 코드
                const caller = stack[2];

                if (caller) {
                    logEntry.function_name = logEntry.function_name ||
                        caller.getFunctionName() ||
                        caller.getMethodName() ||
                        '<anonymous>';
                    logEntry.file_path = logEntry.file_path || caller.getFileName();
                }
            } catch (err) {
                // 스택 추출 실패 시 무시
            }
        }

        // HTTP 요청 컨텍스트 자동 추가 (웹 프레임워크에서 설정한 경우)
        const requestContext = asyncLocalStorage.getStore();
        if (requestContext) {
            for (const [key, value] of Object.entries(requestContext)) {
                logEntry[key] = logEntry[key] || value;
            }
        }

        // 사용자 컨텍스트 자동 추가 (user_id, trace_id, session_id 등)
        const userContext = userContextStorage.getStore();
        if (userContext) {
            for (const [key, value] of Object.entries(userContext)) {
                logEntry[key] = logEntry[key] || value;
            }
        }

        if (this.service) logEntry.service = logEntry.service || this.service;
        if (this.environment) logEntry.environment = logEntry.environment || this.environment;
        if (this.serviceVersion) logEntry.service_version = logEntry.service_version || this.serviceVersion;
        if (this.logType) logEntry.log_type = logEntry.log_type || this.logType;

        // Worker로 메시지만 전달 (즉시 리턴!)
        this.worker.postMessage({
            type: 'log',
            data: logEntry
        });
    }

    /**
     * HTTP 요청 컨텍스트 설정 (웹 프레임워크 미들웨어에서 사용)
     * @param {Object} context - HTTP 요청 정보 (path, method, ip 등)
     * @param {Function} fn - 실행할 함수
     * @returns {*} fn의 반환값
     *
     * @example
     * // Express 미들웨어
     * app.use((req, res, next) => {
     *     WorkerThreadsLogClient.runWithContext({
     *         path: req.path,
     *         method: req.method,
     *         ip: req.ip
     *     }, () => next());
     * });
     */
    static runWithContext(context, fn) {
        return asyncLocalStorage.run(context, fn);
    }

    /**
     * 현재 HTTP 요청 컨텍스트 조회
     * @returns {Object|undefined} 현재 설정된 컨텍스트
     */
    static getRequestContext() {
        return asyncLocalStorage.getStore();
    }

    /**
     * 사용자 컨텍스트 설정 (애플리케이션 코드에서 사용)
     * @param {Object} context - 사용자 정보 (user_id, trace_id, session_id 등)
     * @param {Function} fn - 실행할 함수
     * @returns {*} fn의 반환값
     *
     * @example
     * // 인증 후 사용자 컨텍스트 설정
     * WorkerThreadsLogClient.runWithUserContext({
     *     user_id: 'user_12345',
     *     trace_id: 'trace_xyz',
     *     session_id: 'sess_abc'
     * }, () => {
     *     logger.info('User action completed');
     *     // → user_id, trace_id, session_id 자동 포함
     *     processPayment();
     * });
     *
     * @example
     * // Promise와 함께 사용
     * await WorkerThreadsLogClient.runWithUserContext(
     *     { user_id: 'user_123' },
     *     async () => {
     *         await fetchUserData();
     *         logger.info('Data fetched');
     *     }
     * );
     */
    static runWithUserContext(context, fn) {
        return userContextStorage.run(context, fn);
    }

    /**
     * 현재 사용자 컨텍스트 조회
     * @returns {Object|undefined} 현재 설정된 컨텍스트
     */
    static getUserContext() {
        return userContextStorage.getStore();
    }

    /**
     * 사용자 컨텍스트 설정 (set/clear 방식)
     * @param {Object} context - 사용자 정보
     *
     * @example
     * // 로그인 시
     * WorkerThreadsLogClient.setUserContext({
     *     user_id: 'user_123',
     *     trace_id: 'trace_xyz'
     * });
     *
     * // 이후 모든 로그에 자동 포함
     * logger.info('User action');
     * // → user_id, trace_id 자동 포함
     *
     * // 로그아웃 시
     * WorkerThreadsLogClient.clearUserContext();
     */
    static setUserContext(context) {
        // AsyncLocalStorage는 기본적으로 enterWith()를 제공하지 않으므로
        // 현재 컨텍스트를 저장하는 방식으로 구현
        // 주의: 이 방식은 동기 코드에서만 안전하게 작동
        // 비동기 작업에는 runWithUserContext() 사용 권장
        console.warn('[Log Client] setUserContext는 동기 코드에서만 안전합니다. 비동기 작업에는 runWithUserContext()를 사용하세요.');
        userContextStorage.enterWith(context);
    }

    /**
     * 사용자 컨텍스트 초기화
     */
    static clearUserContext() {
        userContextStorage.enterWith(undefined);
    }

    /**
     * 타이머 시작
     * @returns {number} 시작 시간 (ms)
     */
    startTimer() {
        return Date.now();
    }

    /**
     * 타이머 종료 및 로그 전송 (duration_ms 자동 계산)
     * @param {number} startTime - startTimer()의 반환값
     * @param {string} level - 로그 레벨
     * @param {string} message - 로그 메시지
     * @param {Object} metadata - 추가 메타데이터
     */
    endTimer(startTime, level, message, metadata = {}) {
        const durationMs = Date.now() - startTime;
        this.log(level, message, { ...metadata, duration_ms: durationMs });
    }

    /**
     * 함수 실행 시간 측정 래퍼
     * @param {Function} fn - 측정할 함수
     * @param {string} message - 로그 메시지 (기본: 함수명)
     * @param {string} level - 로그 레벨 (기본: INFO)
     * @returns {*} 함수 실행 결과
     */
    measure(fn, message = null, level = 'INFO') {
        const startTime = this.startTimer();
        const functionName = fn.name || 'anonymous';

        try {
            const result = fn();

            // Promise 처리
            if (result && typeof result.then === 'function') {
                return result
                    .then(res => {
                        const durationMs = Date.now() - startTime;
                        this.log(level, message || `${functionName} completed`, {
                            duration_ms: durationMs,
                            function_name: functionName
                        });
                        return res;
                    })
                    .catch(err => {
                        const durationMs = Date.now() - startTime;
                        this.errorWithTrace(
                            message || `${functionName} failed`,
                            err,
                            { duration_ms: durationMs, function_name: functionName }
                        );
                        throw err;
                    });
            }

            // 동기 함수 처리
            const durationMs = Date.now() - startTime;
            this.log(level, message || `${functionName} completed`, {
                duration_ms: durationMs,
                function_name: functionName
            });
            return result;

        } catch (err) {
            const durationMs = Date.now() - startTime;
            this.errorWithTrace(
                message || `${functionName} failed`,
                err,
                { duration_ms: durationMs, function_name: functionName }
            );
            throw err;
        }
    }

    /**
     * 에러 로그 + stack_trace 자동 추출
     * @param {string} message - 에러 메시지
     * @param {Error} error - Error 객체
     * @param {Object} metadata - 추가 메타데이터
     */
    errorWithTrace(message, error = null, metadata = {}) {
        let stackTrace = null;
        let errorType = null;
        let functionName = null;
        let filePath = null;

        if (error && error.stack) {
            stackTrace = error.stack;
            errorType = error.name || 'Error';

            // Stack trace 파싱
            const stackLines = stackTrace.split('\n');
            for (const line of stackLines) {
                // 예: "at functionName (/path/to/file.js:123:45)"
                const match = line.match(/at\s+([^\s]+)\s+\(([^:]+):(\d+):(\d+)\)/);
                if (match) {
                    functionName = match[1];
                    filePath = match[2];
                    break;
                }
                // 예: "at /path/to/file.js:123:45"
                const simpleMatch = line.match(/at\s+([^:]+):(\d+):(\d+)/);
                if (simpleMatch) {
                    filePath = simpleMatch[1];
                    break;
                }
            }
        } else {
            // 현재 stack trace 캡처
            const err = new Error();
            stackTrace = err.stack;
        }

        this.log('ERROR', message, {
            ...metadata,
            stack_trace: stackTrace,
            error_type: errorType,
            function_name: functionName,
            file_path: filePath
        });
    }

    /**
     * 수동 flush - 큐에 있는 모든 로그 즉시 전송
     */
    flush() {
        if (this.worker) {
            this.worker.postMessage({ type: 'flush' });
        }
    }

    /**
     * 클라이언트 종료
     */
    async close() {
        if (this.worker) {
            this.flush();
            await new Promise(resolve => setTimeout(resolve, 100));
            await this.worker.terminate();
            this.worker = null;
        }

        // 글로벌 에러 핸들러 해제
        if (this.options.enableGlobalErrorHandler) {
            this._teardownGlobalErrorHandler();
        }
    }

    /**
     * 글로벌 에러 핸들러 설정
     * 모든 uncaught exceptions와 unhandled promise rejections를 자동으로 로깅
     */
    _setupGlobalErrorHandler() {
        // 기존 핸들러 저장
        this._originalExceptionHandlers = {
            uncaughtException: process.listeners('uncaughtException').slice(),
            unhandledRejection: process.listeners('unhandledRejection').slice()
        };

        // Uncaught Exception 핸들러
        process.on('uncaughtException', (error, origin) => {
            this.errorWithTrace('Uncaught exception', error, {
                error_type: 'UncaughtException',
                origin: origin
            });
        });

        // Unhandled Promise Rejection 핸들러
        process.on('unhandledRejection', (reason, promise) => {
            const error = reason instanceof Error ? reason : new Error(String(reason));
            this.errorWithTrace('Unhandled promise rejection', error, {
                error_type: 'UnhandledRejection',
                reason: String(reason)
            });
        });
    }

    /**
     * 글로벌 에러 핸들러 해제
     */
    _teardownGlobalErrorHandler() {
        if (this._originalExceptionHandlers) {
            // 모든 리스너 제거
            process.removeAllListeners('uncaughtException');
            process.removeAllListeners('unhandledRejection');

            // 기존 핸들러 복원
            this._originalExceptionHandlers.uncaughtException.forEach(handler => {
                process.on('uncaughtException', handler);
            });
            this._originalExceptionHandlers.unhandledRejection.forEach(handler => {
                process.on('unhandledRejection', handler);
            });

            this._originalExceptionHandlers = null;
        }
    }

    // 편의 메서드
    trace(message, metadata = {}) { this._logWithCallerAdjustment('TRACE', message, metadata); }
    debug(message, metadata = {}) { this._logWithCallerAdjustment('DEBUG', message, metadata); }
    info(message, metadata = {}) { this._logWithCallerAdjustment('INFO', message, metadata); }
    warn(message, metadata = {}) { this._logWithCallerAdjustment('WARN', message, metadata); }
    error(message, metadata = {}) { this._logWithCallerAdjustment('ERROR', message, metadata); }
    fatal(message, metadata = {}) { this._logWithCallerAdjustment('FATAL', message, metadata); }

    /**
     * 편의 메서드를 위한 로그 호출 (호출자 스택 조정)
     * 편의 메서드를 통해 호출되므로 한 단계 위의 스택을 추적
     */
    _logWithCallerAdjustment(level, message, metadata = {}) {
        if (metadata.autoCaller !== false && !metadata.function_name) {
            try {
                const originalPrepareStackTrace = Error.prepareStackTrace;
                Error.prepareStackTrace = (err, stack) => stack;

                const err = new Error();
                const stack = err.stack;

                Error.prepareStackTrace = originalPrepareStackTrace;

                // stack[0] = 현재 함수 (_logWithCallerAdjustment)
                // stack[1] = 편의 메서드 (info/debug/...)
                // stack[2] = 실제 사용자 코드  ← 우리가 원하는 프레임
                const caller = stack[2];

                if (caller) {
                    metadata.function_name = metadata.function_name ||
                        caller.getFunctionName() ||
                        caller.getMethodName() ||
                        '<anonymous>';
                    metadata.file_path = metadata.file_path || caller.getFileName();
                }
            } catch (err) {
                // 스택 추출 실패 시 무시
            }
        }

        // autoCaller를 false로 설정해서 log()에서 중복 추출 방지
        this.log(level, message, { ...metadata, autoCaller: false });
    }
}

export { WorkerThreadsLogClient };
