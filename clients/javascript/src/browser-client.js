/**
 * 브라우저 로그 클라이언트 (Web Worker 사용)
 *
 * 특징:
 * - 메인 스레드 렉 0% (완전 격리)
 * - 앱 블로킹 < 0.01ms
 * - Graceful shutdown (beforeunload)
 */

export class WebWorkerLogClient {
    /**
     * @param {string} serverUrl - 로그 서버 URL (기본: 환경 변수 VUE_APP_LOG_SERVER_URL 등)
     * @param {Object} options - 옵션
     * @param {string} options.service - 서비스 이름 (기본: 환경 변수에서 읽기)
     * @param {string} options.environment - 환경 (기본: 환경 변수에서 읽기 또는 'development')
     * @param {string} options.serviceVersion - 서비스 버전 (기본: 환경 변수에서 읽기)
     * @param {string} options.logType - 로그 타입 (기본: 환경 변수에서 읽기 또는 'FRONTEND')
     * @param {number} options.batchSize - 배치 크기 (기본: 1000)
     * @param {number} options.flushInterval - Flush 간격 (ms, 기본: 1000)
     * @param {boolean} options.enableCompression - 압축 활성화 (기본: true)
     * @param {boolean} options.enableGlobalErrorHandler - 글로벌 에러 핸들러 활성화 (기본: false)
     *
     * 환경 변수 우선순위: 명시적 파라미터 > 빌드 시점 환경 변수 > 기본값
     *
     * 빌드 시점 환경 변수 예시 (webpack/vite):
     *   - React: REACT_APP_LOG_SERVER_URL
     *   - Vue: VUE_APP_LOG_SERVER_URL
     *   - Vite: VITE_LOG_SERVER_URL
     *
     * .env 파일 예시:
     *   VITE_LOG_SERVER_URL=http://localhost:8000
     *   VITE_SERVICE_NAME=web-app
     *   VITE_ENVIRONMENT=production
     *   VITE_SERVICE_VERSION=v2.1.0
     *   VITE_LOG_TYPE=FRONTEND
     *   VITE_ENABLE_GLOBAL_ERROR_HANDLER=true
     */
    constructor(serverUrl = null, options = {}) {
        // 빌드 시점 환경 변수에서 자동 로드
        // 다양한 프레임워크 지원 (React, Vue, Vite)
        const getEnv = (name) => {
            return (
                typeof process !== 'undefined' && process.env?.[`REACT_APP_${name}`] ||
                typeof process !== 'undefined' && process.env?.[`VUE_APP_${name}`] ||
                typeof process !== 'undefined' && process.env?.[`VITE_${name}`] ||
                typeof import.meta !== 'undefined' && import.meta.env?.[`VITE_${name}`] ||
                null
            );
        };

        this.serverUrl = (serverUrl || getEnv('LOG_SERVER_URL') || 'http://localhost:8000').replace(/\/$/, '');
        this.service = options.service || getEnv('SERVICE_NAME') || null;
        this.environment = options.environment || getEnv('ENVIRONMENT') || 'development';
        this.serviceVersion = options.serviceVersion || getEnv('SERVICE_VERSION') || 'v0.0.0-dev';
        this.logType = options.logType || getEnv('LOG_TYPE') || 'FRONTEND';

        this.options = {
            batchSize: options.batchSize || 1000,
            flushInterval: options.flushInterval || 1000,
            enableCompression: options.enableCompression !== false,
            enableGlobalErrorHandler: options.enableGlobalErrorHandler || false
        };

        // Web Worker 생성
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
            // Worker 스크립트 URL 생성
            this.worker = new Worker(
                new URL('./browser-worker.js', import.meta.url),
                { type: 'module' }
            );

            // Worker 초기화
            this.worker.postMessage({
                type: 'init',
                serverUrl: this.serverUrl,
                ...this.options
            });

            // Worker 에러 핸들링
            this.worker.onerror = (error) => {
                console.error('[Log Client] Worker error:', error);
            };

        } catch (error) {
            console.error('[Log Client] Failed to create worker:', error);
            throw error;
        }
    }

    _setupGracefulShutdown() {
        // 브라우저 종료 시 큐 비우기
        window.addEventListener('beforeunload', () => {
            this.flush();
        });

        // 페이지 숨김 시 (모바일, 탭 전환)
        document.addEventListener('visibilitychange', () => {
            if (document.hidden) {
                this.flush();
            }
        });
    }

    /**
     * 글로벌 에러 핸들러 설정
     * 모든 uncaught errors와 unhandled promise rejections를 자동으로 로깅
     */
    _setupGlobalErrorHandler() {
        // 동기 에러 핸들러
        window.addEventListener('error', (event) => {
            this.errorWithTrace('Uncaught error', event.error || new Error(event.message), {
                source: event.filename,
                line: event.lineno,
                column: event.colno,
                error_type: 'UncaughtError'
            });
        });

        // 비동기 에러 핸들러 (Promise rejection)
        window.addEventListener('unhandledrejection', (event) => {
            const error = event.reason instanceof Error ? event.reason : new Error(String(event.reason));
            this.errorWithTrace('Unhandled promise rejection', error, {
                error_type: 'UnhandledRejection',
                reason: String(event.reason)
            });
        });
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

        // 호출 위치 자동 추적 (function_name, file_path)
        if (metadata.autoCaller !== false && !metadata.function_name) {
            try {
                const stack = new Error().stack;
                const stackLines = stack.split('\n');
                const callerLine = stackLines[2];

                if (callerLine) {
                    // 브라우저 스타일: "    at functionName (http://example.com/file.js:123:45)"
                    let match = callerLine.match(/at\s+([^\s]+)\s+\(([^:]+):\d+:\d+\)/);
                    if (match) {
                        logEntry.function_name = logEntry.function_name || match[1];
                        logEntry.file_path = logEntry.file_path || match[2];
                    } else {
                        // 단순 형식: "    at http://example.com/file.js:123:45"
                        match = callerLine.match(/at\s+([^:]+):\d+:\d+/);
                        if (match) {
                            logEntry.file_path = logEntry.file_path || match[1];
                        }
                    }
                }
            } catch (err) {
                // 스택 추출 실패 시 무시
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
                // 예: "at functionName (http://example.com/file.js:123:45)"
                const match = line.match(/at\s+([^\s]+)\s+\(([^:]+):(\d+):(\d+)\)/);
                if (match) {
                    functionName = match[1];
                    filePath = match[2];
                    break;
                }
                // 예: "at http://example.com/file.js:123:45"
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
    close() {
        if (this.worker) {
            this.flush();
            this.worker.terminate();
            this.worker = null;
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
                const stack = new Error().stack;
                const stackLines = stack.split('\n');
                const callerLine = stackLines[3];

                if (callerLine) {
                    let match = callerLine.match(/at\s+([^\s]+)\s+\(([^:]+):\d+:\d+\)/);
                    if (match) {
                        metadata.function_name = metadata.function_name || match[1];
                        metadata.file_path = metadata.file_path || match[2];
                    } else {
                        match = callerLine.match(/at\s+([^:]+):\d+:\d+/);
                        if (match) {
                            metadata.file_path = metadata.file_path || match[1];
                        }
                    }
                }
            } catch (err) {
                // 스택 추출 실패 시 무시
            }
        }

        // autoCaller를 false로 설정해서 log()에서 중복 추출 방지
        this.log(level, message, { ...metadata, autoCaller: false });
    }
}
