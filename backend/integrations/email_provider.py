"""
Email Notification Provider Service with CIT Branding & Non-blocking SMTP Support.
"""

import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Dict, Any, Optional


class EmailProvider:
    """
    Handles email notifications using SMTP.
    Uses environment variables for credentials and provides non-blocking delivery,
    graceful fallback when unconfigured, and CIT campus visual branding.
    """

    def __init__(self):
        self.smtp_host = os.environ.get("SMTP_HOST", "")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("SMTP_USER", "")
        self.smtp_password = os.environ.get("SMTP_PASSWORD", "")
        self.from_email = os.environ.get("SMTP_FROM", "notifications@cit.ac.in")
        self.from_name = "CIT Campus Scheduling & Operations"
        self.mock_mode = os.environ.get("MOCK_EMAIL", "0") == "1"

    def is_configured(self) -> bool:
        """Returns True if valid SMTP credentials are configured or in mock test mode."""
        return bool(self.smtp_host and self.smtp_user and self.smtp_password) or self.mock_mode

    def render_cit_email_html(
        self,
        title: str,
        message: str,
        category: str,
        severity: str,
        record_id: Optional[str] = None,
        action_url: Optional[str] = None
    ) -> str:
        """Generates CIT-branded HTML email body."""
        severity_colors = {
            "critical": "#ef4444",
            "high": "#f59e0b",
            "medium": "#2563eb",
            "low": "#64748b"
        }
        accent_color = severity_colors.get(severity.lower(), "#2563eb")
        badge_text = severity.upper()
        cat_text = category.replace("_", " ").title()

        return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #f8fafc; margin: 0; padding: 20px; color: #0f172a; }}
    .container {{ max-width: 600px; margin: 0 auto; background: #ffffff; border-radius: 8px; border: 1px solid #e2e8f0; overflow: hidden; }}
    .header {{ background: #0f172a; padding: 24px 30px; display: flex; align-items: center; border-bottom: 3px solid {accent_color}; }}
    .logo {{ color: #ffffff; font-size: 18px; font-weight: 800; letter-spacing: 0.5px; }}
    .logo span {{ color: #38bdf8; }}
    .body {{ padding: 30px; }}
    .badge {{ display: inline-block; padding: 4px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700; background: {accent_color}15; color: {accent_color}; text-transform: uppercase; margin-bottom: 12px; }}
    .title {{ font-size: 20px; font-weight: 700; color: #0f172a; margin-top: 0; margin-bottom: 16px; line-height: 1.3; }}
    .content {{ font-size: 15px; line-height: 1.6; color: #334155; margin-bottom: 24px; white-space: pre-line; }}
    .details-box {{ background: #f1f5f9; border-radius: 6px; padding: 14px 18px; margin-bottom: 24px; font-size: 13px; color: #475569; }}
    .details-box p {{ margin: 4px 0; }}
    .btn {{ display: inline-block; background: #2563eb; color: #ffffff; text-decoration: none; padding: 10px 22px; border-radius: 6px; font-weight: 600; font-size: 14px; }}
    .footer {{ background: #f8fafc; padding: 20px 30px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center; }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="logo">CIT <span>CAMPUS OPERATIONS</span></div>
    </div>
    <div class="body">
      <span class="badge">{badge_text} &bull; {cat_text}</span>
      <h1 class="title">{title}</h1>
      <div class="content">{message}</div>
      <div class="details-box">
        <p><strong>Category:</strong> {cat_text}</p>
        <p><strong>Severity:</strong> {badge_text}</p>
        {f'<p><strong>Record ID:</strong> {record_id}</p>' if record_id else ''}
      </div>
      {f'<a href="{action_url}" class="btn">View in CIT Portal &rarr;</a>' if action_url else ''}
    </div>
    <div class="footer">
      <p>This is an automated notification from Chilika Institute of Technology Campus Operations Platform.</p>
      <p>Do not reply to this email directly.</p>
    </div>
  </div>
</body>
</html>"""

    def send_email(
        self,
        recipient_email: str,
        subject: str,
        html_body: str,
        text_body: str
    ) -> Dict[str, Any]:
        """
        Sends an email message via SMTP.
        Returns a delivery result dict with status, error details, and delivery tracking metadata.
        """
        if not recipient_email or "@" not in recipient_email:
            return {
                "status": "failed",
                "configured": self.is_configured(),
                "error": "Invalid recipient email address",
                "recipient": recipient_email
            }

        # Mock mode for testing without real internet connection
        if self.mock_mode:
            return {
                "status": "delivered",
                "configured": True,
                "provider": "MockSMTP",
                "recipient": recipient_email,
                "message_id": f"mock-{os.urandom(4).hex()}"
            }

        if not self.is_configured():
            return {
                "status": "not_configured",
                "configured": False,
                "error": "SMTP server credentials are not configured in environment variables.",
                "recipient": recipient_email
            }

        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = f"{self.from_name} <{self.from_email}>"
            msg["To"] = recipient_email

            part1 = MIMEText(text_body, "plain", "utf-8")
            part2 = MIMEText(html_body, "html", "utf-8")
            msg.attach(part1)
            msg.attach(part2)

            with smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=10) as server:
                server.ehlo()
                if self.smtp_port in (587, 25):
                    server.starttls()
                    server.ehlo()
                if self.smtp_user and self.smtp_password:
                    server.login(self.smtp_user, self.smtp_password)
                server.sendmail(self.from_email, [recipient_email], msg.as_string())

            return {
                "status": "delivered",
                "configured": True,
                "provider": "SMTP",
                "recipient": recipient_email
            }
        except Exception as ex:
            return {
                "status": "failed",
                "configured": True,
                "error": str(ex),
                "recipient": recipient_email
            }
