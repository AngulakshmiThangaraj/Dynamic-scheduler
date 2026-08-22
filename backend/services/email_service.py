import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

EMAIL_HOST = os.environ.get("EMAIL_HOST", "smtp.gmail.com")
EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
EMAIL_USER = os.environ.get("EMAIL_USER", "")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "")
EMAIL_FROM = os.environ.get("EMAIL_FROM", "noreply@scheduler-app.com")

class EmailService:
    @staticmethod
    def send_email(to_email: str, subject: str, body: str) -> bool:
        """
        Sends an email if SMTP credentials are fully configured.
        Otherwise logs to console/in-app gracefully without raising runtime errors.
        """
        if not EMAIL_USER or not EMAIL_PASSWORD:
            print(f"[In-App Email Simulation] To: {to_email} | Subject: {subject} | Body: {body}")
            return True

        try:
            msg = MIMEMultipart()
            msg["From"] = EMAIL_FROM
            msg["To"] = to_email
            msg["Subject"] = subject
            msg.attach(MIMEText(body, "plain"))

            server = smtplib.SMTP(EMAIL_HOST, EMAIL_PORT)
            server.starttls()
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            print(f"[Email Send Error] Failed to send email to {to_email}: {e}")
            return False
