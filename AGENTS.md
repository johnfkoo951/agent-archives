# AGENTS.md - Agent Archives (Claude History Viewer)

Desktop app for browsing Claude Code session history.

## Tech Stack

| Component | File | Tech |
|-----------|------|------|
| Backend | `history-server.py` | Python 3, FastAPI, Pydantic |
| Frontend | `history-viewer.html` | Vue.js (CDN), Tailwind CSS |
| Desktop | `app/src/main.js` | Electron 28 |
| IPC | `app/src/preload.js` | contextBridge |
| Indexer | `update-index.py` | Python stdlib |

## Commands

```bash
# Development
./dev.sh server        # Start dev server → http://127.0.0.1:8080
./dev.sh app           # Start Electron app
./dev.sh index         # Update session index
./dev.sh install       # pip3 + npm install

# Build
cd app && npm run build      # macOS .dmg
cd app && npm run build:all  # All platforms
```

### No Automated Tests

Manual verification:
1. `./dev.sh server` → open browser
2. Verify session list, tags, search, rename all work

---

## Code Style

### Python (FastAPI)

**Type hints required**:
```python
from typing import List, Optional
from pydantic import BaseModel

class MyRequest(BaseModel):
    session_id: str
    tags: Optional[List[str]] = None

@app.post("/api/endpoint")
async def my_endpoint(request: MyRequest) -> MyResponse:
    ...
```

**Path handling**: Use `pathlib.Path`, not `os.path`:
```python
from pathlib import Path
CLAUDE_DIR = Path.home() / '.claude'
```

**JSON I/O pattern**:
```python
def load_data() -> dict:
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data: dict):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)  # Korean text support
```

**Error handling**: Use HTTPException with detail:
```python
if not file_path.exists():
    raise HTTPException(status_code=404, detail=f"File not found: {path}")
```

### JavaScript (Electron)

**Module system**: CommonJS
```javascript
const { app, BrowserWindow, ipcMain } = require('electron');
const path = require('path');
```

**IPC pattern**:
```javascript
// main.js
ipcMain.handle('my-action', async (event, arg) => result);

// preload.js
contextBridge.exposeInMainWorld('electronAPI', {
    myAction: (arg) => ipcRenderer.invoke('my-action', arg)
});
```

**Async lifecycle**:
```javascript
app.whenReady().then(async () => {
    try {
        await startServer();
        createWindow();
    } catch (err) {
        dialog.showErrorBox('Error', err.message);
        app.quit();
    }
});
```

### HTML/Vue.js

- Single-file architecture (all in `history-viewer.html`)
- CSS variables for theming: `[data-theme="dark"]` support
- Tailwind utility classes

---

## API Conventions

```python
# GET for reads
@app.get("/api/resource")
@app.get("/api/resource/{id}")

# POST for mutations
@app.post("/api/resource/add")
@app.post("/api/resource/remove")
```

---

## Architecture Rules

```
claude-history/
├── history-server.py      # DO NOT SPLIT
├── history-viewer.html    # DO NOT SPLIT
├── update-index.py        # Indexer script
├── dev.sh                 # Dev helper
├── app/
│   ├── src/main.js        # Electron main
│   ├── src/preload.js     # IPC bridge
│   └── package.json
└── *.json                 # Data (gitignored)
```

**Single-file architecture is intentional. Do NOT refactor into modules.**

---

## Common Pitfalls

1. **Unicode paths** (macOS): Always normalize
   ```python
   import unicodedata
   path = unicodedata.normalize('NFC', path_string)
   ```

2. **Port 8080 in use**: Check `lsof -i :8080`

3. **Python in Electron**: Use `/usr/bin/python3` for macOS compatibility

4. **JSON Korean text**: Always `ensure_ascii=False`

5. **Path traversal security**: Validate paths before file operations
   ```python
   if '..' in request.path:
       raise HTTPException(status_code=400, detail="Invalid path")
   ```

---

## Git Conventions

```bash
# Commit format
git commit -m "feat: add new feature"
git commit -m "fix: resolve specific bug"
git commit -m "refactor: improve structure"

# Release
git tag v1.0.x
cd app && npm run build
```

---

## Dependencies

**Python**: `pip3 install fastapi uvicorn pydantic`

**Node.js**: electron ^28.0.0, electron-builder ^24.9.1
