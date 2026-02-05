-- 로그 분석 시스템 데이터베이스 스키마
-- 최적화된 21개 필드 + 4개 인덱스

-- ENUM 타입 정의
CREATE TYPE log_level AS ENUM ('TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL');
CREATE TYPE source_type AS ENUM ('BACKEND', 'FRONTEND', 'MOBILE', 'IOT', 'WORKER');
CREATE TYPE env_type AS ENUM ('production', 'staging', 'development', 'test', 'local');
CREATE TYPE http_method AS ENUM ('GET', 'POST', 'PUT', 'DELETE', 'PATCH', 'HEAD', 'OPTIONS');

-- 메인 로그 테이블
CREATE TABLE logs (
    -- 기본 정보 (4)
    id BIGSERIAL PRIMARY KEY,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    level log_level NOT NULL DEFAULT 'INFO',
    log_type source_type NOT NULL,

    -- 서비스 식별 (3)
    service VARCHAR(100) NOT NULL,
    environment env_type NOT NULL DEFAULT 'development',
    service_version VARCHAR(50) NOT NULL DEFAULT 'v0.0.0-dev',

    -- 분산 추적 (3)
    trace_id VARCHAR(32),
    user_id VARCHAR(255),
    session_id VARCHAR(100),

    -- 에러 정보 (3)
    error_type VARCHAR(200),
    message TEXT NOT NULL,
    stack_trace TEXT,

    -- 위치 정보 (3)
    path VARCHAR(500),              -- 백엔드: /api/v1/payment, 프론트: /checkout
    method http_method,             -- 백엔드 전용: HTTP 메서드
    action_type VARCHAR(50),        -- 프론트엔드 전용: click, submit, navigate

    -- 코드 위치 (2) - 프론트/백 공통
    function_name VARCHAR(300),     -- stack trace에서 추출
    file_path VARCHAR(1000),        -- stack trace에서 추출

    -- 성능 (1)
    duration_ms DECIMAL(10, 3),

    -- 관리 (1)
    deleted BOOLEAN NOT NULL DEFAULT FALSE,

    -- 확장 메타데이터 (1)
    metadata JSONB
);

-- 테이블 및 컬럼 설명
COMMENT ON TABLE logs IS '통합 로그 테이블 (프론트엔드 + 백엔드)';
COMMENT ON COLUMN logs.path IS '경로: 백엔드는 API endpoint, 프론트엔드는 page path';
COMMENT ON COLUMN logs.function_name IS '함수명: stack trace에서 추출 (프론트/백 공통)';
COMMENT ON COLUMN logs.file_path IS '파일 경로: stack trace에서 추출 (프론트/백 공통)';
COMMENT ON COLUMN logs.deleted IS 'Soft delete 플래그 (true = 삭제됨)';
COMMENT ON COLUMN logs.metadata IS '확장 데이터: 성능 메트릭, 브라우저 정보, 비즈니스 컨텍스트 등';

-- 핵심 4개 인덱스 (성능 최적화)
CREATE INDEX idx_service_level_time
ON logs(service, level, created_at DESC)
WHERE deleted = FALSE;

CREATE INDEX idx_error_time
ON logs(error_type, created_at DESC)
WHERE error_type IS NOT NULL AND deleted = FALSE;

CREATE INDEX idx_user_time
ON logs(user_id, created_at DESC)
WHERE user_id IS NOT NULL AND deleted = FALSE;

CREATE INDEX idx_trace
ON logs(trace_id)
WHERE trace_id IS NOT NULL AND deleted = FALSE;

-- 인덱스 설명
COMMENT ON INDEX idx_service_level_time IS '서비스별 로그 레벨 조회 최적화';
COMMENT ON INDEX idx_error_time IS '에러 타입별 시계열 조회 최적화';
COMMENT ON INDEX idx_user_time IS '사용자별 로그 조회 최적화';
COMMENT ON INDEX idx_trace IS '분산 추적 (trace_id) 조회 최적화';
