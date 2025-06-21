# Network Traffic Monitor 

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/Python-3.8%2B-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20Linux-lightgrey.svg)]()

![Network Traffic Monitor Dashboard](./docs/image_demo.png)

> Enterprise-grade network monitoring solution with real-time analytics and machine learning-powered threat detection

## 🔍 Overview

The Network Traffic Monitor is a comprehensive solution for real-time network analysis, providing:
- Live traffic visualization and protocol breakdowns
- Bandwidth consumption monitoring by application/IP
- Machine learning-based intrusion detection system
- Alerting for suspicious network activities

## ✨ Key Features

| Feature | Description |
|---------|-------------|
|  Real-time Visualization | Interactive dashboards showing live network traffic |
|  Protocol Analytics | Detailed breakdown by protocol (TCP/UDP/ICMP etc.) |
|  Traffic Filtering | Advanced filtering of captured packets |
|  Performance Metrics | Download/upload speed monitoring |
|  Threat Detection | ML-powered anomaly detection |
|  Alert System | Notifications for suspicious activities |

## 🛠️ Technical Stack

### Backend
- **Core**: Python 3.8+
- **Frameworks**: Flask (API server)
- **Networking**: Scapy, Npcap (Windows)
- **ML**: scikit-learn, joblib (model persistence)
- **Utilities**: psutil, pandas, NumPy

### Frontend
- **Framework**: Electron.js
- **Visualization**: Chart.js
- **UI**: HTML5, CSS3

## 🚀 Installation Guide

### Prerequisites

```bash
# System Requirements
- OS: Windows 10/11 (64-bit) or Linux
- RAM: 4GB minimum (8GB recommended)
- Storage: 500MB available space
- Admin/root privileges required
```

## Step-By-Step Setup

### 1. Clone the repository
```bash
git clone https://github.com/tacticalYP/NetworkTrafficMonitor.git
cd NetworkTrafficMonitor
```

### 2. Install Npcap (Windows only)
Download and install Npcap from [https://npcap.com/](https://npcap.com/)

### 3. Install Python dependencies
```bash
pip install flask scapy numpy pandas joblib psutil
```
or 
```bash
pip install -r backend/requirements.txt
```

### 4. Install frontend dependencies
```bash
cd frontend
npm install
```

## Running the Application

### Option 1: Quick Start (Recommended)
1. Simply double-click the `run_network_monitor.bat` file in the root directory.
2. This will automatically:
   - Start the backend server with administrator privileges
   - Wait for the backend to initialize
   - Launch the frontend application

### Option 2: Manual Startup
If you prefer to start components individually:

#### 1. Start the backend server (with administrator privileges)
Open a command prompt as Administrator and run:

```bash
cd backend
python app2.py
```

#### 2. Start the frontend application
In a new terminal window:

```bash
cd frontend
npm start
```

The application should automatically open in a new window.

## Project Structure

```
NetworkTrafficMonitor/
├── backend/
│   ├── app.py              # Legacy Flask server
│   ├── app2.py             # Current Flask server with ML integration
│   ├── traffic_analyzer.py # Network traffic analysis
│   ├── pack_sniffer.py     # Packet capture and processing
│   ├── utils.py            # Utility functions
│   └── ml_model/           # Machine learning models for threat detection
├── frontend/
│   ├── index.html          # Main UI
│   ├── style.css           # Styling
│   ├── renderer.js         # Charts and UI logic
│   ├── main.js             # Electron main process
│   └── package.json        # Node.js dependencies
└── README.md
```

## Machine Learning Integration
Our threat detection system utilizes:

- Supervised learning models for known attack patterns
- Anomaly detection algorithms for zero-day threats
- Continuous learning from network behavior
- Model artifacts are stored in backend/ml_model/ with:

- Pre-trained classifiers
- Feature extraction pipelines
- Model evaluation metrics



## Troubleshooting

### Backend Issues
- Ensure you're running with administrator privileges.
- Verify Npcap is installed correctly.
- Check firewall settings if capturing packets fails.

### Frontend Issues
- If charts aren't displaying, check browser console for errors.
- Try clearing browser cache if UI elements are missing.

## License

This project is licensed under the MIT License.

## Acknowledgements

- Chart.js for visualization
- Scapy for packet manipulation
- Electron for desktop application framework
