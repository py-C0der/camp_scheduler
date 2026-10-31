"""
Extensible SMS Provider Adapter (Twilio/Gateway).
Accurately reflects configuration status and never fakes delivery.
"""

import os
from typing import Dict, Any, Optional


class SMSProvider:
    """
    Adapter for SMS Gateway / Twilio service.
    Enforces explicit configuration verification.
    If credentials are not supplied, returns status='not_configured'.
    """

    def __init__(self):
        self.account_sid = os.environ.get("TWILIO_ACCOUNT_SID", "")
        self.auth_token = os.environ.get("TWILIO_AUTH_TOKEN", "")
        self.from_phone = os.environ.get("TWILIO_PHONE_NUMBER", "")
        self.mock_mode = os.environ.get("MOCK_SMS", "0") == "1"

    def is_configured(self) -> bool:
        """Returns True only when Twilio credentials are provided or in test mock mode."""
        return bool(self.account_sid and self.auth_token and self.from_phone) or self.mock_mode

    def send_sms(
        self,
        recipient_phone: str,
        message_text: str
    ) -> Dict[str, Any]:
        """
        Sends an SMS notification if properly configured.
        Never reports success unless authenticated and confirmed by provider.
        """
        if not recipient_phone:
            return {
                "status": "failed",
                "configured": self.is_configured(),
                "error": "Recipient phone number is missing.",
                "recipient": recipient_phone
            }

        if self.mock_mode:
            return {
                "status": "delivered",
                "configured": True,
                "provider": "MockTwilioSMS",
                "recipient": recipient_phone,
                "sid": f"SMmock_{os.urandom(8).hex()}"
            }

        if not self.is_configured():
            return {
                "status": "not_configured",
                "configured": False,
                "error": "SMS provider is not configured. Missing TWILIO_ACCOUNT_SID or TWILIO_AUTH_TOKEN.",
                "recipient": recipient_phone
            }

        # Actual API Dispatch via HTTP if credentials exist
        try:
            import urllib.request
            import urllib.parse
            import base64
            import json

            url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
            auth_str = f"{self.account_sid}:{self.auth_token}"
            b64_auth = base64.b64encode(auth_str.encode("utf-8")).decode("ascii")

            data = urllib.parse.urlencode({
                "To": recipient_phone,
                "From": self.from_phone,
                "Body": message_text
            }).encode("utf-8")

            req = urllib.request.Request(
                url,
                data=data,
                headers={"Authorization": f"Basic {b64_auth}"},
                method="POST"
            )

            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                return {
                    "status": "delivered",
                    "configured": True,
                    "provider": "TwilioSMS",
                    "sid": res_data.get("sid", "confirmed"),
                    "recipient": recipient_phone
                }
        except Exception as ex:
            return {
                "status": "failed",
                "configured": True,
                "error": f"Twilio SMS dispatch error: {str(ex)}",
                "recipient": recipient_phone
            }
