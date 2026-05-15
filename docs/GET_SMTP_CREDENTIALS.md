# How to Get SMTP Credentials for Email Alerts

## Gmail (Recommended & Free)

### Step 1: Enable 2-Factor Authentication

1. Go to [Google Account](https://myaccount.google.com/)
2. Click **Security** (left sidebar)
3. Under "How you sign in to Google", click **2-Step Verification**
4. Follow the steps to enable it

### Step 2: Generate App Password

1. Go to [App Passwords](https://myaccount.google.com/apppasswords)
2. You'll see a dropdown for **Select app** and **Select device**
   - **Select app**: Choose **Mail**
   - **Select device**: Choose **Windows Computer** (or your device type)
3. Click **Generate**
4. Google will show you a **16-character password** like: `abcd efgh ijkl mnop`
5. **Copy this password** (you'll need it)

### Step 3: Use in Network Monitor

```bash
ALERT_EMAIL_SENDER=your-email@gmail.com
ALERT_EMAIL_PASSWORD=abcd efgh ijkl mnop
ALERT_SMTP_HOST=smtp.gmail.com
ALERT_SMTP_PORT=465
ALERT_SMTP_USER=your-email@gmail.com
ALERT_SMTP_SSL=True
```

---

## Outlook / Office365

### Credentials

```bash
ALERT_EMAIL_SENDER=your-email@outlook.com
ALERT_EMAIL_PASSWORD=your-password
ALERT_SMTP_HOST=smtp-mail.outlook.com
ALERT_SMTP_PORT=587
ALERT_SMTP_USER=your-email@outlook.com
ALERT_SMTP_SSL=True
```

**Note**: Use your actual Outlook password, not an app password (unless you've set one up).

---

## Yahoo Mail

### Step 1: Generate App Password

1. Go to [Yahoo Account Security](https://login.yahoo.com/?activity=account-security)
2. Click **Generate app password**
3. Select:
   - **App**: Mail
   - **Device**: Other App (or your device)
4. Click **Generate**
5. Copy the 16-character password

### Credentials

```bash
ALERT_EMAIL_SENDER=your-email@yahoo.com
ALERT_EMAIL_PASSWORD=xxxx xxxx xxxx xxxx
ALERT_SMTP_HOST=smtp.mail.yahoo.com
ALERT_SMTP_PORT=465
ALERT_SMTP_USER=your-email@yahoo.com
ALERT_SMTP_SSL=True
```

---

## SendGrid (Free Tier Available)

### Step 1: Create SendGrid Account

1. Sign up at [SendGrid](https://sendgrid.com/)
2. Verify your email
3. Go to **Settings → API Keys**
4. Click **Create API Key**
5. Copy the API key

### Step 2: Create Sender Email

1. Go to **Settings → Sender Authentication**
2. Verify your sender email domain

### Credentials

```bash
ALERT_EMAIL_SENDER=noreply@yourdomain.com
ALERT_EMAIL_PASSWORD=SG.your-api-key-here
ALERT_SMTP_HOST=smtp.sendgrid.net
ALERT_SMTP_PORT=587
ALERT_SMTP_USER=apikey
ALERT_SMTP_SSL=True
```

---

## AWS SES (Amazon Simple Email Service)

### Step 1: Set Up SES

1. Go to [AWS Console → SES](https://console.aws.amazon.com/ses/)
2. Request production access (default is sandbox)
3. Verify sender email: **Verified Identities → Create Identity**
4. Go to **SMTP Settings** and click **Create SMTP Credentials**

### Credentials

```bash
ALERT_EMAIL_SENDER=your-verified-email@domain.com
ALERT_EMAIL_PASSWORD=your-smtp-password
ALERT_SMTP_HOST=email-smtp.region.amazonaws.com
ALERT_SMTP_PORT=465
ALERT_SMTP_USER=your-smtp-username
ALERT_SMTP_SSL=True
```

---

## Custom/Company Email Server

### Get Info From Your Admin

Ask your email administrator for:
- **SMTP Host**: (e.g., `mail.company.com`)
- **SMTP Port**: (usually 465 for SSL or 587 for TLS)
- **Username**: (usually your email address)
- **Password**: (your email account password)
- **Encryption**: (SSL or TLS)

### Example

```bash
ALERT_EMAIL_SENDER=john@company.com
ALERT_EMAIL_PASSWORD=your-password
ALERT_SMTP_HOST=mail.company.com
ALERT_SMTP_PORT=465
ALERT_SMTP_USER=john@company.com
ALERT_SMTP_SSL=True
```

---

## How to Set Environment Variables

### Option 1: Create .env File (Easiest)

1. Copy the example:
   ```bash
   cd /Users/mohi1038/Desktop/NetworkTrafficMonitor
   cp .env.example .env
   ```

2. Edit `.env`:
   ```bash
   nano .env
   ```

3. Paste your credentials:
   ```
   ALERT_EMAIL_SENDER=your-email@gmail.com
   ALERT_EMAIL_PASSWORD=xxxx xxxx xxxx xxxx
   ALERT_SMTP_HOST=smtp.gmail.com
   ALERT_SMTP_PORT=465
   ALERT_SMTP_USER=your-email@gmail.com
   ALERT_SMTP_SSL=True
   ```

4. Save (Ctrl+O, Enter, Ctrl+X)

5. **Important**: Add to `.gitignore` to prevent committing credentials:
   ```bash
   echo ".env" >> .gitignore
   ```

### Option 2: Export in Terminal (Session Only)

```bash
export ALERT_EMAIL_SENDER="your-email@gmail.com"
export ALERT_EMAIL_PASSWORD="xxxx xxxx xxxx xxxx"
export ALERT_SMTP_HOST="smtp.gmail.com"
export ALERT_SMTP_PORT="465"
export ALERT_SMTP_USER="your-email@gmail.com"
export ALERT_SMTP_SSL="True"

# Then start the backend
cd backend
python app2.py
```

### Option 3: Set in System (macOS/Linux)

```bash
# Add to ~/.zshrc or ~/.bashrc
echo 'export ALERT_EMAIL_SENDER="your-email@gmail.com"' >> ~/.zshrc
echo 'export ALERT_EMAIL_PASSWORD="xxxx xxxx xxxx xxxx"' >> ~/.zshrc
# ... add other variables

# Reload shell
source ~/.zshrc
```

---

## Test Your Setup

### 1. Verify Environment Variables Are Set

```bash
# Check if variables are loaded
env | grep ALERT_
```

Should show:
```
ALERT_EMAIL_SENDER=your-email@gmail.com
ALERT_EMAIL_PASSWORD=xxxx xxxx xxxx xxxx
ALERT_SMTP_HOST=smtp.gmail.com
ALERT_SMTP_PORT=465
ALERT_SMTP_USER=your-email@gmail.com
ALERT_SMTP_SSL=True
```

### 2. Start Backend with Env Vars

```bash
cd backend
python app2.py
```

You should see:
```
[INFO] Starting Flask server on 127.0.0.1:5001...
```

### 3. Test Email in UI

1. Open Network Monitor (Frontend)
2. Go to **Settings** tab
3. Under **Security Settings**, enter your **Notification Email**
4. Click **Save Email**
5. Click **Send Test Email**
6. Check your inbox for the test email

### 4. If Email Doesn't Arrive

Check `backend/saved_emails/` folder:
```bash
ls -la backend/saved_emails/
cat backend/saved_emails/email_*.json
```

This shows emails were saved as fallback (SMTP may have failed).

---

## Complete Setup Example (Gmail)

### Step-by-Step:

1. **Get Gmail App Password**
   - Go to https://myaccount.google.com/apppasswords
   - Generate password for Mail + Windows Computer
   - Copy: `abcd efgh ijkl mnop`

2. **Create .env File**
   ```bash
   cd /Users/mohi1038/Desktop/NetworkTrafficMonitor
   cp .env.example .env
   nano .env
   ```

3. **Edit .env**
   ```
   ALERT_EMAIL_SENDER=your-email@gmail.com
   ALERT_EMAIL_PASSWORD=abcd efgh ijkl mnop
   ALERT_SMTP_HOST=smtp.gmail.com
   ALERT_SMTP_PORT=465
   ALERT_SMTP_USER=your-email@gmail.com
   ALERT_SMTP_SSL=True
   ```

4. **Save to .gitignore**
   ```bash
   echo ".env" >> .gitignore
   ```

5. **Start Backend**
   ```bash
   cd backend
   python app2.py
   ```

6. **Start Frontend** (new terminal)
   ```bash
   cd frontend
   npm start
   ```

7. **Test in UI**
   - Settings → Notification Email → Save Email
   - Click Send Test Email
   - Check inbox

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| "Connection refused" | Check SMTP host and port are correct |
| "Authentication failed" | Verify email/password in .env file |
| "Email not received" | Check spam folder, verify recipient email |
| "No password set" | Emails save to `backend/saved_emails/` folder |
| "403 Forbidden" | For Gmail: verify 2FA is enabled and app password is correct |

---

## Security Tips

✅ **DO:**
- Use app passwords (not main account password)
- Store credentials in `.env` file (excluded from git)
- Rotate credentials if compromised
- Use SSL/TLS encryption (port 465 or 587)

❌ **DON'T:**
- Commit `.env` file to version control
- Share credentials via email or chat
- Use main account password for SMTP
- Store passwords in plain text in code

---

## Quick Reference: SMTP Servers

| Provider | Host | Port | SSL |
|----------|------|------|-----|
| Gmail | smtp.gmail.com | 465 | Yes |
| Outlook | smtp-mail.outlook.com | 587 | Yes |
| Yahoo | smtp.mail.yahoo.com | 465 | Yes |
| SendGrid | smtp.sendgrid.net | 587 | Yes |
| AWS SES | email-smtp.{region}.amazonaws.com | 465 | Yes |
| iCloud | smtp.mail.me.com | 587 | Yes |

---

Need help? Check:
- [Backend Email Code](../backend/alert_mail.py)
- [.env.example](.env.example)
- [EMAIL_ALERTS_SETUP.md](EMAIL_ALERTS_SETUP.md)
