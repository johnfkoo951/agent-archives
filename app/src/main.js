const { app, BrowserWindow, shell, ipcMain, dialog } = require('electron');
const path = require('path');
const { spawn } = require('child_process');
const http = require('http');

let mainWindow;
let serverProcess;
const SERVER_PORT = 8080;
const SERVER_HOST = '127.0.0.1';

// Claude directory paths
const CLAUDE_DIR = path.join(require('os').homedir(), '.claude');
const HISTORY_DIR = path.join(CLAUDE_DIR, 'claude-history');

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    titleBarStyle: 'hiddenInset',
    trafficLightPosition: { x: 15, y: 15 },
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js')
    },
    backgroundColor: '#0f172a',
    show: false
  });

  // Show window when ready
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
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

function startServer() {
  return new Promise((resolve, reject) => {
    const serverScript = path.join(HISTORY_DIR, 'history-server.py');

    // Try different Python paths
    const pythonPaths = [
      '/usr/bin/python3',
      '/opt/homebrew/bin/python3',
      'python3',
      'python'
    ];

    let pythonPath = pythonPaths[0];

    console.log(`Starting server: ${pythonPath} ${serverScript}`);

    serverProcess = spawn(pythonPath, [
      serverScript,
      '--host', SERVER_HOST,
      '--port', String(SERVER_PORT),
      '--skip-index'
    ], {
      cwd: HISTORY_DIR,
      env: { ...process.env }
    });

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
}

function stopServer() {
  if (serverProcess) {
    console.log('Stopping server...');
    serverProcess.kill('SIGTERM');
    serverProcess = null;
  }
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
