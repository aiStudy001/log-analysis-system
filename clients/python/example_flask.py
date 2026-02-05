"""
Flask HTTP 컨텍스트 자동 수집 예제

실행 방법:
    pip install flask
    python example_flask.py

테스트:
    curl http://localhost:5000/api/users/123
    curl -X POST http://localhost:5000/api/users -H "Content-Type: application/json" -d '{"name":"John"}'
"""
from flask import Flask, request, jsonify
import sys
import os

# 로컬 log_collector 모듈 사용
sys.path.insert(0, os.path.dirname(__file__))
from log_collector import AsyncLogClient

app = Flask(__name__)

# 로그 클라이언트 초기화
logger = AsyncLogClient(
    "http://localhost:8000",
    service="flask-example",
    environment="development"
)

@app.before_request
def set_log_context():
    """요청 시작 시 HTTP 컨텍스트 설정"""
    AsyncLogClient.set_request_context(
        path=request.path,
        method=request.method,
        ip=request.remote_addr
    )
    logger.info(f"Request started: {request.method} {request.path}")

@app.after_request
def clear_log_context(response):
    """요청 종료 시 컨텍스트 초기화"""
    logger.info(f"Request completed: {response.status_code}")
    AsyncLogClient.clear_request_context()
    return response

@app.route('/api/users/<user_id>')
def get_user(user_id):
    """사용자 조회"""
    logger.info(f"Fetching user {user_id}")
    # 자동으로 포함됨: path="/api/users/123", method="GET", ip="127.0.0.1"

    # 가짜 데이터
    user = {"id": user_id, "name": f"User {user_id}"}

    logger.info("User fetched successfully", user_id=user_id)
    return jsonify(user)

@app.route('/api/users', methods=['POST'])
def create_user():
    """사용자 생성"""
    data = request.get_json()
    logger.info("Creating new user", username=data.get('name'))
    # 자동으로 포함됨: path="/api/users", method="POST", ip="127.0.0.1"

    # 가짜 생성
    new_user = {"id": "999", "name": data.get('name')}

    logger.info("User created successfully", user_id=new_user['id'])
    return jsonify(new_user), 201

@app.route('/api/error')
def trigger_error():
    """에러 테스트"""
    logger.warn("About to trigger an error")

    try:
        raise ValueError("This is a test error")
    except Exception as e:
        logger.error_with_trace("Error occurred", exception=e)
        # HTTP 컨텍스트도 에러 로그에 포함됨
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print("Starting Flask server...")
    print("Test with:")
    print("  curl http://localhost:5000/api/users/123")
    print("  curl -X POST http://localhost:5000/api/users -H 'Content-Type: application/json' -d '{\"name\":\"John\"}'")
    print("  curl http://localhost:5000/api/error")
    print("\nCheck logs in PostgreSQL:")
    print("  SELECT path, method, ip, function_name, message FROM logs ORDER BY created_at DESC LIMIT 10;")
    app.run(debug=True, port=5000)
