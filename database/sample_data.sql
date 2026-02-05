-- 샘플 로그 데이터 생성 스크립트
-- 200개의 다양한 로그를 생성합니다

-- 1. 정상 로그 (INFO) - 100개
INSERT INTO logs (
    level, log_type, service, environment, service_version,
    trace_id, user_id, session_id,
    message, path, method, duration_ms,
    created_at, deleted
)
SELECT
    'INFO'::log_level,
    'BACKEND'::source_type,
    (ARRAY['payment-api', 'user-api', 'order-api', 'auth-api'])[floor(random() * 4 + 1)],
    'production'::env_type,
    'v1.0.' || floor(random() * 10),
    'trace_' || substring(md5(random()::text), 1, 26),
    'user_' || (1000 + floor(random() * 100)),
    'session_' || md5(random()::text),
    'Request processed successfully',
    '/api/v1/' || (ARRAY['users', 'orders', 'payments', 'products'])[floor(random() * 4 + 1)],
    (ARRAY['GET', 'POST', 'PUT'])[floor(random() * 3 + 1)]::http_method,
    50 + random() * 750,  -- 개선: 50-800ms (정상 응답)
    NOW() - (random() * interval '24 hours'),
    FALSE
FROM generate_series(1, 100);

-- 2. 경고 로그 (WARN) - 30개
INSERT INTO logs (
    level, log_type, service, environment, service_version,
    trace_id, user_id, message, path, method, duration_ms,
    created_at, deleted
)
SELECT
    'WARN'::log_level,
    'BACKEND'::source_type,
    (ARRAY['payment-api', 'user-api', 'order-api', 'auth-api'])[floor(random() * 4 + 1)],
    'production'::env_type,
    'v1.0.' || floor(random() * 10),
    'trace_' || substring(md5(random()::text), 1, 26),
    'user_' || (1000 + floor(random() * 100)),
    'Slow query detected - took ' || (800 + floor(random() * 2200))::text || 'ms',
    '/api/v1/' || (ARRAY['users', 'orders', 'payments'])[floor(random() * 3 + 1)],
    (ARRAY['GET', 'POST'])[floor(random() * 2 + 1)]::http_method,
    800 + random() * 2200,  -- 개선: 800-3000ms (느린 응답)
    NOW() - (random() * interval '24 hours'),
    FALSE
FROM generate_series(1, 30);

-- 3. 에러 로그 (ERROR) - 50개
INSERT INTO logs (
    level, log_type, service, environment, service_version,
    trace_id, user_id, error_type, message, stack_trace,
    path, method, duration_ms,
    created_at, deleted
)
SELECT
    'ERROR'::log_level,
    'BACKEND'::source_type,
    (ARRAY['payment-api', 'user-api', 'order-api', 'auth-api'])[floor(random() * 4 + 1)],
    'production'::env_type,
    'v1.0.' || floor(random() * 10),
    'trace_' || substring(md5(random()::text), 1, 26),
    'user_' || (1000 + floor(random() * 100)),
    (ARRAY['DatabaseConnectionError', 'TimeoutError', 'ValidationError', 'AuthenticationError', 'NetworkError'])[floor(random() * 5 + 1)],
    'Error occurred during request processing',
    E'Error: Connection timeout\n  at DatabasePool.query (db.js:45)\n  at UserService.getUser (user.service.js:23)\n  at main (index.js:12)',
    '/api/v1/' || (ARRAY['users', 'orders', 'payments'])[floor(random() * 3 + 1)],
    (ARRAY['GET', 'POST', 'PUT', 'DELETE'])[floor(random() * 4 + 1)]::http_method,
    1000 + random() * 4000,  -- 개선: 1000-5000ms (에러 시 매우 느림)
    NOW() - (random() * interval '24 hours'),
    FALSE
FROM generate_series(1, 50);

-- 4. 디버그 로그 (DEBUG) - 20개
INSERT INTO logs (
    level, log_type, service, environment, service_version,
    trace_id, message, function_name, file_path,
    created_at, deleted
)
SELECT
    'DEBUG'::log_level,
    'BACKEND'::source_type,
    (ARRAY['payment-api', 'user-api', 'order-api', 'auth-api'])[floor(random() * 4 + 1)],
    'development'::env_type,
    'v1.0.' || floor(random() * 10),
    'trace_' || substring(md5(random()::text), 1, 26),
    'Debug: Variable value = ' || floor(random() * 1000),
    (ARRAY['processRequest', 'validateInput', 'executeQuery', 'handleResponse'])[floor(random() * 4 + 1)],
    '/src/services/' || (ARRAY['user', 'payment', 'order'])[floor(random() * 3 + 1)] || '.service.js',
    NOW() - (random() * interval '24 hours'),
    FALSE
FROM generate_series(1, 20);

-- 5. 프론트엔드 로그 (FRONTEND) - 30개
INSERT INTO logs (
    level, log_type, service, environment, service_version,
    trace_id, user_id, session_id,
    message, path, action_type,
    created_at, deleted,
    metadata
)
SELECT
    (ARRAY['INFO', 'WARN', 'ERROR'])[floor(random() * 3 + 1)]::log_level,
    'FRONTEND'::source_type,
    'web-app',
    'production'::env_type,
    'v2.5.0',
    'trace_' || substring(md5(random()::text), 1, 26),
    'user_' || (1000 + floor(random() * 100)),
    'session_' || md5(random()::text),
    (ARRAY['Page loaded', 'Button clicked', 'Form submitted', 'Navigation completed'])[floor(random() * 4 + 1)],
    (ARRAY['/home', '/dashboard', '/profile', '/checkout', '/payment'])[floor(random() * 5 + 1)],
    (ARRAY['click', 'submit', 'navigate', 'load'])[floor(random() * 4 + 1)],
    NOW() - (random() * interval '24 hours'),
    FALSE,
    jsonb_build_object(
        'browser', (ARRAY['Chrome', 'Firefox', 'Safari', 'Edge'])[floor(random() * 4 + 1)],
        'device', (ARRAY['Desktop', 'Mobile', 'Tablet'])[floor(random() * 3 + 1)],
        'screen_width', floor(random() * 1920 + 800)
    )
FROM generate_series(1, 30);

-- 6. 최근 1시간 에러 (테스트용) - 15개
INSERT INTO logs (
    level, log_type, service, environment,
    trace_id, user_id, error_type, message,
    path, method,
    created_at, deleted
)
SELECT
    'ERROR'::log_level,
    'BACKEND'::source_type,
    (ARRAY['payment-api', 'user-api', 'order-api'])[floor(random() * 3 + 1)],
    'production'::env_type,
    'trace_' || substring(md5(random()::text), 1, 26),
    'user_' || (1000 + floor(random() * 100)),
    (ARRAY['DatabaseConnectionError', 'TimeoutError', 'NetworkError'])[floor(random() * 3 + 1)],
    'Critical error in recent request',
    '/api/v1/' || (ARRAY['payments', 'orders'])[floor(random() * 2 + 1)],
    'POST'::http_method,
    NOW() - (random() * interval '1 hour'),
    FALSE
FROM generate_series(1, 15);

-- 7. 명시적 느린 API 샘플 (성능 분석용) - 50개
-- duration_ms > 1000ms를 보장하여 "느린 API" 질문에 대응
INSERT INTO logs (
    level, log_type, service, environment, service_version,
    trace_id, user_id, message, path, method, duration_ms,
    created_at, deleted
)
SELECT
    'WARN'::log_level,
    'BACKEND'::source_type,
    (ARRAY['payment-api', 'user-api', 'order-api', 'auth-api'])[floor(random() * 4 + 1)],
    'production'::env_type,
    'v1.0.' || floor(random() * 10),
    'trace_' || substring(md5(random()::text), 1, 26),
    'user_' || (1000 + floor(random() * 100)),
    'Slow API request detected',
    '/api/v1/' || (ARRAY['payments/process', 'users/profile', 'orders/history', 'auth/verify', 'payments/refund', 'users/settings'])[floor(random() * 6 + 1)],
    (ARRAY['GET', 'POST', 'PUT'])[floor(random() * 3 + 1)]::http_method,
    1500 + random() * 3500,  -- 확실히 느림: 1500-5000ms
    NOW() - (random() * interval '24 hours'),  -- 24시간 전체에 분산
    FALSE
FROM generate_series(1, 50);

-- 8. 서비스별 최소 보장 로그 - 각 서비스당 25개
-- 서비스 분포를 균등하게 만들어 "서비스별" 집계 쿼리에 대응
INSERT INTO logs (
    level, log_type, service, environment, service_version,
    trace_id, message, path, method, duration_ms,
    created_at, deleted
)
SELECT
    (ARRAY['INFO', 'WARN', 'ERROR', 'DEBUG'])[floor(random() * 4 + 1)]::log_level,
    'BACKEND'::source_type,
    svc,
    'production'::env_type,
    'v1.0.' || floor(random() * 10),
    'trace_' || substring(md5(random()::text), 1, 26),
    'Service log for ' || svc,
    '/api/v1/' || lower(replace(svc, '-api', '')) || '/' || (ARRAY['list', 'get', 'create', 'update'])[floor(random() * 4 + 1)],
    (ARRAY['GET', 'POST', 'PUT'])[floor(random() * 3 + 1)]::http_method,
    50 + random() * 2000,
    NOW() - (random() * interval '24 hours'),
    FALSE
FROM unnest(ARRAY['payment-api', 'user-api', 'order-api', 'auth-api']) AS svc,
     generate_series(1, 25);

-- 9. 시간대별 에러 로그 (시계열 분석용) - 24개
-- 각 시간대마다 최소 1개씩 에러 로그를 생성하여 "시간대별 추이" 질문에 대응
INSERT INTO logs (
    level, log_type, service, environment,
    trace_id, error_type, message, path, method,
    created_at, deleted
)
SELECT
    'ERROR'::log_level,
    'BACKEND'::source_type,
    (ARRAY['payment-api', 'user-api', 'order-api', 'auth-api'])[floor(random() * 4 + 1)],
    'production'::env_type,
    'trace_' || substring(md5(random()::text), 1, 26),
    (ARRAY['DatabaseConnectionError', 'TimeoutError', 'ValidationError'])[floor(random() * 3 + 1)],
    'Hourly error - hour ' || hour_offset,
    '/api/v1/' || (ARRAY['users', 'orders', 'payments'])[floor(random() * 3 + 1)],
    (ARRAY['GET', 'POST'])[floor(random() * 2 + 1)]::http_method,
    NOW() - (interval '1 hour' * hour_offset),  -- 각 시간대마다 정확히 1개
    FALSE
FROM generate_series(0, 23) AS hour_offset;

-- 통계 조회
SELECT
    '총 로그 개수' as metric,
    COUNT(*)::text as value
FROM logs
WHERE deleted = FALSE

UNION ALL

SELECT
    '최근 1시간 에러',
    COUNT(*)::text
FROM logs
WHERE level = 'ERROR'
  AND created_at > NOW() - INTERVAL '1 hour'
  AND deleted = FALSE

UNION ALL

SELECT
    '레벨별 분포 - ' || level,
    COUNT(*)::text
FROM logs
WHERE deleted = FALSE
GROUP BY level
ORDER BY metric;
