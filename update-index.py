#!/usr/bin/env python3
"""
Claude History Index Updater
Run this script to update the sessions index after new conversations.
Extracts original Korean folder names from session files.

Updated: 2025-12-15 - Resume path fix: migrate sessions instead of mapping paths in index
"""

import json
import os
import unicodedata
from pathlib import Path
from datetime import datetime

def extract_cwd_from_file(jsonl_file):
    """Extract the original cwd (working directory) from a jsonl file."""
    try:
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    if 'cwd' in data and data['cwd']:
                        return data['cwd']
                except:
                    continue
    except:
        pass
    return None

def get_folder_cwd(project_folder):
    """Get cwd from any file in the project folder (including agent files)."""
    # First try non-agent files
    for jsonl_file in project_folder.glob('*.jsonl'):
        cwd = extract_cwd_from_file(jsonl_file)
        if cwd:
            return cwd
    return None

def main():
    claude_dir = Path(os.path.expanduser('~/.claude'))
    history_dir = claude_dir / 'claude-history'
    projects_dir = claude_dir / 'projects'
    history_file = claude_dir / 'history.jsonl'
    names_file = history_dir / 'session-names.json'

    if not projects_dir.exists():
        print("Error: Projects directory not found")
        return

    # Load custom session names
    session_names = {}
    if names_file.exists():
        try:
            with open(names_file, 'r', encoding='utf-8') as f:
                session_names = json.load(f)
        except:
            pass

    sessions = []
    history_entries = []

    # ===== 1. Scan session files =====
    print("Scanning sessions...")

    for project_folder in projects_dir.iterdir():
        if project_folder.is_dir() and not project_folder.name.startswith('.'):
            folder_name = project_folder.name

            # Use cwd from session files (Claude Code's projectPath).
            # If folders were reorganized, migrate the sessions on disk (see
            # ~/.claude/migrate-claude-project-paths.py) instead of mapping here.
            folder_cwd = get_folder_cwd(project_folder)

            if folder_cwd:
                project_name = unicodedata.normalize('NFC', folder_cwd).lstrip('/')
            else:
                clean_folder = folder_name[1:] if folder_name.startswith('-') else folder_name
                project_name = clean_folder.replace('-', '/')

            for jsonl_file in project_folder.glob('*.jsonl'):
                if jsonl_file.name.startswith('agent-'):
                    continue

                session_id = jsonl_file.stem
                file_size = jsonl_file.stat().st_size
                modified_time = jsonl_file.stat().st_mtime

                # Read session content for metadata
                try:
                    with open(jsonl_file, 'r', encoding='utf-8') as f:
                        lines = f.readlines()

                    first_user_msg = None
                    first_timestamp = None
                    last_timestamp = None
                    message_count = 0
                    all_user_texts = []  # Collect all user messages for search

                    for line in lines:
                        try:
                            data = json.loads(line.strip())
                            if data.get('type') == 'user' and data.get('message', {}).get('role') == 'user':
                                message_count += 1
                                content = data.get('message', {}).get('content', '')

                                # Extract text content
                                text_content = ''
                                if isinstance(content, str):
                                    text_content = content
                                elif isinstance(content, list):
                                    for c in content:
                                        if isinstance(c, dict) and c.get('type') == 'text':
                                            text_content = c.get('text', '')
                                            break

                                # Skip meta messages for preview
                                if text_content and not text_content.startswith('Caveat:') and not text_content.startswith('<command-'):
                                    if not first_user_msg:
                                        first_user_msg = text_content[:200]
                                    # Add to searchable content (limit each message to 500 chars)
                                    all_user_texts.append(text_content[:500])

                            if data.get('timestamp'):
                                ts = data.get('timestamp')
                                if not first_timestamp:
                                    first_timestamp = ts
                                last_timestamp = ts
                        except:
                            continue

                    # Create searchable content (limit total to 5000 chars)
                    searchable_content = ' '.join(all_user_texts)[:5000]

                    # Skip sessions with 0 messages
                    if message_count > 0:
                        session_data = {
                            'sessionId': session_id,
                            'project': project_name,
                            'projectFolder': folder_name,
                            'fileName': jsonl_file.name,
                            'fileSize': file_size,
                            'modifiedTime': modified_time,
                            'firstTimestamp': first_timestamp,
                            'lastTimestamp': last_timestamp,
                            'messageCount': message_count,
                            'preview': first_user_msg or 'No preview available',
                            'searchableContent': searchable_content,
                            'type': 'session'
                        }
                        # Add custom name if exists
                        if session_id in session_names:
                            session_data['customName'] = session_names[session_id]
                        sessions.append(session_data)
                except Exception as e:
                    print(f"  Warning: Error reading {jsonl_file.name}: {e}")

    print(f"  Found {len(sessions)} sessions")

    # ===== 2. Load history.jsonl for matching =====
    print("Loading history.jsonl...")

    if history_file.exists():
        try:
            with open(history_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        entry = json.loads(line.strip())
                        history_entries.append(entry)
                    except:
                        continue
            print(f"  Found {len(history_entries)} history entries")
        except Exception as e:
            print(f"  Warning: Error reading history.jsonl: {e}")

    # ===== 3. Check for orphaned history entries =====
    print("Checking for orphaned history entries...")

    # Get all unique project paths from sessions
    session_projects = set()
    for s in sessions:
        # Normalize for comparison
        proj = s['project'].lower().replace('/', '-').replace('_', '-').replace(' ', '-')
        while '--' in proj:
            proj = proj.replace('--', '-')
        session_projects.add(proj.strip('-'))

    skipped_commands = 0
    matched_count = 0
    unmatched_entries = []

    skip_commands = {'/status', '/login', '/logout', '/model', '/mcp', '/plugin',
                    '/context', '/compact', '/tasks', '/usage', '/help', '/clear',
                    '/resume', '/mco', '/cost', '/config', '/doctor', '/bug',
                    '/smart-handoff', '/init', '/version', '/memory'}

    for entry in history_entries:
        project = entry.get('project', '').lstrip('/')
        timestamp = entry.get('timestamp', 0)
        display = entry.get('display', '')

        # Skip slash commands
        if display.startswith('/') and not display.startswith('/Users'):
            cmd = display.split()[0] if display else ''
            if cmd in skip_commands:
                skipped_commands += 1
                continue

        # Normalize history project for comparison
        norm_project = project.lower().replace('/', '-').replace('_', '-').replace(' ', '-')
        while '--' in norm_project:
            norm_project = norm_project.replace('--', '-')
        norm_project = norm_project.strip('-')

        # Check if this project has any sessions
        if norm_project in session_projects:
            matched_count += 1
            continue

        # Check partial match
        matched = False
        for sp in session_projects:
            if norm_project in sp or sp in norm_project:
                matched = True
                matched_count += 1
                break

        if not matched:
            try:
                ts_iso = datetime.fromtimestamp(timestamp / 1000).isoformat()
            except:
                ts_iso = None

            unmatched_entries.append({
                'historyId': f"history-{timestamp}",
                'project': project if project else 'Unknown',
                'timestamp': timestamp,
                'timestampISO': ts_iso,
                'display': display,
                'preview': display[:200] if display else 'No preview',
                'pastedContents': entry.get('pastedContents', {}),
                'type': 'history'
            })

    print(f"  Skipped commands: {skipped_commands}")
    print(f"  Matched to sessions: {matched_count}")
    print(f"  Orphaned: {len(unmatched_entries)}")

    # ===== 4. Combine and sort =====
    all_items = sessions + unmatched_entries

    def get_sort_key(item):
        if item['type'] == 'session':
            # Use lastTimestamp (actual conversation time), fallback to modifiedTime
            if item.get('lastTimestamp'):
                from datetime import datetime
                try:
                    dt = datetime.fromisoformat(item['lastTimestamp'].replace('Z', '+00:00'))
                    return dt.timestamp() * 1000
                except:
                    pass
            return item.get('modifiedTime', 0) * 1000
        else:
            return item.get('timestamp', 0)

    all_items.sort(key=get_sort_key, reverse=True)

    # ===== 5. Save index =====
    index_path = history_dir / 'sessions-index.json'
    with open(index_path, 'w', encoding='utf-8') as f:
        json.dump({
            'generatedAt': datetime.now().isoformat(),
            'totalSessions': len(sessions),
            'totalHistoryEntries': len(history_entries),
            'unmatchedHistoryEntries': len(unmatched_entries),
            'items': all_items
        }, f, ensure_ascii=False, indent=2)

    print(f"\nDone!")
    print(f"  Sessions: {len(sessions)}")
    print(f"  Orphaned history: {len(unmatched_entries)}")
    print(f"  Total items: {len(all_items)}")
    print(f"Index saved to: {index_path}")

    # Show unique projects
    projects = set(s['project'] for s in sessions)
    print(f"\nUnique projects: {len(projects)}")

if __name__ == '__main__':
    main()
