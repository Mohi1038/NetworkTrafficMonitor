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
const fetchData = async () => {
  try {
    const res = await fetch("http://localhost:5000/api/data");
    const data = await res.json();

    // Update speed
    document.getElementById("incoming").innerText = data.speed.incoming_kbps;
    document.getElementById("outgoing").innerText = data.speed.outgoing_kbps;

    // Update charts
    updateBarChart(data.top_ips);
    updateProtoChart(data.protocol_distribution);

    // Update table
    const tbody = document.querySelector("#trafficTable tbody");
    tbody.innerHTML = "";
    data.traffic_table.slice(-20).reverse().forEach(entry => {
      const row = `<tr>
        <td>${entry.timestamp}</td>
        <td>${entry.src_ip}</td>
        <td>${entry.dst_ip}</td>
        <td>${entry.dst_port}</td>
        <td>${entry.protocol}</td>
        <td>${entry.bytes}</td>
      </tr>`;
      tbody.innerHTML += row;
    });
  } catch (e) {
    console.error("Failed to fetch data:", e);
  }
};

let barChart, protoChart;

function updateBarChart(data) {
  const ctx = document.getElementById("barChart").getContext("2d");
  const labels = Object.keys(data);
  const values = Object.values(data);
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
    }
  });
}

function updateProtoChart(data) {
  const ctx = document.getElementById("protoChart").getContext("2d");
  const labels = Object.keys(data);
  const values = Object.values(data);
  if (protoChart) protoChart.destroy();
  protoChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels,
      datasets: [{
        label: "Protocols (Bytes)",
        data: values,
        backgroundColor: "rgba(255, 99, 132, 0.7)"
      }]
    }
  });
}

// Poll every second
setInterval(fetchData, 1000);
