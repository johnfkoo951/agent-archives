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
import mimetypes
import urllib.parse
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse, Response
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

# 파일 경로 - Claude Code
CLAUDE_DIR = Path.home() / '.claude'
HISTORY_DIR = CLAUDE_DIR / 'claude-history'
TAGS_FILE = HISTORY_DIR / 'session-tags.json'
NAMES_FILE = HISTORY_DIR / 'session-names.json'
DESCRIPTIONS_FILE = HISTORY_DIR / 'session-descriptions.json'
UPDATE_INDEX_SCRIPT = HISTORY_DIR / 'update-index.py'

# 파일 경로 - OpenCode
OPENCODE_DIR = Path.home() / '.local' / 'share' / 'opencode'
OPENCODE_STORAGE_DIR = OPENCODE_DIR / 'storage'
OPENCODE_SESSION_DIR = OPENCODE_STORAGE_DIR / 'session'  # Contains global/ and project-specific subdirs
OPENCODE_MESSAGE_DIR = OPENCODE_STORAGE_DIR / 'message'
OPENCODE_PART_DIR = OPENCODE_STORAGE_DIR / 'part'
OPENCODE_LOG_DIR = OPENCODE_DIR / 'log'

# Pydantic 모델
class AddTagsRequest(BaseModel):
    session_id: str
    tags: str  # 쉼표로 구분된 태그 문자열

class RemoveTagRequest(BaseModel):
    session_id: str
    tag: str

class DownloadRequest(BaseModel):
    content: str
    filename: str

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
    project_path: str  # Project path (cwd)
    skip_permissions: bool = False
    terminal_app: str = "iterm2"  # "terminal", "iterm2", or "warp"

class ResumeResponse(BaseModel):
    session_id: str
    success: bool
    terminal_app: str

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
    """Resume session in selected terminal app"""
    # Build claude command
    if request.skip_permissions:
        claude_cmd = f"claude --resume {request.session_id} --dangerously-skip-permissions"
    else:
        claude_cmd = f"claude --resume {request.session_id}"

    # Escape path properly for shell
    # For single quotes: escape ' as '\''
    escaped_path_sq = request.project_path.replace("'", "'\\''")

    # Build AppleScript based on terminal app
    if request.terminal_app == "terminal":
        # Terminal: use single quotes for path (works with AppleScript)
        full_cmd = f"cd '{escaped_path_sq}' && {claude_cmd}"
        applescript = f'''
        tell application "Terminal"
            activate
            do script "{full_cmd}"
        end tell
        '''
    elif request.terminal_app == "warp":
        # Warp: write command with double quotes to temp file, then cat|pbcopy
        # This avoids all escaping issues
        full_cmd_warp = f'cd "{request.project_path}" && {claude_cmd}'
        # Write to temp file to avoid escaping issues
        tmp_file = "/tmp/claude_warp_cmd.txt"
        with open(tmp_file, 'w') as f:
            f.write(full_cmd_warp)

        applescript = f'''
        tell application "Warp"
            activate
        end tell
        delay 0.5
        tell application "System Events"
            tell process "Warp"
                keystroke "t" using command down
                delay 0.3
            end tell
        end tell
        do shell script "cat /tmp/claude_warp_cmd.txt | pbcopy"
        delay 0.2
        tell application "System Events"
            tell process "Warp"
                keystroke "v" using command down
                delay 0.3
                keystroke return
            end tell
        end tell
        '''
    else:  # iterm2 (default)
        # iTerm2: use single quotes for path (works with AppleScript)
        full_cmd = f"cd '{escaped_path_sq}' && {claude_cmd}"
        applescript = f'''
        tell application "iTerm2"
            activate
            set newWindow to (create window with default profile)
            tell current session of newWindow
                write text "{full_cmd}"
            end tell
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
            terminal_app=request.terminal_app
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

# ============== OpenCode API 엔드포인트 ==============

@app.get("/api/opencode/sessions")
async def get_opencode_sessions():
    """OpenCode 세션 목록 조회"""
    if not OPENCODE_SESSION_DIR.exists():
        return JSONResponse([])

    sessions = []
    for session_file in OPENCODE_SESSION_DIR.glob("*/ses_*.json"):
        try:
            with open(session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)

            session_id = session_data.get('id', session_file.stem)

            # Count messages for this session
            msg_count = 0
            msg_dir = OPENCODE_MESSAGE_DIR / session_id
            if msg_dir.exists():
                msg_count = len(list(msg_dir.glob("msg_*.json")))

            # Convert timestamps (ms to ISO string)
            time_data = session_data.get('time', {})
            created_ts = time_data.get('created', 0)
            updated_ts = time_data.get('updated', 0)

            from datetime import datetime
            created_str = datetime.fromtimestamp(created_ts / 1000).isoformat() if created_ts else None
            updated_str = datetime.fromtimestamp(updated_ts / 1000).isoformat() if updated_ts else None

            sessions.append({
                "sessionId": session_id,
                "project": session_data.get('directory', ''),
                "title": session_data.get('title', 'Untitled Session'),
                "lastActivity": updated_str,
                "createdAt": created_str,
                "messageCount": msg_count,
                "parentId": session_data.get('parentID'),
                "version": session_data.get('version'),
                "model": None  # Will be populated from messages if needed
            })
        except Exception as e:
            print(f"Error loading OpenCode session {session_file}: {e}")
            continue

    # Sort by lastActivity (most recent first)
    sessions.sort(key=lambda x: x.get('lastActivity') or '', reverse=True)
    return JSONResponse(sessions)

@app.get("/api/opencode/session/{session_id}")
async def get_opencode_session_messages(session_id: str):
    """OpenCode 특정 세션의 메시지 목록 조회"""
    msg_dir = OPENCODE_MESSAGE_DIR / session_id

    if not msg_dir.exists():
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    messages = []
    for msg_file in sorted(msg_dir.glob("msg_*.json")):
        try:
            with open(msg_file, 'r', encoding='utf-8') as f:
                msg_data = json.load(f)

            # Load message parts if needed
            msg_id = msg_data.get('id')
            parts = []

            # Check for parts in the part directory (OpenCode stores parts in folders)
            # Structure: storage/part/{msg_id}/prt_*.json
            part_dir = OPENCODE_PART_DIR / msg_id
            if part_dir.exists() and part_dir.is_dir():
                try:
                    for prt_file in sorted(part_dir.glob("prt_*.json")):
                        with open(prt_file, 'r', encoding='utf-8') as f:
                            part_data = json.load(f)
                        parts.append(part_data)
                except Exception as e:
                    print(f"Error loading parts for {msg_id}: {e}")

            # Convert timestamp
            time_data = msg_data.get('time', {})
            created_ts = time_data.get('created', 0)
            from datetime import datetime
            created_str = datetime.fromtimestamp(created_ts / 1000).isoformat() if created_ts else None

            # Extract model info
            model_info = msg_data.get('model', {})

            messages.append({
                "id": msg_id,
                "sessionId": session_id,
                "role": msg_data.get('role', 'unknown'),
                "timestamp": created_str,
                "summary": msg_data.get('summary', {}),
                "agent": msg_data.get('agent'),
                "model": {
                    "provider": model_info.get('providerID'),
                    "model": model_info.get('modelID')
                },
                "tools": msg_data.get('tools', {}),
                "parts": parts
            })
        except Exception as e:
            print(f"Error loading message {msg_file}: {e}")
            continue

    return JSONResponse(messages)

@app.get("/api/opencode/session/{session_id}/content")
async def get_opencode_session_content(session_id: str):
    """OpenCode 세션 전체 내용 (Claude JSONL 형식과 유사하게 변환)"""
    msg_dir = OPENCODE_MESSAGE_DIR / session_id

    if not msg_dir.exists():
        raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

    content_lines = []
    for msg_file in sorted(msg_dir.glob("msg_*.json")):
        try:
            with open(msg_file, 'r', encoding='utf-8') as f:
                msg_data = json.load(f)

            msg_id = msg_data.get('id')
            role = msg_data.get('role', 'unknown')

            # Load parts for actual content (OpenCode stores parts in folders)
            # Structure: storage/part/{msg_id}/prt_*.json
            parts_content = []
            part_dir = OPENCODE_PART_DIR / msg_id
            if part_dir.exists() and part_dir.is_dir():
                try:
                    for prt_file in sorted(part_dir.glob("prt_*.json")):
                        with open(prt_file, 'r', encoding='utf-8') as f:
                            part_data = json.load(f)
                        # Convert to Claude-like content format
                        if part_data.get('type') == 'text':
                            parts_content.append({
                                "type": "text",
                                "text": part_data.get('text', '')
                            })
                        elif part_data.get('type') == 'tool_use':
                            parts_content.append({
                                "type": "tool_use",
                                "name": part_data.get('name', 'tool'),
                                "input": part_data.get('input', {})
                            })
                        elif part_data.get('type') == 'tool_result':
                            parts_content.append({
                                "type": "tool_result",
                                "content": part_data.get('content', '')
                            })
                        else:
                            parts_content.append(part_data)
                except Exception as e:
                    print(f"Error loading parts for content {msg_id}: {e}")

            # Format similar to Claude JSONL
            formatted_msg = {
                "type": role,
                "message": {
                    "id": msg_id,
                    "role": role,
                    "content": parts_content,
                    "model": msg_data.get('model', {}).get('modelID'),
                },
                "timestamp": msg_data.get('time', {}).get('created')
            }
            content_lines.append(formatted_msg)
        except Exception as e:
            print(f"Error loading message content {msg_file}: {e}")
            continue

    return JSONResponse(content_lines)

# ============== End OpenCode API ==============

# Download API 엔드포인트 (마크다운 다운로드)
@app.post("/api/download")
async def download_file(request: DownloadRequest):
    """마크다운 파일 다운로드"""
    # 파일명에서 위험 문자 제거
    safe_filename = request.filename.replace('/', '_').replace('\\', '_')
    if not safe_filename.endswith('.md'):
        safe_filename += '.md'

    # RFC 5987 방식으로 파일명 인코딩 (한글 파일명 지원)
    encoded_filename = urllib.parse.quote(safe_filename)

    return Response(
        content=request.content.encode('utf-8'),
        media_type='application/octet-stream',
        headers={
            'Content-Disposition': f"attachment; filename*=UTF-8''{encoded_filename}",
            'Content-Length': str(len(request.content.encode('utf-8')))
        }
    )

# 로컬 이미지/파일 서빙 API
@app.get("/api/local-file")
async def serve_local_file(path: str):
    """로컬 파일 시스템의 파일을 서빙 (이미지, PDF 등)"""
    try:
        # URL 디코딩
        decoded_path = urllib.parse.unquote(path)
        file_path = Path(decoded_path)

        if not file_path.exists():
            raise HTTPException(status_code=404, detail=f"File not found: {decoded_path}")

        if not file_path.is_file():
            raise HTTPException(status_code=400, detail="Path is not a file")

        # MIME 타입 감지
        mime_type, _ = mimetypes.guess_type(str(file_path))
        if mime_type is None:
            mime_type = 'application/octet-stream'

        return FileResponse(
            path=str(file_path),
            media_type=mime_type,
            filename=file_path.name
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Active Sessions API - 실행 중인 claude/opencode 프로세스 감지
@app.get("/api/active-sessions")
async def get_active_sessions():
    """실행 중인 Claude/OpenCode 세션의 작업 디렉토리 반환"""
    active_projects = []
    
    try:
        pgrep_result = subprocess.run(
            ["pgrep", "-f", "claude|opencode"],
            capture_output=True, text=True, timeout=2
        )
        pids = [p for p in pgrep_result.stdout.strip().split('\n') if p]
        
        if not pids:
            return {"active": []}
        
        pid_list = ','.join(pids)
        lsof_result = subprocess.run(
            ["lsof", "-d", "cwd", "-Fpn", "-p", pid_list],
            capture_output=True, text=True, timeout=5
        )
        
        # lsof -Fpn 파싱: p<pid>, fcwd, n<path> 순서
        pid_cwd_map = {}
        current_pid = None
        is_cwd = False
        for line in lsof_result.stdout.split('\n'):
            if line.startswith('p'):
                current_pid = line[1:]
                is_cwd = False
            elif line == 'fcwd':
                is_cwd = True
            elif line.startswith('n') and current_pid and is_cwd:
                cwd = line[1:]
                if cwd.startswith('/') and not cwd.startswith('/dev') and not cwd.startswith('/private/tmp'):
                    pid_cwd_map[current_pid] = cwd
                is_cwd = False
        
        ps_result = subprocess.run(
            ["ps", "-p", pid_list, "-o", "pid=,comm="],
            capture_output=True, text=True, timeout=2
        )
        
        pid_cmd_map = {}
        for line in ps_result.stdout.strip().split('\n'):
            parts = line.split()
            if len(parts) >= 2:
                pid_cmd_map[parts[0]] = parts[1]
        
        for pid in pids:
            if pid in pid_cwd_map:
                cmd = pid_cmd_map.get(pid, '')
                active_projects.append({
                    "pid": int(pid),
                    "cwd": pid_cwd_map[pid],
                    "tool": "opencode" if "opencode" in cmd.lower() else "claude"
                })
    except subprocess.TimeoutExpired:
        pass
    except Exception:
        pass
    
    return {"active": active_projects}

# projects 폴더 정적 파일 서빙
app.mount("/projects", StaticFiles(directory=str(CLAUDE_DIR / 'projects')), name="projects")

# assets 폴더 정적 파일 서빙 (로고 등)
ASSETS_DIR = HISTORY_DIR / "assets"
if ASSETS_DIR.exists():
    app.mount("/assets", StaticFiles(directory=str(ASSETS_DIR)), name="assets")

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
