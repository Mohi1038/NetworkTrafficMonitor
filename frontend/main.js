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

const { app, BrowserWindow } = require('electron');
const path = require('path');

function createWindow() {
  const win = new BrowserWindow({
    width: 1200,
    height: 800,
    webPreferences: {
      preload: path.join(__dirname, "renderer.js"),
      nodeIntegration: true,
      contextIsolation: false,
    }
  });

  win.loadFile("index.html");
}

app.whenReady().then(createWindow);
