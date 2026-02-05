"""
FastAPI HTTP 컨텍스트 자동 수집 예제

실행 방법:
    pip install fastapi uvicorn
    python example_fastapi.py

테스트:
    curl http://localhost:8000/api/users/123
    curl -X POST http://localhost:8000/api/users -H "Content-Type: application/json" -d '{"name":"John"}'
"""
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel
import sys
import os
import time

# 로컬 log_collector 모듈 사용
sys.path.insert(0, os.path.dirname(__file__))
from log_collector import AsyncLogClient

app = FastAPI()

# 로그 클라이언트 초기화
logger = AsyncLogClient(
    "http://localhost:8000",
    service="fastapi-example",
    environment="development"
)

class UserCreate(BaseModel):
    name: str

@app.middleware("http")
async def log_context_middleware(request: Request, call_next):
    """모든 요청에 HTTP 컨텍스트 자동 설정"""
    # 컨텍스트 설정
    AsyncLogClient.set_request_context(
        path=request.url.path,
        method=request.method,
        ip=request.client.host if request.client else None
    )

    # 요청 시작 로그
    start_time = time.time()
    logger.info(f"Request started: {request.method} {request.url.path}")

    try:
        response = await call_next(request)

        # 요청 완료 로그
        duration_ms = (time.time() - start_time) * 1000
        logger.info(
            f"Request completed: {response.status_code}",
            status_code=response.status_code,
            duration_ms=duration_ms
        )

        return response

    except Exception as e:
        # 예외 로그
        duration_ms = (time.time() - start_time) * 1000
        logger.error_with_trace(
            "Request failed",
            exception=e,
            duration_ms=duration_ms
        )
        raise

    finally:
        # 컨텍스트 초기화
        AsyncLogClient.clear_request_context()

@app.get("/api/users/{user_id}")
async def get_user(user_id: int):
    """사용자 조회"""
    logger.info("Fetching user from database", user_id=user_id)
    # 자동으로 포함됨: path="/api/users/123", method="GET", ip="127.0.0.1"

    # 가짜 데이터
    user = {"id": user_id, "name": f"User {user_id}"}

    logger.info("User fetched successfully", user_id=user_id)
    return {"user": user}

@app.post("/api/users")
async def create_user(user: UserCreate):
    """사용자 생성"""
    logger.info("Creating new user", username=user.name)
    # 자동으로 포함됨: path="/api/users", method="POST", ip="127.0.0.1"

    # 가짜 생성
    new_user = {"id": 999, "name": user.name}

    logger.info("User created successfully", user_id=new_user['id'])
    return {"user": new_user}

@app.get("/api/error")
async def trigger_error():
    """에러 테스트"""
    logger.warn("About to trigger an error")

    try:
        raise ValueError("This is a test error")
    except Exception as e:
        logger.error_with_trace("Error occurred", exception=e)
        # HTTP 컨텍스트도 에러 로그에 포함됨
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == '__main__':
    import uvicorn

    print("Starting FastAPI server...")
    print("Test with:")
    print("  curl http://localhost:8000/api/users/123")
    print("  curl -X POST http://localhost:8000/api/users -H 'Content-Type: application/json' -d '{\"name\":\"John\"}'")
    print("  curl http://localhost:8000/api/error")
    print("\nCheck logs in PostgreSQL:")
    print("  SELECT path, method, ip, function_name, message FROM logs ORDER BY created_at DESC LIMIT 10;")

    uvicorn.run(app, host="0.0.0.0", port=8000)
