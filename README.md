# Agent Archives

Claude Code와 OpenCode 세션 히스토리를 탐색하는 macOS 데스크톱 앱.

## 설치

### DMG 다운로드 (권장)

**[📦 Releases 페이지에서 다운로드](https://github.com/johnfkoo951/agent-archives/releases/latest)**

| 파일 | Mac 종류 |
|------|----------|
| `Agent-Archives-x.x.x-mac-arm64.dmg` | Apple Silicon (M1/M2/M3/M4) |
| `Agent-Archives-x.x.x-mac-x64.dmg` | Intel Mac |

> **Mac 종류 확인**: 메뉴바 →  → "이 Mac에 관하여" → 칩 확인

### 설치 방법

1. DMG 파일 다운로드
2. DMG 열고 `Agent Archives.app`을 Applications 폴더로 드래그
3. 앱 실행

> ⚠️ "개발자를 확인할 수 없습니다" 경고 시: 시스템 설정 → 개인정보 보호 및 보안 → "확인 없이 열기" 클릭

## 기능

- **세션 탐색**: Claude Code / OpenCode 대화 히스토리 검색 및 탐색
- **태그 & 이름**: 세션에 태그 추가, 이름 지정
- **대시보드**: 활동 통계, 프로젝트별 분석
- **Resume**: 터미널에서 세션 이어서 작업 (iTerm2, Terminal, Warp 지원)
- **Hookmark 연동**: `agentarchives://session/{id}` 딥링크 지원

## 요구사항

- macOS 10.15 (Catalina) 이상
- Python 3.8+ (앱 내장 서버용)
- Claude Code 또는 OpenCode 설치됨

---

## 개발자용

### 소스에서 실행

```bash
# 저장소 클론
git clone https://github.com/johnfkoo951/agent-archives.git
cd agent-archives

# Python 의존성 설치
pip3 install fastapi uvicorn pydantic

# Node.js 의존성 설치
cd app && npm install && cd ..

# 개발 모드 실행
cd app && npm start
```

### 빌드

```bash
cd app
npm run build

# 결과물: dist/Agent-Archives-x.x.x-mac-arm64.dmg, dist/Agent-Archives-x.x.x-mac-x64.dmg
```

### 프로젝트 구조

```
agent-archives/
├── history-server.py       # FastAPI 백엔드 (Python)
├── history-viewer.html     # Vue.js 프론트엔드 (Single HTML)
├── update-index.py         # 세션 인덱스 생성
├── app/
│   ├── src/main.js         # Electron 메인 프로세스
│   ├── src/preload.js      # IPC 브릿지
│   └── package.json        # Electron 설정
└── assets/                 # 로고, 아이콘
```

### 기술 스택

| 구성요소 | 기술 |
|----------|------|
| Backend | Python 3, FastAPI, Uvicorn |
| Frontend | Vue.js 3, Tailwind CSS, Chart.js |
| Desktop | Electron 28, electron-builder |

## 라이선스

MIT
