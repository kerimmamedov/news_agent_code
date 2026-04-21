import os
import smtplib
from email.message import EmailMessage
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape


BASE_DIR = Path(__file__).resolve().parents[1]
TEMPLATES_DIR = BASE_DIR / "templates"

jinja_env = Environment(
    loader=FileSystemLoader(TEMPLATES_DIR),
    autoescape=select_autoescape(["html", "xml"]),
)


def render_digest_email(digest: dict) -> tuple[str, str]:
    html_template = jinja_env.get_template("daily_news_email.html")
    text_template = jinja_env.get_template("daily_news_email.txt")

    html_body = html_template.render(digest=digest)
    text_body = text_template.render(digest=digest)

    return html_body, text_body


def send_email(to_email: str, subject: str, html_body: str, text_body: str) -> None:
    email_sender = os.getenv("EMAIL_SENDER")
    email_password = os.getenv("EMAIL_PASSWORD")
    email_host = os.getenv("EMAIL_HOST", "smtp.gmail.com")
    email_port = int(os.getenv("EMAIL_PORT", "587"))
    email_use_tls = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"

    if not email_sender:
        raise ValueError("EMAIL_SENDER is missing in environment.")
    if not email_password:
        raise ValueError("EMAIL_PASSWORD is missing in environment.")

    msg = EmailMessage()
    msg["From"] = email_sender
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(text_body)
    msg.add_alternative(html_body, subtype="html")

    with smtplib.SMTP(email_host, email_port) as server:
        server.ehlo()
        if email_use_tls:
            server.starttls()
            server.ehlo()
        server.login(email_sender, email_password)
        server.send_message(msg)
