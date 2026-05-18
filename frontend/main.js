// const { app, BrowserWindow } = require('electron');
// const path = require('path');

// function createWindow() {
//   const win = new BrowserWindow({
//     width: 1000,
//     height: 800,
//     webPreferences: {
//       preload: path.join(__dirname, 'preload.js')
//     }
//   });

//   win.loadFile('index.html');
// }

// app.whenReady().then(createWindow);



// //// After JSON//////

// const { app, BrowserWindow } = require('electron');
// const path = require('path');

// function createWindow() {
//   const win = new BrowserWindow({
//     width: 1200,
//     height: 800,
//     webPreferences: {
//       preload: path.join(__dirname, "renderer.js"),
//       nodeIntegration: true,
//       contextIsolation: false,
//     }
//   });

//   win.loadFile("index.html");
// }

// app.whenReady().then(createWindow);

const { app, BrowserWindow, ipcMain } = require('electron');
const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const isDev = require('electron-is-dev');

let backendProcess = null;

const BACKEND_BASE_URLS = ['http://127.0.0.1:5000', 'http://127.0.0.1:5001'];

function delay(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function getBackendDir() {
  if (app.isPackaged) {
    return path.join(process.resourcesPath, 'backend');
  }

  return path.join(__dirname, '..', 'backend');
}

function getPythonCommandCandidates() {
  const bundledPythonCandidates = process.platform === 'win32'
    ? [
        path.join(getBackendDir(), 'venv', 'Scripts', 'python.exe'),
        path.join(getBackendDir(), 'venv', 'Scripts', 'python')
      ]
    : [
        path.join(getBackendDir(), 'venv', 'bin', 'python'),
        path.join(getBackendDir(), 'venv', 'bin', 'python3')
      ];

  const availableBundledCandidates = bundledPythonCandidates
    .filter((candidatePath) => fs.existsSync(candidatePath))
    .map((candidatePath) => ({ command: candidatePath, args: [] }));

  if (process.platform === 'win32') {
    return [
      ...availableBundledCandidates,
      { command: 'py', args: ['-3'] },
      { command: 'python', args: [] },
      { command: 'python3', args: [] }
    ];
  }

  return [
    ...availableBundledCandidates,
    { command: 'python3', args: [] },
    { command: 'python', args: [] }
  ];
}

async function getHealthyBackendBaseUrl() {
  for (const baseUrl of BACKEND_BASE_URLS) {
    try {
      const response = await fetch(`${baseUrl}/api/health`);
      if (response.ok) {
        return baseUrl;
      }
    } catch (error) {
      // try next candidate
    }
  }

  return null;
}

function getPreferredBackendPort() {
  return process.env.NTM_BACKEND_PORT || '5001';
}

function startBackend() {
  if (backendProcess && !backendProcess.killed) {
    return Promise.resolve({ started: true, reused: true });
  }

  const backendDir = getBackendDir();
  const backendScript = path.join(backendDir, 'app2.py');

  return new Promise((resolve, reject) => {
    getHealthyBackendBaseUrl().then((healthyBaseUrl) => {
      if (healthyBaseUrl) {
        resolve({ started: true, reused: true, baseUrl: healthyBaseUrl });
        return;
      }

    const candidates = getPythonCommandCandidates();
    let lastError = null;

    const tryNextCandidate = () => {
      const candidate = candidates.shift();
      if (!candidate) {
        reject(lastError || new Error('No Python interpreter found'));
        return;
      }

      const child = spawn(candidate.command, [...candidate.args, backendScript], {
        cwd: backendDir,
        env: {
          ...process.env,
          FLASK_HOST: '127.0.0.1',
          FLASK_PORT: getPreferredBackendPort(),
          FLASK_DEBUG: 'False',
          NTM_CAPTURE_CONSENT: '1'
        },
        shell: false,
        stdio: ['ignore', 'pipe', 'pipe']
      });

      let launchTimer = null;
      let stderrBuffer = '';
      let readyCheckActive = true;

      const cleanup = () => {
        if (launchTimer) {
          clearTimeout(launchTimer);
        }
        readyCheckActive = false;
      };

      const waitForReady = async () => {
        const backendPort = process.env.NTM_BACKEND_PORT || '5001';
        const healthUrl = `http://127.0.0.1:${backendPort}/api/health`;
        const timeoutAt = Date.now() + 15000;

        while (readyCheckActive && Date.now() < timeoutAt) {
          if (child.exitCode !== null || child.killed) {
            break;
          }

          try {
            const response = await fetch(healthUrl);
            if (response.ok) {
              backendProcess = child;
              cleanup();
              resolve({ started: true, command: candidate.command, ready: true });
              return;
            }
          } catch (error) {
            // keep polling until the backend is up
          }

          await delay(400);
        }

        if (readyCheckActive) {
          cleanup();
          lastError = new Error(stderrBuffer || 'Backend did not become ready in time');
          if (backendProcess === child) {
            backendProcess = null;
          }
          tryNextCandidate();
        }
      };

      child.stdout.on('data', (chunk) => {
        console.log(`[Backend] ${chunk}`.trimEnd());
      });

      child.stderr.on('data', (chunk) => {
        const text = chunk.toString();
        stderrBuffer += text;
        console.error(`[Backend] ${text}`.trimEnd());
      });

      child.on('error', (error) => {
        cleanup();
        lastError = error;
        tryNextCandidate();
      });

      child.on('exit', (code) => {
        if (backendProcess === child) {
          backendProcess = null;
        }

        if (code !== null && code !== 0) {
          cleanup();
          lastError = new Error(stderrBuffer || `Backend exited with code ${code}`);
        }
      });

      launchTimer = setTimeout(() => {
        if (child.exitCode === null && !child.killed) {
          waitForReady();
        } else {
          cleanup();
          lastError = new Error(stderrBuffer || 'Backend failed to launch');
          tryNextCandidate();
        }
      }, 600);

      backendProcess = child;
    };

    tryNextCandidate();
    });
  });
}

function stopBackend() {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill('SIGTERM');
    backendProcess = null;
  }
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      preload: path.join(__dirname, 'preload.js'),
      sandbox: false
    }
  });

  win.loadFile('index.html');
  
  // Always open dev tools to see console errors
  win.webContents.openDevTools();
}

app.whenReady().then(() => {
  createWindow();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

ipcMain.handle('backend:start', async () => {
  return startBackend();
});

ipcMain.handle('backend:stop', async () => {
  stopBackend();
  return { stopped: true };
});

app.on('before-quit', () => {
  stopBackend();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

