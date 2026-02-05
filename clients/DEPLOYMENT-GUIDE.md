# 로그 수집 라이브러리 배포 가이드

Python 및 JavaScript 로그 수집 클라이언트 라이브러리를 배포하는 방법

---

## 📋 목차

1. [배포 준비](#-배포-준비)
2. [Python 라이브러리 배포 (PyPI)](#-python-라이브러리-배포-pypi)
3. [JavaScript 라이브러리 배포 (npm)](#-javascript-라이브러리-배포-npm)
4. [비공개 배포 (사내용)](#-비공개-배포-사내용)
5. [버전 관리 전략](#-버전-관리-전략)
6. [CI/CD 자동화](#-cicd-자동화)
7. [배포 체크리스트](#-배포-체크리스트)

---

## 🚀 배포 준비

### 현재 라이브러리 정보

| 항목 | Python | JavaScript |
|------|--------|------------|
| **패키지명** | `log-collector` | `log-client` |
| **현재 버전** | 1.0.0 | 1.0.0 |
| **레지스트리** | PyPI | npm |
| **라이선스** | MIT | MIT |

---

## 🐍 Python 라이브러리 배포 (PyPI)

### 1단계: 사전 준비

#### PyPI 계정 생성
```bash
# PyPI 회원가입
# https://pypi.org/account/register/

# TestPyPI 회원가입 (테스트용)
# https://test.pypi.org/account/register/
```

#### 필수 도구 설치
```bash
# 배포 도구 설치
pip install --upgrade pip setuptools wheel twine

# 설치 확인
twine --version
```

#### API 토큰 생성
```bash
# PyPI 로그인 → Account Settings → API tokens
# Scope: "Entire account" 또는 "Project: log-collector"
# 토큰 저장: pypi-AgEIcHlwaS5vcmc...
```

#### ~/.pypirc 설정
```bash
# Windows: C:\Users\<username>\.pypirc
# Linux/Mac: ~/.pypirc

cat > ~/.pypirc << 'EOF'
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmc...

[testpypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmc...
EOF

chmod 600 ~/.pypirc
```

---

### 2단계: 빌드 준비

#### 필수 파일 확인
```bash
cd clients/python

# 필수 파일 체크리스트
ls -la
# ✅ setup.py          - 패키지 설정
# ✅ README.md         - 패키지 설명
# ✅ LICENSE           - 라이선스 파일
# ✅ MANIFEST.in       - 포함 파일 지정 (선택)
# ✅ log_collector/    - 소스 코드
```

#### setup.py 확인
```python
# clients/python/setup.py
setup(
    name="log-collector",              # PyPI 패키지명
    version="1.0.0",                   # 버전 (Semantic Versioning)
    author="Log Analysis System Team",
    description="고성능 비동기 로그 수집 클라이언트",
    long_description=long_description,  # README.md 내용
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "aiohttp>=3.8.0",
    ],
)
```

#### README.md 작성 (필수!)
```markdown
# log-collector

고성능 비동기 로그 수집 클라이언트

## 설치

\`\`\`bash
pip install log-collector
\`\`\`

## 사용법

\`\`\`python
from log_collector import AsyncLogClient

client = AsyncLogClient("http://localhost:8000")
client.info("Hello, World!")
\`\`\`

## 특징

- 비블로킹 (~0.05ms)
- 스마트 배치 (1000건 or 1초)
- gzip 압축
- Graceful shutdown
```

---

### 3단계: 테스트 및 빌드

#### 로컬 테스트
```bash
cd clients/python

# 테스트 실행
pytest tests/ -v

# 코드 품질 검사
black .
flake8 log_collector/
```

#### 패키지 빌드
```bash
# 이전 빌드 제거
rm -rf dist/ build/ *.egg-info

# 빌드 실행
python setup.py sdist bdist_wheel

# 결과 확인
ls dist/
# log-collector-1.0.0.tar.gz        (소스 배포본)
# log_collector-1.0.0-py3-none-any.whl  (휠 배포본)
```

#### 빌드 검증
```bash
# 패키지 내용 확인
tar -tzf dist/log-collector-1.0.0.tar.gz

# 휠 파일 검증
twine check dist/*
# Checking dist/log-collector-1.0.0.tar.gz: PASSED
# Checking dist/log_collector-1.0.0-py3-none-any.whl: PASSED
```

---

### 4단계: TestPyPI 배포 (테스트)

```bash
# TestPyPI에 업로드
twine upload --repository testpypi dist/*

# 업로드 성공 시 URL 표시
# https://test.pypi.org/project/log-collector/1.0.0/
```

#### TestPyPI에서 설치 테스트
```bash
# 가상환경 생성
python -m venv test_env
source test_env/bin/activate  # Windows: test_env\Scripts\activate

# TestPyPI에서 설치
pip install --index-url https://test.pypi.org/simple/ log-collector

# 동작 확인
python -c "from log_collector import AsyncLogClient; print('Success!')"

# 정리
deactivate
rm -rf test_env
```

---

### 5단계: 공식 PyPI 배포

```bash
# 최종 배포
twine upload dist/*

# 업로드 성공 확인
# https://pypi.org/project/log-collector/1.0.0/
```

#### 배포 후 검증
```bash
# 새 가상환경에서 설치 테스트
python -m venv verify_env
source verify_env/bin/activate

# PyPI에서 설치
pip install log-collector

# 동작 확인
python -c "
from log_collector import AsyncLogClient
client = AsyncLogClient('http://localhost:8000')
client.info('Test from PyPI')
print('✅ PyPI installation successful!')
"

# 정리
deactivate
rm -rf verify_env
```

---

### 6단계: 사용자 설치

이제 사용자는 다음과 같이 설치할 수 있습니다:

```bash
# 공식 설치
pip install log-collector

# 특정 버전 설치
pip install log-collector==1.0.0

# 최신 버전으로 업그레이드
pip install --upgrade log-collector

# 개발 의존성 포함 설치
pip install log-collector[dev]
```

---

## 📦 JavaScript 라이브러리 배포 (npm)

### 1단계: 사전 준비

#### npm 계정 생성
```bash
# npm 회원가입
# https://www.npmjs.com/signup

# npm 로그인
npm login
# Username: your-username
# Password: your-password
# Email: your-email@example.com
```

#### 계정 확인
```bash
# 로그인 상태 확인
npm whoami
# your-username
```

#### 2FA 설정 (권장)
```bash
# Two-Factor Authentication 활성화
npm profile enable-2fa auth-and-writes

# 인증 앱 (Google Authenticator, Authy 등)에 등록
```

---

### 2단계: 빌드 준비

#### 필수 파일 확인
```bash
cd clients/javascript

# 필수 파일 체크리스트
ls -la
# ✅ package.json      - 패키지 설정
# ✅ README.md         - 패키지 설명
# ✅ LICENSE           - 라이선스 파일
# ✅ .npmignore        - 제외 파일 지정 (선택)
# ✅ src/              - 소스 코드
```

#### package.json 확인
```json
{
  "name": "log-client",
  "version": "1.0.0",
  "description": "고성능 비동기 로그 수집 클라이언트 (Browser + Node.js)",
  "main": "src/index.js",
  "type": "module",
  "keywords": [
    "logging",
    "async",
    "web-worker",
    "worker-threads",
    "performance"
  ],
  "author": "Log Analysis System Team",
  "license": "MIT",
  "engines": {
    "node": ">=12.0.0"
  }
}
```

#### .npmignore 생성 (선택)
```bash
cat > .npmignore << 'EOF'
# 테스트 파일
__tests__/
*.test.js
test-manual.js
coverage/

# 빌드 도구
jest.config.js
.eslintrc.js
rollup.config.js

# 기타
.git
.gitignore
node_modules/
*.log
EOF
```

#### README.md 작성 (필수!)
```markdown
# log-client

고성능 비동기 로그 수집 클라이언트 (Browser + Node.js)

## 설치

\`\`\`bash
npm install log-client
\`\`\`

## 사용법

### Node.js
\`\`\`javascript
import { createLogClient } from 'log-client';

const logger = createLogClient('http://localhost:8000');
logger.info('Hello, World!');
\`\`\`

### 브라우저
\`\`\`html
<script type="module">
import { createLogClient } from 'log-client';

const logger = createLogClient('http://localhost:8000');
logger.info('Button clicked');
</script>
\`\`\`

## 특징

- 비블로킹 (~0.01ms)
- Worker Threads / Web Worker
- 스마트 배치 (1000건 or 1초)
- gzip 압축
```

---

### 3단계: 테스트 및 빌드

#### 로컬 테스트
```bash
cd clients/javascript

# 의존성 설치
npm install

# 테스트 실행
npm test

# 린트 검사
npm run lint
```

#### 배포 전 검증
```bash
# package.json 검증
npm pkg fix

# 포함될 파일 확인
npm pack --dry-run

# 출력 예시:
# npm notice package: log-client@1.0.0
# npm notice === Tarball Contents ===
# npm notice 1.2kB  package.json
# npm notice 2.5kB  README.md
# npm notice 1.1kB  LICENSE
# npm notice 500B   src/index.js
# npm notice 2.3kB  src/node-client.js
# npm notice 2.1kB  src/browser-client.js
# npm notice ...
```

#### 로컬 패키지 생성
```bash
# .tgz 파일 생성
npm pack

# 결과: log-client-1.0.0.tgz

# 로컬 설치 테스트
npm install ./log-client-1.0.0.tgz

# 동작 확인
node -e "import('./node_modules/log-client/src/index.js').then(m => console.log('✅ Success!'))"
```

---

### 4단계: npm 배포

#### 배포 실행
```bash
# 배포 (공개)
npm publish

# 만약 스코프 패키지라면 (@your-org/log-client)
npm publish --access public
```

#### 2FA 인증
```
npm notice
npm notice Publishing to https://registry.npmjs.org/
npm notice
Enter OTP: 123456  # 인증 앱의 코드 입력
```

#### 배포 성공 확인
```bash
# npm 웹사이트 확인
# https://www.npmjs.com/package/log-client

# 패키지 정보 확인
npm view log-client

# 출력:
# log-client@1.0.0 | MIT | deps: none | versions: 1
# 고성능 비동기 로그 수집 클라이언트 (Browser + Node.js)
# https://www.npmjs.com/package/log-client
```

---

### 5단계: 배포 후 검증

```bash
# 새 디렉토리에서 설치 테스트
mkdir test-install && cd test-install
npm init -y
npm install log-client

# Node.js에서 테스트
node -e "
import('./node_modules/log-client/src/index.js').then(m => {
  const { createLogClient } = m;
  const logger = createLogClient('http://localhost:8000');
  logger.info('Test from npm');
  console.log('✅ npm installation successful!');
});
"

# 정리
cd ..
rm -rf test-install
```

---

### 6단계: 사용자 설치

이제 사용자는 다음과 같이 설치할 수 있습니다:

```bash
# 공식 설치
npm install log-client

# 특정 버전 설치
npm install log-client@1.0.0

# 최신 버전으로 업그레이드
npm update log-client
```

---

## 🔒 비공개 배포 (사내용)

### Python - Private PyPI

#### 옵션 A: PyPI Server 구축

```bash
# pypiserver 설치
pip install pypiserver passlib

# 서버 실행 (htpasswd 인증)
htpasswd -sc .htpasswd myuser
pypi-server run -p 8080 -P .htpasswd packages/

# 패키지 업로드
twine upload --repository-url http://localhost:8080 dist/*

# 사용자 설치
pip install --index-url http://myuser:mypass@localhost:8080/simple/ log-collector
```

#### 옵션 B: Git 직접 설치

```bash
# Git 저장소에 푸시
git push origin main

# 사용자 설치
pip install git+https://github.com/your-org/log-collector.git

# 특정 브랜치/태그
pip install git+https://github.com/your-org/log-collector.git@v1.0.0
```

#### 옵션 C: 파일 서버

```bash
# 패키지 빌드
python setup.py sdist bdist_wheel

# 파일 서버에 업로드
scp dist/* server:/path/to/packages/

# 사용자 설치
pip install http://internal-server/packages/log-collector-1.0.0.tar.gz
```

---

### JavaScript - Private npm

#### 옵션 A: npm Private Packages (유료)

```bash
# package.json 수정
{
  "name": "@your-org/log-client",  # 스코프 추가
  "private": true
}

# 배포
npm publish

# 사용자 설치
npm install @your-org/log-client
```

#### 옵션 B: Verdaccio (무료 Private Registry)

```bash
# Verdaccio 설치
npm install -g verdaccio

# 서버 실행
verdaccio
# http://localhost:4873/

# npm 레지스트리 변경
npm set registry http://localhost:4873/

# 사용자 추가
npm adduser --registry http://localhost:4873/

# 패키지 배포
npm publish --registry http://localhost:4873/

# 사용자 설치
npm install log-client --registry http://localhost:4873/
```

#### 옵션 C: Git 직접 설치

```bash
# Git 저장소에 푸시
git push origin main

# package.json에 의존성 추가
{
  "dependencies": {
    "log-client": "git+https://github.com/your-org/log-client.git#v1.0.0"
  }
}

# 설치
npm install
```

---

## 📌 버전 관리 전략

### Semantic Versioning (SemVer)

```
MAJOR.MINOR.PATCH
  1  .  0  .  0

MAJOR: 호환되지 않는 API 변경
MINOR: 하위 호환되는 기능 추가
PATCH: 하위 호환되는 버그 수정
```

### 버전 업데이트 예시

| 변경 내용 | 기존 버전 | 새 버전 |
|----------|----------|---------|
| 버그 수정 | 1.0.0 | 1.0.1 |
| 새 기능 추가 | 1.0.1 | 1.1.0 |
| API 변경 (Breaking) | 1.1.0 | 2.0.0 |

### Python 버전 업데이트

```bash
# setup.py 수정
setup(
    name="log-collector",
    version="1.0.1",  # 버전 업데이트
    ...
)

# Git 태그 생성
git tag -a v1.0.1 -m "Release version 1.0.1"
git push origin v1.0.1

# 빌드 및 배포
rm -rf dist/
python setup.py sdist bdist_wheel
twine upload dist/*
```

### JavaScript 버전 업데이트

```bash
# npm 명령어로 자동 업데이트
npm version patch  # 1.0.0 → 1.0.1
npm version minor  # 1.0.1 → 1.1.0
npm version major  # 1.1.0 → 2.0.0

# Git 태그 자동 생성됨
git push origin main --tags

# 배포
npm publish
```

---

## 🤖 CI/CD 자동화

### GitHub Actions - Python 배포

```yaml
# .github/workflows/publish-python.yml
name: Publish Python Package

on:
  release:
    types: [created]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install --upgrade pip setuptools wheel twine

      - name: Build package
        run: |
          cd clients/python
          python setup.py sdist bdist_wheel

      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: |
          cd clients/python
          twine upload dist/*
```

### GitHub Actions - JavaScript 배포

```yaml
# .github/workflows/publish-npm.yml
name: Publish npm Package

on:
  release:
    types: [created]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          registry-url: 'https://registry.npmjs.org'

      - name: Install dependencies
        run: |
          cd clients/javascript
          npm ci

      - name: Run tests
        run: |
          cd clients/javascript
          npm test

      - name: Publish to npm
        env:
          NODE_AUTH_TOKEN: ${{ secrets.NPM_TOKEN }}
        run: |
          cd clients/javascript
          npm publish
```

### Secrets 설정

```bash
# GitHub Repository Settings → Secrets and variables → Actions

# Python
PYPI_API_TOKEN: pypi-AgEIcHlwaS5vcmc...

# JavaScript
NPM_TOKEN: npm_aBcDeFgHiJkLmNoPqRsTuVwXyZ...
```

---

## ✅ 배포 체크리스트

### Python (PyPI) 배포 전

- [ ] 테스트 통과 (`pytest tests/ -v`)
- [ ] 코드 품질 검사 (`black .`, `flake8`)
- [ ] setup.py 버전 업데이트
- [ ] README.md 최신화
- [ ] CHANGELOG.md 업데이트
- [ ] Git 태그 생성 (`git tag v1.0.0`)
- [ ] TestPyPI 테스트 완료
- [ ] 빌드 검증 (`twine check dist/*`)

### JavaScript (npm) 배포 전

- [ ] 테스트 통과 (`npm test`)
- [ ] 린트 검사 (`npm run lint`)
- [ ] package.json 버전 업데이트
- [ ] README.md 최신화
- [ ] CHANGELOG.md 업데이트
- [ ] Git 태그 생성 (`npm version`)
- [ ] 로컬 설치 테스트 (`npm pack`)
- [ ] 포함 파일 확인 (`npm pack --dry-run`)

### 배포 후

- [ ] PyPI/npm 웹사이트에서 확인
- [ ] 새 환경에서 설치 테스트
- [ ] 동작 확인
- [ ] 문서 업데이트 (설치 가이드)
- [ ] Release Notes 작성
- [ ] 팀에 공지

---

## 📝 추가 자료

### Python 배포 참고 자료
- [PyPI 공식 가이드](https://packaging.python.org/tutorials/packaging-projects/)
- [Twine 문서](https://twine.readthedocs.io/)
- [setuptools 문서](https://setuptools.pypa.io/)

### JavaScript 배포 참고 자료
- [npm 공식 가이드](https://docs.npmjs.com/packages-and-modules)
- [package.json 명세](https://docs.npmjs.com/cli/v9/configuring-npm/package-json)
- [Semantic Versioning](https://semver.org/)

### CI/CD 참고 자료
- [GitHub Actions](https://docs.github.com/en/actions)
- [GitLab CI/CD](https://docs.gitlab.com/ee/ci/)

---

## 🚨 문제 해결

### Python 배포 오류

**오류: "Invalid distribution"**
```bash
# 해결: dist/ 디렉토리 정리
rm -rf dist/ build/ *.egg-info
python setup.py sdist bdist_wheel
```

**오류: "Duplicate version"**
```bash
# 해결: 버전 증가 필요
# setup.py에서 version="1.0.1"로 변경
```

### JavaScript 배포 오류

**오류: "Package name already exists"**
```bash
# 해결 1: 다른 이름 사용
# package.json에서 "name": "log-client-v2"

# 해결 2: 스코프 추가
# package.json에서 "name": "@your-org/log-client"
```

**오류: "OTP required"**
```bash
# 해결: 2FA 코드 입력
npm publish --otp=123456
```

---

## 🎯 Quick Reference

### Python 빠른 배포
```bash
cd clients/python
pytest tests/ -v
rm -rf dist/
python setup.py sdist bdist_wheel
twine check dist/*
twine upload dist/*
```

### JavaScript 빠른 배포
```bash
cd clients/javascript
npm test
npm version patch
npm publish
```
