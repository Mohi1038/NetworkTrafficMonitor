import smtplib
from email.mime.text import MIMEText

def send_email_alert(subject, body):
    sender_email = "sender@gmail.com"
    receiver_email = "receiver@gmail.com"
    password = "App password from Gmail"

    try:
        print("[EMAIL] Preparing to send email...")
        msg = MIMEText(body)
        msg['Subject'] = subject
        msg['From'] = sender_email
        msg['To'] = receiver_email

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(sender_email, password)
            server.send_message(msg)

        print("[EMAIL] Email sent successfully!")

    except Exception as e:
        print("[EMAIL ERROR]", e)

def alert_callback(attack_type, src, dst, protocol):
    print(f"[ALERT CALLBACK] Attack Detected: {attack_type}, {src} → {dst}, Protocol: {protocol}")
    subject = f"[ALERT] {attack_type} Detected"
    body = (
        f"Network Threat Detected 🚨\n\n"
        f"🛡️ **Attack Type:** {attack_type}\n"
        f"**Source IP:** {src}\n"
        f"**Destination IP:** {dst}\n"
        f"**Protocol:** {protocol}\n\n"
        f"Stay vigilant. This may indicate a potential threat in your network."
    )
    send_email_alert(subject, body)
