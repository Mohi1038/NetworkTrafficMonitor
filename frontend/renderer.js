const TRAFFIC_ENDPOINT = "http://127.0.0.1:5000/api/data";
const maxPoints = 100; // Keep as a constant now, no longer configurable via UI
let timeWindowMs = 5 * 60 * 1000; // 5 minute time window
let timeLabels = [];
let incomingBytes = [];
let outgoingBytes = [];
let updateInterval = 2000; // Default update interval in ms

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
  
  // If no data, add dummy entry
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
  
  // If no data, add dummy entry to show empty chart
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
              return `${context.label}: ${context.raw} packets`;
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

// Add offline mode and automatic reconnection
let isOffline = false;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;
const RECONNECT_INTERVAL = 3000; // 3 seconds

// Generate dummy data for offline mode
function generateDummyData() {
  const now = new Date().toLocaleTimeString();
  const incomingKbps = Math.random() * 500;
  const outgoingKbps = Math.random() * 250;
  
  return {
    total_incoming_bytes: Math.floor(Math.random() * 10000000),
    total_outgoing_bytes: Math.floor(Math.random() * 5000000),
    speed: {
      incoming_kbps: incomingKbps.toFixed(2),
      outgoing_kbps: outgoingKbps.toFixed(2)
    },
    protocol_distribution: {
      "TCP": Math.floor(Math.random() * 5000),
      "UDP": Math.floor(Math.random() * 3000),
      "HTTP": Math.floor(Math.random() * 2000),
      "HTTPS": Math.floor(Math.random() * 4000),
      "DNS": Math.floor(Math.random() * 1000)
    },
    top_ips: {
      "192.168.1.10": {
        hostname: "local-device",
        app: "chrome.exe",
        incoming_bytes: Math.floor(Math.random() * 1000000),
        outgoing_bytes: Math.floor(Math.random() * 500000)
      },
      "8.8.8.8": {
        hostname: "dns.google",
        app: "firefox.exe",
        incoming_bytes: Math.floor(Math.random() * 500000),
        outgoing_bytes: Math.floor(Math.random() * 250000)
      },
      "142.250.190.78": {
        hostname: "google.com",
        app: "chrome.exe",
        incoming_bytes: Math.floor(Math.random() * 800000),
        outgoing_bytes: Math.floor(Math.random() * 400000)
      }
    },
    traffic_table: Array(20).fill().map(() => ({
      timestamp: now,
      src_ip: `192.168.1.${Math.floor(Math.random() * 254) + 1}`,
      src_port: Math.floor(Math.random() * 60000) + 1024,
      dst_ip: `172.16.${Math.floor(Math.random() * 254) + 1}.${Math.floor(Math.random() * 254) + 1}`,
      dst_port: [80, 443, 8080, 22, 53][Math.floor(Math.random() * 5)],
      protocol: ["TCP", "UDP", "HTTP", "HTTPS", "DNS"][Math.floor(Math.random() * 5)],
      bytes: Math.floor(Math.random() * 1500) + 40
    }))
  };
}

// Modified fetchData with offline fallback
async function fetchData() {
  if (isOffline && reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
    return generateDummyData();
  }
  
  try {
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 2000); // 2 second timeout
    
    const res = await fetch(TRAFFIC_ENDPOINT, { 
      signal: controller.signal 
    });
    clearTimeout(timeoutId);
    
    if (!res.ok) {
      throw new Error(`HTTP error: ${res.status}`);
    }
    
    const data = await res.json();
    
    // If we get here, we're online
    if (isOffline) {
      console.log("🟢 Reconnected to backend server");
      document.getElementById('connection-status')?.classList.remove('offline');
      document.getElementById('connection-status')?.classList.add('online');
      document.getElementById('connection-status')?.setAttribute('title', 'Connected to backend');
    }
    isOffline = false;
    reconnectAttempts = 0;
    
    return data;
  } catch (err) {
    if (!isOffline) {
      console.error(`🔴 Error fetching network data: ${err.message}`);
      console.log("Switching to offline mode with dummy data");
      document.getElementById('connection-status')?.classList.remove('online');
      document.getElementById('connection-status')?.classList.add('offline');
      document.getElementById('connection-status')?.setAttribute('title', 'Disconnected - Using dummy data');
    }
    
    isOffline = true;
    reconnectAttempts++;
    
    if (reconnectAttempts <= MAX_RECONNECT_ATTEMPTS) {
      console.log(`Reconnect attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS} in ${RECONNECT_INTERVAL/1000}s`);
    } else if (reconnectAttempts === MAX_RECONNECT_ATTEMPTS + 1) {
      console.log(`Maximum reconnection attempts reached. Continuing with dummy data.`);
    }
    
    return generateDummyData();
  }
}

// Format bytes to human-readable format
function formatBytes(bytes, decimals = 2) {
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
  const tableData = data.traffic_table || [];
  
  // Get filter values
  const searchTerm = document.getElementById('traffic-search')?.value?.toLowerCase() || '';
  const protocolFilter = document.getElementById('protocol-filter')?.value || 'all';
  
  // Clear existing rows first
  tbody.innerHTML = '';
  
  // Add filtered data
  tableData.slice(-50).reverse().forEach(entry => {
    // Apply filters
    if (searchTerm && 
        !entry.src_ip.toLowerCase().includes(searchTerm) && 
        !entry.dst_ip.toLowerCase().includes(searchTerm) && 
        !entry.protocol.toLowerCase().includes(searchTerm)) {
      return;
    }
    
    if (protocolFilter !== 'all' && entry.protocol !== protocolFilter) {
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
    
    // Add active class to clicked button
    button.addEventListener('click', () => {
      button.classList.add('active');
    });
    
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
    const incomingKbps = data.speed.incoming_kbps || 0;
    const outgoingKbps = data.speed.outgoing_kbps || 0;

    const incomingBps = Math.round((incomingKbps * 1000) / 8);
    const outgoingBps = Math.round((outgoingKbps * 1000) / 8);

    // Remove data points older than our time window
    const cutoffTime = now.getTime() - timeWindowMs;
    while (timeLabels.length > 0 && new Date(timeLabels[0]).getTime() < cutoffTime) {
      timeLabels.shift();
      incomingBytes.shift();
      outgoingBytes.shift();
    }

    // Add new data point
    const timeStr = now.toLocaleTimeString();
    timeLabels.push(timeStr);
    incomingBytes.push(incomingBps);
    outgoingBytes.push(outgoingBps);

    // Ensure we don't exceed maxPoints
    while (timeLabels.length > maxPoints) {
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

    // Update speedometers
    incomingGauge.data.datasets[0].data = [incomingKbps, Math.max(5000 - incomingKbps, 0)];
    outgoingGauge.data.datasets[0].data = [outgoingKbps, Math.max(5000 - outgoingKbps, 0)];

    incomingGauge.options.plugins.title.text = `Download Speed: ${incomingKbps} kbps`;
    outgoingGauge.options.plugins.title.text = `Upload Speed: ${outgoingKbps} kbps`;

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

// Initialize the update timer with the default interval
window.updateTimer = setInterval(updateCharts, updateInterval);

// Add logging to debug data flow
function debugDataFlow(data) {
  console.log("Debugging Data Flow:");
  console.log("Speed:", data.speed);
  console.log("Protocol Distribution:", data.protocol_distribution);
  console.log("Top IPs:", data.top_ips);
  console.log("Traffic Table:", data.traffic_table);
}

// Call debugDataFlow after fetching data
setInterval(async () => {
  const data = await fetchData();
  if (data) {
    debugDataFlow(data);
  }
}, 5000);

// Add a debug function to check DOM elements and charts
function debugCharts() {
  console.log("Traffic Chart:", trafficChart);
  console.log("Protocol Chart:", protocolChart);
  console.log("Bandwidth Chart:", topBandwidthChart);
  console.log("Incoming Gauge:", incomingGauge);
  console.log("Outgoing Gauge:", outgoingGauge);
  
  console.log("Traffic Chart Element:", document.getElementById('trafficChart'));
  console.log("Protocol Chart Element:", document.getElementById('protocolChart'));
  console.log("Bandwidth Chart Element:", document.getElementById('topBandwidthChart'));
  console.log("Incoming Speedo Element:", document.getElementById('incomingSpeedo'));
  console.log("Outgoing Speedo Element:", document.getElementById('outgoingSpeedo'));
}

// Run debug after initial page load
setTimeout(debugCharts, 3000);
