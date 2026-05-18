import smtplib
import os
from email.mime.text import MIMEText
from pathlib import Path
import json
import threading
from datetime import datetime, timedelta


_alert_lock = threading.Lock()
_sent_alert_signatures = set()
_ALERT_HISTORY_FILE = Path(__file__).parent / ".ntm_alert_history.json"


def _load_alert_history():
    """Load previously sent alerts from file."""
    try:
        if _ALERT_HISTORY_FILE.exists():
            data = json.loads(_ALERT_HISTORY_FILE.read_text())
            return set(data.get("sent_signatures", []))
    except Exception:
        pass
    return set()


def _save_alert_history():
    """Persist alert signatures to file."""
    try:
        _ALERT_HISTORY_FILE.write_text(
            json.dumps({"sent_signatures": list(_sent_alert_signatures)})
        )
    except Exception as e:
        print(f"[ALERT HISTORY] Failed to save: {e}")


_sent_alert_signatures = _load_alert_history()


def _read_saved_email_settings():
    cfg_path = Path(__file__).parent / 'email_settings.json'
    if cfg_path.exists():
        try:
            return json.loads(cfg_path.read_text())
        except Exception:
            return {}
    return {}


def send_email_alert(subject, body):
    # Priority: explicit env vars > saved settings file
    sender_email = os.environ.get("ALERT_EMAIL_SENDER", "").strip()
    receiver_email = os.environ.get("ALERT_EMAIL_RECEIVER", "").strip()
    password = os.environ.get("ALERT_EMAIL_PASSWORD", "").strip()

    if not (sender_email and receiver_email and password):
        saved = _read_saved_email_settings()
        sender_email = sender_email or saved.get('sender', '')
        receiver_email = receiver_email or saved.get('receiver', '')
        # allow using password from saved settings (optional). This stores password in file.
        password = password or saved.get('smtp_password', '')
        smtp_host = saved.get('smtp_host', 'smtp.gmail.com')
        smtp_port = int(saved.get('smtp_port', 465) or 465)
        use_ssl = bool(saved.get('use_ssl', True))
        smtp_user = saved.get('smtp_user') or sender_email
    else:
        smtp_host = os.environ.get('ALERT_SMTP_HOST', 'smtp.gmail.com')
        smtp_port = int(os.environ.get('ALERT_SMTP_PORT', 465) or 465)
        use_ssl = os.environ.get('ALERT_SMTP_SSL', 'True').lower() in ('1','true','yes')
        smtp_user = os.environ.get('ALERT_SMTP_USER', sender_email)

    if not sender_email or not receiver_email:
        print("[EMAIL] Error: sender and receiver emails required.")
        return False

    if not password:
        print("[EMAIL] No SMTP password configured. Saving email to file...")
        return _save_email_to_file(subject, body, sender_email, receiver_email)

    try:
        print(f"[EMAIL] Sending email from {sender_email} to {receiver_email}")
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = receiver_email

        if use_ssl:
            with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
                server.login(smtp_user, password)
                server.send_message(msg)
        else:
            with smtplib.SMTP(smtp_host, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, password)
                server.send_message(msg)

        print("[EMAIL] Email sent successfully via SMTP!")
        return True

    except Exception as e:
        print(f"[EMAIL ERROR] {e}")
        print("[EMAIL] Fallback: saving to file")
        return _save_email_to_file(subject, body, sender_email, receiver_email)


def _save_email_to_file(subject, body, sender, receiver):
    """Save email to file when SMTP is not configured."""
    try:
        from datetime import datetime
        emails_dir = Path(__file__).parent / 'saved_emails'
        emails_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        email_data = {
            'timestamp': timestamp,
            'from': sender,
            'to': receiver,
            'subject': subject,
            'body': body
        }
        email_file = emails_dir / f'email_{timestamp}.json'
        email_file.write_text(json.dumps(email_data, indent=2))
        print(f"[EMAIL] Email saved to: {email_file}")
        return True
    except Exception as e:
        print(f"[EMAIL ERROR FILE] {e}")
        return False


def alert_callback(attack_type, src, dst, protocol):
    signature = f"{attack_type}|{src}|{dst}|{protocol}".lower().strip()

    with _alert_lock:
        if signature in _sent_alert_signatures:
            print(f"[ALERT CALLBACK] Duplicate alert skipped: {attack_type}, {src} → {dst}, Protocol: {protocol}")
            return False
        _sent_alert_signatures.add(signature)
        _save_alert_history()

    print(f"[ALERT CALLBACK] Attack Detected: {attack_type}, {src} → {dst}, Protocol: {protocol}")
    subject = f"[ALERT] {attack_type} Detected"
    body = (
        f"Network Threat Detected 🚨\n\n"
        f"Attack Type: {attack_type}\n"
        f"Source IP: {src}\n"
        f"Destination IP: {dst}\n"
        f"Protocol: {protocol}\n\n"
        f"Please check the Network Traffic Monitor for details."
    )
    sent = send_email_alert(subject, body)
    if not sent:
        with _alert_lock:
            _sent_alert_signatures.discard(signature)
            _save_alert_history()
    return sent
