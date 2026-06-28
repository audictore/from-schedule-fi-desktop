const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

let solverProcess = null;

function getSolverPath() {
  const isPackaged = process.resourcesPath !== undefined
    && !process.resourcesPath.includes('node_modules');

  if (isPackaged) {
    const ext = process.platform === 'win32' ? '.exe' : '';
    return path.join(process.resourcesPath, 'solver', `solver_ipc${ext}`);
  }
  return path.join(__dirname, '..', 'solver', 'solver_ipc.py');
}

function solveCPSAT(datos, onProgress) {
  return new Promise((resolve, reject) => {
    const solverPath = getSolverPath();
    const isPython = solverPath.endsWith('.py');

    let cmd, args;
    if (isPython) {
      if (process.platform === 'win32') {
        const wslPath = solverPath.replace(/\\/g, '/').replace(/^([A-Z]):/i, (_, d) => `/mnt/${d.toLowerCase()}`);
        cmd = 'wsl';
        args = ['python3', wslPath];
      } else {
        cmd = 'python3';
        args = [solverPath];
      }
    } else {
      cmd = solverPath;
      args = [];
    }

    if (!isPython && !fs.existsSync(solverPath)) {
      return reject(new Error(`Solver no encontrado: ${solverPath}`));
    }

    solverProcess = spawn(cmd, args, {
      stdio: ['pipe', 'pipe', 'pipe'],
      windowsHide: true
    });

    let stdout = '';
    let stderr = '';

    solverProcess.stdout.on('data', (chunk) => {
      stdout += chunk.toString();
      const lines = stdout.split('\n');
      stdout = lines.pop();
      for (const line of lines) {
        if (!line.trim()) continue;
        try {
          const msg = JSON.parse(line);
          if (msg.type === 'progress' && onProgress) {
            onProgress(msg);
          } else if (msg.type === 'result') {
            resolve(msg.data);
          }
        } catch {}
      }
    });

    solverProcess.stderr.on('data', (chunk) => {
      stderr += chunk.toString();
      console.log('[solver stderr]', chunk.toString().trim());
    });

    solverProcess.on('close', (code) => {
      solverProcess = null;
      if (stdout.trim()) {
        try {
          const msg = JSON.parse(stdout.trim());
          if (msg.type === 'result') return resolve(msg.data);
        } catch {}
      }
      if (code !== 0) {
        reject(new Error(`Solver terminó con código ${code}: ${stderr.slice(0, 500)}`));
      }
    });

    solverProcess.on('error', (err) => {
      solverProcess = null;
      reject(new Error(`No se pudo iniciar el solver: ${err.message}`));
    });

    solverProcess.stdin.write(JSON.stringify(datos) + '\n');
    solverProcess.stdin.end();
  });
}

function cancelSolve() {
  if (solverProcess) {
    solverProcess.kill('SIGTERM');
    solverProcess = null;
  }
}

module.exports = { solveCPSAT, cancelSolve };
