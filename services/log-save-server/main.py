"""
FastAPI 로그 수집 서버

기능:
- POST /logs (배치 전송 지원)
- gzip 압축 처리
- PostgreSQL COPY (bulk insert)
- Connection Pool
"""

import gzip
import json
from datetime import datetime
from typing import List, Dict, Any, Optional

from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import asyncpg
from pydantic import BaseModel, Field


# Pydantic 모델
class LogEntry(BaseModel):
    level: str
    message: str
    created_at: Optional[float] = None  # Unix timestamp
    log_type: Optional[str] = None
    service: Optional[str] = None
    environment: Optional[str] = "development"
    service_version: Optional[str] = "v0.0.0-dev"
    trace_id: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    error_type: Optional[str] = None
    stack_trace: Optional[str] = None
    path: Optional[str] = None
    method: Optional[str] = None
    action_type: Optional[str] = None
    function_name: Optional[str] = None
    file_path: Optional[str] = None
    duration_ms: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None


class LogBatch(BaseModel):
    logs: List[LogEntry]


# FastAPI 앱
app = FastAPI(title="Log Collection Server", version="1.0.0")

# CORS 설정 (프론트엔드에서 직접 로그 전송 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 개발 환경용, 프로덕션에서는 특정 도메인만 허용
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DB Connection Pool
pool: Optional[asyncpg.Pool] = None


@app.on_event("startup")
async def startup():
    """서버 시작 시 DB Connection Pool 생성"""
    import os

    global pool
    pool = await asyncpg.create_pool(
        host=os.getenv("DATABASE_HOST", "localhost"),
        port=int(os.getenv("DATABASE_PORT", "5432")),
        database=os.getenv("DATABASE_NAME", "logs_db"),
        user=os.getenv("DATABASE_USER", "postgres"),
        password=os.getenv("DATABASE_PASSWORD", "password"),
        min_size=int(os.getenv("DB_POOL_MIN_SIZE", "10")),
        max_size=int(os.getenv("DB_POOL_MAX_SIZE", "20"))
    )
    print("✅ Database connection pool created")


@app.on_event("shutdown")
async def shutdown():
    """서버 종료 시 Connection Pool 정리"""
    global pool
    if pool:
        await pool.close()
        print("✅ Database connection pool closed")


@app.get("/")
async def root():
    """헬스 체크"""
    return {"status": "ok", "service": "log-server"}


@app.post("/logs")
async def receive_logs(request: Request):
    """
    로그 배치 수신 엔드포인트

    지원:
    - JSON (Content-Type: application/json)
    - gzip 압축 (Content-Encoding: gzip)
    - 배치 전송 (logs 배열)
    """
    try:
        # gzip 압축 처리
        content_encoding = request.headers.get("content-encoding", "").lower()
        body = await request.body()

        if content_encoding == "gzip":
            try:
                body = gzip.decompress(body)
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Failed to decompress gzip: {str(e)}")

        # JSON 파싱
        try:
            data = json.loads(body.decode('utf-8'))
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Invalid JSON: {str(e)}")

        # 로그 배치 검증
        if "logs" not in data:
            raise HTTPException(status_code=400, detail="Missing 'logs' field")

        logs = data["logs"]
        if not isinstance(logs, list):
            raise HTTPException(status_code=400, detail="'logs' must be an array")

        if len(logs) == 0:
            return JSONResponse({"status": "ok", "count": 0})

        # DB 삽입
        inserted_count = await insert_logs_batch(logs)

        return JSONResponse({
            "status": "ok",
            "count": inserted_count
        })

    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error processing logs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def insert_logs_batch(logs: List[Dict[str, Any]]) -> int:
    """
    로그 배치 삽입 (PostgreSQL COPY)

    Args:
        logs: 로그 배치

    Returns:
        삽입된 로그 개수
    """
    if not pool:
        raise Exception("Database pool not initialized")

    # 로그 데이터 정규화
    records = []
    for log in logs:
        # created_at 변환 (Unix timestamp → datetime)
        if "created_at" in log and log["created_at"]:
            created_at = datetime.fromtimestamp(log["created_at"])
        else:
            created_at = datetime.now()

        # metadata JSON 직렬화
        metadata = json.dumps(log.get("metadata")) if log.get("metadata") else None

        record = (
            created_at,
            log.get("level", "INFO"),
            log.get("log_type", "BACKEND"),
            log.get("service", "unknown"),
            log.get("environment", "development"),
            log.get("service_version", "v0.0.0-dev"),
            log.get("trace_id"),
            log.get("user_id"),
            log.get("session_id"),
            log.get("error_type"),
            log.get("message", ""),
            log.get("stack_trace"),
            log.get("path"),
            log.get("method"),
            log.get("action_type"),
            log.get("function_name"),
            log.get("file_path"),
            log.get("duration_ms"),
            False,  # deleted
            metadata
        )
        records.append(record)

    # Bulk Insert (PostgreSQL COPY - 최고 성능!)
    async with pool.acquire() as conn:
        await conn.copy_records_to_table(
            'logs',
            records=records,
            columns=[
                'created_at', 'level', 'log_type', 'service', 'environment',
                'service_version', 'trace_id', 'user_id', 'session_id',
                'error_type', 'message', 'stack_trace', 'path', 'method',
                'action_type', 'function_name', 'file_path', 'duration_ms',
                'deleted', 'metadata'
            ]
        )

    return len(records)


@app.get("/stats")
async def get_stats():
    """로그 통계 조회"""
    if not pool:
        raise HTTPException(status_code=500, detail="Database pool not initialized")

    async with pool.acquire() as conn:
        # 전체 로그 개수
        total_count = await conn.fetchval(
            "SELECT COUNT(*) FROM logs WHERE deleted = FALSE"
        )

        # 레벨별 개수
        level_counts = await conn.fetch(
            """
            SELECT level, COUNT(*) as count
            FROM logs
            WHERE deleted = FALSE
            GROUP BY level
            ORDER BY count DESC
            """
        )

        # 서비스별 개수
        service_counts = await conn.fetch(
            """
            SELECT service, COUNT(*) as count
            FROM logs
            WHERE deleted = FALSE
            GROUP BY service
            ORDER BY count DESC
            LIMIT 10
            """
        )

        # 최근 1시간 에러 개수
        recent_errors = await conn.fetchval(
            """
            SELECT COUNT(*) FROM logs
            WHERE level = 'ERROR'
              AND created_at > NOW() - INTERVAL '1 hour'
              AND deleted = FALSE
            """
        )

        return {
            "total_logs": total_count,
            "level_distribution": [
                {"level": row["level"], "count": row["count"]}
                for row in level_counts
            ],
            "service_distribution": [
                {"service": row["service"], "count": row["count"]}
                for row in service_counts
            ],
            "recent_errors_1h": recent_errors
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
