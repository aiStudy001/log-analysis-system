/**
 * Node.js Worker Threads 스크립트
 *
 * 백그라운드에서 실행되어 메인 이벤트 루프에 영향 없이 로그 전송
 */

import { parentPort, workerData } from 'worker_threads';
import zlib from 'zlib';
import { promisify } from 'util';
const gzip = promisify(zlib.gzip);

// node-fetch 동적 import (Node.js 18+ 내장 fetch 사용 또는 폴백)
let fetch;
(async () => {
    if (typeof globalThis.fetch !== 'undefined') {
        fetch = globalThis.fetch;
    } else {
        const nodeFetch = await import('node-fetch');
        fetch = nodeFetch.default;
    }
})();

let queue = [];
const { serverUrl, batchSize, flushInterval, enableCompression } = workerData;
const maxQueueSize = 10000;
let flushTimer = null;

// 메인 스레드로부터 메시지 수신
if (parentPort) {
    parentPort.on('message', async (message) => {
        const { type, data } = message;

        switch (type) {
            case 'log':
                // 로그 추가
                queue.push(data);

                // 큐 크기 제한
                if (queue.length > maxQueueSize) {
                    queue.shift();
                }

                // 배치 크기 도달 시 즉시 전송
                if (queue.length >= batchSize) {
                    await sendBatch();
                }
                break;

            case 'flush':
                // 강제 flush
                if (queue.length > 0) {
                    await sendBatch();
                }
                break;

            default:
                console.warn('[Worker] Unknown message type:', type);
        }
    });
}

/**
 * 주기적 flush 루프 시작
 */
function startFlushLoop() {
    if (flushTimer) {
        clearInterval(flushTimer);
    }

    flushTimer = setInterval(async () => {
        if (queue.length > 0 && queue.length < batchSize) {
            await sendBatch();
        }
    }, flushInterval);
}

/**
 * 배치 전송
 */
async function sendBatch() {
    if (queue.length === 0) return;
    if (!fetch) {
        console.warn('[Worker] Fetch not available yet');
        return;
    }

    // 큐에서 배치 추출
    const batch = queue.splice(0, Math.min(batchSize, queue.length));

    try {
        // JSON 직렬화
        let payload = JSON.stringify({ logs: batch });
        let headers = { 'Content-Type': 'application/json' };

        // gzip 압축 (100건 이상)
        if (enableCompression && batch.length >= 100) {
            payload = await gzip(Buffer.from(payload));
            headers['Content-Encoding'] = 'gzip';
        }

        // HTTP POST
        const response = await fetch(`${serverUrl}/logs`, {
            method: 'POST',
            headers: headers,
            body: payload
        });

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

    } catch (error) {
        console.error('[Worker] Log send failed:', error);
        // 실패한 로그는 큐 맨 앞에 다시 추가 (재시도)
        queue.unshift(...batch);
    }
}

// Worker 시작 시 flush 루프 시작
startFlushLoop();

// Worker 종료 처리
process.on('exit', async () => {
    if (queue.length > 0) {
        await sendBatch();
    }
});
