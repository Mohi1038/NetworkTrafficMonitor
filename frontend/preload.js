const { contextBridge } = require('electron');
contextBridge.exposeInMainWorld('api', {
  fetchTraffic: async () => {
    const res = await fetch('http://localhost:5000/api/data');
    return res.json();
  }
});
