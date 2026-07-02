const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('electronAPI', {
  solve: (datos) => ipcRenderer.invoke('solve', datos),
  cancelSolve: () => ipcRenderer.invoke('cancel-solve'),
  onProgress: (callback) => {
    ipcRenderer.on('solve-progress', (_, data) => callback(data));
  },
  dialogOpen: (options) => ipcRenderer.invoke('dialog-open', options),
  dialogSave: (options) => ipcRenderer.invoke('dialog-save', options),
  fileWrite: (filePath, content) => ipcRenderer.invoke('file-write', filePath, content),
  fileRead: (filePath) => ipcRenderer.invoke('file-read', filePath),
  onMenuOpen: (callback) => ipcRenderer.on('menu-open', callback),
  onMenuSave: (callback) => ipcRenderer.on('menu-save', callback),
  onShowLicense: (callback) => ipcRenderer.on('show-license', callback),
  license: {
    getStatus: () => ipcRenderer.invoke('license-status'),
    activate: (key) => ipcRenderer.invoke('license-activate', key),
    deactivate: () => ipcRenderer.invoke('license-deactivate')
  },
  institutional: {
    getConfig: () => ipcRenderer.invoke('institutional:getConfig'),
    setConfig: (data) => ipcRenderer.invoke('institutional:setConfig', data),
    publish: (data) => ipcRenderer.invoke('institutional:publish', data)
  }
});
