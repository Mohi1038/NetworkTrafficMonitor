# Network Traffic Monitor - Quick Start Guide

## ⚡ Quick Start (5 minutes)

### Prerequisites Check
```bash
# Check Python version (need 3.8+)
python3 --version

# Check Node.js version (need 14+)
node --version
```

### macOS / Linux
```bash
# Navigate to project directory
cd NetworkTrafficMonitor

# Make launcher executable
chmod +x run_network_monitor.sh

# Run the application
./run_network_monitor.sh
```

The script will automatically:
- Create a Python virtual environment
- Install all Python dependencies
- Install Node.js dependencies
- Start the backend server (with sudo if needed)
- Launch the Electron frontend

### Windows
```bash
# Navigate to project directory
cd NetworkTrafficMonitor

# Run the launcher
run_network_monitor.bat
```

The batch file will automatically:
- Create a Python virtual environment
- Install all Python dependencies
- Install Node.js dependencies
- Start the backend with admin privileges
- Launch the Electron frontend

## 🖥️ Manual Start (If automated script fails)

### Terminal 1 - Start Backend
```bash
cd backend

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
sudo python3 app2.py  # Note: sudo required for packet capture on Linux/macOS

# Windows (run as Administrator)
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app2.py
```

### Terminal 2 - Start Frontend
```bash
cd frontend
npm install
npm start
```

## 📊 What You'll See

1. **Flask Backend** starts on port 5000
2. **Electron App** opens automatically
3. **Network Dashboard** shows:
   - Real-time traffic graphs
   - Protocol distribution
   - Top bandwidth consumers
   - Packet details table

## 🚨 Troubleshooting

### "Permission denied" or "Packet capture failed"
**Problem**: Backend can't capture packets
```bash
# macOS/Linux - Re-run with proper privileges
sudo python3 app2.py

# Windows - Run terminal as Administrator
# Right-click cmd.exe → "Run as administrator"
```

### "Port 5000 already in use"
```bash
# macOS/Linux - Kill the process
lsof -i :5000
kill -9 <PID>

# Windows - Find and end the process
netstat -ano | findstr :5000
taskkill /PID <PID> /F
```

### Frontend won't load
```bash
# Clear npm cache and reinstall
cd frontend
rm -rf node_modules package-lock.json
npm install
npm start
```

### Backend won't connect
1. Check backend is running: `http://localhost:5000/api/health`
2. Wait 5-10 seconds for backend to initialize
3. Try refreshing the Electron app (Ctrl+R or Cmd+R)

## 🔧 Configuration

Edit `.env` file for advanced settings:

```bash
# Backend settings
FLASK_PORT=5000           # Change backend port
FLASK_DEBUG=False         # Enable debug mode (False for production)

# Email alerts (optional)
ALERT_EMAIL_SENDER=       # Your Gmail address
ALERT_EMAIL_RECEIVER=     # Recipient email
ALERT_EMAIL_PASSWORD=     # Gmail App Password (not your password!)

# ML Settings
ML_MODEL_ENABLED=True     # Enable/disable AI threat detection
ML_ANOMALY_THRESHOLD=0.5  # Sensitivity (0.0-1.0)
```

## 📚 API Endpoints

### Get Network Traffic Data
```bash
curl http://localhost:5000/api/data
```

Response includes:
- Total incoming/outgoing bytes
- Current speeds (kbps)
- Protocol distribution
- Top IPs and connections
- Recent packet details

### Health Check
```bash
curl http://localhost:5000/api/health
```

Response:
```json
{"status": "ok", "message": "Backend is running"}
```

## 🎯 Features

- ✅ Real-time network traffic monitoring
- ✅ Protocol analysis (TCP, UDP, ICMP, DNS, HTTP/HTTPS)
- ✅ Bandwidth monitoring by application/IP
- ✅ ML-based threat detection
- ✅ Email alerts for suspicious activity
- ✅ Cross-platform (Windows, macOS, Linux)
- ✅ Interactive dashboards with Chart.js
- ✅ Packet-level detail view

## 🎓 Understanding the Data

### Speed Section
- **Download Speed**: Incoming data rate (kbps)
- **Upload Speed**: Outgoing data rate (kbps)

### Protocol Distribution
Shows breakdown of all network protocols detected:
- TCP/UDP: Connection-oriented protocols
- HTTP/HTTPS: Web traffic
- DNS: Domain name resolution
- Others: ARP, IPv6, etc.

### Top Bandwidth Consumers
Lists applications and IPs using most bandwidth
- Can toggle between "Incoming" and "Outgoing"
- Shows hostname, app name, and total bytes

### Traffic Details Table
Real-time packet information:
- Source/destination IP and port
- Protocol type
- Packet size
- Timestamp

## 🤖 ML Threat Detection

The app includes a pre-trained Random Forest model that:
- Analyzes network flow patterns
- Detects anomalous behavior
- Triggers alerts when threats are detected
- Can be configured for sensitivity

To enable email alerts:
1. Set up Gmail App Password in `.env`
2. Restart backend
3. Alerts will be sent when anomalies detected

## 📁 Project Structure

```
NetworkTrafficMonitor/
├── backend/                 # Flask API server
│   ├── app2.py             # Main Flask app
│   ├── packet_sniffer.py   # Packet capture
│   ├── traffic_analyzer.py # Traffic stats
│   ├── alert_mail.py       # Email alerts
│   ├── ml_models/          # ML models
│   ├── venv/               # Virtual env (created on install)
│   └── requirements.txt    # Python dependencies
├── frontend/               # Electron app
│   ├── main.js            # Electron main process
│   ├── preload.js         # Electron preload
│   ├── renderer.js        # Frontend logic
│   ├── index.html         # Main UI
│   ├── style.css          # Styling
│   └── package.json       # Node dependencies
├── .env                   # Your configuration
├── .env.example          # Example config
├── run_network_monitor.sh # Linux/macOS launcher
├── run_network_monitor.bat # Windows launcher
└── README.md             # Full documentation
```

## 💡 Tips & Tricks

1. **High CPU Usage?**
   - Reduce update frequency in Settings tab
   - Disable ML threat detection if not needed

2. **Bandwidth Spikes?**
   - Check "Top Bandwidth" section for culprits
   - Filter traffic table to investigate

3. **Testing ML Detection?**
   - Simulate unusual traffic patterns
   - Model trained on NSL-KDD dataset
   - Can detect various network anomalies

4. **Analyzing Specific IPs?**
   - Use search box in Traffic Details tab
   - Can filter by IP, protocol, or port

## 📞 Getting Help

1. **Check logs**:
   ```bash
   # Backend logs
   tail -f /tmp/ntm_backend.log  # macOS/Linux
   
   # Frontend: Check browser console (F12)
   ```

2. **Verify connectivity**:
   ```bash
   curl http://localhost:5000/api/health
   ```

3. **Common issues**: See README.md Troubleshooting section

## 🚀 Next Steps

- Configure email alerts in `.env`
- Adjust ML sensitivity for your network
- Set up monitoring dashboard
- Review traffic patterns over time
- Create custom filters for investigation

---

**Enjoy monitoring your network! 🎉**
