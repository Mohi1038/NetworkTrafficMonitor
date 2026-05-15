const { contextBridge, ipcRenderer } = require('electron');

console.log('[Preload] Electron preload script loaded');

contextBridge.exposeInMainWorld('api', {
  fetchTraffic: async () => {
    const bases = ['http://127.0.0.1:5000', 'http://127.0.0.1:5001'];
    let lastErr = null;
    for (const b of bases) {
      try {
        console.log(`[Preload] Fetching traffic from ${b}/api/data`);
        const res = await fetch(`${b}/api/data`);
        console.log('[Preload] Response received:', res.status);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        const data = await res.json();
        console.log('[Preload] Data parsed successfully:', data?.speed);
        return data;
      } catch (error) {
        lastErr = error;
      }
    }
    console.error('[Preload] Error fetching traffic data:', lastErr);
    throw lastErr;
  },

  checkHealth: async () => {
    const bases = ['http://127.0.0.1:5000', 'http://127.0.0.1:5001'];
    for (const b of bases) {
      try {
        const res = await fetch(`${b}/api/health`);
        if (!res.ok) continue;
        return await res.json();
      } catch (error) {
        // try next
      }
    }
    return { status: 'error', message: 'No backend reachable' };
  }
});

console.log('[Preload] API exposed to renderer process');
