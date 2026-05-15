# Quick Render Deployment Guide

## 5-Minute Setup

### Step 1: Create Render Account
- Go to https://render.com
- Sign up (free)
- Connect GitHub

### Step 2: Create Web Service on Render
1. Click **"New +" → "Web Service"**
2. Select **NetworkTrafficMonitor** repository
3. Choose branch: **main**

### Step 3: Configure Service
```
Name:                 network-traffic-monitor-api
Environment:          Python 3
Region:               Choose closest to you
Build Command:        pip install -r backend/requirements.txt
Start Command:        cd backend && gunicorn --bind 0.0.0.0:$PORT app2:app
```

### Step 4: Set Environment Variables
Click **"Environment"** and add:

```
ALERT_EMAIL_SENDER        = your-email@gmail.com
ALERT_EMAIL_PASSWORD      = your-app-password
ALERT_SMTP_HOST          = smtp.gmail.com
ALERT_SMTP_PORT          = 465
ALERT_SMTP_USER          = your-email@gmail.com
ALERT_SMTP_SSL           = True
FLASK_DEBUG              = False
```

### Step 5: Deploy
- Click **"Create Web Service"**
- Wait 2-3 minutes
- Get your URL: `https://network-traffic-monitor-api-xxxxx.onrender.com`

### Step 6: Use in Electron App
Edit `frontend/renderer.js` - find this line:
```javascript
const API_BASE_URL = 'http://127.0.0.1:5000';
```

Change to:
```javascript
const API_BASE_URL = 'https://network-traffic-monitor-api-xxxxx.onrender.com';
```

Then rebuild:
```bash
cd frontend
npm run build-all
```

---

## Test Your Backend

```bash
curl https://network-traffic-monitor-api-xxxxx.onrender.com/api/data
```

Should return JSON traffic data.

---

## Common Issues

| Problem | Solution |
|---------|----------|
| Build fails | Check `requirements.txt` has all packages |
| API returns 502 | Wait 2 mins, check Render logs |
| "Module not found" | Make sure all imports exist in `requirements.txt` |
| No email alerts | Verify env vars are set in Render dashboard |

---

## Costs
- **Free Tier:** 750 hours/month (enough for hobby use)
- **Auto-sleep:** App sleeps after 15 mins inactivity
- **Paid:** $7+/month for always-on

---

## More Help
- [Render Docs](https://render.com/docs)
- [Deploying Python Apps](https://render.com/docs/deploy-flask)
- [GitHub Integration](https://render.com/docs/github)
