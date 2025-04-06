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
const API_URL = "http://localhost:5000/api/data";

// Initialize Chart instances
let barChart, protoChart;

// Fetch and update UI every second
setInterval(fetchData, 1000);

async function fetchData() {
  try {
    const response = await fetch(API_URL);
    const data = await response.json();

    updateSpeed(data.speed);
    updateBarChart(data.top_ips);
    updateProtoChart(data.protocol_distribution);
    updateTrafficTable(data.traffic_table);
  } catch (error) {
    console.error("Error fetching data:", error);
  }
}

function updateSpeed(speed) {
  document.getElementById("incoming").innerText = speed.incoming_kbps;
  document.getElementById("outgoing").innerText = speed.outgoing_kbps;
}

function updateBarChart(topIps) {
  const ctx = document.getElementById("barChart").getContext("2d");
  const labels = Object.keys(topIps);
  const values = Object.values(topIps);

  if (barChart) barChart.destroy();
  barChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Top IPs (Bytes)",
        data: values,
        backgroundColor: "rgba(54, 162, 235, 0.7)"
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: { display: false }
      }
    }
  });
}

function updateProtoChart(protoData) {
  const ctx = document.getElementById("protoChart").getContext("2d");
  const labels = Object.keys(protoData);
  const values = Object.values(protoData);

  if (protoChart) protoChart.destroy();
  protoChart = new Chart(ctx, {
    type: "doughnut",
    data: {
      labels,
      datasets: [{
        label: "Protocol Distribution",
        data: values,
        backgroundColor: [
          "rgba(255, 99, 132, 0.6)",
          "rgba(255, 159, 64, 0.6)",
          "rgba(255, 205, 86, 0.6)",
          "rgba(75, 192, 192, 0.6)",
          "rgba(54, 162, 235, 0.6)",
          "rgba(153, 102, 255, 0.6)"
        ]
      }]
    },
    options: {
      responsive: true,
      plugins: {
        legend: {
          position: "bottom"
        }
      }
    }
  });
}

function updateTrafficTable(entries) {
  const tbody = document.querySelector("#trafficTable tbody");
  tbody.innerHTML = "";

  entries.slice(-20).reverse().forEach(entry => {
    const row = document.createElement("tr");
    row.innerHTML = `
      <td>${entry.timestamp}</td>
      <td>${entry.src_ip}</td>
      <td>${entry.dst_ip}</td>
      <td>${entry.dst_port}</td>
      <td>${entry.protocol}</td>
      <td>${entry.bytes}</td>
    `;
    tbody.appendChild(row);
  });
}
