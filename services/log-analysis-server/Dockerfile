FROM python:3.13-slim

WORKDIR /app

# 의존성 설치
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 애플리케이션 코드 복사 (새로운 MVC 구조)
COPY main.py .
COPY app/ ./app/

# 포트 노출
EXPOSE 8000

# 서버 실행 (Uvicorn 직접 사용)
CMD ["uvicorn", "main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "1", \
     "--timeout-keep-alive", "600", \
     "--log-level", "info"]
