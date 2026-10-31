"""
User Notification Preferences Manager for CIT Campus Platform.
"""

from typing import Dict, Any, Optional
import json
import sqlite3
from backend.db.database import get_connection
from backend.schemas.notification_preference import NotificationPreferenceResponse, NotificationPreferenceUpdate

SEVERITY_ORDER = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4
}


class PreferenceManager:
    """
    Manages user channel and category notification preferences with secure user isolation.
    """

    def __init__(self, db_conn_factory=get_connection):
        self.get_conn = db_conn_factory

    def get_user_preferences(self, user_id: str) -> NotificationPreferenceResponse:
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("SELECT * FROM notification_preferences WHERE user_id = ?", (user_id,))
        row = cur.fetchone()

        if not row:
            # Create default preferences
            default_cats = {"timetable": True, "examination": True, "venue_booking": True, "disruption": True, "approval": True}
            cur.execute("""
                INSERT OR IGNORE INTO notification_preferences (user_id, in_app_enabled, email_enabled, whatsapp_enabled, sms_enabled, categories_json, min_severity)
                VALUES (?, 1, 1, 0, 0, ?, 'low')
            """, (user_id, json.dumps(default_cats)))
            conn.commit()
            conn.close()
            return NotificationPreferenceResponse(
                user_id=user_id,
                in_app_enabled=True,
                email_enabled=True,
                whatsapp_enabled=False,
                sms_enabled=False,
                categories=default_cats,
                min_severity="low"
            )

        cats = json.loads(row["categories_json"]) if row["categories_json"] else {}
        conn.close()
        return NotificationPreferenceResponse(
            user_id=row["user_id"],
            in_app_enabled=bool(row["in_app_enabled"]),
            email_enabled=bool(row["email_enabled"]),
            whatsapp_enabled=bool(row["whatsapp_enabled"]),
            sms_enabled=bool(row["sms_enabled"]),
            categories=cats,
            min_severity=row["min_severity"] or "low",
            updated_at=str(row["updated_at"]) if row["updated_at"] else None
        )

    def update_user_preferences(self, user_id: str, updates: NotificationPreferenceUpdate) -> NotificationPreferenceResponse:
        current = self.get_user_preferences(user_id)

        in_app = updates.in_app_enabled if updates.in_app_enabled is not None else current.in_app_enabled
        email = updates.email_enabled if updates.email_enabled is not None else current.email_enabled
        whatsapp = updates.whatsapp_enabled if updates.whatsapp_enabled is not None else current.whatsapp_enabled
        sms = updates.sms_enabled if updates.sms_enabled is not None else current.sms_enabled
        cats = updates.categories if updates.categories is not None else current.categories
        min_sev = updates.min_severity if updates.min_severity is not None else current.min_severity

        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("""
            UPDATE notification_preferences
            SET in_app_enabled = ?,
                email_enabled = ?,
                whatsapp_enabled = ?,
                sms_enabled = ?,
                categories_json = ?,
                min_severity = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ?
        """, (1 if in_app else 0, 1 if email else 0, 1 if whatsapp else 0, 1 if sms else 0, json.dumps(cats), min_sev, user_id))
        conn.commit()
        conn.close()

        return self.get_user_preferences(user_id)

    def should_deliver(self, user_id: str, channel: str, category: str, severity: str) -> bool:
        """
        Determines whether a notification should be delivered to the user through the specified channel.
        Critical notifications bypass category opt-outs for in-app delivery.
        """
        pref = self.get_user_preferences(user_id)

        # Critical alerts are always delivered in-app regardless of category toggles
        if severity == "critical" and channel == "in_app":
            return True

        # Check channel enabled
        if channel == "in_app" and not pref.in_app_enabled:
            return False
        if channel == "email" and not pref.email_enabled:
            return False
        if channel == "whatsapp" and not pref.whatsapp_enabled:
            return False
        if channel == "sms" and not pref.sms_enabled:
            return False

        # Check category enabled
        if category in pref.categories and not pref.categories[category]:
            return False

        # Check severity threshold
        event_weight = SEVERITY_ORDER.get(severity.lower(), 1)
        user_weight = SEVERITY_ORDER.get(pref.min_severity.lower(), 1)
        if event_weight < user_weight:
            return False

        return True
