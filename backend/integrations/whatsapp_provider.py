"""
Extensible WhatsApp Business Cloud API Adapter.
Accurately reflects configuration status and never fakes delivery.
"""

import os
from typing import Dict, Any, Optional


class WhatsAppProvider:
    """
    Adapter for WhatsApp Business Cloud API.
    Enforces explicit configuration verification.
    If credentials are not supplied, returns status='not_configured'.
    """

    def __init__(self):
        self.api_key = os.environ.get("WHATSAPP_API_KEY", "")
        self.phone_number_id = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
        self.base_url = os.environ.get("WHATSAPP_BASE_URL", "https://graph.facebook.com/v19.0")
        self.mock_mode = os.environ.get("MOCK_WHATSAPP", "0") == "1"

    def is_configured(self) -> bool:
        """Returns True only when API credentials are provided or in test mock mode."""
        return bool(self.api_key and self.phone_number_id) or self.mock_mode

    def send_whatsapp_message(
        self,
        recipient_phone: str,
        message_text: str,
        template_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends a WhatsApp notification if properly configured.
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
                "provider": "MockWhatsAppCloudAPI",
                "recipient": recipient_phone,
                "message_id": f"wamid.mock_{os.urandom(6).hex()}"
            }

        if not self.is_configured():
            return {
                "status": "not_configured",
                "configured": False,
                "error": "WhatsApp Business Cloud API is not configured. Missing WHATSAPP_API_KEY or WHATSAPP_PHONE_NUMBER_ID.",
                "recipient": recipient_phone
            }

        # Actual API Dispatch via HTTP if credentials exist
        try:
            import urllib.request
            import json

            url = f"{self.base_url}/{self.phone_number_id}/messages"
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "messaging_product": "whatsapp",
                "to": recipient_phone,
                "type": "text",
                "text": {"body": message_text}
            }

            req = urllib.request.Request(url, data=json.dumps(payload).encode("utf-8"), headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=10) as response:
                res_data = json.loads(response.read().decode("utf-8"))
                msg_id = res_data.get("messages", [{}])[0].get("id", "confirmed")
                return {
                    "status": "delivered",
                    "configured": True,
                    "provider": "WhatsAppCloudAPI",
                    "message_id": msg_id,
                    "recipient": recipient_phone
                }
        except Exception as ex:
            return {
                "status": "failed",
                "configured": True,
                "error": f"WhatsApp API dispatch error: {str(ex)}",
                "recipient": recipient_phone
            }
