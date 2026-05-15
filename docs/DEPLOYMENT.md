# Deployment Guide

This guide covers:
1. **Building & Packaging** the Electron desktop app for Windows, macOS, and Linux
2. **Deploying the Backend** to Render (cloud platform)

---

## Part 1: Building Electron App for All Platforms

### Prerequisites
- Node.js 16+ installed
- npm or yarn package manager
- Python (for backend dependencies)

### Step 1: Install electron-builder

```bash
cd /Users/mohi1038/Desktop/NetworkTrafficMonitor/frontend
npm install electron-builder --save-dev
```

### Step 2: Build for All Platforms

**Build for Current Platform:**
```bash
npm run build
```

**Build for Specific Platform:**
```bash
# Windows (NSIS installer + portable exe)
npm run build-win

# macOS (DMG + ZIP)
npm run build-mac

# Linux (AppImage + DEB package)
npm run build-linux

# All Platforms at Once
npm run build-all
```

### Step 3: Output Locations

Built packages will be in `frontend/dist/`:

```
dist/
├── Network Traffic Monitor Setup 1.0.0.exe  (Windows installer)
├── Network Traffic Monitor 1.0.0.exe        (Windows portable)
├── Network Traffic Monitor-1.0.0.dmg        (macOS disk image)
├── Network Traffic Monitor-1.0.0.zip        (macOS zip)
├── network-traffic-monitor-1.0.0.AppImage  (Linux AppImage)
└── network-traffic-monitor-1.0.0.deb       (Linux Debian package)
```

### Step 4: Distribution

**Windows Users:**
- Can install using the `.exe` installer or run the portable `.exe` directly

**macOS Users:**
- Mount the `.dmg` file and drag app to Applications folder
- Or extract and use the `.zip` file

**Linux Users:**
- Install `.deb` package: `sudo dpkg -i network-traffic-monitor-*.deb`
- Or run `.AppImage` directly: `./network-traffic-monitor-*.AppImage`

---

## Part 2: Deploy Backend to Render

### Overview
Render is a free cloud platform for deploying web services. Your Flask backend will run on Render servers.

### Step 1: Prepare Backend for Render

Create a `Procfile` in the backend directory:

```bash
cat > /Users/mohi1038/Desktop/NetworkTrafficMonitor/Procfile << 'EOF'
web: cd backend && gunicorn --bind 0.0.0.0:$PORT app2:app
EOF
```

Create `runtime.txt` to specify Python version:

```bash
cat > /Users/mohi1038/Desktop/NetworkTrafficMonitor/runtime.txt << 'EOF'
python-3.11.0
EOF
```

### Step 2: Update requirements.txt for Production

```bash
cat > /Users/mohi1038/Desktop/NetworkTrafficMonitor/backend/requirements.txt << 'EOF'
Flask==2.3.0
flask-cors==4.0.0
scapy==2.5.0
pandas==2.0.0
scikit-learn==1.3.0
numpy==1.24.0
requests==2.31.0
python-dotenv==1.0.0
gunicorn==21.0.0
geolite2==2023.4
maxminddb-geolite2-reader==2023.4
geoip2==4.8.0
EOF
```

Install locally:
```bash
cd /Users/mohi1038/Desktop/NetworkTrafficMonitor/backend
pip install -r requirements.txt
```

### Step 3: Create GitHub Repository (if not already done)

```bash
cd /Users/mohi1038/Desktop/NetworkTrafficMonitor
git remote -v  # Check if already added
# If needed: git remote add origin https://github.com/Mohi1038/NetworkTrafficMonitor.git
git push origin main
```

### Step 4: Deploy to Render

1. **Go to Render Dashboard:** https://dashboard.render.com/
2. **Sign up** (free account)
3. **Create New Web Service:**
   - Click "New +" → "Web Service"
   - Connect your GitHub account
   - Select `NetworkTrafficMonitor` repository
   - Branch: `main`

4. **Configure:**
   - **Name:** `network-traffic-monitor-api`
   - **Runtime:** Python 3
   - **Build Command:** `pip install -r backend/requirements.txt`
   - **Start Command:** `cd backend && gunicorn --bind 0.0.0.0:$PORT app2:app`
   - **Environment Variables:** Add these:
     ```
     ALERT_EMAIL_SENDER=your-email@gmail.com
     ALERT_EMAIL_PASSWORD=your-app-password
     ALERT_SMTP_HOST=smtp.gmail.com
     ALERT_SMTP_PORT=465
     ALERT_SMTP_USER=your-email@gmail.com
     ALERT_SMTP_SSL=True
     FLASK_DEBUG=False
     ```

5. **Deploy:** Click "Create Web Service"
   - Wait 2-3 minutes for build and deployment
   - Get your URL: `https://network-traffic-monitor-api-xxxxx.onrender.com`

### Step 5: Update Frontend to Connect to Render

Edit `frontend/renderer.js`:

```javascript
// Change this:
const API_BASE_URL = 'http://127.0.0.1:5000';

// To this (use your Render URL):
const API_BASE_URL = 'https://network-traffic-monitor-api-xxxxx.onrender.com';
```

Rebuild your Electron app:
```bash
cd /Users/mohi1038/Desktop/NetworkTrafficMonitor/frontend
npm run build-all
```

### Step 6: Test the Backend

Check if backend is running:
```bash
curl https://network-traffic-monitor-api-xxxxx.onrender.com/api/data
```

---

## Complete Deployment Workflow

### 1. Build Desktop App (for local/offline use)
```bash
cd frontend
npm install electron-builder --save-dev
npm run build-all
# Packages in: frontend/dist/
```

### 2. Deploy Backend (cloud)
```bash
# Ensure .env has all vars set
# Push to GitHub
git push origin main

# On Render dashboard: Deploy (auto-deploys from GitHub)
```

### 3. Update Frontend to Use Cloud Backend
```bash
# Edit frontend/renderer.js with Render URL
npm run build-all  # Rebuild with new backend URL
```

### 4. Distribute
- **Windows:** Share `.exe` installer
- **macOS:** Share `.dmg` file
- **Linux:** Share `.AppImage` or `.deb`
- **Web:** (Optional) Deploy frontend to Vercel/Netlify as SPA

---

## Troubleshooting

### Build fails on macOS
```bash
# Install Python 3 build tools
xcode-select --install
```

### Build fails on Windows
```bash
# Install Visual Studio Build Tools
# Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
```

### Render deployment fails
- Check build logs in Render dashboard
- Verify Python dependencies in `requirements.txt`
- Ensure all env vars are set in Render settings
- Check if port binding is correct (Render uses `$PORT` env var)

### Frontend can't reach backend
- Verify Render URL is correct in `renderer.js`
- Check CORS is enabled in Flask (`flask-cors` is installed)
- Test API: `curl https://your-render-url/api/data`

---

## Environment Variables for Render

Set these in Render dashboard → Settings → Environment Variables:

```
ALERT_EMAIL_SENDER=your-email@gmail.com
ALERT_EMAIL_PASSWORD=your-16-char-app-password
ALERT_SMTP_HOST=smtp.gmail.com
ALERT_SMTP_PORT=465
ALERT_SMTP_USER=your-email@gmail.com
ALERT_SMTP_SSL=True
FLASK_DEBUG=False
FLASK_ENV=production
```

---

## Cost Breakdown

- **Electron App:** Free (distributable)
- **Render Backend:** Free tier available
  - 750 hours/month free
  - Auto-sleep after 15 mins inactivity
  - Paid tiers start at $7/month for always-on

---

## Alternative Deployment Platforms

If you prefer other platforms:
- **Heroku:** Similar to Render (paid)
- **AWS:** More complex, powerful
- **Railway:** Simple, pay-as-you-go
- **DigitalOcean App Platform:** $12/month starting

---

## Next Steps

1. Build Electron app:
   ```bash
   cd frontend && npm run build-all
   ```

2. Deploy backend to Render (instructions above)

3. Update frontend with Render URL

4. Rebuild Electron app with new backend URL

5. Distribute packages to users!

Need help with any step? Let me know!
