# AWS 배포 가이드

## 목차

1. [배포 옵션 비교](#1-배포-옵션-비교)
2. [EC2 + Docker PostgreSQL 배포](#2-ec2--docker-postgresql-배포)
3. [네트워크 및 보안 설정](#3-네트워크-및-보안-설정)
4. [Docker Compose 전체 스택 배포](#4-docker-compose-전체-스택-배포)
5. [백업 및 복구 전략](#5-백업-및-복구-전략)
6. [모니터링 (CloudWatch 통합)](#6-모니터링-cloudwatch-통합)
7. [비용 최적화 전략](#7-비용-최적화-전략)
8. [CI/CD 파이프라인](#8-cicd-파이프라인)

---

## 1. 배포 옵션 비교

### 1.1 AWS RDS vs EC2 Docker PostgreSQL

| 항목 | AWS RDS PostgreSQL | EC2 + Docker PostgreSQL |
|-----|-------------------|------------------------|
| **관리** | 완전 관리형 | 직접 관리 |
| **백업** | 자동 (point-in-time recovery) | 수동 (스크립트 필요) |
| **고가용성** | Multi-AZ 자동 failover | 직접 구성 (복잡) |
| **확장** | 수직 확장 쉬움 | 수직/수평 확장 모두 가능 |
| **성능** | 최적화됨 | 튜닝 필요 |
| **비용** | 높음 ($100-500/월) | 낮음 ($30-150/월) |
| **커스터마이징** | 제한적 | 완전한 제어 |
| **모니터링** | CloudWatch 기본 제공 | 직접 구성 |
| **보안** | VPC, 암호화 기본 | 직접 구성 |
| **학습 곡선** | 낮음 | 중간 |

### 1.2 권장 배포 방식

#### 프로덕션 환경
```
추천: AWS RDS PostgreSQL
이유:
- 고가용성 필수
- 자동 백업 및 복구
- 운영 부담 최소화
- 기업용 SLA
```

#### 개발/테스트 환경
```
추천: EC2 + Docker PostgreSQL
이유:
- 비용 효율적
- 빠른 프로비저닝
- 실험 및 테스트 자유
- 프로덕션 환경 시뮬레이션
```

#### 스타트업/MVP
```
추천: EC2 + Docker PostgreSQL
이유:
- 초기 비용 절감 ($500/월 → $150/월)
- 유연한 리소스 조정
- 향후 RDS 마이그레이션 가능
```

### 1.3 하이브리드 아키텍처

```
┌─────────────────────────────────────────────┐
│  프로덕션: AWS RDS                          │
│  - Multi-AZ                                │
│  - 자동 백업                                │
│  - 고가용성                                 │
└─────────────────────────────────────────────┘
                    │
                    │ Read Replica
                    ▼
┌─────────────────────────────────────────────┐
│  분석 워크로드: EC2 + Docker PostgreSQL     │
│  - Text-to-SQL 쿼리                         │
│  - 대시보드                                 │
│  - 리포팅                                   │
└─────────────────────────────────────────────┘
```

---

## 2. EC2 + Docker PostgreSQL 배포

### 2.1 EC2 인스턴스 생성

#### 인스턴스 타입 선택

| 로그 볼륨 | 인스턴스 타입 | vCPU | 메모리 | 스토리지 | 월 비용 (us-east-1) |
|----------|--------------|------|--------|---------|---------------------|
| < 1GB/일 | t3.small     | 2    | 2GB    | 30GB    | $15 |
| 1-10GB/일 | t3.medium    | 2    | 4GB    | 50GB    | $30 |
| 10-50GB/일 | t3.large     | 2    | 8GB    | 100GB   | $60 |
| 50-100GB/일 | m5.xlarge   | 4    | 16GB   | 200GB   | $140 |
| > 100GB/일 | m5.2xlarge  | 8    | 32GB   | 500GB   | $280 |

#### Terraform 코드

**파일**: `infrastructure/terraform/ec2/main.tf`

```hcl
# Provider 설정
provider "aws" {
  region = var.aws_region
}

# EC2 인스턴스
resource "aws_instance" "log_server" {
  ami           = data.aws_ami.amazon_linux_2.id
  instance_type = var.instance_type
  key_name      = var.key_pair_name

  vpc_security_group_ids = [aws_security_group.log_server.id]
  subnet_id              = var.subnet_id

  # EBS 볼륨 설정
  root_block_device {
    volume_type           = "gp3"
    volume_size           = var.root_volume_size
    delete_on_termination = false
    encrypted             = true

    tags = {
      Name = "log-server-root"
    }
  }

  # 추가 데이터 볼륨 (PostgreSQL 데이터)
  ebs_block_device {
    device_name           = "/dev/sdf"
    volume_type           = "gp3"
    volume_size           = var.data_volume_size
    iops                  = 3000
    throughput            = 125
    delete_on_termination = false
    encrypted             = true

    tags = {
      Name = "log-server-data"
    }
  }

  user_data = templatefile("${path.module}/user_data.sh", {
    postgres_password = var.postgres_password
    log_server_port   = var.log_server_port
  })

  tags = {
    Name        = "log-analysis-server"
    Environment = var.environment
    Project     = "log-analysis-system"
  }
}

# AMI 데이터 소스
data "aws_ami" "amazon_linux_2" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["amzn2-ami-hvm-*-x86_64-gp2"]
  }
}

# Elastic IP (선택사항)
resource "aws_eip" "log_server" {
  instance = aws_instance.log_server.id
  vpc      = true

  tags = {
    Name = "log-server-eip"
  }
}

# Outputs
output "instance_id" {
  value = aws_instance.log_server.id
}

output "public_ip" {
  value = aws_eip.log_server.public_ip
}

output "private_ip" {
  value = aws_instance.log_server.private_ip
}
```

#### User Data 스크립트

**파일**: `infrastructure/terraform/ec2/user_data.sh`

```bash
#!/bin/bash
set -e

# 로그 설정
exec > >(tee /var/log/user-data.log)
exec 2>&1

echo "=== Starting EC2 initialization ==="

# 시스템 업데이트
yum update -y

# Docker 설치
yum install -y docker
systemctl start docker
systemctl enable docker
usermod -a -G docker ec2-user

# Docker Compose 설치
curl -L "https://github.com/docker/compose/releases/download/v2.24.0/docker-compose-$(uname -s)-$(uname -m)" \
  -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose

# 데이터 볼륨 마운트
mkdir -p /mnt/data
mkfs -t ext4 /dev/xvdf
mount /dev/xvdf /mnt/data
echo "/dev/xvdf /mnt/data ext4 defaults,nofail 0 2" >> /etc/fstab

# PostgreSQL 데이터 디렉토리
mkdir -p /mnt/data/postgres
mkdir -p /mnt/data/fluentd
chown -R 999:999 /mnt/data/postgres  # PostgreSQL UID

# 애플리케이션 디렉토리
mkdir -p /opt/log-analysis
cd /opt/log-analysis

# Docker Compose 파일 생성
cat > docker-compose.yml <<'EOF'
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: postgres
    environment:
      POSTGRES_DB: logs
      POSTGRES_USER: loguser
      POSTGRES_PASSWORD: ${postgres_password}
      POSTGRES_INITDB_ARGS: "-E UTF8 --locale=en_US.utf8"
    volumes:
      - /mnt/data/postgres:/var/lib/postgresql/data
      - ./init-db:/docker-entrypoint-initdb.d
    ports:
      - "5432:5432"
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U loguser"]
      interval: 10s
      timeout: 5s
      retries: 5
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  log-server:
    image: log-server:latest
    container_name: log-server
    environment:
      DATABASE_URL: postgresql://loguser:${postgres_password}@postgres:5432/logs
      LOG_LEVEL: info
    ports:
      - "${log_server_port}:8000"
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

  fluentd:
    image: fluentd:latest
    container_name: fluentd
    environment:
      LOG_SERVER_URL: http://log-server:8000
    ports:
      - "24224:24224"
    volumes:
      - /mnt/data/fluentd:/fluentd/buffer
      - ./fluentd/fluent.conf:/fluentd/etc/fluent.conf
    depends_on:
      - log-server
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
EOF

# PostgreSQL 초기화 SQL
mkdir -p init-db
cat > init-db/01-schema.sql <<'SQL'
-- 스키마 생성 (db-schema-analysis.md 참조)
CREATE TYPE log_level AS ENUM ('TRACE', 'DEBUG', 'INFO', 'WARN', 'ERROR', 'FATAL');
-- ... (나머지 스키마)
SQL

# 시스템 재시작 시 자동 시작
cat > /etc/systemd/system/log-analysis.service <<'SERVICE'
[Unit]
Description=Log Analysis System
Requires=docker.service
After=docker.service

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/log-analysis
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable log-analysis

# CloudWatch Agent 설치 (선택사항)
yum install -y amazon-cloudwatch-agent

echo "=== EC2 initialization complete ==="
```

### 2.2 수동 배포 단계

```bash
# 1. EC2 인스턴스 SSH 접속
ssh -i your-key.pem ec2-user@<EC2_PUBLIC_IP>

# 2. Docker 및 Docker Compose 설치 확인
docker --version
docker-compose --version

# 3. 프로젝트 클론 또는 파일 전송
git clone https://github.com/your-repo/log-analysis-system.git
cd log-analysis-system

# 4. 환경 변수 설정
cat > .env <<EOF
POSTGRES_PASSWORD=your_secure_password
DATABASE_URL=postgresql://loguser:your_secure_password@postgres:5432/logs
ANTHROPIC_API_KEY=sk-ant-...
ENVIRONMENT=production
EOF

# 5. Docker 이미지 빌드
docker-compose build

# 6. 서비스 시작
docker-compose up -d

# 7. 상태 확인
docker-compose ps
docker-compose logs -f

# 8. PostgreSQL 연결 테스트
docker exec -it postgres psql -U loguser -d logs -c "SELECT version();"

# 9. Log Server health check
curl http://localhost:8000/health
```

### 2.3 자동화된 배포

**파일**: `scripts/deploy.sh`

```bash
#!/bin/bash
set -e

# 설정
EC2_HOST="ec2-user@<EC2_PUBLIC_IP>"
SSH_KEY="~/.ssh/your-key.pem"
DEPLOY_DIR="/opt/log-analysis"

echo "=== Deploying to AWS EC2 ==="

# 1. SSH 키 권한 확인
chmod 400 $SSH_KEY

# 2. 최신 코드 전송
rsync -avz -e "ssh -i $SSH_KEY" \
  --exclude='.git' \
  --exclude='node_modules' \
  --exclude='__pycache__' \
  . $EC2_HOST:$DEPLOY_DIR/

# 3. 원격 서버에서 배포 실행
ssh -i $SSH_KEY $EC2_HOST <<'ENDSSH'
cd /opt/log-analysis

# Docker 이미지 재빌드
docker-compose build

# 서비스 재시작 (무중단 배포)
docker-compose up -d --no-deps --build log-server

# Health check
sleep 10
curl -f http://localhost:8000/health || exit 1

echo "Deployment successful!"
ENDSSH

echo "=== Deployment complete ==="
```

---

## 3. 네트워크 및 보안 설정

### 3.1 VPC 설계

```
VPC: 10.0.0.0/16

├── Public Subnet (10.0.1.0/24)
│   ├── NAT Gateway
│   └── Bastion Host (선택)
│
└── Private Subnet (10.0.2.0/24)
    ├── Log Server (EC2)
    ├── PostgreSQL (Docker)
    └── Fluentd
```

**Terraform 코드**:

```hcl
# VPC
resource "aws_vpc" "main" {
  cidr_block           = "10.0.0.0/16"
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = {
    Name = "log-analysis-vpc"
  }
}

# Public Subnet
resource "aws_subnet" "public" {
  vpc_id                  = aws_vpc.main.id
  cidr_block              = "10.0.1.0/24"
  map_public_ip_on_launch = true
  availability_zone       = "${var.aws_region}a"

  tags = {
    Name = "log-analysis-public"
  }
}

# Private Subnet
resource "aws_subnet" "private" {
  vpc_id            = aws_vpc.main.id
  cidr_block        = "10.0.2.0/24"
  availability_zone = "${var.aws_region}a"

  tags = {
    Name = "log-analysis-private"
  }
}

# Internet Gateway
resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id

  tags = {
    Name = "log-analysis-igw"
  }
}

# NAT Gateway (Private Subnet용)
resource "aws_eip" "nat" {
  vpc = true
}

resource "aws_nat_gateway" "main" {
  allocation_id = aws_eip.nat.id
  subnet_id     = aws_subnet.public.id

  tags = {
    Name = "log-analysis-nat"
  }
}

# Route Tables
resource "aws_route_table" "public" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.main.id
  }

  tags = {
    Name = "log-analysis-public-rt"
  }
}

resource "aws_route_table" "private" {
  vpc_id = aws_vpc.main.id

  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main.id
  }

  tags = {
    Name = "log-analysis-private-rt"
  }
}

# Route Table Associations
resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}

resource "aws_route_table_association" "private" {
  subnet_id      = aws_subnet.private.id
  route_table_id = aws_route_table.private.id
}
```

### 3.2 보안 그룹 설정

```hcl
# Log Server 보안 그룹
resource "aws_security_group" "log_server" {
  name        = "log-server-sg"
  description = "Security group for log server"
  vpc_id      = aws_vpc.main.id

  # SSH (관리용)
  ingress {
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.admin_cidr]  # 관리자 IP만
  }

  # Log Server HTTP API
  ingress {
    from_port   = 8000
    to_port     = 8000
    protocol    = "tcp"
    cidr_blocks = [var.application_cidr]  # 애플리케이션 서버만
  }

  # Fluentd
  ingress {
    from_port   = 24224
    to_port     = 24224
    protocol    = "tcp"
    cidr_blocks = [var.application_cidr]
  }

  # PostgreSQL (내부 전용)
  ingress {
    from_port = 5432
    to_port   = 5432
    protocol  = "tcp"
    self      = true  # 같은 보안 그룹 내에서만
  }

  # Outbound (모든 트래픽 허용)
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "log-server-sg"
  }
}

# Application 서버 보안 그룹
resource "aws_security_group" "application" {
  name        = "application-sg"
  description = "Security group for application servers"
  vpc_id      = aws_vpc.main.id

  # Outbound to Log Server
  egress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.log_server.id]
  }

  # Outbound to Fluentd
  egress {
    from_port       = 24224
    to_port         = 24224
    protocol        = "tcp"
    security_groups = [aws_security_group.log_server.id]
  }

  tags = {
    Name = "application-sg"
  }
}
```

### 3.3 IAM 역할 및 정책

```hcl
# EC2 인스턴스 역할
resource "aws_iam_role" "log_server" {
  name = "log-server-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "ec2.amazonaws.com"
        }
      }
    ]
  })
}

# S3 백업 권한
resource "aws_iam_policy" "s3_backup" {
  name = "log-server-s3-backup"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:PutObject",
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          "${aws_s3_bucket.log_backup.arn}",
          "${aws_s3_bucket.log_backup.arn}/*"
        ]
      }
    ]
  })
}

# CloudWatch 로그 권한
resource "aws_iam_policy" "cloudwatch_logs" {
  name = "log-server-cloudwatch-logs"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "arn:aws:logs:*:*:*"
      }
    ]
  })
}

# 정책 연결
resource "aws_iam_role_policy_attachment" "s3_backup" {
  role       = aws_iam_role.log_server.name
  policy_arn = aws_iam_policy.s3_backup.arn
}

resource "aws_iam_role_policy_attachment" "cloudwatch_logs" {
  role       = aws_iam_role.log_server.name
  policy_arn = aws_iam_policy.cloudwatch_logs.arn
}

# Instance Profile
resource "aws_iam_instance_profile" "log_server" {
  name = "log-server-profile"
  role = aws_iam_role.log_server.name
}
```

---

## 4. Docker Compose 전체 스택 배포

### 4.1 프로덕션 Docker Compose

**파일**: `infrastructure/docker/docker-compose.prod.yml`

```yaml
version: '3.8'

services:
  postgres:
    image: postgres:15
    container_name: postgres
    environment:
      POSTGRES_DB: logs
      POSTGRES_USER: loguser
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_INITDB_ARGS: "-E UTF8 --locale=en_US.utf8"
      # 성능 튜닝
      POSTGRES_MAX_CONNECTIONS: "200"
      POSTGRES_SHARED_BUFFERS: "2GB"
      POSTGRES_EFFECTIVE_CACHE_SIZE: "6GB"
      POSTGRES_WORK_MEM: "10MB"
      POSTGRES_MAINTENANCE_WORK_MEM: "512MB"
    volumes:
      - /mnt/data/postgres:/var/lib/postgresql/data
      - ./init-db:/docker-entrypoint-initdb.d:ro
      - ./postgres/postgresql.conf:/etc/postgresql/postgresql.conf:ro
    ports:
      - "127.0.0.1:5432:5432"  # localhost만 접근
    command: postgres -c config_file=/etc/postgresql/postgresql.conf
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U loguser"]
      interval: 10s
      timeout: 5s
      retries: 5
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G

  log-server:
    build:
      context: ../../services/log-server
      dockerfile: Dockerfile
    image: log-server:${VERSION:-latest}
    container_name: log-server
    environment:
      DATABASE_URL: postgresql://loguser:${POSTGRES_PASSWORD}@postgres:5432/logs
      LOG_LEVEL: ${LOG_LEVEL:-info}
      ENVIRONMENT: production
      MAX_WORKERS: "4"
      BATCH_SIZE: "1000"
    ports:
      - "8000:8000"
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "5"
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 2G
        reservations:
          cpus: '1'
          memory: 1G

  fluentd:
    build:
      context: ../../infrastructure/docker/fluentd
      dockerfile: Dockerfile
    image: fluentd-custom:${VERSION:-latest}
    container_name: fluentd
    environment:
      LOG_SERVER_URL: http://log-server:8000
      ENVIRONMENT: production
    ports:
      - "24224:24224"
      - "24224:24224/udp"
      - "127.0.0.1:24231:24231"  # Prometheus metrics
    volumes:
      - /mnt/data/fluentd:/fluentd/buffer
      - ./fluentd/fluent.conf:/fluentd/etc/fluent.conf:ro
      - /var/lib/docker/containers:/var/lib/docker/containers:ro
    depends_on:
      - log-server
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G
        reservations:
          cpus: '0.5'
          memory: 512M

  text-to-sql-agent:
    build:
      context: ../../services/text-to-sql-agent
      dockerfile: Dockerfile
    image: text-to-sql-agent:${VERSION:-latest}
    container_name: text-to-sql-agent
    environment:
      DATABASE_URL: postgresql://loguser:${POSTGRES_PASSWORD}@postgres:5432/logs
      ANTHROPIC_API_KEY: ${ANTHROPIC_API_KEY}
      MODEL: claude-sonnet-4-5-20250929
    ports:
      - "8501:8501"  # Streamlit UI
    depends_on:
      postgres:
        condition: service_healthy
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
    deploy:
      resources:
        limits:
          cpus: '1'
          memory: 1G

  # 선택사항: Nginx 리버스 프록시
  nginx:
    image: nginx:alpine
    container_name: nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/nginx.conf:ro
      - ./nginx/ssl:/etc/nginx/ssl:ro
    depends_on:
      - log-server
      - text-to-sql-agent
    restart: unless-stopped
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"

networks:
  default:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

volumes:
  postgres_data:
    driver: local
  fluentd_buffer:
    driver: local
```

### 4.2 환경 변수 관리

**파일**: `.env.production`

```bash
# PostgreSQL
POSTGRES_PASSWORD=<SECURE_PASSWORD>

# Application
VERSION=1.0.0
ENVIRONMENT=production
LOG_LEVEL=info

# Text-to-SQL Agent
ANTHROPIC_API_KEY=sk-ant-...

# AWS (CloudWatch 등)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=<YOUR_ACCESS_KEY>
AWS_SECRET_ACCESS_KEY=<YOUR_SECRET_KEY>

# Monitoring
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
```

**보안 권장사항:**
```bash
# .env 파일 권한 설정
chmod 600 .env.production

# Git에서 제외
echo ".env.production" >> .gitignore

# AWS Secrets Manager 사용 (권장)
aws secretsmanager create-secret \
  --name log-analysis/production \
  --secret-string file://.env.production
```

---

## 5. 백업 및 복구 전략

### 5.1 PostgreSQL 백업

#### 자동 백업 스크립트

**파일**: `scripts/backup-postgres.sh`

```bash
#!/bin/bash
set -e

# 설정
BACKUP_DIR="/mnt/data/backups/postgres"
S3_BUCKET="s3://my-log-backups/postgres"
RETENTION_DAYS=7
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

# 백업 디렉토리 생성
mkdir -p $BACKUP_DIR

# PostgreSQL 덤프
docker exec postgres pg_dump -U loguser -d logs -F c -f /tmp/backup_$TIMESTAMP.dump

# 컨테이너에서 백업 파일 복사
docker cp postgres:/tmp/backup_$TIMESTAMP.dump $BACKUP_DIR/

# 압축
gzip $BACKUP_DIR/backup_$TIMESTAMP.dump

# S3 업로드
aws s3 cp $BACKUP_DIR/backup_$TIMESTAMP.dump.gz $S3_BUCKET/

# 로컬 오래된 백업 삭제
find $BACKUP_DIR -name "backup_*.dump.gz" -mtime +$RETENTION_DAYS -delete

# S3 오래된 백업 삭제
aws s3 ls $S3_BUCKET/ | \
  grep "backup_" | \
  awk '{print $4}' | \
  while read file; do
    age=$(( ($(date +%s) - $(date -d "$(echo $file | sed 's/backup_\([0-9]\{8\}\).*/\1/' | sed 's/\(....\)\(..\)\(..\)/\1-\2-\3/')" +%s)) / 86400 ))
    if [ $age -gt $RETENTION_DAYS ]; then
      aws s3 rm $S3_BUCKET/$file
    fi
  done

echo "Backup completed: backup_$TIMESTAMP.dump.gz"
```

#### Cron 설정

```bash
# 매일 새벽 2시 백업
0 2 * * * /opt/log-analysis/scripts/backup-postgres.sh >> /var/log/postgres-backup.log 2>&1
```

### 5.2 복구 절차

```bash
# 1. S3에서 백업 다운로드
aws s3 cp s3://my-log-backups/postgres/backup_20240115_020000.dump.gz /tmp/

# 2. 압축 해제
gunzip /tmp/backup_20240115_020000.dump.gz

# 3. PostgreSQL 컨테이너에 복사
docker cp /tmp/backup_20240115_020000.dump postgres:/tmp/

# 4. 데이터베이스 복원
docker exec postgres pg_restore -U loguser -d logs -c /tmp/backup_20240115_020000.dump

# 5. 검증
docker exec postgres psql -U loguser -d logs -c "SELECT COUNT(*) FROM logs;"
```

### 5.3 Point-in-Time Recovery

**WAL 아카이빙 설정:**

```bash
# PostgreSQL 설정
cat >> /mnt/data/postgres/postgresql.conf <<EOF
wal_level = replica
archive_mode = on
archive_command = 'aws s3 cp %p s3://my-log-backups/wal/%f'
max_wal_senders = 3
wal_keep_size = 1GB
EOF

# Docker 재시작
docker-compose restart postgres
```

---

## 6. 모니터링 (CloudWatch 통합)

### 6.1 CloudWatch Agent 설정

**파일**: `/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json`

```json
{
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "root"
  },
  "metrics": {
    "namespace": "LogAnalysisSystem",
    "metrics_collected": {
      "cpu": {
        "measurement": [
          {"name": "cpu_usage_idle", "rename": "CPU_IDLE", "unit": "Percent"},
          {"name": "cpu_usage_iowait", "rename": "CPU_IOWAIT", "unit": "Percent"}
        ],
        "totalcpu": false
      },
      "disk": {
        "measurement": [
          {"name": "used_percent", "rename": "DISK_USED", "unit": "Percent"}
        ],
        "metrics_collection_interval": 60,
        "resources": ["/", "/mnt/data"]
      },
      "mem": {
        "measurement": [
          {"name": "mem_used_percent", "rename": "MEM_USED", "unit": "Percent"}
        ]
      },
      "netstat": {
        "measurement": [
          {"name": "tcp_established", "rename": "TCP_CONNECTIONS", "unit": "Count"}
        ]
      }
    }
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/user-data.log",
            "log_group_name": "/aws/ec2/log-analysis/user-data",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/opt/log-analysis/logs/*.log",
            "log_group_name": "/aws/ec2/log-analysis/application",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  }
}
```

**시작:**
```bash
sudo /opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config \
  -m ec2 \
  -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
```

### 6.2 CloudWatch 알람

```hcl
# CPU 사용률 알람
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "log-server-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EC2"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "CPU usage above 80%"
  alarm_actions       = [aws_sns_topic.alerts.arn]

  dimensions = {
    InstanceId = aws_instance.log_server.id
  }
}

# 디스크 사용률 알람
resource "aws_cloudwatch_metric_alarm" "disk_high" {
  alarm_name          = "log-server-disk-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "DISK_USED"
  namespace           = "LogAnalysisSystem"
  period              = "300"
  statistic           = "Average"
  threshold           = "85"
  alarm_description   = "Disk usage above 85%"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

# SNS 토픽 (알림용)
resource "aws_sns_topic" "alerts" {
  name = "log-analysis-alerts"
}

resource "aws_sns_topic_subscription" "email" {
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}
```

---

## 7. 비용 최적화 전략

### 7.1 월별 예상 비용

**시나리오 1: 소규모 (< 10GB/일)**
```
EC2 (t3.medium):        $30/월
EBS (100GB gp3):        $8/월
Data Transfer:          $5/월
CloudWatch:             $3/월
S3 Backup (100GB):      $2/월
───────────────────────────
총계:                   $48/월
```

**시나리오 2: 중규모 (10-50GB/일)**
```
EC2 (t3.large):         $60/월
EBS (200GB gp3):        $16/월
Data Transfer:          $15/월
CloudWatch:             $5/월
S3 Backup (500GB):      $10/월
───────────────────────────
총계:                   $106/월
```

**시나리오 3: 대규모 (50-100GB/일)**
```
EC2 (m5.xlarge):        $140/월
EBS (500GB gp3):        $40/월
Data Transfer:          $30/월
CloudWatch:             $10/월
S3 Backup (2TB):        $40/월
───────────────────────────
총계:                   $260/월
```

### 7.2 비용 절감 팁

#### Spot Instances 사용

```hcl
resource "aws_spot_instance_request" "log_server" {
  ami           = data.aws_ami.amazon_linux_2.id
  instance_type = "m5.xlarge"
  spot_price    = "0.08"  # on-demand 가격의 50%

  # Persistent request (인스턴스 종료 시 자동 재생성)
  spot_type               = "persistent"
  instance_interruption_behavior = "stop"

  # 기타 설정은 일반 instance와 동일
}
```

**비용 절감**: 최대 70%

#### Reserved Instances

```bash
# 1년 Reserved Instance (50% 할인)
# AWS Console → EC2 → Reserved Instances → Purchase

# 예시:
# m5.xlarge on-demand: $0.192/hour ($140/월)
# m5.xlarge 1yr reserved: $0.096/hour ($70/월)
```

#### S3 Intelligent-Tiering

```hcl
resource "aws_s3_bucket" "log_backup" {
  bucket = "my-log-backups"
}

resource "aws_s3_bucket_intelligent_tiering_configuration" "archive" {
  bucket = aws_s3_bucket.log_backup.id
  name   = "archive-after-90-days"

  tiering {
    access_tier = "ARCHIVE_ACCESS"
    days        = 90
  }

  tiering {
    access_tier = "DEEP_ARCHIVE_ACCESS"
    days        = 180
  }
}
```

**비용 절감**: 스토리지 비용 70% 감소 (180일 후)

#### Auto Scaling

```hcl
resource "aws_autoscaling_group" "log_server" {
  name                = "log-server-asg"
  min_size            = 1
  max_size            = 3
  desired_capacity    = 1
  vpc_zone_identifier = [aws_subnet.private.id]

  launch_template {
    id      = aws_launch_template.log_server.id
    version = "$Latest"
  }

  # Scale up when CPU > 70%
  # Scale down when CPU < 30%
  # (CloudWatch alarms 필요)
}
```

---

## 8. CI/CD 파이프라인

### 8.1 GitHub Actions

**파일**: `.github/workflows/deploy.yml`

```yaml
name: Deploy to AWS EC2

on:
  push:
    branches:
      - main
    paths:
      - 'services/**'
      - 'infrastructure/**'
  workflow_dispatch:

env:
  AWS_REGION: us-east-1
  EC2_HOST: ${{ secrets.EC2_HOST }}
  SSH_PRIVATE_KEY: ${{ secrets.SSH_PRIVATE_KEY }}

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r services/log-server/requirements.txt
          pip install pytest

      - name: Run tests
        run: pytest tests/

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v1

      - name: Build and push Docker images
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/log-server:$IMAGE_TAG services/log-server
          docker push $ECR_REGISTRY/log-server:$IMAGE_TAG

  deploy:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Deploy to EC2
        run: |
          # SSH 키 설정
          echo "$SSH_PRIVATE_KEY" > key.pem
          chmod 400 key.pem

          # 배포 스크립트 실행
          ssh -i key.pem -o StrictHostKeyChecking=no ec2-user@$EC2_HOST << 'EOF'
            cd /opt/log-analysis
            git pull origin main
            docker-compose pull
            docker-compose up -d --no-deps --build log-server
            docker-compose ps
          EOF

      - name: Health check
        run: |
          sleep 30
          curl -f http://$EC2_HOST:8000/health || exit 1

      - name: Notify Slack
        if: always()
        uses: 8398a7/action-slack@v3
        with:
          status: ${{ job.status }}
          text: 'Deployment to production: ${{ job.status }}'
          webhook_url: ${{ secrets.SLACK_WEBHOOK }}
```

---

**문서 버전**: 1.0
**최종 수정일**: 2024-01-15
**작성자**: Log Analysis System Team
