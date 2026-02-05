# 라이브러리 배포 가이드

Python (PyPI)과 JavaScript (npm) 로그 수집 라이브러리 배포 방법

## 📦 Python 라이브러리 배포 (PyPI)

### 1. 사전 준비

**필수 패키지 설치:**
```bash
pip install --upgrade pip setuptools wheel twine
```

**PyPI 계정 생성:**
- PyPI: https://pypi.org/account/register/
- TestPyPI (테스트용): https://test.pypi.org/account/register/

**API 토큰 생성:**
1. PyPI 로그인 → Account Settings → API tokens
2. "Add API token" 클릭
3. Token name: `log-collector-upload`
4. Scope: "Entire account" 또는 "Project: log-collector"
5. 생성된 토큰 복사 (한 번만 표시됨!)

**~/.pypirc 설정 (선택사항):**
```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmc...  # 실제 토큰으로 교체

[testpypi]
username = __token__
password = pypi-AgEIcHlwaS5vcmc...  # TestPyPI 토큰으로 교체
```

### 2. 배포 전 체크리스트

```bash
cd clients/python

# ✅ 모든 테스트 통과 확인
pytest tests/ -v

# ✅ 코드 스타일 확인
black log_collector/ tests/
flake8 log_collector/ tests/

# ✅ README.md 확인
cat README.md

# ✅ setup.py 버전 확인
grep "version=" setup.py
```

### 3. 빌드

```bash
cd clients/python

# 이전 빌드 정리
rm -rf dist/ build/ *.egg-info

# 패키지 빌드
python setup.py sdist bdist_wheel
```

**빌드 결과 확인:**
```bash
ls -la dist/
# 출력:
# log-collector-1.0.0.tar.gz         (소스 배포판)
# log_collector-1.0.0-py3-none-any.whl  (휠 배포판)
```

### 4. TestPyPI에 업로드 (테스트)

```bash
# TestPyPI에 업로드
twine upload --repository testpypi dist/*

# 또는 API 토큰 직접 입력
twine upload --repository-url https://test.pypi.org/legacy/ dist/*
# Username: __token__
# Password: [TestPyPI 토큰 입력]
```

**설치 테스트:**
```bash
# 가상환경 생성
python -m venv test_env
source test_env/bin/activate  # Windows: test_env\Scripts\activate

# TestPyPI에서 설치
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ log-collector

# 테스트
python -c "from log_collector import AsyncLogClient; print('✅ Import successful')"
```

### 5. PyPI에 업로드 (프로덕션)

**최종 확인:**
- [ ] 버전 번호 확인 (setup.py)
- [ ] 모든 테스트 통과
- [ ] README.md 최신화
- [ ] CHANGELOG.md 작성 (선택)

```bash
# PyPI에 업로드
twine upload dist/*

# 또는 API 토큰 직접 입력
twine upload --repository-url https://upload.pypi.org/legacy/ dist/*
# Username: __token__
# Password: [PyPI 토큰 입력]
```

**업로드 성공 확인:**
```bash
# PyPI 페이지 확인
open https://pypi.org/project/log-collector/

# 설치 테스트
pip install log-collector
python -c "from log_collector import AsyncLogClient; print('✅ PyPI installation successful')"
```

### 6. 버전 업데이트 (다음 배포)

```bash
# setup.py 버전 업데이트
# version="1.0.0" → version="1.0.1"

# 빌드 및 업로드
rm -rf dist/ build/ *.egg-info
python setup.py sdist bdist_wheel
twine upload dist/*
```

---

## 📦 JavaScript 라이브러리 배포 (npm)

### 1. 사전 준비

**npm 계정 생성:**
- npm: https://www.npmjs.com/signup

**로그인:**
```bash
npm login
# Username: [npm 사용자명]
# Password: [비밀번호]
# Email: [이메일]
```

**로그인 확인:**
```bash
npm whoami
# 출력: your-username
```

### 2. 배포 전 체크리스트

```bash
cd clients/javascript

# ✅ 모든 테스트 통과 확인
npm test

# ✅ 린트 확인
npm run lint

# ✅ README.md 확인
cat README.md

# ✅ package.json 확인
cat package.json
```

**중요 필드 확인:**
```json
{
  "name": "log-collector-async",        // ✅ 패키지 이름 (고유해야 함)
  "version": "1.0.0",                // ✅ 버전 번호
  "description": "...",              // ✅ 설명
  "main": "src/index.js",           // ✅ 진입점
  "repository": {...},               // ✅ 저장소 URL
  "keywords": [...],                 // ✅ 검색 키워드
  "license": "MIT"                   // ✅ 라이선스
}
```

### 3. .npmignore 설정 (선택)

**.npmignore 파일 생성:**
```bash
cd clients/javascript
cat > .npmignore << 'EOF'
# 테스트 파일
__tests__/
*.test.js
coverage/

# 개발 파일
.eslintrc.js
jest.config.js

# 문서 (필요시)
docs/
examples/

# 기타
.DS_Store
node_modules/
.env
EOF
```

### 4. 패키지 테스트

**dry-run으로 배포 시뮬레이션:**
```bash
npm publish --dry-run
```

**출력 확인:**
```
npm notice
npm notice 📦  log-collector-async@1.0.0
npm notice === Tarball Contents ===
npm notice 2.5kB  package.json
npm notice 8.2kB  README.md
npm notice 15.1kB src/index.js
npm notice 12.3kB src/node-client.js
npm notice 8.9kB  src/node-worker.js
npm notice 10.5kB src/browser-client.js
npm notice 7.8kB  src/browser-worker.js
npm notice === Tarball Details ===
npm notice name:          log-collector-async
npm notice version:       1.0.0
npm notice package size:  18.2 kB
npm notice unpacked size: 65.3 kB
npm notice total files:   7
```

### 5. npm에 배포

**프로덕션 배포:**
```bash
npm publish
```

**스코프 패키지로 배포 (조직 이름 사용):**
```bash
# package.json name을 "@yourorg/log-collector-async"로 변경 후
npm publish --access public
```

**배포 성공 확인:**
```bash
# npm 페이지 확인
open https://www.npmjs.com/package/log-collector-async

# 설치 테스트
mkdir test-install
cd test-install
npm init -y
npm install log-collector-async

# 테스트
node -e "const {createLogClient} = require('log-collector-async'); console.log('✅ npm installation successful');"
```

### 6. 버전 업데이트 (다음 배포)

**시맨틱 버저닝:**
```bash
# Patch (버그 수정): 1.0.0 → 1.0.1
npm version patch

# Minor (기능 추가): 1.0.0 → 1.1.0
npm version minor

# Major (Breaking changes): 1.0.0 → 2.0.0
npm version major
```

**수동 버전 업데이트:**
```bash
# package.json 직접 수정
# "version": "1.0.0" → "version": "1.0.1"

# Git 태그 생성
git add package.json
git commit -m "Bump version to 1.0.1"
git tag v1.0.1
git push origin main --tags

# 배포
npm publish
```

---

## 🔄 배포 자동화 (GitHub Actions)

### Python (PyPI) 자동 배포

**.github/workflows/publish-python.yml:**
```yaml
name: Publish Python Package

on:
  release:
    types: [published]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          cd clients/python
          pip install --upgrade pip setuptools wheel twine
          pip install -e ".[dev]"

      - name: Run tests
        run: |
          cd clients/python
          pytest tests/

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

### JavaScript (npm) 자동 배포

**.github/workflows/publish-npm.yml:**
```yaml
name: Publish npm Package

on:
  release:
    types: [published]

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
          npm install

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

**GitHub Secrets 설정:**
1. GitHub 저장소 → Settings → Secrets and variables → Actions
2. "New repository secret" 클릭
3. Python: `PYPI_API_TOKEN` = PyPI API 토큰
4. JavaScript: `NPM_TOKEN` = npm 액세스 토큰

---

## 📝 배포 후 체크리스트

### Python
- [ ] PyPI 페이지 확인: https://pypi.org/project/log-collector/
- [ ] 새로운 환경에서 설치 테스트: `pip install log-collector`
- [ ] README 렌더링 확인
- [ ] Git 태그 생성: `git tag v1.0.0 && git push --tags`
- [ ] GitHub Release 생성 (선택)

### JavaScript
- [ ] npm 페이지 확인: https://www.npmjs.com/package/log-collector
- [ ] 새로운 환경에서 설치 테스트: `npm install log-collector`
- [ ] README 렌더링 확인
- [ ] Git 태그 생성: `git tag v1.0.0 && git push --tags`
- [ ] GitHub Release 생성 (선택)

---

## 🚨 트러블슈팅

### Python

**"Invalid distribution file" 에러:**
```bash
# 빌드 정리 후 재빌드
rm -rf dist/ build/ *.egg-info
python setup.py sdist bdist_wheel
```

**"Package name already exists" 에러:**
```bash
# setup.py에서 패키지 이름 변경
name="log-collector-yourname"
```

**"Upload failed (403)" 에러:**
```bash
# API 토큰 확인
twine upload --verbose dist/*
```

### JavaScript

**"403 Forbidden" 에러:**
```bash
# 로그인 상태 확인
npm whoami

# 재로그인
npm logout
npm login
```

**"Package name too similar" 에러:**
```bash
# package.json에서 이름 변경
"name": "@yourorg/log-collector"

# 스코프 패키지로 배포
npm publish --access public
```

**"Pre-publish script failed" 에러:**
```bash
# prepublishOnly 스크립트 비활성화 (임시)
npm publish --ignore-scripts
```

---

## 📚 참고 자료

**Python (PyPI):**
- PyPI 공식 문서: https://packaging.python.org/
- Twine 문서: https://twine.readthedocs.io/
- 시맨틱 버저닝: https://semver.org/

**JavaScript (npm):**
- npm 공식 문서: https://docs.npmjs.com/
- package.json 스펙: https://docs.npmjs.com/cli/v9/configuring-npm/package-json
- 시맨틱 버저닝: https://semver.org/

---

## ✅ 빠른 시작 (요약)

### Python
```bash
cd clients/python
pip install --upgrade pip setuptools wheel twine
pytest tests/
rm -rf dist/ build/ *.egg-info
python setup.py sdist bdist_wheel
twine upload dist/*
```

### JavaScript
```bash
cd clients/javascript
npm test
npm run lint
npm publish --dry-run  # 테스트
npm publish             # 실제 배포
```

---

**배포 완료! 🎉**
