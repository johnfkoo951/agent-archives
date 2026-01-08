const { contextBridge, ipcRenderer } = require('electron');

// Expose protected methods to the renderer process
contextBridge.exposeInMainWorld('electronAPI', {
  // Get paths
  getClaudeDir: () => ipcRenderer.invoke('get-claude-dir'),
  getHistoryDir: () => ipcRenderer.invoke('get-history-dir'),

  // Open project in terminal
  openInTerminal: (projectPath) => ipcRenderer.invoke('open-in-terminal', projectPath),

  // Reveal in Finder
  revealInFinder: (projectPath) => ipcRenderer.invoke('reveal-in-finder', projectPath),

  // Platform info
  platform: process.platform,

  // Check if running in Electron
  isElectron: true
});

// Log when preload is ready
console.log('Preload script loaded - Electron API available');
