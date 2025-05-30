import os
import smtplib
from email.mime.text import MIMEText

def send_email_by_smtp(subject: str, body: str, from_email: str, to_emails: list[str], smtp_server: str) -> str:
    """
    Sends an email with the given subject and body using SMTP.
    The password is stored in the environment variable `EMAIL_PASSWORD`.

    Args:
        subject (str): Email subject line.
        body (str): Email body text.
        from_email (str): Sender email address.
        to_emails (list[str]): List of recipient email addresses.
        password (str): Sender email password.
        smtp_server (str): SMTP server address.
    Returns:
        str: Success message if email sent.

    Raises:
        RuntimeError: If email sending fails.
    """
    # to_emails = TO_EMAILS
    # from_email = FROM_EMAIL
    # smtp_server = SMTP_SERVER
    
    password = os.environ.get("EMAIL_PASSWORD")
    if not password:
        raise RuntimeError("EMAIL_PASSWORD environment variable not set")

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = ', '.join(to_emails)

    try:
        with smtplib.SMTP_SSL(smtp_server, 465) as server:
            server.login(from_email, password)
            server.sendmail(from_email, to_emails, msg.as_string())
        return "Email sent successfully."
    except Exception as e:
        raise Exception(f"Failed to send email: {e}")