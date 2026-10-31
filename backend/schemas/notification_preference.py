"""
Pydantic Schemas for User Notification Preferences.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field


class NotificationPreferenceResponse(BaseModel):
    user_id: str
    in_app_enabled: bool = True
    email_enabled: bool = True
    whatsapp_enabled: bool = False
    sms_enabled: bool = False
    categories: Dict[str, bool] = Field(default_factory=lambda: {
        "timetable": True,
        "examination": True,
        "venue_booking": True,
        "disruption": True,
        "approval": True
    })
    min_severity: str = "low" # low, medium, high, critical
    updated_at: Optional[str] = None


class NotificationPreferenceUpdate(BaseModel):
    in_app_enabled: Optional[bool] = None
    email_enabled: Optional[bool] = None
    whatsapp_enabled: Optional[bool] = None
    sms_enabled: Optional[bool] = None
    categories: Optional[Dict[str, bool]] = None
    min_severity: Optional[str] = None
