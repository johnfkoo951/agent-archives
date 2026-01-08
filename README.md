# Claude History Viewer

Claude Code 세션 히스토리를 시각적으로 탐색하는 데스크톱 앱.

## 프로젝트 구조

```
claude-history/
├── app/                        # Electron 앱
│   ├── src/
│   │   ├── main.js             # 메인 프로세스 (앱 생명주기, 윈도우 관리)
│   │   └── preload.js          # 보안 브릿지 (IPC 통신)
│   ├── assets/                 # 아이콘 등 리소스
│   ├── dist/                   # 빌드 결과물 (gitignore)
│   └── package.json            # Electron 설정
│
├── history-server.py           # FastAPI 백엔드 서버
├── history-viewer.html         # 웹 프론트엔드 (Vue.js 기반)
├── update-index.py             # 세션 인덱스 생성 스크립트
├── migrate-claude-project-paths.py  # 폴더 이동 마이그레이션
│
├── sessions-index.json         # 세션 인덱스 데이터 (자동 생성)
├── session-tags.json           # 사용자 태그 저장
├── session-names.json          # 사용자 세션 이름
└── session-descriptions.json   # 사용자 세션 설명
```

## 개발 워크플로우

### 1. 개발 모드 실행

```bash
# 서버만 실행 (브라우저에서 테스트)
cd ~/.claude/claude-history
python3 history-server.py --host 127.0.0.1 --port 8080

# 브라우저에서 열기
open http://127.0.0.1:8080/history-viewer.html
```

```bash
# Electron 앱으로 실행 (개발 모드)
cd ~/.claude/claude-history/app
npm start
```

### 2. 코드 수정

| 수정 대상 | 파일 | 설명 |
|----------|------|------|
| **UI/프론트엔드** | `history-viewer.html` | Vue.js 기반, 단일 파일 |
| **API/백엔드** | `history-server.py` | FastAPI, Python |
| **앱 동작** | `app/src/main.js` | Electron 메인 프로세스 |
| **앱-웹 통신** | `app/src/preload.js` | IPC 브릿지 |

### 3. 빌드 & 배포

```bash
cd ~/.claude/claude-history/app

# macOS용 빌드
npm run build

# 결과물 위치
# - dist/Claude History Viewer-x.x.x-arm64.dmg (Apple Silicon)
# - dist/Claude History Viewer-x.x.x.dmg (Intel)
```

### 4. 버전 업데이트

```bash
# 1. package.json에서 version 수정
# 2. 변경사항 커밋
git add .
git commit -m "v1.0.1: 새 기능 추가"

# 3. 태그 생성
git tag v1.0.1

# 4. 빌드
cd app && npm run build
```

## 주요 파일 설명

### history-viewer.html (프론트엔드)

- **구조**: 단일 HTML 파일에 Vue.js 앱 포함
- **스타일**: Tailwind CSS
- **주요 컴포넌트**:
  - 세션 목록 (좌측 사이드바)
  - 대화 뷰어 (메인 영역)
  - 태그/검색 필터

**수정 예시 - 새 버튼 추가:**
```html
<!-- history-viewer.html 내 해당 위치에 추가 -->
<button @click="myNewFunction" class="px-3 py-1 bg-blue-600 rounded">
  새 버튼
</button>

<script>
// Vue methods에 추가
methods: {
  myNewFunction() {
    console.log('새 기능!');
  }
}
</script>
```

### history-server.py (백엔드)

- **프레임워크**: FastAPI
- **주요 엔드포인트**:
  - `GET /sessions-index.json` - 세션 목록
  - `POST /api/tags` - 태그 추가/삭제
  - `POST /api/rename` - 세션 이름 변경
  - `POST /api/delete` - 세션 삭제
  - `POST /api/resume` - 세션 재개 (Claude Code 실행)

**수정 예시 - 새 API 추가:**
```python
# history-server.py에 추가

@app.post("/api/my-new-endpoint")
async def my_new_endpoint(data: dict):
    # 새 기능 구현
    return {"status": "success", "data": data}
```

### app/src/main.js (Electron)

- **역할**: 앱 생명주기, 윈도우 관리, Python 서버 실행
- **주요 기능**:
  - `createWindow()` - 윈도우 생성
  - `startServer()` - Python 서버 자동 시작
  - IPC 핸들러 (터미널 열기, Finder 열기 등)

## 자주 사용하는 명령어

```bash
# 개발 서버 실행
alias chv-dev="cd ~/.claude/claude-history && python3 history-server.py"

# Electron 앱 실행
alias chv-app="cd ~/.claude/claude-history/app && npm start"

# 빌드
alias chv-build="cd ~/.claude/claude-history/app && npm run build"

# 인덱스 업데이트
alias chv-index="cd ~/.claude/claude-history && python3 update-index.py"
```

## Git 워크플로우

```bash
# 기능 브랜치 생성
git checkout -b feature/new-feature

# 작업 후 커밋
git add .
git commit -m "feat: 새 기능 설명"

# main에 병합
git checkout main
git merge feature/new-feature

# 릴리스
git tag v1.0.1
npm run build
```

## 트러블슈팅

### 서버가 시작되지 않을 때
```bash
# Python 패키지 확인
pip3 install fastapi uvicorn pydantic

# 포트 충돌 확인
lsof -i :8080
```

### 앱이 열리지 않을 때
```bash
# 이전 프로세스 종료
pkill -f "history-server.py"
pkill -f "Electron"

# 다시 실행
cd ~/.claude/claude-history/app && npm start
```

### 인덱스가 업데이트되지 않을 때
```bash
cd ~/.claude/claude-history
python3 update-index.py
```

## 향후 개선 아이디어

- [ ] 세션 북마크 기능
- [ ] 대화 내보내기 (Markdown, PDF)
- [ ] 다크/라이트 테마 전환
- [ ] 키보드 단축키 지원
- [ ] 세션 통계 대시보드
- [ ] 자동 업데이트 기능
