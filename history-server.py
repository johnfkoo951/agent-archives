#!/usr/bin/env python3
"""
FastAPI server for Claude History Viewer.
Serves static files and provides API endpoints for tag/rename/delete operations.

Usage:
    cd ~/.claude && python3 history-server.py
    # or with custom host/port:
    cd ~/.claude && python3 history-server.py --host 0.0.0.0 --port 8080
"""

import json
import argparse
import subprocess
import sys
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import uvicorn

app = FastAPI(title="Claude History Viewer API")

# CORS 설정 (로컬 개발용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 파일 경로
CLAUDE_DIR = Path.home() / '.claude'
HISTORY_DIR = CLAUDE_DIR / 'claude-history'
TAGS_FILE = HISTORY_DIR / 'session-tags.json'
NAMES_FILE = HISTORY_DIR / 'session-names.json'
DESCRIPTIONS_FILE = HISTORY_DIR / 'session-descriptions.json'
UPDATE_INDEX_SCRIPT = HISTORY_DIR / 'update-index.py'

# Pydantic 모델
class AddTagsRequest(BaseModel):
    session_id: str
    tags: str  # 쉼표로 구분된 태그 문자열

class RemoveTagRequest(BaseModel):
    session_id: str
    tag: str

class TagsResponse(BaseModel):
    session_id: str
    tags: List[str]
    added: Optional[List[str]] = None
    skipped: Optional[List[str]] = None
    removed: Optional[str] = None

class RenameRequest(BaseModel):
    session_id: str
    name: Optional[str] = None  # None이면 이름 삭제

class RenameResponse(BaseModel):
    session_id: str
    name: Optional[str] = None
    action: str  # 'renamed' or 'removed'

class DescriptionRequest(BaseModel):
    session_id: str
    description: Optional[str] = None  # None이면 설명 삭제

class DescriptionResponse(BaseModel):
    session_id: str
    description: Optional[str] = None
    action: str  # 'updated' or 'removed'

class DeleteRequest(BaseModel):
    session_id: str
    project_folder: str
    file_name: str

class DeleteResponse(BaseModel):
    session_id: str
    deleted: bool
    file_path: str

class ResumeRequest(BaseModel):
    session_id: str
    project_path: str  # 프로젝트 경로 (cwd)
    skip_permissions: bool = False
    open_in: str = "tab"  # "tab" or "window"

class ResumeResponse(BaseModel):
    session_id: str
    success: bool
    open_in: str

# 헬퍼 함수
def load_tags() -> dict:
    """session-tags.json 로드"""
    if TAGS_FILE.exists():
        with open(TAGS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_tags(tags: dict):
    """session-tags.json 저장"""
    with open(TAGS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tags, f, indent=2, ensure_ascii=False)

def load_names() -> dict:
    """session-names.json 로드"""
    if NAMES_FILE.exists():
        with open(NAMES_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_names(names: dict):
    """session-names.json 저장"""
    with open(NAMES_FILE, 'w', encoding='utf-8') as f:
        json.dump(names, f, indent=2, ensure_ascii=False)

def load_descriptions() -> dict:
    """session-descriptions.json 로드"""
    if DESCRIPTIONS_FILE.exists():
        with open(DESCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_descriptions(descriptions: dict):
    """session-descriptions.json 저장"""
    with open(DESCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
        json.dump(descriptions, f, indent=2, ensure_ascii=False)

def run_update_index():
    """update-index.py 실행"""
    if UPDATE_INDEX_SCRIPT.exists():
        result = subprocess.run(
            [sys.executable, str(UPDATE_INDEX_SCRIPT)],
            cwd=str(CLAUDE_DIR),
            capture_output=True,
            text=True
        )
        return result.returncode == 0
    return False

# API 엔드포인트
@app.get("/api/tags")
async def get_all_tags():
    """모든 세션의 태그 조회"""
    return load_tags()

@app.get("/api/tags/{session_id}")
async def get_session_tags(session_id: str):
    """특정 세션의 태그 조회"""
    all_tags = load_tags()
    return {"session_id": session_id, "tags": all_tags.get(session_id, [])}

@app.post("/api/tags/add")
async def add_tags(request: AddTagsRequest):
    """태그 추가 (쉼표로 구분된 여러 태그 지원)"""
    all_tags = load_tags()
    session_tags = all_tags.get(request.session_id, [])

    # 쉼표로 구분된 태그 파싱
    tags_to_add = [t.strip() for t in request.tags.split(',') if t.strip()]

    added = []
    skipped = []

    for tag in tags_to_add:
        if tag == 'named':
            skipped.append(tag)
            continue
        if tag not in session_tags:
            session_tags.append(tag)
            added.append(tag)
        else:
            skipped.append(tag)

    if added:
        all_tags[request.session_id] = session_tags
        save_tags(all_tags)

    return TagsResponse(
        session_id=request.session_id,
        tags=session_tags,
        added=added,
        skipped=skipped
    )

@app.post("/api/tags/remove")
async def remove_tag(request: RemoveTagRequest):
    """태그 삭제"""
    if request.tag == 'named':
        raise HTTPException(status_code=400, detail="'named' 태그는 자동 태그이므로 삭제할 수 없습니다.")

    all_tags = load_tags()
    session_tags = all_tags.get(request.session_id, [])

    if request.tag not in session_tags:
        raise HTTPException(status_code=404, detail=f"태그 '{request.tag}'를 찾을 수 없습니다.")

    session_tags.remove(request.tag)

    if session_tags:
        all_tags[request.session_id] = session_tags
    else:
        if request.session_id in all_tags:
            del all_tags[request.session_id]

    save_tags(all_tags)

    return TagsResponse(
        session_id=request.session_id,
        tags=session_tags,
        removed=request.tag
    )

# Rename API 엔드포인트
@app.get("/api/names")
async def get_all_names():
    """모든 세션의 이름 조회"""
    return load_names()

@app.get("/api/names/{session_id}")
async def get_session_name(session_id: str):
    """특정 세션의 이름 조회"""
    all_names = load_names()
    return {"session_id": session_id, "name": all_names.get(session_id)}

@app.post("/api/rename")
async def rename_session(request: RenameRequest):
    """세션 이름 변경 또는 삭제"""
    all_names = load_names()

    if request.name is None or request.name.strip() == '':
        # 이름 삭제
        if request.session_id in all_names:
            del all_names[request.session_id]
        save_names(all_names)
        run_update_index()
        return RenameResponse(
            session_id=request.session_id,
            name=None,
            action='removed'
        )
    else:
        # 이름 변경
        all_names[request.session_id] = request.name.strip()
        save_names(all_names)
        run_update_index()
        return RenameResponse(
            session_id=request.session_id,
            name=request.name.strip(),
            action='renamed'
        )

# Description API 엔드포인트
@app.get("/api/descriptions")
async def get_all_descriptions():
    """모든 세션의 설명 조회"""
    return load_descriptions()

@app.get("/api/descriptions/{session_id}")
async def get_session_description(session_id: str):
    """특정 세션의 설명 조회"""
    all_descriptions = load_descriptions()
    return {"session_id": session_id, "description": all_descriptions.get(session_id)}

@app.post("/api/description")
async def update_description(request: DescriptionRequest):
    """세션 설명 변경 또는 삭제"""
    all_descriptions = load_descriptions()

    if request.description is None or request.description.strip() == '':
        # 설명 삭제
        if request.session_id in all_descriptions:
            del all_descriptions[request.session_id]
        save_descriptions(all_descriptions)
        return DescriptionResponse(
            session_id=request.session_id,
            description=None,
            action='removed'
        )
    else:
        # 설명 변경
        all_descriptions[request.session_id] = request.description.strip()
        save_descriptions(all_descriptions)
        return DescriptionResponse(
            session_id=request.session_id,
            description=request.description.strip(),
            action='updated'
        )

# Index 업데이트 API
@app.post("/api/update-index")
async def update_index():
    """sessions-index.json 업데이트"""
    success = run_update_index()
    if success:
        return {"status": "success", "message": "Index updated successfully"}
    raise HTTPException(status_code=500, detail="Failed to update index")

# Delete API 엔드포인트
@app.post("/api/delete")
async def delete_session(request: DeleteRequest):
    """세션 파일 삭제"""
    # 보안: project_folder와 file_name에 경로 탐색 문자가 없는지 확인
    if '..' in request.project_folder or '..' in request.file_name:
        raise HTTPException(status_code=400, detail="Invalid path")
    if '/' in request.file_name or '\\' in request.file_name:
        raise HTTPException(status_code=400, detail="Invalid file name")

    # 파일 경로 구성
    file_path = CLAUDE_DIR / 'projects' / request.project_folder / request.file_name

    if not file_path.exists():
        raise HTTPException(status_code=404, detail=f"Session file not found: {request.file_name}")

    # 파일이 projects 폴더 내에 있는지 확인 (보안)
    try:
        file_path.resolve().relative_to((CLAUDE_DIR / 'projects').resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")

    # 파일 삭제
    try:
        file_path.unlink()

        # 관련 태그 삭제
        all_tags = load_tags()
        if request.session_id in all_tags:
            del all_tags[request.session_id]
            save_tags(all_tags)

        # 관련 이름 삭제
        all_names = load_names()
        if request.session_id in all_names:
            del all_names[request.session_id]
            save_names(all_names)

        # 관련 설명 삭제
        all_descriptions = load_descriptions()
        if request.session_id in all_descriptions:
            del all_descriptions[request.session_id]
            save_descriptions(all_descriptions)

        # 인덱스 업데이트
        run_update_index()

        return DeleteResponse(
            session_id=request.session_id,
            deleted=True,
            file_path=str(file_path)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete: {str(e)}")

# Resume API 엔드포인트
@app.post("/api/resume")
async def resume_session(request: ResumeRequest):
    """iTerm2에서 세션 재개"""
    # claude 명령어 구성
    if request.skip_permissions:
        claude_cmd = f"claude --resume {request.session_id} --dangerously-skip-permissions"
    else:
        claude_cmd = f"claude --resume {request.session_id}"

    # 프로젝트 경로로 이동 후 claude 실행
    full_cmd = f"cd {request.project_path} && {claude_cmd}"

    # AppleScript 구성
    if request.open_in == "window":
        applescript = f'''
        tell application "iTerm2"
            create window with default profile
            tell current session of current window
                write text "{full_cmd}"
            end tell
            activate
        end tell
        '''
    else:  # tab
        applescript = f'''
        tell application "iTerm2"
            tell current window
                create tab with default profile
                tell current session
                    write text "{full_cmd}"
                end tell
            end tell
            activate
        end tell
        '''

    try:
        result = subprocess.run(
            ["osascript", "-e", applescript],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"AppleScript failed: {result.stderr}")

        return ResumeResponse(
            session_id=request.session_id,
            success=True,
            open_in=request.open_in
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to open iTerm2: {str(e)}")

# 정적 파일 서빙 (history-viewer.html 등)
@app.get("/")
async def root():
    return FileResponse(HISTORY_DIR / 'history-viewer.html')

@app.get("/history-viewer.html")
async def history_viewer():
    return FileResponse(HISTORY_DIR / 'history-viewer.html')

# sessions-index.json 서빙
@app.get("/sessions-index.json")
async def sessions_index():
    index_file = HISTORY_DIR / 'sessions-index.json'
    if index_file.exists():
        return FileResponse(index_file)
    raise HTTPException(status_code=404, detail="sessions-index.json not found")

# session-tags.json 서빙 (GET으로 직접 접근용)
@app.get("/session-tags.json")
async def session_tags_file():
    if TAGS_FILE.exists():
        return FileResponse(TAGS_FILE)
    return JSONResponse({})

# session-descriptions.json 서빙 (GET으로 직접 접근용)
@app.get("/session-descriptions.json")
async def session_descriptions_file():
    if DESCRIPTIONS_FILE.exists():
        return FileResponse(DESCRIPTIONS_FILE)
    return JSONResponse({})

# projects 폴더 정적 파일 서빙
app.mount("/projects", StaticFiles(directory=str(CLAUDE_DIR / 'projects')), name="projects")

def main():
    parser = argparse.ArgumentParser(description='Claude History Viewer Server')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind (default: 127.0.0.1)')
    parser.add_argument('--port', type=int, default=8080, help='Port to bind (default: 8080)')
    parser.add_argument('--skip-index', action='store_true', help='Skip running update-index.py on startup')
    args = parser.parse_args()

    print(f"\n🚀 Claude History Viewer Server")
    print(f"   http://{args.host}:{args.port}/history-viewer.html")
    print(f"\n📁 Serving from: {CLAUDE_DIR}")

    # 시작 시 update-index.py 실행
    if not args.skip_index:
        print("📊 Updating session index...")
        if run_update_index():
            print("   Index updated successfully")
        else:
            print("   Warning: Failed to update index")

    print(f"\n🏷️  Tags API: /api/tags")
    print(f"✏️  Rename API: /api/rename")
    print(f"📝 Description API: /api/description")
    print(f"🗑️  Delete API: /api/delete")
    print(f"▶️  Resume API: /api/resume")
    print(f"🔄 Update Index API: /api/update-index")
    print(f"\nPress Ctrl+C to stop\n")

    uvicorn.run(app, host=args.host, port=args.port)

if __name__ == '__main__':
    main()
