from app.tools.core.email import send_email_by_smtp
from app import config

def test_send_email():
    subject = "Hello"
    body = "How are you"
    from_email = config.FROM_EMAIL
    to_email = config.TO_EMAIL
    smtp_server = config.SMTP_SERVER
    
    send_email_by_smtp(subject=subject, body=body, from_email=from_email, to_emails=to_email, smtp_server=smtp_server)