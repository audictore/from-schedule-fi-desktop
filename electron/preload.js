const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  solve: (datos) => ipcRenderer.invoke('solve', datos),
  cancelSolve: () => ipcRenderer.invoke('cancel-solve'),
  onProgress: (callback) => {
    ipcRenderer.on('solve-progress', (_, data) => callback(data));
  },
  dialogOpen: (options) => ipcRenderer.invoke('dialog-open', options),
  dialogSave: (options) => ipcRenderer.invoke('dialog-save', options),
  onMenuOpen: (callback) => ipcRenderer.on('menu-open', callback),
  onMenuSave: (callback) => ipcRenderer.on('menu-save', callback)
});
