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
  },

  startBackend: async () => {
    return ipcRenderer.invoke('backend:start');
  },

  stopBackend: async () => {
    return ipcRenderer.invoke('backend:stop');
  },

  getConsentStatus: async () => {
    const bases = ['http://127.0.0.1:5000', 'http://127.0.0.1:5001'];
    for (const b of bases) {
      try {
        const res = await fetch(`${b}/api/consent/status`);
        if (!res.ok) continue;
        return await res.json();
      } catch (error) {
        // try next
      }
    }
    return { success: false, allowed: false, capture_running: false };
  },

  acceptConsent: async () => {
    const bases = ['http://127.0.0.1:5000', 'http://127.0.0.1:5001'];
    let lastErr = null;
    for (const b of bases) {
      try {
        const res = await fetch(`${b}/api/consent/accept`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ allowed: true })
        });
        if (!res.ok) {
          lastErr = new Error(`HTTP error! status: ${res.status}`);
          continue;
        }
        return await res.json();
      } catch (error) {
        lastErr = error;
      }
    }
    throw lastErr;
  }
});

console.log('[Preload] API exposed to renderer process');
