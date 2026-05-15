console.log('[Renderer] Starting renderer.js');

// Packaged app must only read local traffic from the user's machine.
const API_CANDIDATES = ['http://127.0.0.1:5000', 'http://127.0.0.1:5001'];

async function apiFetch(path, opts) {
  let lastErr = null;
  for (const base of API_CANDIDATES) {
    try {
      const res = await fetch(base + path, opts);
      if (res.ok) return res;
      // If 404/500 etc, remember and try next
      lastErr = res;
    } catch (err) {
      lastErr = err;
    }
  }
  // If we reach here, return the last error/response
  if (lastErr instanceof Response) return lastErr;
  throw lastErr;
}

const TRAFFIC_ENDPOINT = '/api/data';
const maxPoints = 100; // Keep as a constant now, no longer configurable via UI
let timeWindowMs = 5 * 60 * 1000; // 5 minute time window
let timeLabels = [];
let timePoints = [];
let incomingBytes = [];
let outgoingBytes = [];
let updateInterval = 2000; // Default update interval in ms
let monitoringStarted = false;
let consentGranted = false;

const consentModal = document.getElementById('capture-consent-modal');
const consentMessage = document.getElementById('capture-consent-message');
const allowCaptureButton = document.getElementById('allow-capture-btn');
const denyCaptureButton = document.getElementById('deny-capture-btn');

function showConsentModal(message = '') {
  if (consentModal) {
    consentModal.classList.remove('hidden');
  }
  if (consentMessage) {
    consentMessage.textContent = message;
  }
}

function hideConsentModal() {
  if (consentModal) {
    consentModal.classList.add('hidden');
  }
}

async function loadConsentStatus() {
  try {
    const status = window.api?.getConsentStatus
      ? await window.api.getConsentStatus()
      : await apiFetch('/api/consent/status');

    consentGranted = Boolean(status?.allowed);
    return status;
  } catch (error) {
    console.error('[Consent] Failed to load consent status:', error);
    consentGranted = false;
    return { success: false, allowed: false };
  }
}

async function requestConsent() {
  try {
    if (window.api?.startBackend) {
      showConsentModal('Starting the local backend on your machine...');
      await window.api.startBackend();
    }

    const response = window.api?.acceptConsent
      ? await window.api.acceptConsent()
      : await apiFetch('/api/consent/accept', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ allowed: true })
        }).then((res) => res.json());

    consentGranted = Boolean(response?.success);
    if (consentGranted) {
      hideConsentModal();
      startMonitoring();
    }
    return response;
  } catch (error) {
    console.error('[Consent] Failed to grant consent:', error);
    showConsentModal('Unable to start capture yet. Make sure the local backend is running, then try again.');
    throw error;
  }
}

// AREA CHART SETUP
const trafficCtx = document.getElementById('trafficChart').getContext('2d');
const trafficChart = new Chart(trafficCtx, {
  type: 'line',
  data: {
    labels: timeLabels,
    datasets: [
      {
        label: 'Incoming (Bytes/s)',
        data: incomingBytes,
        borderColor: 'rgb(54, 162, 235)',
        backgroundColor: 'rgba(54, 162, 235, 0.2)',
        fill: true,
        tension: 0.4,
        borderWidth: 2
      },
      {
        label: 'Outgoing (Bytes/s)',
        data: outgoingBytes,
        borderColor: 'rgb(255, 99, 132)',
        backgroundColor: 'rgba(255, 99, 132, 0.2)',
        fill: true,
        tension: 0.4,
        borderWidth: 2
      }
    ]
  },
  options: {
    responsive: true,
    maintainAspectRatio: false,
    animation: {
      duration: 300
    },
    scales: {
      x: {
        title: {
          display: true,
          text: 'Time',
          color: '#666'
        },
        ticks: {
          maxTicksLimit: 8,
          autoSkip: true,
          color: '#666'
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.1)'
        }
      },
      y: {
        beginAtZero: true,
        title: {
          display: true,
          text: 'Bytes/s',
          color: '#666'
        },
        ticks: {
          color: '#666'
        },
        grid: {
          color: 'rgba(0, 0, 0, 0.1)'
        }
      }
    },
    plugins: {
      legend: {
        labels: {
          color: '#666'
        }
      }
    }
  }
});

// FUNCTION TO CREATE DOUGHNUT CHART FOR SPEEDOMETER
const createSpeedometer = (ctxId, label) => {
  const ctx = document.getElementById(ctxId).getContext('2d');
  return new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: ['Used', 'Remaining'],
      datasets: [{
        data: [0, 100],
        backgroundColor: ['#007bff', '#e9ecef'],
        borderWidth: 0
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '75%',
      plugins: {
        tooltip: { enabled: false },
        legend: { display: false },
        title: {
          display: true,
          text: `${label}: 0 kbps`,
          padding: { top: 10, bottom: 0 },
          font: { size: 14 },
          color: '#333'
        }
      }
    }
  });
};

let topBandwidthChart = null;  // Keep the chart instance here

function sortTopIps(topIps, bytes) {
    // Convert the object into an array of [key, value] pairs
    const entries = Object.entries(topIps);

    // Sort the array based on the 'bytes' property in descending order
    if(bytes=="incoming_bytes")
      entries.sort(([, a], [, b]) => b.incoming_bytes - a.incoming_bytes);
    else
    entries.sort(([, a], [, b]) => b.outgoing_bytes - a.outgoing_bytes);

    // Convert the sorted array back into an object
    const sortedTopIps = Object.fromEntries(entries);

    return sortedTopIps;
}

let bandwidthType = "incoming_bytes"; // Changed from const to let

document.getElementById("bandwidthToggle").addEventListener("change", (e) => {
  bandwidthType = e.target.value; // Now correctly reassignable
  fetchData();  // Trigger re-fetch to update chart
});

// Fix the bandwidth chart rendering
function renderTopBandwidthChart(data) {
  let topIps = data.top_ips || {};
  const labels = [];
  const values = [];

  topIps = sortTopIps(topIps, bandwidthType);
  let i=0;

  for (const ip in topIps) {
    const entry = topIps[ip];
    const name = entry.app || entry.hostname || ip;
    labels.push(`${name} (${ip})`);
    values.push(entry[bandwidthType] || 0);
    i++;
    if(i>5) break;
  }

  // If no data, show an empty placeholder
  if (labels.length === 0) {
    labels.push('No Data');
    values.push(0);
  }

  const ctx = document.getElementById("topBandwidthChart").getContext("2d");

  if (topBandwidthChart instanceof Chart) {
    topBandwidthChart.destroy();
  }

  topBandwidthChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: labels,
      datasets: [{
        label: bandwidthType === "incoming_bytes" ? "Incoming Bandwidth (Bytes)" : "Outgoing Bandwidth (Bytes)",
        data: values,
        backgroundColor: bandwidthType === "incoming_bytes" ? "rgba(54, 162, 235, 0.7)" : "rgba(255, 99, 132, 0.7)",
        borderColor: bandwidthType === "incoming_bytes" ? "rgba(54, 162, 235, 1)" : "rgba(255, 99, 132, 1)",
        borderWidth: 1
      }]
    },
    options: {
      indexAxis: 'y',
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
          labels: {
            color: '#666'
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return `${formatBytes(context.parsed.x)}`;
            }
          }
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Bandwidth Usage (Bytes)',
            color: '#666'
          },
          ticks: {
            color: '#666'
          },
          grid: {
            color: 'rgba(0, 0, 0, 0.1)'
          }
        },
        y: {
          title: {
            display: true,
            text: 'App / Hostname / IP',
            color: '#666'
          },
          ticks: {
            color: '#666'
          },
          grid: {
            color: 'rgba(0, 0, 0, 0.1)'
          }
        }
      }
    }
  });
}

let protocolChart = null;

// Fix the protocol chart rendering
function renderProtocolChart(data) {
  const protocols = data.protocol_distribution || {};
  const labels = Object.keys(protocols);
  const values = Object.values(protocols);

  // If no data, show an empty placeholder
  if (labels.length === 0) {
    labels.push('No Data');
    values.push(1);
  }

  const ctx = document.getElementById("protocolChart").getContext("2d");

  if (protocolChart instanceof Chart) {
    protocolChart.destroy();
  }

  protocolChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels: labels,
      datasets: [{
        data: values,
        backgroundColor: [
          "#36A2EB",
          "#FF6384",
          "#FFCE56",
          "#4BC0C0",
          "#9966FF",
          "#FF9F40",
          "#7ED957"
        ],
        borderWidth: 1
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          position: "bottom",
          labels: {
            color: '#666',
            font: {
              size: 12
            }
          }
        },
        tooltip: {
          callbacks: {
            label: function(context) {
              return `${context.label}: ${formatBytes(context.raw)}`;
            }
          }
        },
        title: {
          display: true,
          text: "Traffic Distribution by Protocol",
          color: '#333'
        }
      }
    }
  });
}

// Connection state. The UI must show actual backend data only.
let isOffline = false;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;
const RECONNECT_INTERVAL = 3000; // 3 seconds

function toFiniteNumber(value, fallback = 0) {
  const number = Number(value);
  return Number.isFinite(number) ? number : fallback;
}

function normalizeTrafficData(data) {
  return {
    total_incoming_bytes: toFiniteNumber(data?.total_incoming_bytes),
    total_outgoing_bytes: toFiniteNumber(data?.total_outgoing_bytes),
    speed: {
      incoming_mbps: toFiniteNumber(data?.speed?.incoming_mbps),
      outgoing_mbps: toFiniteNumber(data?.speed?.outgoing_mbps),
      incoming_kbps: toFiniteNumber(data?.speed?.incoming_kbps),
      outgoing_kbps: toFiniteNumber(data?.speed?.outgoing_kbps)
    },
    protocol_distribution: data?.protocol_distribution || {},
    top_ips: data?.top_ips || {},
    traffic_table: Array.isArray(data?.traffic_table) ? data.traffic_table : []
  };
}

async function fetchData() {
  try {
    console.log('[FetchData] Starting fetch, window.api available:', !!window.api);
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000); // 2 second timeout

    const rawData = window.api?.fetchTraffic
      ? await window.api.fetchTraffic()
      : await fetch(TRAFFIC_ENDPOINT, { signal: controller.signal }).then((res) => {
          console.log('[FetchData] Direct fetch response:', res.status);
          if (!res.ok) {
            throw new Error(`HTTP error: ${res.status}`);
          }
          return res.json();
        });
    clearTimeout(timeoutId);
    console.log('[FetchData] Raw data received, speed field:', rawData?.speed);

    const data = normalizeTrafficData(rawData);

    // If we get here, we're online
    if (isOffline) {
      console.log("Reconnected to backend server");
      document.getElementById('connection-status')?.classList.remove('offline');
      document.getElementById('connection-status')?.classList.add('online');
      document.getElementById('connection-status')?.setAttribute('title', 'Connected to backend');
    }
    isOffline = false;
    reconnectAttempts = 0;

    return data;
  } catch (err) {
    if (!isOffline) {
      console.error(`Error fetching network data: ${err.message}`);
      document.getElementById('connection-status')?.classList.remove('online');
      document.getElementById('connection-status')?.classList.add('offline');
      document.getElementById('connection-status')?.setAttribute('title', 'Disconnected - waiting for live backend data');
    }

    isOffline = true;
    reconnectAttempts++;

    if (reconnectAttempts <= MAX_RECONNECT_ATTEMPTS) {
      console.log(`Reconnect attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS} in ${RECONNECT_INTERVAL/1000}s`);
    } else if (reconnectAttempts === MAX_RECONNECT_ATTEMPTS + 1) {
      console.log("Maximum reconnection attempts reached. Keeping the last real data on screen.");
    }

    return null;
  }
}

// Format bytes to human-readable format
function formatBytes(bytes, decimals = 2) {
  bytes = Math.max(0, toFiniteNumber(bytes));
  if (bytes === 0) return '0 B';

  const k = 1024;
  const dm = decimals < 0 ? 0 : decimals;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB', 'PB'];

  const i = Math.floor(Math.log(bytes) / Math.log(k));

  return parseFloat((bytes / Math.pow(k, i)).toFixed(dm)) + ' ' + sizes[i];
}

// Update summary statistics
function updateSummaryStats(data) {
  document.getElementById('total-incoming').textContent = formatBytes(data.total_incoming_bytes);
  document.getElementById('total-outgoing').textContent = formatBytes(data.total_outgoing_bytes);

  // Count unique connections
  const connections = new Set();
  (data.traffic_table || []).forEach(entry => {
    connections.add(`${entry.src_ip}:${entry.src_port}-${entry.dst_ip}:${entry.dst_port}`);
  });
  document.getElementById('active-connections').textContent = connections.size;

  // Find top protocol
  let topProtocol = '-';
  let maxCount = 0;
  for (const [protocol, count] of Object.entries(data.protocol_distribution || {})) {
    if (count > maxCount) {
      maxCount = count;
      topProtocol = protocol;
    }
  }
  document.getElementById('top-protocol').textContent = topProtocol;
}

// Update traffic table
function updateTrafficTable(data) {
  const tbody = document.getElementById('traffic-tbody');
  const tableData = data?.traffic_table || [];

  // Get filter values
  const searchTerm = document.getElementById('traffic-search')?.value?.toLowerCase() || '';
  const protocolFilter = document.getElementById('protocol-filter')?.value || 'all';
  const directionFilter = document.getElementById('direction-filter')?.value || 'all';

  // Clear existing rows first
  tbody.innerHTML = '';

  // Add filtered data
  tableData.slice(-50).reverse().forEach(entry => {
    // Apply filters
    if (searchTerm &&
        !String(entry.src_ip).toLowerCase().includes(searchTerm) &&
        !String(entry.dst_ip).toLowerCase().includes(searchTerm) &&
        !String(entry.protocol).toLowerCase().includes(searchTerm)) {
      return;
    }

    if (protocolFilter !== 'all' && entry.protocol !== protocolFilter) {
      return;
    }

    if (directionFilter !== 'all' && entry.direction && entry.direction !== directionFilter) {
      return;
    }

    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${entry.timestamp}</td>
      <td>${entry.src_ip}:${entry.src_port}</td>
      <td>${entry.dst_ip}:${entry.dst_port}</td>
      <td>${entry.protocol}</td>
      <td>${entry.dst_port}</td>
      <td>${formatBytes(entry.bytes)}</td>
    `;
    tbody.appendChild(row);
  });
}

// Tab navigation
document.querySelectorAll('.tab-btn').forEach(button => {
  button.addEventListener('click', () => {
    // Remove active class from all buttons
    document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));

    button.classList.add('active');

    // Hide all tab contents
    document.querySelectorAll('.tab-content').forEach(content => content.classList.add('hidden'));

    // Show the selected tab content
    const tabId = button.dataset.tab;
    document.getElementById(tabId).classList.remove('hidden');
  });
});

// Settings handling
document.getElementById('apply-settings').addEventListener('click', () => {
  const newUpdateInterval = parseInt(document.getElementById('update-interval').value);

  // Only update if the value has changed
  if (newUpdateInterval !== updateInterval) {
    updateInterval = newUpdateInterval;

    // Clear any existing update timers
    if (window.updateTimer) {
      clearInterval(window.updateTimer);
    }

    // Start new update timer with the selected interval
    window.updateTimer = setInterval(updateCharts, updateInterval);
    console.log(`Chart update interval changed to ${updateInterval}ms`);
  }

  alert('Settings applied successfully!');
});

// Add event listeners for table filters
document.getElementById('traffic-search')?.addEventListener('input', () => updateTrafficTable(lastData));
document.getElementById('protocol-filter')?.addEventListener('change', () => updateTrafficTable(lastData));
document.getElementById('direction-filter')?.addEventListener('change', () => updateTrafficTable(lastData));

// Store the last data received to avoid unnecessary fetches
let lastData = null;

// INITIALIZE GAUGES
const incomingGauge = createSpeedometer('incomingSpeedo', 'Download Speed');
const outgoingGauge = createSpeedometer('outgoingSpeedo', 'Upload Speed');

// Define the update function that will be called by the timer
async function updateCharts() {
  try {
    const data = await fetchData();
    if (!data) {
      console.error("No data received");
      return;
    }

    lastData = data;

    const now = new Date();
    // Use Mbps for accurate industry-standard speed measurement (Akamai/Ookla standard)
    const incomingMbps = parseFloat(data.speed?.incoming_mbps) || 0;
    const outgoingMbps = parseFloat(data.speed?.outgoing_mbps) || 0;
    
    // Also get kbps for chart display
    const incomingKbps = incomingMbps * 1000;
    const outgoingKbps = outgoingMbps * 1000;

    // Convert Mbps to Bytes/s for chart: (Mbps * 1,000,000 bits/Mb) / 8 bits/byte
    const incomingBps = Math.round((incomingMbps * 1_000_000) / 8);
    const outgoingBps = Math.round((outgoingMbps * 1_000_000) / 8);

    // Remove data points older than our time window
    const cutoffTime = now.getTime() - timeWindowMs;
    while (timePoints.length > 0 && timePoints[0] < cutoffTime) {
      timePoints.shift();
      timeLabels.shift();
      incomingBytes.shift();
      outgoingBytes.shift();
    }

    // Add new data point
    const timeStr = now.toLocaleTimeString();
    timePoints.push(now.getTime());
    timeLabels.push(timeStr);
    incomingBytes.push(incomingBps);
    outgoingBytes.push(outgoingBps);

    // Ensure we don't exceed maxPoints
    while (timeLabels.length > maxPoints) {
      timePoints.shift();
      timeLabels.shift();
      incomingBytes.shift();
      outgoingBytes.shift();
    }

    // Update traffic chart with error handling
    try {
      trafficChart.data.labels = [...timeLabels];
      trafficChart.data.datasets[0].data = [...incomingBytes];
      trafficChart.data.datasets[1].data = [...outgoingBytes];
      trafficChart.update();
    } catch (chartError) {
      console.error("Error updating traffic chart:", chartError);
    }

    // Update speedometers with industry-standard Mbps scale (typical home internet: 0-100 Mbps)
    // Scale gauges to realistic broadband speeds: 0-100 Mbps
    const GAUGE_MAX_MBPS = 100;
    const incomingGaugeValue = Math.min(incomingMbps, GAUGE_MAX_MBPS);
    const outgoingGaugeValue = Math.min(outgoingMbps, GAUGE_MAX_MBPS);

    incomingGauge.data.datasets[0].data = [incomingGaugeValue, Math.max(GAUGE_MAX_MBPS - incomingGaugeValue, 0)];
    outgoingGauge.data.datasets[0].data = [outgoingGaugeValue, Math.max(GAUGE_MAX_MBPS - outgoingGaugeValue, 0)];

    // Display in Mbps (industry standard: Akamai, Ookla, etc.)
    incomingGauge.options.plugins.title.text = `Download Speed: ${incomingMbps.toFixed(2)} Mbps`;
    outgoingGauge.options.plugins.title.text = `Upload Speed: ${outgoingMbps.toFixed(2)} Mbps`;

    incomingGauge.update();
    outgoingGauge.update();

    renderProtocolChart(data);
    renderTopBandwidthChart(data);

    // Update new UI elements
    updateSummaryStats(data);
    updateTrafficTable(data);
  } catch (err) {
    console.error("Error updating UI:", err);
  }
}

function startMonitoring() {
  if (monitoringStarted || !consentGranted) {
    return;
  }

  monitoringStarted = true;
  window.updateTimer = setInterval(updateCharts, updateInterval);
  updateCharts();
}

// Speed Test Functionality
let isSpeedTesting = false;

async function startSpeedTest() {
  if (isSpeedTesting) {
    console.log("Speed test already running");
    return;
  }
  
  isSpeedTesting = true;
  const button = document.getElementById('speedtest-btn');
  const resultsDiv = document.getElementById('speedtest-results');
  const statusText = document.getElementById('speedtest-status-text');
  const downloadDiv = document.getElementById('speedtest-download');
  const uploadDiv = document.getElementById('speedtest-upload');
  const progressBar = document.getElementById('speedtest-progress');
  
  // Show results container and disable button
  button.disabled = true;
  resultsDiv.style.display = 'block';
  statusText.textContent = 'Running speed test... This may take a minute.';
  downloadDiv.textContent = '-';
  uploadDiv.textContent = '-';
  if (progressBar) {
    progressBar.style.setProperty('--progress', '0%');
  }

  const phaseLabel = (phase, progress) => {
    const clamped = Math.max(0, Math.min(100, Number(progress) || 0));
    switch (phase) {
      case 'upload_warmup':
        return `Warming up upload... (${clamped}% complete)`;
      case 'upload':
        return `Measuring upload... (${clamped}% complete)`;
      case 'download_warmup':
        return `Warming up download... (${clamped}% complete)`;
      case 'download':
        return `Measuring download... (${clamped}% complete)`;
      case 'complete':
        return '✓ Speed test complete!';
      case 'error':
        return '✗ Speed test failed. Network may be unavailable.';
      default:
        return `Testing... (${clamped}% complete)`;
    }
  };
  
  try {
    // Start the test
    const startResponse = await apiFetch('/api/speedtest/start', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ duration: 15, workers: 8, repeats: 3 })
    });
    
    if (!startResponse.ok) {
      throw new Error(`HTTP error: ${startResponse.status}`);
    }
    
    // Poll for results
    let pollCount = 0;
    const maxPolls = 120; // 2 minutes max
    
    while (pollCount < maxPolls) {
      await new Promise(resolve => setTimeout(resolve, 1000)); // Wait 1 second
      pollCount++;
      
      const statusResponse = await apiFetch('/api/speedtest/status');
      if (!statusResponse.ok) continue;
      
      const statusData = await statusResponse.json();
      const results = statusData.data;
      const progress = Math.max(0, Math.min(100, Number(results.progress) || 0));
      const phase = results.current_phase || results.test_status || 'testing';

      if (progressBar) {
        progressBar.style.setProperty('--progress', `${progress}%`);
      }

      if (Number.isFinite(results.upload_mbps) && results.upload_mbps > 0) {
        uploadDiv.textContent = `${results.upload_mbps} Mbps`;
      }
      if (Number.isFinite(results.download_mbps) && results.download_mbps > 0) {
        downloadDiv.textContent = `${results.download_mbps} Mbps`;
      }
      
      if (results.test_status === 'complete') {
        // Test complete!
        downloadDiv.textContent = `${results.download_mbps} Mbps`;
        uploadDiv.textContent = `${results.upload_mbps} Mbps`;
        if (progressBar) {
          progressBar.style.setProperty('--progress', '100%');
        }
        statusText.textContent = '✓ Speed test complete!';
        break;
      } else if (results.test_status === 'error') {
        statusText.textContent = phaseLabel(phase, progress);
        break;
      } else {
        // Still testing
        statusText.textContent = phaseLabel(phase, progress);
      }
    }
    
    if (pollCount >= maxPolls) {
      statusText.textContent = '⏱ Test timed out. Check if backend is responding.';
    }
  } catch (err) {
    console.error('Speed test error:', err);
    statusText.textContent = `✗ Error: ${err.message}`;
    downloadDiv.textContent = 'N/A';
    uploadDiv.textContent = 'N/A';
  } finally {
    isSpeedTesting = false;
    button.disabled = false;
  }
}

// Attach event listener to speed test button
document.getElementById('speedtest-btn')?.addEventListener('click', startSpeedTest);

async function initializeConsentFlow() {
  const consentStatus = await loadConsentStatus();

  if (consentStatus?.allowed) {
    hideConsentModal();
    startMonitoring();
    return;
  }

  showConsentModal('This app will capture traffic only from this device after you allow it.');
}

allowCaptureButton?.addEventListener('click', async () => {
  await requestConsent();
});

denyCaptureButton?.addEventListener('click', () => {
  showConsentModal('Capture is paused until you allow local network access.');
});

initializeConsentFlow();

/* ========== THEME MANAGEMENT ========== */
function initTheme() {
  // Check for saved theme preference
  const savedTheme = localStorage.getItem('theme') || 'auto';
  applyTheme(savedTheme);
  
  // Set radio button to current theme
  const themeRadio = document.querySelector(`input[name="theme"][value="${savedTheme}"]`);
  if (themeRadio) themeRadio.checked = true;
}

function applyTheme(theme) {
  const body = document.body;
  const icon = document.querySelector('.theme-toggle i');
  
  if (theme === 'auto') {
    // Check system preference
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    body.classList.toggle('dark-mode', prefersDark);
    icon.className = prefersDark ? 'fas fa-sun' : 'fas fa-moon';
  } else if (theme === 'dark') {
    body.classList.add('dark-mode');
    icon.className = 'fas fa-sun';
  } else {
    body.classList.remove('dark-mode');
    icon.className = 'fas fa-moon';
  }
  
  localStorage.setItem('theme', theme);
}

// Theme toggle button
document.getElementById('theme-toggle')?.addEventListener('click', () => {
  const savedTheme = localStorage.getItem('theme') || 'auto';
  const nextTheme = savedTheme === 'light' ? 'dark' : savedTheme === 'dark' ? 'auto' : 'light';
  applyTheme(nextTheme);
  const radio = document.querySelector(`input[name="theme"][value="${nextTheme}"]`);
  if (radio) radio.checked = true;
});

// Theme radio buttons in settings
document.querySelectorAll('input[name="theme"]').forEach(radio => {
  radio.addEventListener('change', (e) => {
    applyTheme(e.target.value);
  });
});

/* ========== SECURITY UPDATES ========== */
async function updateSecurityStats() {
  try {
    // fetch DDoS alerts and threat summary in parallel
    const [ddosResp, threatResp] = await Promise.all([
      apiFetch('/api/ddos/alerts'),
      apiFetch('/api/threat/summary')
    ]);

    const ddosJson = ddosResp && ddosResp.ok ? await ddosResp.json() : null;
    const threatJson = threatResp && threatResp.ok ? await threatResp.json() : null;

    // DDoS stats
    const ddosStats = ddosJson?.statistics || {};
    const ddosAlerts = ddosJson?.alerts || [];
    document.getElementById('ddos-blocked').textContent = ddosStats?.blocked_attacks || ddosStats?.blocked || 0;
    document.getElementById('suspicious-flows').textContent = ddosStats?.suspicious_flows || ddosStats?.flows || 0;

    // Threat summary
    const summary = threatJson?.summary || {};
    const maliciousIps = Array.isArray(summary?.malicious_ips) ? summary.malicious_ips : (summary?.malicious || []);
    document.getElementById('suspicious-ips').textContent = maliciousIps.length || 0;
    document.getElementById('anomalies').textContent = summary?.anomalies_detected || summary?.anomalies || 0;

    // Protocol analysis
    const protocols = (await (await apiFetch('/api/data')).json()).protocol_distribution || {};
    const tcpCount = protocols.TCP || protocols.TCPv6 || 0;
    const total = Object.values(protocols).reduce((a, b) => a + b, 0) || 1;
    const encryptedPercent = Math.min(100, Math.round((tcpCount / total) * 100));
    document.getElementById('encrypted-traffic').textContent = `${encryptedPercent}%`;
    document.getElementById('unencrypted-traffic').textContent = `${100 - encryptedPercent}%`;
    document.getElementById('suspicious-ports').textContent = summary?.suspicious_ports_count || summary?.suspicious_ports || 0;

    // Threat level bar: map anomaly counts to severity
    const threatScore = Math.min(100, Math.round((document.getElementById('anomalies').textContent || 0) * 20));
    const threatLabel = threatScore < 30 ? 'Low' : threatScore < 70 ? 'Medium' : 'High';
    document.getElementById('threat-level').textContent = threatLabel;
    document.getElementById('threat-bar').style.width = `${threatScore}%`;

    // Render recent alerts list using DDoS alerts
    const alertsList = document.getElementById('security-alerts');
    alertsList.innerHTML = '';
    if (Array.isArray(ddosAlerts) && ddosAlerts.length) {
      ddosAlerts.slice(0, 10).forEach(a => {
        const el = document.createElement('div');
        el.className = 'alert-item warning';
        el.innerHTML = `
          <span class="alert-icon"><i class="fas fa-exclamation-circle"></i></span>
          <div class="alert-content">
            <span class="alert-title">${a.summary || a.type || 'DDoS attempt'}</span>
            <span class="alert-time">${a.first_seen || a.time || 'just now'}</span>
          </div>
        `;
        alertsList.appendChild(el);
      });
    } else {
      alertsList.innerHTML = '<div class="alert-item info"><span class="alert-icon"><i class="fas fa-info-circle"></i></span><div class="alert-content"><span class="alert-title">No recent security alerts</span></div></div>';
    }

  } catch (err) {
    console.error('Error updating security stats:', err);
  }
}

// Open modal and populate with detailed report
async function openSecurityDetail(type) {
  const modal = document.getElementById('security-modal');
  const title = document.getElementById('modal-title');
  const body = document.getElementById('modal-body');
  const actionBtn = document.getElementById('modal-action');

  title.textContent = 'Loading...';
  body.innerHTML = '<p>Loading details...</p>';
  modal.classList.remove('hidden');

  try {
    if (type === 'ddos') {
      title.textContent = 'DDoS Alerts and Recommendations';
      const resp = await apiFetch('/api/ddos/alerts');
      const json = resp.ok ? await resp.json() : {};
      const alerts = json.alerts || [];
      body.innerHTML = alerts.length ? alerts.slice(0,50).map(a=>`<div class="detail-alert"><strong>${a.type||a.summary}</strong><div>Source: ${a.src_ip||'unknown'}</div><div>First seen: ${a.first_seen||a.time||'n/a'}</div><div>Details: ${a.details||a.note||''}</div></div>`).join('') : '<p>No DDoS alerts found.</p>';
      actionBtn.textContent = 'Block Source IPs';
      actionBtn.onclick = async () => {
        try {
          const resp = await apiFetch('/api/ddos/alerts');
          const json = resp.ok ? await resp.json() : {};
          const alerts = json.alerts || [];
          const ips = Array.from(new Set(alerts.map(a=>a.src_ip).filter(Boolean)));
          if (ips.length === 0) {
            alert('No source IPs available to block');
            return;
          }

          for (const ip of ips) {
            const rule = { action: 'block', target: ip, reason: 'Blocked via UI - DDoS mitigation' };
            await apiFetch('/api/rules/add', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(rule) });
          }
          alert(`Requested block for ${ips.length} IP(s). Check rules endpoint for status.`);
        } catch (err) {
          console.error('Failed to create block rules', err);
          alert('Failed to create block rules: ' + err.message);
        }
      };
    } else if (type === 'threat') {
      title.textContent = 'Threat Intelligence Report';
      const resp = await apiFetch('/api/threat/summary');
      const json = resp.ok ? await resp.json() : {};
      const summary = json.summary || {};
      const ips = Array.isArray(summary.malicious_ips) ? summary.malicious_ips : (summary.malicious || []);
      body.innerHTML = `
        <h4>Malicious IPs (${ips.length})</h4>
        ${ips.length ? '<ul>' + ips.slice(0,100).map(i=>`<li>${i} - <button class="btn btn-secondary" data-ip="${i}">Check</button></li>`).join('') + '</ul>' : '<p>No flagged IPs in recent traffic.</p>'}
        <h4>Summary</h4>
        <pre>${JSON.stringify(summary, null, 2)}</pre>
      `;
      // attach ip check handlers
      body.querySelectorAll('button[data-ip]').forEach(btn=>{
        btn.addEventListener('click', async (e)=>{
          const ip = e.target.dataset.ip;
          const r = await apiFetch(`/api/threat/check/${ip}`);
          const j = r && r.ok ? await r.json() : { error: 'failed' };
          alert(`IP ${ip} report:\n` + JSON.stringify(j, null, 2));
        });
      });
      actionBtn.textContent = 'Create Block Rule';
      actionBtn.onclick = async () => {
        try {
          const ipToBlock = ips && ips.length ? ips[0] : null;
          if (!ipToBlock) {
            alert('No IP selected to block');
            return;
          }
          const rule = { action: 'block', target: ipToBlock, reason: 'Blocked via UI - Threat rule' };
          const r = await apiFetch('/api/rules/add', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(rule) });
          const jr = r && r.ok ? await r.json() : { success: false };
          alert('Rule response: ' + (jr.message || JSON.stringify(jr)));
        } catch (err) {
          console.error('Error creating rule', err);
          alert('Error creating rule: ' + err.message);
        }
      };
    } else if (type === 'geo') {
      title.textContent = 'Geo-Blocking Details';
      const resp = await apiFetch('/api/geomap');
      const json = resp.ok ? await resp.json() : {};
      body.innerHTML = `<pre>${JSON.stringify(json.data || json, null, 2)}</pre>`;
      actionBtn.textContent = 'Edit Blocked Countries';
      actionBtn.onclick = () => { document.getElementById('blocked-countries-input').focus(); };
    } else if (type === 'protocol') {
      title.textContent = 'Protocol Analysis Details';
      const resp = await apiFetch('/api/data');
      const json = resp.ok ? await resp.json() : {};
      body.innerHTML = `
        <h4>Protocol Distribution</h4>
        <pre>${JSON.stringify(json.protocol_distribution || {}, null, 2)}</pre>
      `;
      actionBtn.textContent = 'Investigate Ports';
      actionBtn.onclick = () => { alert('Action: Investigate suspicious ports via packet logs'); };
    }
  } catch (err) {
    body.innerHTML = `<p>Error loading details: ${err.message}</p>`;
    actionBtn.textContent = 'Close';
    actionBtn.onclick = () => {};
  }
}

// Close modal
document.getElementById('modal-close')?.addEventListener('click', () => {
  document.getElementById('security-modal').classList.add('hidden');
});

// Wire view details buttons
document.addEventListener('click', (e) => {
  const btn = e.target.closest('.view-details');
  if (btn) {
    const t = btn.dataset.type;
    openSecurityDetail(t);
  }
});

// Update security stats every 5 seconds
setInterval(updateSecurityStats, 5000);
updateSecurityStats();

/* ========== NOTIFICATION EMAIL SETTINGS ========== */
// Load saved notification email
function loadNotificationEmail() {
  const saved = localStorage.getItem('notificationEmail') || '';
  const input = document.getElementById('notification-email');
  if (input) input.value = saved;
}

document.getElementById('save-email-btn')?.addEventListener('click', async () => {
  const btn = document.getElementById('save-email-btn');
  const input = document.getElementById('notification-email');
  if (!input) return;
  const email = input.value.trim();
  if (!email) { alert('Please provide an email address'); return; }

  const oldText = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Saving...';

  localStorage.setItem('notificationEmail', email);

  try {
    const payload = { receiver: email };

    const resp = await apiFetch('/api/settings/email_config', {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload)
    });
    if (!resp.ok) throw new Error('HTTP ' + resp.status);
    const j = await resp.json();
    alert('✓ Email configuration saved!');
  } catch (err) {
    console.error('Failed to save email config', err);
    alert('Error: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = oldText;
  }
});

document.getElementById('test-email-btn')?.addEventListener('click', async () => {
  const btn = document.getElementById('test-email-btn');
  const input = document.getElementById('notification-email');
  if (!input) return;
  const email = input.value.trim();
  if (!email) { alert('Please provide an email address'); return; }

  const oldText = btn.textContent;
  btn.disabled = true;
  btn.textContent = 'Sending...';

  try {
    const smtpHost = document.getElementById('smtp-host')?.value || 'smtp.gmail.com';
    const smtpPort = parseInt(document.getElementById('smtp-port')?.value || '465');
    const smtpUser = document.getElementById('smtp-user')?.value || '';
    const smtpPassword = document.getElementById('smtp-password')?.value || '';
    const useSsl = !!document.getElementById('smtp-ssl')?.checked;

    const payload = {
      receiver: email,
      sender: smtpUser || email,
      smtp_host: smtpHost,
      smtp_port: smtpPort,
      smtp_user: smtpUser,
      smtp_password: smtpPassword,
      use_ssl: useSsl
    };

    await apiFetch('/api/settings/email_config', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
    const resp = await apiFetch('/api/settings/test_email', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ subject: '🔐 Network Monitor - Test Alert', body: 'This is a test email from your Network Traffic Monitor application. If you received this, email alerts are working correctly!' }) });
    const j = resp && resp.ok ? await resp.json() : { success: false };
    alert('✓ Test email sent!\\n\\nIf SMTP password not configured: email saved to backend/saved_emails/\\nIf SMTP configured: check your inbox');
  } catch (err) {
    console.error('Error sending test email', err);
    alert('Error: ' + err.message);
  } finally {
    btn.disabled = false;
    btn.textContent = oldText;
  }
});

// Load saved email config
function loadEmailConfig() {
  apiFetch('/api/settings/email_config').then(async r => {
    if (r && r.ok) {
      const data = await r.json();
      const cfg = data.config || {};
      if (cfg.receiver) document.getElementById('notification-email').value = cfg.receiver;
    }
  }).catch(err => console.log('No saved email config yet'));
}

loadNotificationEmail();
loadEmailConfig();

/* ========== ENHANCED SETTINGS ========== */
document.getElementById('apply-settings')?.addEventListener('click', () => {
  const newUpdateInterval = parseInt(document.getElementById('update-interval')?.value || 2000);
  
  // Update interval
  if (newUpdateInterval !== updateInterval) {
    updateInterval = newUpdateInterval;
    if (window.updateTimer) {
      clearInterval(window.updateTimer);
    }
    window.updateTimer = setInterval(updateCharts, updateInterval);
    console.log(`Chart update interval changed to ${updateInterval}ms`);
  }
  
  // Security settings
  const geoBlockingEnabled = document.getElementById('geo-blocking-enabled')?.checked;
  const ddosProtectionEnabled = document.getElementById('ddos-protection-enabled')?.checked;
  const threatDetectionEnabled = document.getElementById('threat-detection-enabled')?.checked;
  const blockedCountries = document.getElementById('blocked-countries-input')?.value || '';
  
  localStorage.setItem('geoBlockingEnabled', geoBlockingEnabled);
  localStorage.setItem('ddosProtectionEnabled', ddosProtectionEnabled);
  localStorage.setItem('threatDetectionEnabled', threatDetectionEnabled);
  localStorage.setItem('blockedCountries', blockedCountries);
  
  console.log('Security settings saved:', { geoBlockingEnabled, ddosProtectionEnabled, threatDetectionEnabled, blockedCountries });
  
  alert('✓ Settings applied successfully!');
});

document.getElementById('reset-settings')?.addEventListener('click', () => {
  if (confirm('Reset all settings to defaults?')) {
    localStorage.clear();
    location.reload();
  }
});

// Load saved security settings on startup
function loadSecuritySettings() {
  const geoBlockingEnabled = localStorage.getItem('geoBlockingEnabled') !== 'false';
  const ddosProtectionEnabled = localStorage.getItem('ddosProtectionEnabled') !== 'false';
  const threatDetectionEnabled = localStorage.getItem('threatDetectionEnabled') !== 'false';
  const blockedCountries = localStorage.getItem('blockedCountries') || 'CN,RU,KP';
  
  const geoCheckbox = document.getElementById('geo-blocking-enabled');
  const ddosCheckbox = document.getElementById('ddos-protection-enabled');
  const threatCheckbox = document.getElementById('threat-detection-enabled');
  const countriesInput = document.getElementById('blocked-countries-input');
  
  if (geoCheckbox) geoCheckbox.checked = geoBlockingEnabled;
  if (ddosCheckbox) ddosCheckbox.checked = ddosProtectionEnabled;
  if (threatCheckbox) threatCheckbox.checked = threatDetectionEnabled;
  if (countriesInput) countriesInput.value = blockedCountries;
}

loadSecuritySettings();
initTheme();
