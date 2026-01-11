const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods to the renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  getClaudeDir: () => ipcRenderer.invoke('get-claude-dir'),
  getHistoryDir: () => ipcRenderer.invoke('get-history-dir'),
  openInTerminal: (projectPath) => ipcRenderer.invoke('open-in-terminal', projectPath),
  revealInFinder: (projectPath) => ipcRenderer.invoke('reveal-in-finder', projectPath),
  platform: process.platform,
  isElectron: true,
  
  onDeepLink: (callback) => {
    ipcRenderer.on('deep-link', (event, data) => callback(data));
  }
});

// Log when preload is ready
console.log('Preload script loaded - Electron API available');
