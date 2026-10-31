"""
Pydantic Schemas for Module 6: Notification, Alerts & Communication Management.
"""

from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from enum import Enum


class NotificationCategory(str, Enum):
    TIMETABLE = "timetable"
    EXAMINATION = "examination"
    VENUE_BOOKING = "venue_booking"
    DISRUPTION = "disruption"
    APPROVAL = "approval"


class NotificationSeverity(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DeliveryChannel(str, Enum):
    IN_APP = "in_app"
    EMAIL = "email"
    WHATSAPP = "whatsapp"
    SMS = "sms"


class DeliveryStatus(str, Enum):
    DELIVERED = "delivered"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"
    NOT_CONFIGURED = "not_configured"


class NotificationItem(BaseModel):
    id: str
    event_type: str
    category: str
    severity: str
    title: str
    message: str
    related_module: str
    related_record_id: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    created_at: str
    is_read: bool = False
    read_at: Optional[str] = None
    is_archived: bool = False


class NotificationListResponse(BaseModel):
    total: int
    unread_count: int
    notifications: List[NotificationItem]


class UnreadCountResponse(BaseModel):
    user_id: str
    unread_count: int
    by_category: Dict[str, int]
    by_severity: Dict[str, int]


class DeliveryRecord(BaseModel):
    id: int
    notification_id: str
    recipient_id: str
    channel: str
    status: str
    attempt_count: int = 1
    error_message: Optional[str] = None
    provider_response: Optional[str] = None
    sent_at: str


class NotificationDetailResponse(BaseModel):
    notification: NotificationItem
    deliveries: List[DeliveryRecord] = []


class MarkReadResponse(BaseModel):
    status: str
    marked_count: int
    unread_count: int


class AdminSummaryResponse(BaseModel):
    total_notifications: int
    total_delivered: int
    total_failed: int
    total_skipped: int
    total_not_configured: int
    by_category: Dict[str, int]
    by_severity: Dict[str, int]
    by_channel: Dict[str, int]
    recent_alerts: List[NotificationItem] = []


class AdminDeliveryLogItem(BaseModel):
    id: int
    notification_id: str
    recipient_id: str
    recipient_name: Optional[str] = None
    channel: str
    status: str
    attempt_count: int
    error_message: Optional[str] = None
    sent_at: str
    title: Optional[str] = None
    category: Optional[str] = None


class TestProviderRequest(BaseModel):
    channel: str # 'email', 'whatsapp', 'sms'
    target: str # email address or phone number
    message: Optional[str] = None


class TestProviderResponse(BaseModel):
    channel: str
    status: str
    configured: bool
    details: str
