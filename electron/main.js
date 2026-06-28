const { app, BrowserWindow, ipcMain, dialog, Menu } = require('electron');
const path = require('path');
const fs = require('fs');
const { solveCPSAT, cancelSolve } = require('./solver');

let mainWindow;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    minWidth: 800,
    minHeight: 600,
    title: 'From Schedule FI',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false
    }
  });

  mainWindow.loadFile(path.join(__dirname, '..', 'app', 'index.html'));

  const menu = Menu.buildFromTemplate([
    {
      label: 'Archivo',
      submenu: [
        {
          label: 'Abrir proyecto...',
          accelerator: 'CmdOrCtrl+O',
          click: () => mainWindow.webContents.send('menu-open')
        },
        {
          label: 'Guardar proyecto',
          accelerator: 'CmdOrCtrl+S',
          click: () => mainWindow.webContents.send('menu-save')
        },
        { type: 'separator' },
        { role: 'quit', label: 'Salir' }
      ]
    },
    {
      label: 'Ver',
      submenu: [
        { role: 'reload', label: 'Recargar' },
        { role: 'toggleDevTools', label: 'Herramientas de desarrollo' },
        { type: 'separator' },
        { role: 'zoomIn', label: 'Acercar' },
        { role: 'zoomOut', label: 'Alejar' },
        { role: 'resetZoom', label: 'Zoom original' }
      ]
    },
    {
      label: 'Ayuda',
      submenu: [
        {
          label: 'Acerca de From Schedule FI',
          click: () => {
            dialog.showMessageBox(mainWindow, {
              type: 'info',
              title: 'From Schedule FI',
              message: 'From Schedule FI v1.0.0',
              detail: 'Generador de horarios universitarios\nMotor: CP-SAT (OR-Tools)\n\n© From Industries'
            });
          }
        }
      ]
    }
  ]);
  Menu.setApplicationMenu(menu);
}

app.whenReady().then(createWindow);

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit();
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) createWindow();
});

ipcMain.handle('solve', async (event, datos) => {
  return solveCPSAT(datos, (progress) => {
    mainWindow.webContents.send('solve-progress', progress);
  });
});

ipcMain.handle('cancel-solve', () => {
  cancelSolve();
});

ipcMain.handle('dialog-open', async (event, options) => {
  return dialog.showOpenDialog(mainWindow, options);
});

ipcMain.handle('dialog-save', async (event, options) => {
  return dialog.showSaveDialog(mainWindow, options);
});

ipcMain.handle('file-write', async (event, filePath, content) => {
  try {
    await fs.promises.writeFile(filePath, content, 'utf8');
    return { ok: true };
  } catch (err) {
    return { ok: false, error: err.message };
  }
});

ipcMain.handle('file-read', async (event, filePath) => {
  try {
    const content = await fs.promises.readFile(filePath, 'utf8');
    return { ok: true, content };
  } catch (err) {
    return { ok: false, error: err.message };
  }
});
