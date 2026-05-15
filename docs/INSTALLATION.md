# Installation Guide - Network Traffic Monitor

Complete step-by-step installation instructions for Windows, macOS, and Linux.

## Table of Contents
- [Windows Installation](#windows-installation)
- [macOS Installation](#macos-installation)
- [Linux Installation](#linux-installation)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

---

## Windows Installation

### Step 1: Install Python
1. Download Python 3.10+ from https://www.python.org/downloads/
2. **Important**: Check "Add Python to PATH" during installation
3. Verify installation:
   ```cmd
   python --version
   ```

### Step 2: Install Node.js
1. Download Node.js LTS from https://nodejs.org/
2. Run the installer and follow defaults
3. Verify installation:
   ```cmd
   node --version
   npm --version
   ```

### Step 3: Install Npcap (Required for packet capture)
1. Download Npcap from https://nmap.org/npcap/
2. Run installer
3. **Important**: Enable "WinPcap API compatibility" in the installer
4. Restart your computer

### Step 4: Run the Application
1. Open Command Prompt (cmd.exe)
2. Navigate to the project folder:
   ```cmd
   cd C:\path\to\NetworkTrafficMonitor
   ```
3. Run the launcher:
   ```cmd
   run_network_monitor.bat
   ```

The script will:
- Create Python virtual environment
- Install all dependencies
- Prompt for Administrator privileges
- Start backend and frontend automatically

### Troubleshooting Windows

**"Python is not recognized"**
- Reinstall Python with "Add Python to PATH" checked
- Or add Python manually: Control Panel → System → Environment Variables

**"npm: command not found"**
- Restart your computer after installing Node.js
- Check if Node.js is added to PATH

**"Npcap: Cannot open adapter"**
- Run Command Prompt as Administrator
- Run launcher again

---

## macOS Installation

### Step 1: Install Homebrew (if not already installed)
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Step 2: Install Python
```bash
brew install python@3.10
python3 --version
```

### Step 3: Install Node.js
```bash
brew install node
node --version
npm --version
```

### Step 4: Install libpcap
```bash
brew install libpcap
```

### Step 5: Clone or Download the Project
```bash
cd ~/Desktop
git clone <repository-url> NetworkTrafficMonitor
# OR download and extract ZIP file
cd NetworkTrafficMonitor
```

### Step 6: Run the Application
```bash
chmod +x run_network_monitor.sh
./run_network_monitor.sh
```

You may be prompted for your password (required for packet capture).

### Troubleshooting macOS

**"Permission denied" error**
```bash
# Make script executable
chmod +x run_network_monitor.sh

# Run with sudo if needed
sudo ./run_network_monitor.sh
```

**"libpcap not found"**
```bash
brew install libpcap
```

**"Command not found: python3"**
```bash
# Install via Homebrew
brew install python@3.11

# Or download from python.org
```

---

## Linux Installation

### Ubuntu/Debian

#### Step 1: Update System
```bash
sudo apt-get update
sudo apt-get upgrade
```

#### Step 2: Install Python
```bash
sudo apt-get install python3 python3-pip python3-venv
python3 --version
```

#### Step 3: Install Node.js
```bash
# Using NodeSource repository (recommended)
curl -fsSL https://deb.nodesource.com/setup_18.x | sudo -E bash -
sudo apt-get install -y nodejs

# Verify
node --version
npm --version
```

#### Step 4: Install System Dependencies
```bash
# For packet capture
sudo apt-get install libpcap-dev

# For building Python packages
sudo apt-get install build-essential python3-dev
```

#### Step 5: Download and Setup
```bash
cd ~
# Download from GitHub or unzip file
cd NetworkTrafficMonitor
chmod +x run_network_monitor.sh
```

#### Step 6: Run the Application
```bash
sudo ./run_network_monitor.sh
```

You will be prompted for your password (required for packet capture).

### Fedora/RHEL/CentOS

```bash
# Install Python
sudo dnf install python3 python3-pip python3-devel

# Install Node.js
sudo dnf install nodejs npm

# Install system dependencies
sudo dnf install libpcap-devel gcc

# Run application
cd NetworkTrafficMonitor
chmod +x run_network_monitor.sh
sudo ./run_network_monitor.sh
```

### Troubleshooting Linux

**"Permission denied"**
```bash
# Make launcher executable
chmod +x run_network_monitor.sh

# Run with sudo
sudo ./run_network_monitor.sh
```

**"libpcap not found"**
```bash
# Ubuntu/Debian
sudo apt-get install libpcap-dev

# Fedora/CentOS
sudo dnf install libpcap-devel
```

**"python3: command not found"**
```bash
# Ubuntu/Debian
sudo apt-get install python3

# Fedora
sudo dnf install python3
```

---

## Verification

### Verify Setup

Run the setup verification script:

```bash
# macOS/Linux
python3 setup_verify.py

# Windows
python setup_verify.py
```

This will check:
- ✓ Python version
- ✓ Node.js and npm
- ✓ System libraries (libpcap)
- ✓ Directory structure
- ✓ ML model files
- ✓ Configuration files
- ✓ Network ports availability

### Manual Verification

1. **Check Python:**
   ```bash
   python3 --version  # Should be 3.8+
   ```

2. **Check Node.js:**
   ```bash
   node --version    # Should be 14+
   npm --version
   ```

3. **Check Ports:**
   ```bash
   # Check if port 5000 is available
   # macOS/Linux
   lsof -i :5000
   
   # Windows
   netstat -ano | findstr :5000
   ```

---

## Configuration

### 1. Environment Variables
Copy example to create your config:
```bash
cp .env.example .env
```

Edit `.env` and customize:
```bash
# Backend settings
FLASK_PORT=5000
FLASK_DEBUG=False

# Email alerts (optional)
ALERT_EMAIL_SENDER=your-email@gmail.com
ALERT_EMAIL_RECEIVER=recipient@example.com
ALERT_EMAIL_PASSWORD=your-app-password

# ML settings
ML_MODEL_ENABLED=True
ML_ANOMALY_THRESHOLD=0.5
```

### 2. Email Setup (Optional)

To enable email alerts:

1. **Gmail Users:**
   - Enable 2-Factor Authentication: https://myaccount.google.com/security
   - Generate App Password: https://myaccount.google.com/apppasswords
   - Copy the 16-character password

2. **Update `.env`:**
   ```
   ALERT_EMAIL_SENDER=your-email@gmail.com
   ALERT_EMAIL_RECEIVER=alert-recipient@example.com
   ALERT_EMAIL_PASSWORD=xxxx xxxx xxxx xxxx
   ```

3. **Restart backend** for changes to take effect

---

## Troubleshooting

### General Issues

**Port Already in Use**
```bash
# Find what's using the port
# macOS/Linux
lsof -i :5000

# Windows
netstat -ano | findstr :5000

# Kill the process (use PID from above)
# macOS/Linux
kill -9 <PID>

# Windows
taskkill /PID <PID> /F
```

**Backend won't start**
```bash
# Check if running with proper privileges
# macOS/Linux - try with sudo
sudo python3 backend/app2.py

# Windows - run as Administrator
```

**Frontend won't load**
```bash
cd frontend
# Clear cache and reinstall
rm -rf node_modules package-lock.json
npm install
npm start
```

**Packet capture not working**

This requires elevated privileges:
- **macOS/Linux**: Must run with `sudo`
- **Windows**: Must run as Administrator

```bash
# macOS/Linux
sudo ./run_network_monitor.sh

# Windows
# Right-click run_network_monitor.bat → "Run as administrator"
```

### Platform-Specific

**macOS: "System Extension blocked"**
- Open System Preferences → Security & Privacy
- Allow system extensions if prompted
- Restart if needed

**Linux: "Permission denied" for network interface**
```bash
# Grant packet capture permissions without sudo
sudo setcap cap_net_raw,cap_net_admin=eip /usr/bin/python3.10
```

**Windows: "Npcap: Cannot open adapter"**
- Verify Npcap installed with WinPcap compatibility
- Reinstall Npcap from https://nmap.org/npcap/
- Run as Administrator

### Getting More Help

1. Check the application logs:
   ```bash
   # macOS/Linux
   tail -f /tmp/ntm_backend.log
   
   # Windows
   # Check command prompt window for error messages
   ```

2. Check browser console (F12):
   - Frontend errors appear here

3. Read full documentation:
   - [README.md](README.md) - Complete documentation
   - [QUICKSTART.md](QUICKSTART.md) - Quick start guide

---

## Next Steps

1. **Configure Email Alerts** (optional)
   - See [Configuration](#configuration) section

2. **Adjust Settings**
   - Open Settings tab in application
   - Configure update interval and thresholds

3. **Monitor Your Network**
   - Check Dashboard for traffic overview
   - Use Traffic Details for packet inspection

4. **Review Security Alerts**
   - ML model will flag suspicious activity
   - Check email for alerts (if configured)

---

**Installation complete! Enjoy monitoring your network. 🎉**

For issues, check:
- README.md - Full documentation
- QUICKSTART.md - Quick start guide
- Application logs - Debug information
