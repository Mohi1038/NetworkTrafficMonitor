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

const { app, BrowserWindow } = require('electron');
const path = require('path');
const isDev = require('electron-is-dev');

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

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

