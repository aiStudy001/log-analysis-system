"""
FastAPI Todo Backend with log-collector

Python log-collector 패키지 테스트용 데모 서버
"""
import time
import uuid
from typing import Optional, List, Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from log_collector import AsyncLogClient

# ============================================================================
# 로거 초기화
# ============================================================================
logger = AsyncLogClient(
    "http://localhost:8000",
    service="demo-todo-backend-python",
    environment="development"
)

print("Logger initialized")

# ============================================================================
# FastAPI 앱
# ============================================================================
app = FastAPI(title="Todo Backend (Python)", version="1.0.0")

# CORS 설정
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# Pydantic 모델
# ============================================================================
class LoginRequest(BaseModel):
    username: str
    password: str

class TodoCreate(BaseModel):
    text: str

# ============================================================================
# 인메모리 데이터 저장소
# ============================================================================
todos: List[Dict] = [
    {"id": "1", "text": "첫 번째 할 일", "completed": False, "userId": "user_demo"},
    {"id": "2", "text": "두 번째 할 일", "completed": True, "userId": "user_demo"},
]

users = {
    "demo": {"id": "user_demo", "username": "demo", "password": "demo123"}
}

# ============================================================================
# HTTP 컨텍스트 미들웨어
# ============================================================================
@app.middleware("http")
async def log_requests(request: Request, call_next):
    # 요청 시작 시간
    start_time = time.time()

    # trace_id 생성
    trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()).replace("-", "")[:32])

    # HTTP 컨텍스트
    log_context = {
        "path": request.url.path,
        "method": request.method,
        "ip": request.client.host if request.client else None,
        "trace_id": trace_id,
    }

    # 사용자 컨텍스트 추가
    user_id = request.headers.get("x-user-id")
    if user_id:
        log_context["user_id"] = user_id

    # 요청 컨텍스트를 request.state에 저장
    request.state.log_context = log_context
    request.state.start_time = start_time

    logger.info("Request received", **log_context)

    # 요청 처리
    response = await call_next(request)

    # 응답 완료
    duration_ms = int((time.time() - start_time) * 1000)
    logger.info("Request completed",
                status_code=response.status_code,
                duration_ms=duration_ms,
                **log_context)

    return response

# ============================================================================
# API 엔드포인트
# ============================================================================

@app.post("/api/login")
async def login(request: Request, body: LoginRequest):
    log_ctx = request.state.log_context

    logger.info("Login attempt", username=body.username, **log_ctx)

    if not body.username or not body.password:
        logger.warn("Login failed: missing credentials", **log_ctx)
        raise HTTPException(status_code=400, detail="Username and password required")

    user = users.get(body.username)
    if not user or user["password"] != body.password:
        logger.warn("Login failed: invalid credentials", username=body.username, **log_ctx)
        raise HTTPException(status_code=401, detail="Invalid credentials")

    logger.info("Login successful", user_id=user["id"], username=body.username, **log_ctx)

    return {
        "success": True,
        "user": {"id": user["id"], "username": user["username"]},
        "traceId": log_ctx["trace_id"]
    }

@app.get("/api/todos")
async def get_todos(request: Request):
    log_ctx = request.state.log_context
    user_id = request.headers.get("x-user-id", "user_demo")

    logger.info("Fetching todos", count=len(todos), **log_ctx)

    user_todos = [todo for todo in todos if todo["userId"] == user_id]

    return {
        "success": True,
        "todos": user_todos
    }

@app.post("/api/todos")
async def create_todo(request: Request, body: TodoCreate):
    log_ctx = request.state.log_context
    user_id = request.headers.get("x-user-id", "user_demo")

    if not body.text:
        logger.warn("Todo creation failed: missing text", **log_ctx)
        raise HTTPException(status_code=400, detail="Text is required")

    new_todo = {
        "id": str(uuid.uuid4()),
        "text": body.text,
        "completed": False,
        "userId": user_id
    }

    todos.append(new_todo)

    logger.info("Todo created",
                todo_id=new_todo["id"],
                text=new_todo["text"],
                **log_ctx)

    return {
        "success": True,
        "todo": new_todo
    }

@app.put("/api/todos/{todo_id}")
async def toggle_todo(request: Request, todo_id: str):
    log_ctx = request.state.log_context
    user_id = request.headers.get("x-user-id", "user_demo")

    todo = next((t for t in todos if t["id"] == todo_id and t["userId"] == user_id), None)

    if not todo:
        logger.warn("Todo not found", todo_id=todo_id, **log_ctx)
        raise HTTPException(status_code=404, detail="Todo not found")

    todo["completed"] = not todo["completed"]

    logger.info("Todo updated",
                todo_id=todo_id,
                completed=todo["completed"],
                **log_ctx)

    return {
        "success": True,
        "todo": todo
    }

@app.delete("/api/todos/{todo_id}")
async def delete_todo(request: Request, todo_id: str):
    log_ctx = request.state.log_context
    user_id = request.headers.get("x-user-id", "user_demo")

    global todos
    todo = next((t for t in todos if t["id"] == todo_id and t["userId"] == user_id), None)

    if not todo:
        logger.warn("Todo not found for deletion", todo_id=todo_id, **log_ctx)
        raise HTTPException(status_code=404, detail="Todo not found")

    todos = [t for t in todos if t["id"] != todo_id]

    logger.info("Todo deleted",
                todo_id=todo_id,
                text=todo["text"],
                **log_ctx)

    return {
        "success": True,
        "todo": todo
    }

@app.get("/api/error")
async def test_error(request: Request):
    log_ctx = request.state.log_context

    logger.warn("Error endpoint called", **log_ctx)

    try:
        raise Exception("This is a test error!")
    except Exception as e:
        logger.error_with_trace("Intentional error occurred",
                                exception=e,
                                test=True,
                                **log_ctx)

        raise HTTPException(status_code=500, detail={"error": "Internal server error", "message": str(e)})

@app.get("/api/slow")
async def test_slow(request: Request):
    log_ctx = request.state.log_context

    timer = logger.start_timer()

    logger.info("Slow API called", **log_ctx)

    # 2초 대기
    time.sleep(2)

    logger.end_timer(timer, "INFO", "Slow API completed", **log_ctx)

    return {
        "success": True,
        "message": "This took 2 seconds"
    }

# ============================================================================
# 서버 시작
# ============================================================================
if __name__ == "__main__":
    import uvicorn

    print("=" * 60)
    print("Todo Backend Server (Python) running on http://localhost:3002")
    print("=" * 60)

    logger.info("Server started", port=3002)

    uvicorn.run(app, host="0.0.0.0", port=3002, log_level="info")
