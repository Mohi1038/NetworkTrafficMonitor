# Email Alerts Configuration Guide

This guide explains how to set up SMTP-based email alerts for Network Traffic Monitor.

## Overview

The application uses **environment variables** for SMTP credentials (not the UI) to ensure security. This prevents credentials from being exposed in the browser or configuration files.

- **Receiver Email**: Can be set via the UI Settings tab (stored in `backend/email_settings.json`)
- **SMTP Credentials**: Must be set via environment variables (never in UI)

## Step 1: Get SMTP Credentials

### For Gmail:

1. Enable 2-factor authentication on your Gmail account
2. Go to [Google App Passwords](https://myaccount.google.com/apppasswords)
3. Select "Mail" and "Windows Computer" (or your device)
4. Google will generate a 16-character password
5. Use this password for `ALERT_EMAIL_PASSWORD`

### For Other Email Providers:

- **Outlook/Office365**: SMTP server: `smtp-mail.outlook.com`, Port: `587`
- **SendGrid**: SMTP server: `smtp.sendgrid.net`, Port: `587`
- **Custom Server**: Contact your email provider for SMTP details

## Step 2: Set Environment Variables

### Option A: Create a `.env` file

1. Copy the example file:
   ```bash
   cp .env.example .env
   ```

2. Edit `.env` and add your SMTP credentials:
   ```
   ALERT_EMAIL_SENDER=your-email@gmail.com
   ALERT_EMAIL_PASSWORD=xxxx xxxx xxxx xxxx  (16-char app password)
   ALERT_SMTP_HOST=smtp.gmail.com
   ALERT_SMTP_PORT=465
   ALERT_SMTP_USER=your-email@gmail.com
   ALERT_SMTP_SSL=True
   ```

3. **Important**: Add `.env` to `.gitignore` to prevent committing credentials

### Option B: Export Environment Variables (macOS/Linux)

```bash
export ALERT_EMAIL_SENDER="your-email@gmail.com"
export ALERT_EMAIL_PASSWORD="xxxx xxxx xxxx xxxx"
export ALERT_SMTP_HOST="smtp.gmail.com"
export ALERT_SMTP_PORT="465"
export ALERT_SMTP_USER="your-email@gmail.com"
export ALERT_SMTP_SSL="True"
```

### Option C: System Environment Variables (Windows)

Use `setx` to set environment variables permanently:
```cmd
setx ALERT_EMAIL_SENDER "your-email@gmail.com"
setx ALERT_EMAIL_PASSWORD "xxxx xxxx xxxx xxxx"
```

## Step 3: Set Receiver Email in UI

1. Open Network Traffic Monitor
2. Go to **Settings** tab
3. Under **Security Settings**, enter your **Notification Email**
4. Click **Save Email**

This stores the receiver email in `backend/email_settings.json`.

## Step 4: Test Email Alerts

1. In the **Settings** tab, click **Send Test Email**
2. Check your inbox for the test email
3. **If you don't receive it:**
   - Check spam folder
   - Verify SMTP credentials are correct
   - Check `backend/saved_emails/` for fallback email files
   - Check backend logs for errors

## Environment Variables Reference

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `ALERT_EMAIL_SENDER` | Yes | - | Gmail or SMTP account email |
| `ALERT_EMAIL_PASSWORD` | Yes | - | Gmail app password (16 chars) |
| `ALERT_EMAIL_RECEIVER` | No | - | Recipient email (can set in UI) |
| `ALERT_SMTP_HOST` | No | `smtp.gmail.com` | SMTP server hostname |
| `ALERT_SMTP_PORT` | No | `465` | SMTP server port (465=SSL, 587=TLS) |
| `ALERT_SMTP_USER` | No | sender email | SMTP login username |
| `ALERT_SMTP_SSL` | No | `True` | Use SSL/TLS encryption |

## How It Works

1. **Startup**: Backend reads SMTP config from environment variables
2. **Fallback**: If SMTP fails, emails are saved to `backend/saved_emails/`
3. **Receiver**: UI-configured email address takes precedence over env var `ALERT_EMAIL_RECEIVER`
4. **Alerts**: Security events trigger emails via `alert_mail.py`

## Troubleshooting

### "Email sent but not received"
- Check spam/junk folder
- Verify recipient email in Settings
- Check Gmail app password is correct (16 chars, with spaces)

### "SMTP authentication failed"
- Verify `ALERT_EMAIL_SENDER` and `ALERT_SMTP_USER` are correct
- Confirm `ALERT_EMAIL_PASSWORD` matches your email provider
- For Gmail: Use app password, not regular password

### "Connection refused"
- Check `ALERT_SMTP_HOST` and `ALERT_SMTP_PORT` are correct
- Verify firewall allows outbound SMTP
- Test SMTP manually: `telnet smtp.gmail.com 465`

### "No emails received, check saved_emails"
- If SMTP fails, emails save to `backend/saved_emails/`
- Each file is a JSON with email details
- Configure SMTP credentials to enable live email sending

## Security Best Practices

1. ✅ **Use environment variables** for SMTP credentials
2. ✅ **Never commit `.env` files** to version control
3. ✅ **Use app passwords** (not main account passwords)
4. ✅ **Rotate credentials** if compromised
5. ✅ **Use SSL/TLS** for SMTP connections
6. ⚠️ Avoid storing passwords in plain text files
7. ⚠️ Don't share SMTP credentials via email or chat

## Example: Full Setup with Gmail

```bash
# 1. Copy example config
cp .env.example .env

# 2. Edit .env with your Gmail app password
nano .env

# 3. Start backend (reads from .env)
cd backend
python app2.py

# 4. Start frontend in another terminal
cd frontend
npm start

# 5. Go to Settings > Security Settings
# 6. Enter your receiver email and click "Save Email"
# 7. Click "Send Test Email" to verify
```

## Next Steps

- Integrate email alerts into threat detection (`alert_callback` in `alert_mail.py`)
- Set up email templates for different alert types
- Add email rate limiting to prevent spam
- Implement email signature/branding

For more info, see [alert_mail.py](../backend/alert_mail.py) source code.
