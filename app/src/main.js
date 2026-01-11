const { app, BrowserWindow, shell, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow;
let serverProcess;
let pendingDeepLink = null; // Store deep link URL if app wasn't ready
const SERVER_PORT = 8080;
const SERVER_HOST = '127.0.0.1';
const PROTOCOL = 'agentarchives';

// Claude directory paths
const CLAUDE_DIR = path.join(require('os').homedir(), '.claude');
const HISTORY_DIR = path.join(CLAUDE_DIR, 'claude-history');

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    titleBarStyle: 'default',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    backgroundColor: '#0f172a',
    show: false
  });

  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  mainWindow.webContents.once('did-finish-load', () => {
    if (pendingDeepLink) {
      mainWindow.webContents.send('deep-link', pendingDeepLink);
      pendingDeepLink = null;
    }
  });

  // Open external links in browser
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // Load the viewer
  mainWindow.loadURL(`http://${SERVER_HOST}:${SERVER_PORT}/history-viewer.html`);

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function waitForServer(retries = 30, delay = 500) {
  return new Promise((resolve, reject) => {
    const check = (remaining) => {
      const req = http.get(`http://${SERVER_HOST}:${SERVER_PORT}/sessions-index.json`, (res) => {
        if (res.statusCode === 200) {
          resolve();
        } else if (remaining > 0) {
          setTimeout(() => check(remaining - 1), delay);
        } else {
          reject(new Error('Server not responding'));
        }
      });

      req.on('error', () => {
        if (remaining > 0) {
          setTimeout(() => check(remaining - 1), delay);
        } else {
          reject(new Error('Server connection failed'));
        }
      });

      req.end();
    };

    check(retries);
  });
}

function findPython() {
  const { execSync } = require('child_process');
  const fs = require('fs');
  
  const macOSPaths = [
    '/usr/bin/python3',
    '/opt/homebrew/bin/python3',
    '/usr/local/bin/python3',
  ];
  
  for (const p of macOSPaths) {
    if (fs.existsSync(p)) return p;
  }
  
  try {
    const result = execSync('which python3', { encoding: 'utf8' }).trim();
    if (result && fs.existsSync(result)) return result;
  } catch (e) {}
  
  return 'python3';
}

const PYTHON_PATH = findPython();

function startServer() {
  return new Promise((resolve, reject) => {
    const serverScript = path.join(HISTORY_DIR, 'history-server.py');
    const updateScript = path.join(HISTORY_DIR, 'update-index.py');

    console.log(`HISTORY_DIR: ${HISTORY_DIR}`);
    console.log(`Server script: ${serverScript}`);
    console.log(`Python: ${PYTHON_PATH}`);

    const spawnOpts = { cwd: HISTORY_DIR, env: process.env };

    console.log('Updating index...');
    const updateProcess = spawn(PYTHON_PATH, [updateScript], spawnOpts);

    updateProcess.on('close', (code) => {
      console.log(`Index update finished with code ${code}`);

      serverProcess = spawn(PYTHON_PATH, [
        serverScript,
        '--host', SERVER_HOST,
        '--port', String(SERVER_PORT),
        '--skip-index'
      ], spawnOpts);

      serverProcess.stdout.on('data', (data) => {
        console.log(`Server: ${data}`);
      });

      serverProcess.stderr.on('data', (data) => {
        console.error(`Server Error: ${data}`);
      });

      serverProcess.on('error', (err) => {
        console.error('Failed to start server:', err);
        reject(err);
      });

      serverProcess.on('close', (code) => {
        console.log(`Server exited with code ${code}`);
        serverProcess = null;
      });

      // Wait for server to be ready
      waitForServer()
        .then(resolve)
        .catch(reject);
    });
  });
}

function stopServer() {
  if (serverProcess) {
    console.log('Stopping server...');
    serverProcess.kill('SIGTERM');
    serverProcess = null;
  }
}

// Register as default protocol handler (for development)
if (process.defaultApp) {
  if (process.argv.length >= 2) {
    app.setAsDefaultProtocolClient(PROTOCOL, process.execPath, [path.resolve(process.argv[1])]);
  }
} else {
  app.setAsDefaultProtocolClient(PROTOCOL);
}

function parseDeepLink(url) {
  if (!url || !url.startsWith(`${PROTOCOL}://`)) return null;
  
  const urlPath = url.replace(`${PROTOCOL}://`, '');
  const [action, ...params] = urlPath.split('/');
  
  if (action === 'session' && params.length > 0) {
    const sessionId = params[0].split('?')[0];
    return { action: 'open-session', sessionId };
  }
  return null;
}

function handleDeepLink(url) {
  const parsed = parseDeepLink(url);
  if (!parsed) return;
  
  if (mainWindow && mainWindow.webContents) {
    mainWindow.webContents.send('deep-link', parsed);
    mainWindow.focus();
  } else {
    pendingDeepLink = parsed;
  }
}

// macOS: Handle protocol URL when app is already running
app.on('open-url', (event, url) => {
  event.preventDefault();
  handleDeepLink(url);
});

// Windows/Linux: Handle protocol URL from command line args
const gotTheLock = app.requestSingleInstanceLock();
if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', (event, commandLine) => {
    const url = commandLine.find(arg => arg.startsWith(`${PROTOCOL}://`));
    if (url) handleDeepLink(url);
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
  });
}

// App lifecycle
app.whenReady().then(async () => {
  try {
    console.log('Starting Claude History Viewer...');
    await startServer();
    console.log('Server started successfully');
    createWindow();
  } catch (err) {
    console.error('Failed to start:', err);
    dialog.showErrorBox(
      'Server Error',
      `Failed to start the history server.\n\nPlease ensure:\n1. Python 3 is installed\n2. Required packages are installed (fastapi, uvicorn)\n3. history-server.py exists in ~/.claude/claude-history/\n\nError: ${err.message}`
    );
    app.quit();
  }
});

app.on('window-all-closed', () => {
  stopServer();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

app.on('before-quit', () => {
  stopServer();
});

// IPC handlers
ipcMain.handle('get-claude-dir', () => CLAUDE_DIR);
ipcMain.handle('get-history-dir', () => HISTORY_DIR);

ipcMain.handle('open-in-terminal', async (event, projectPath) => {
  const { exec } = require('child_process');
  const fullPath = path.join(CLAUDE_DIR, 'projects', projectPath);

  // macOS: Open in Terminal
  exec(`open -a Terminal "${fullPath}"`, (err) => {
    if (err) {
      console.error('Failed to open terminal:', err);
    }
  });
});

ipcMain.handle('reveal-in-finder', async (event, projectPath) => {
  const fullPath = path.join(CLAUDE_DIR, 'projects', projectPath);
  shell.showItemInFolder(fullPath);
});
