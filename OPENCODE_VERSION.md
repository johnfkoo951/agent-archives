# Agent Archives - OpenCode/oh-my-opencode Version

This document outlines the key paths and structure needed to create an OpenCode version of Agent Archives.

## Data Location Comparison

| Feature | Claude Code | OpenCode |
|---------|-------------|----------|
| **Base Path** | `~/.claude/` | `~/.local/share/opencode/` |
| **Sessions Index** | `sessions-index.json` | N/A (scan session files) |
| **Session Data** | JSONL in `projects/{path}/*.jsonl` | JSON in `storage/session/global/*.json` |
| **Messages** | Within JSONL files | `storage/message/{session_id}/*.json` |
| **Message Parts** | Within JSONL | `storage/part/msg_*.json` |
| **Projects** | `projects/` | `storage/project/` |
| **Logs** | N/A | `log/*.log` |
| **Snapshots** | N/A | `snapshot/global/` |
| **Auth** | N/A | `auth.json` |

## OpenCode Directory Structure

```
~/.local/share/opencode/
├── auth.json                     # API authentication data
├── bin/                          # Binary files
├── log/                          # Application logs (YYYY-MM-DDTHHMMSS.log)
├── snapshot/
│   └── global/                   # Git-based session snapshots
└── storage/
    ├── agent-usage-reminder/     # Agent usage data
    ├── directory-agents/         # Agent directory
    ├── directory-readme/         # README directory
    ├── message/                   # Messages per session
    │   └── ses_{id}/             # Session folder
    │       └── msg_{id}.json     # Message files
    ├── migration                  # Migration status
    ├── part/                      # Message parts
    │   └── msg_{id}.json         # Part files
    ├── project/                   # Project data
    ├── session/
    │   └── global/               # Session files
    │       └── ses_{id}.json     # Session metadata
    ├── session_diff/             # Session diffs
    └── todo/                     # Todo data
```

## Session JSON Format

```json
{
    "id": "ses_461590a6affe1zncv5rF2OnjYO",
    "version": "1.1.6",
    "projectID": "global",
    "directory": "/Users/yohankoo/some/path",
    "parentID": "ses_464b0909affe0NxThIYrbXiJTo",
    "title": "Session title from first message",
    "time": {
        "created": 1767893300629,  // Unix timestamp (ms)
        "updated": 1767893307135
    },
    "permission": [...]
}
```

## Message JSON Format

```json
{
    "id": "msg_b9ea6f597001AwsshImNI1XgUc",
    "sessionID": "ses_461590a6affe1zncv5rF2OnjYO",
    "role": "user",
    "time": {
        "created": 1767893300631
    },
    "summary": {
        "title": "Message summary",
        "diffs": []
    },
    "agent": "multimodal-looker",
    "model": {
        "providerID": "google",
        "modelID": "antigravity-gemini-3-flash"
    },
    "tools": {...}
}
```

## Key Implementation Differences

### 1. Session Discovery
**Claude Code**: Read `sessions-index.json` or scan JSONL files
**OpenCode**: Scan `storage/session/global/*.json` files

### 2. Session ID Format
**Claude Code**: UUID format (`c4e87862-20e7-40ee-a7b9-6f429af113f9`)
**OpenCode**: Custom format with prefix (`ses_461590a6affe1zncv5rF2OnjYO`)

### 3. Message Retrieval
**Claude Code**: Parse JSONL file line by line
**OpenCode**: Read individual JSON files from `storage/message/{session_id}/`

### 4. Project Path
**Claude Code**: Derived from `projects/` folder structure
**OpenCode**: `directory` field in session JSON

### 5. Resume Command
**Claude Code**: `claude --resume {session_id}`
**OpenCode**: `opencode --resume {session_id}` (verify command)

## Server Endpoint Changes

The history-server.py needs these modifications:

```python
# OpenCode paths
OPENCODE_DIR = Path.home() / ".local" / "share" / "opencode"
STORAGE_DIR = OPENCODE_DIR / "storage"
SESSION_DIR = STORAGE_DIR / "session" / "global"
MESSAGE_DIR = STORAGE_DIR / "message"

# Session loading
def load_opencode_sessions():
    sessions = []
    for session_file in SESSION_DIR.glob("ses_*.json"):
        with open(session_file) as f:
            session = json.load(f)
            sessions.append({
                "sessionId": session["id"],
                "project": session.get("directory", ""),
                "title": session.get("title", ""),
                "lastActivity": session["time"]["updated"],
                "messageCount": count_messages(session["id"])
            })
    return sessions

def count_messages(session_id):
    msg_dir = MESSAGE_DIR / session_id
    if msg_dir.exists():
        return len(list(msg_dir.glob("msg_*.json")))
    return 0

def get_session_messages(session_id):
    messages = []
    msg_dir = MESSAGE_DIR / session_id
    if msg_dir.exists():
        for msg_file in sorted(msg_dir.glob("msg_*.json")):
            with open(msg_file) as f:
                messages.append(json.load(f))
    return messages
```

## UI Changes

1. **App Title**: "OpenCode" instead of "Claude Code"
2. **Resume Command**: Use `opencode` command
3. **Session ID Display**: Show `ses_` prefix format
4. **Model Info**: Display OpenCode model names (e.g., `antigravity-gemini-3-flash`)

## OpenCode vs oh-my-opencode

- **OpenCode**: Base terminal AI coding agent
- **oh-my-opencode**: Shell framework extension (like Oh My Zsh)
  - Same data paths (`~/.local/share/opencode/`)
  - May add `~/.oh-my-opencode/` for plugins/themes
  - Enhanced shell integration and customization

## Useful Commands

```bash
# Check OpenCode data size
du -sh ~/.local/share/opencode/

# List sessions
ls -la ~/.local/share/opencode/storage/session/global/

# View recent logs
tail -f ~/.local/share/opencode/log/*.log

# Clean snapshots (when not running)
rm -rf ~/.local/share/opencode/snapshot/

# Count total messages
ls -la ~/.local/share/opencode/storage/part/ | wc -l
```

## Next Steps

1. Create `opencode-history-server.py` based on `history-server.py`
2. Create `opencode-history-viewer.html` with UI changes
3. Update Electron app to support both Claude Code and OpenCode modes
4. Or create separate app "Agent Archives - OpenCode Edition"
