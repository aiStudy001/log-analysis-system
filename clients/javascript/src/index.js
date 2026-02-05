/**
 * 로그 수집 클라이언트 - 진입점
 *
 * 환경에 따라 최적 구현 자동 선택:
 * - 브라우저: Web Worker (렉 0%)
 * - Node.js: Worker Threads
 */

import { WorkerThreadsLogClient } from './node-client.js';

/**
 * 로그 클라이언트 생성
 * @param {string} serverUrl - 로그 서버 URL
 * @param {Object} options - 옵션
 * @returns {Object} 로그 클라이언트 인스턴스
 */
export function createLogClient(serverUrl, options = {}) {
    // 브라우저 환경은 번들러를 통해 처리됨
    // Node.js 환경
    if (typeof process !== 'undefined' && process.versions && process.versions.node) {
        return new WorkerThreadsLogClient(serverUrl, options);
    }
    else {
        throw new Error('Unsupported environment. Requires Node.js 12+ or browser with bundler');
    }
}

// 기본 내보내기
export default { createLogClient };
