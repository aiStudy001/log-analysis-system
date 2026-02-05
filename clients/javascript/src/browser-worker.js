/**
 * 브라우저 Web Worker 스크립트
 *
 * 백그라운드에서 실행되어 메인 스레드에 영향 없이 로그 전송
 */

let queue = [];
let serverUrl = '';
let batchSize = 1000;
let flushInterval = 1000;
let enableCompression = true;
let maxQueueSize = 10000;
let flushTimer = null;

// 메인 스레드로부터 메시지 수신
self.onmessage = (event) => {
    const { type, data } = event.data;

    switch (type) {
        case 'init':
            // 초기화
            serverUrl = event.data.serverUrl;
            batchSize = event.data.batchSize || 1000;
            flushInterval = event.data.flushInterval || 1000;
            enableCompression = event.data.enableCompression !== false;
            startFlushLoop();
            break;

        case 'log':
            // 로그 추가
            queue.push(data);

            // 큐 크기 제한
            if (queue.length > maxQueueSize) {
                queue.shift(); // 오래된 로그 제거
            }

            // 배치 크기 도달 시 즉시 전송
            if (queue.length >= batchSize) {
                sendBatch();
            }
            break;

        case 'flush':
            // 강제 flush
            if (queue.length > 0) {
                sendBatch();
            }
            break;

        default:
            console.warn('[Worker] Unknown message type:', type);
    }
};

/**
 * 주기적 flush 루프 시작
 */
function startFlushLoop() {
    if (flushTimer) {
        clearInterval(flushTimer);
    }

    flushTimer = setInterval(() => {
        if (queue.length > 0 && queue.length < batchSize) {
            // 배치 크기에 도달하지 않았지만 시간이 지나면 전송
            sendBatch();
        }
    }, flushInterval);
}

/**
 * 배치 전송
 */
async function sendBatch() {
    if (queue.length === 0) return;

    // 큐에서 배치 추출
    const batch = queue.splice(0, Math.min(batchSize, queue.length));

    try {
        // JSON 직렬화
        let payload = JSON.stringify({ logs: batch });
        let headers = { 'Content-Type': 'application/json' };

        // 압축 (100건 이상)
        if (enableCompression && batch.length >= 100) {
            // 브라우저에서는 CompressionStream API 사용 (Chrome 80+)
            if (typeof CompressionStream !== 'undefined') {
                const stream = new Response(payload).body
                    .pipeThrough(new CompressionStream('gzip'));
                payload = await new Response(stream).blob();
                headers['Content-Encoding'] = 'gzip';
            }
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

// Worker 에러 핸들링
self.onerror = (error) => {
    console.error('[Worker] Error:', error);
};
