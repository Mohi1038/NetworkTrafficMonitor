// async function updateUI() {
//     const data = await window.api.fetchTraffic();
  
//     document.getElementById('speed').innerHTML = `
//       <h2>Speedometer</h2>
//       <p>Incoming: ${data.speedometer.incoming_speed} B/s</p>
//       <p>Outgoing: ${data.speedometer.outgoing_speed} B/s</p>`;
  
//     document.getElementById('area-chart').innerHTML = `
//       <h2>Area Chart</h2>
//       <p>Incoming: ${data.area_chart.incoming} B</p>
//       <p>Outgoing: ${data.area_chart.outgoing} B</p>`;
  
//     document.getElementById('top-devices').innerHTML = `
//       <h2>Top Devices</h2>
//       <ul>${data.top_devices.map(([ip, bytes]) => `<li>${ip}: ${bytes} B</li>`).join('')}</ul>`;
  
//     document.getElementById('protocols').innerHTML = `
//       <h2>Protocols</h2>
//       <ul>${Object.entries(data.protocol_distribution).map(([proto, bytes]) => `<li>${proto}: ${bytes} B</li>`).join('')}</ul>`;
  
//     document.getElementById('traffic-table').innerHTML = `
//       <h2>Detailed Traffic Table</h2>
//       <table border="1">
//         <tr><th>Source</th><th>Src Port</th><th>Destination</th><th>Dst Port</th><th>Protocol</th><th>Bytes</th><th>Packets</th></tr>
//         ${data.traffic_table.map(entry => `
//           <tr>
//             <td>${entry.src_ip}</td>
//             <td>${entry.src_port}</td>
//             <td>${entry.dst_ip}</td>
//             <td>${entry.dst_port}</td>
//             <td>${entry.protocol}</td>
//             <td>${entry.bytes}</td>
//             <td>${entry.packets}</td>
//           </tr>`).join('')}
//       </table>`;
//   }
  
//   setInterval(updateUI, 1000);
  


// // After JSon///
// const fetchData = async () => {
//   try {
//     const res = await fetch("http://localhost:5000/api/data");
//     const data = await res.json();

//     // Update speed
//     document.getElementById("incoming").innerText = data.speed.incoming_kbps;
//     document.getElementById("outgoing").innerText = data.speed.outgoing_kbps;

//     // Update charts
//     updateBarChart(data.top_ips);
//     updateProtoChart(data.protocol_distribution);

//     // Update table
//     const tbody = document.querySelector("#trafficTable tbody");
//     tbody.innerHTML = "";
//     data.traffic_table.slice(-20).reverse().forEach(entry => {
//       const row = `<tr>
//         <td>${entry.timestamp}</td>
//         <td>${entry.src_ip}</td>
//         <td>${entry.dst_ip}</td>
//         <td>${entry.dst_port}</td>
//         <td>${entry.protocol}</td>
//         <td>${entry.bytes}</td>
//       </tr>`;
//       tbody.innerHTML += row;
//     });
//   } catch (e) {
//     console.error("Failed to fetch data:", e);
//   }
// };

// let barChart, protoChart;

// function updateBarChart(data) {
//   const ctx = document.getElementById("barChart").getContext("2d");
//   const labels = Object.keys(data);
//   const values = Object.values(data);
//   if (barChart) barChart.destroy();
//   barChart = new Chart(ctx, {
//     type: "bar",
//     data: {
//       labels,
//       datasets: [{
//         label: "Top IPs (Bytes)",
//         data: values,
//         backgroundColor: "rgba(54, 162, 235, 0.7)"
//       }]
//     }
//   });
// }

// function updateProtoChart(data) {
//   const ctx = document.getElementById("protoChart").getContext("2d");
//   const labels = Object.keys(data);
//   const values = Object.values(data);
//   if (protoChart) protoChart.destroy();
//   protoChart = new Chart(ctx, {
//     type: "bar",
//     data: {
//       labels,
//       datasets: [{
//         label: "Protocols (Bytes)",
//         data: values,
//         backgroundColor: "rgba(255, 99, 132, 0.7)"
//       }]
//     }
//   });
// }

// // Poll every second
// setInterval(fetchData, 1000);


// ////traffic, speedometer////
const TRAFFIC_ENDPOINT = "http://127.0.0.1:5000/api/data";
const maxPoints = 100;

let timeLabels = [];
let incomingBytes = [];
let outgoingBytes = [];

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
        borderColor: 'blue',
        backgroundColor: 'rgba(0, 0, 255, 0.1)',
        fill: true,
        tension: 0.4
      },
      {
        label: 'Outgoing (Bytes/s)',
        data: outgoingBytes,
        borderColor: 'red',
        backgroundColor: 'rgba(255, 0, 0, 0.1)',
        fill: true,
        tension: 0.4
      }
    ]
  },
  options: {
    responsive: true,
    scales: {
      x: {
        title: { display: true, text: 'Time' }
      },
      y: {
        beginAtZero: true,
        title: { display: true, text: 'Bytes/s' }
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
      cutout: '75%',
      plugins: {
        tooltip: { enabled: false },
        legend: { display: false },
        title: {
          display: true,
          text: `${label}: 0 kbps`,
          padding: { top: 10, bottom: 0 },
          font: { size: 14 }
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

let bandwidthType = "incoming_bytes"; // default

document.getElementById("bandwidthToggle").addEventListener("change", (e) => {
  bandwidthType = e.target.value;
  fetchData();  // Trigger re-fetch to update chart
});

function renderTopBandwidthChart(data) {
  let topIps = data.top_ips || {};
  const labels = [];
  const values = [];

  topIps = sortTopIps(topIps,bandwidthType);
  let i=0;

  for (const ip in topIps) {
    const entry = topIps[ip];
    const name = entry.app || entry.hostname || ip;
    labels.push(`${name} (${ip})`);
    values.push(entry[bandwidthType] || 0);  // dynamically choose incoming/outgoing

    i++;
    if(i>5) break;
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
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: function(context) {
              return `${context.parsed.x} Bytes`;
            }
          }
        }
      },
      scales: {
        x: {
          title: {
            display: true,
            text: 'Bandwidth Usage (Bytes)'
          }
        },
        y: {
          title: {
            display: true,
            text: 'App / Hostname / IP'
          }
        }
      }
    }
  });
}

let protocolChart = null;

function renderProtocolChart(data) {
  const protocols = data.protocol_distribution || {};
  const labels = Object.keys(protocols);
  const values = Object.values(protocols);

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
      plugins: {
        legend: {
          position: "bottom"
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
          text: "Traffic Distribution by Protocol"
        }
      }
    }
  });
}


// INITIALIZE GAUGES
const incomingGauge = createSpeedometer('incomingSpeedo', 'Download Speed');
const outgoingGauge = createSpeedometer('outgoingSpeedo', 'Upload Speed');

// UPDATE DATA PERIODICALLY
setInterval(async () => {
  try {
    const res = await fetch(TRAFFIC_ENDPOINT);
    const data = await res.json();

    const now = new Date().toLocaleTimeString();

    const incomingKbps = data.speed.incoming_kbps || 0;
    const outgoingKbps = data.speed.outgoing_kbps || 0;

    const incomingBps = Math.round((incomingKbps * 1000) / 8);
    const outgoingBps = Math.round((outgoingKbps * 1000) / 8);

    if (timeLabels.length >= maxPoints) {
      timeLabels.shift();
      incomingBytes.shift();
      outgoingBytes.shift();
    }

    timeLabels.push(now);
    incomingBytes.push(incomingBps);
    outgoingBytes.push(outgoingBps);

    trafficChart.update();

    // Update speedometers
    incomingGauge.data.datasets[0].data = [incomingKbps, Math.max(5000 - incomingKbps, 0)];
    outgoingGauge.data.datasets[0].data = [outgoingKbps, Math.max(5000 - outgoingKbps, 0)];

    incomingGauge.options.plugins.title.text = `Download Speed: ${incomingKbps} kbps`;
    outgoingGauge.options.plugins.title.text = `Upload Speed: ${outgoingKbps} kbps`;

    incomingGauge.update();
    outgoingGauge.update();

    renderProtocolChart(data);
    renderTopBandwidthChart(data);
  } catch (err) {
    console.error("Error fetching network data:", err);
  }
}, 2000);
