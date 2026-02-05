# 버전 1.1.0 배포 가이드

**새 기능**: 글로벌 에러 핸들러 (`enableGlobalErrorHandler` 옵션)

---

## 변경 사항

### 신규 기능

**글로벌 에러 핸들러**:
- 모든 uncaught errors/exceptions 자동 로깅
- 옵션으로 활성화/비활성화 가능
- 기본값: `false` (하위 호환성 유지)

**추가된 옵션**:
- JavaScript: `enableGlobalErrorHandler` (boolean)
- Python: `enable_global_error_handler` (boolean)

---

## 빌드 완료

### Python v1.1.0
- ✅ 빌드 완료: `clients/python/dist/log_collector-1.1.0-py3-none-any.whl`
- ✅ 로컬 설치 완료: `pip install -e clients/python`

### JavaScript v1.1.0
- ✅ 버전 업데이트 완료: `package.json`
- ℹ️ ES 모듈이므로 별도 빌드 불필요 (소스 직접 사용)

---

## 로컬 테스트 방법

### Python 클라이언트 테스트

```bash
# 1. 새 버전 설치 확인
python -c "import log_collector; print(log_collector.__version__)"
# 출력: 1.1.0

# 2. 글로벌 에러 핸들러 테스트
python clients/python/example_global_error_handler.py
```

### JavaScript 클라이언트 테스트

```bash
# 1. 예제 실행
node clients/javascript/example_global_error_handler.js

# 2. 데모 앱에서 테스트
cd tests/demo-app/backend
npm start
# 그리고 브라우저에서 frontend/index.html 열기
```

---

## PyPI 배포 (선택)

```bash
cd clients/python

# 1. 빌드 파일 확인
ls dist/
# log_collector-1.1.0-py3-none-any.whl
# log_collector-1.1.0.tar.gz

# 2. TestPyPI에 업로드 (테스트용)
python -m twine upload --repository testpypi dist/*

# 3. 설치 테스트
pip install --index-url https://test.pypi.org/simple/ log-collector==1.1.0

# 4. 실제 PyPI에 업로드
python -m twine upload dist/*
```

### PyPI 배포 전 체크리스트

- [ ] 모든 테스트 통과 (`pytest`)
- [ ] 버전 번호 확인 (1.1.0)
- [ ] CHANGELOG.md 업데이트
- [ ] README.md에 새 기능 문서화
- [ ] 예제 코드 동작 확인
- [ ] 라이선스 파일 확인

---

## NPM 배포 (선택)

```bash
cd clients/javascript

# 1. 로그인
npm login

# 2. 배포 (자동으로 prepublishOnly 스크립트 실행)
npm publish

# 3. 설치 테스트
npm install log-collector-async@1.1.0
```

### NPM 배포 전 체크리스트

- [ ] 모든 테스트 통과 (`npm test`)
- [ ] ESLint 통과 (`npm run lint`)
- [ ] 버전 번호 확인 (1.1.0)
- [ ] CHANGELOG.md 업데이트
- [ ] README.md에 새 기능 문서화
- [ ] 예제 코드 동작 확인

---

## 로컬 개발 환경에서 사용

### Python (editable install)

```bash
# clients/python을 개발 모드로 설치
pip install -e clients/python

# 이제 어디서든 사용 가능
python
>>> from log_collector import AsyncLogClient
>>> logger = AsyncLogClient("http://localhost:8000", enable_global_error_handler=True)
```

### JavaScript (npm link)

```bash
# 1. 클라이언트를 전역으로 링크
cd clients/javascript
npm link

# 2. 프로젝트에서 링크 사용
cd tests/demo-app/backend
npm link log-collector-async

# 3. 확인
node -e "import('log-collector-async').then(m => console.log('Loaded:', m))"
```

---

## 데모 앱 업데이트

### Backend 재시작 필요

Python 클라이언트를 업데이트했으므로 Python 백엔드 재시작:

```bash
# Ctrl+C로 기존 서버 종료 후
cd tests/demo-app/backend-python
python server.py
```

JavaScript 백엔드는 재시작 불필요 (자동으로 최신 버전 사용)

---

## 롤백 방법

문제가 발생하면 이전 버전으로 롤백:

### Python
```bash
pip install log-collector==1.0.0
```

### JavaScript
```bash
npm install log-collector-async@1.0.1
```

---

## 변경 이력

### v1.1.0 (2026-02-05)

**신규 기능**:
- 글로벌 에러 핸들러 추가 (`enableGlobalErrorHandler` / `enable_global_error_handler`)
- 자동 에러 로깅 (uncaught errors, unhandled rejections)
- 환경 변수 지원 (`ENABLE_GLOBAL_ERROR_HANDLER`)

**개선**:
- 에러 핸들러 자동 해제 (`close()` 호출 시)
- 기존 핸들러와의 호환성 개선

**문서**:
- `GLOBAL-ERROR-HANDLER.md` 추가
- 예제 파일 추가 (JavaScript, Python)
- `CLIENT-LIBRARIES.md` 업데이트

---

## 다음 단계

배포하지 않고 로컬에서만 사용하는 경우:
- ✅ Python: 이미 설치 완료 (v1.1.0)
- ✅ JavaScript: 소스 직접 사용 가능

공개 배포하는 경우:
- [ ] PyPI에 Python 패키지 배포
- [ ] NPM에 JavaScript 패키지 배포
- [ ] GitHub Release 생성
- [ ] 배포 공지
