# Server B Deployment Guide

## Quick Deploy (권장)

SSH로 서버에 접속하여 한 번에 실행:

```bash
ssh ec2-user@13.62.76.208 "cd log-analysis-system/deployment/server-b && docker compose pull && docker compose down && docker compose up -d"
```

## 단계별 Deploy

### 1. 서버 접속
```bash
ssh ec2-user@13.62.76.208
```

### 2. 디렉토리 이동
```bash
cd log-analysis-system/deployment/server-b
```

### 3. 최신 이미지 가져오기
```bash
docker compose pull
```

### 4. 기존 컨테이너 중지
```bash
docker compose down
```

### 5. 새 컨테이너 시작
```bash
docker compose up -d
```

### 6. 상태 확인
```bash
docker compose ps
docker compose logs -f --tail=50
```

## 배포 검증

### Frontend 확인
```bash
curl -I http://13.62.76.208
```

### Analysis API 확인
```bash
curl http://13.62.76.208:8001/
```

### 브라우저 확인
- Frontend: http://13.62.76.208
- Analysis API: http://13.62.76.208:8001

## Rollback (문제 발생 시)

이전 이미지로 되돌리기:
```bash
docker compose down
docker compose pull ljh0/log-analysis-frontend:previous
docker compose up -d
```

## 트러블슈팅

### 컨테이너가 시작되지 않는 경우
```bash
docker compose logs
```

### 포트가 이미 사용 중인 경우
```bash
docker ps -a  # 모든 컨테이너 확인
docker rm -f log-analysis-frontend log-analysis-server  # 강제 삭제
```

### 디스크 공간 부족
```bash
docker system prune -a  # 사용하지 않는 이미지/컨테이너 정리
```
