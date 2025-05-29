import os
import smtplib
from email.mime.text import MIMEText
from app import TO_EMAILS, FROM_EMAIL, SMTP_SERVER

    
def send_email(subject: str, body: str) -> str:
    """
    Sends an email with the given subject and body.

    Args:
        subject (str): Email subject line.
        body (str): Email body text.

    Returns:
        str: Success message if email sent.

    Raises:
        RuntimeError: If email sending fails.
    """
    to_emails = TO_EMAILS
    from_email = FROM_EMAIL
    password = os.environ.get("EMAIL_PASSWORD")
    if not password:
        raise RuntimeError("EMAIL_PASSWORD environment variable not set")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = ', '.join(to_emails)

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, 465) as server:
            server.login(from_email, password)
            server.sendmail(from_email, to_emails, msg.as_string())
        return "Email sent successfully."
    except Exception as e:
        raise Exception(f"Failed to send email: {e}")