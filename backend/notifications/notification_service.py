"""
Centralized Notification Service for CIT Campus Scheduling & Operations Platform.
Coordinates event reception, recipient resolution, preference filtering,
channel dispatching, delivery tracking, and user isolation.
"""

import uuid
import json
import time
import asyncio
from typing import Dict, Any, List, Optional, Tuple
import sqlite3

from backend.db.database import get_connection
from backend.notifications.events import NotificationEvent, EventTypes
from backend.notifications.recipient_resolver import RecipientResolver
from backend.notifications.templates import TemplateEngine
from backend.notifications.preferences import PreferenceManager
from backend.notifications.delivery_tracker import DeliveryTracker
from backend.notifications.websocket_manager import ws_manager
from backend.integrations.email_provider import EmailProvider
from backend.integrations.whatsapp_provider import WhatsAppProvider
from backend.integrations.sms_provider import SMSProvider
from backend.schemas.notification import (
    NotificationItem,
    NotificationListResponse,
    UnreadCountResponse,
    NotificationDetailResponse,
    MarkReadResponse,
    AdminSummaryResponse,
    AdminDeliveryLogItem,
    TestProviderResponse
)
from backend.schemas.notification_preference import NotificationPreferenceResponse, NotificationPreferenceUpdate


class NotificationService:
    """
    Central orchestrator for Module 6.
    Ensures notifications are triggered by actual backend events,
    persisted reliably in SQLite, and isolated per user.
    """

    def __init__(self, db_conn_factory=get_connection):
        self.get_conn = db_conn_factory
        self.recipient_resolver = RecipientResolver(db_conn_factory)
        self.preference_manager = PreferenceManager(db_conn_factory)
        self.delivery_tracker = DeliveryTracker(db_conn_factory)
        self.email_provider = EmailProvider()
        self.whatsapp_provider = WhatsAppProvider()
        self.sms_provider = SMSProvider()
        self._dedup_cache: Dict[str, float] = {} # key -> timestamp

    def process_event(self, event: NotificationEvent) -> str:
        """
        Processes an event published by any business module (Modules 2-5).
        Returns notification ID.
        """
        # 1. Duplicate prevention check (5 second window for identical event + record)
        dedup_key = f"{event.event_type}:{event.related_record_id}:{event.related_module}"
        now = time.time()
        if dedup_key in self._dedup_cache and (now - self._dedup_cache[dedup_key]) < 5.0:
            return "" # skip duplicate
        self._dedup_cache[dedup_key] = now

        # Clean old dedup entries
        if len(self._dedup_cache) > 500:
            self._dedup_cache = {k: v for k, v in self._dedup_cache.items() if now - v < 60.0}

        # 2. Render templates
        title, message, email_subject, action_url = TemplateEngine.render(event)
        notif_id = f"notif_{uuid.uuid4().hex[:12]}"

        conn = self.get_conn()
        cur = conn.cursor()

        # 3. Store notification event log
        cur.execute("""
            INSERT INTO notification_events (id, event_type, payload_json, published_by)
            VALUES (?, ?, ?, ?)
        """, (event.id, event.event_type, json.dumps(event.payload or {}), event.published_by))

        # 4. Store master notification record
        cur.execute("""
            INSERT INTO notifications (
                id, event_type, category, severity, title, message, related_module, related_record_id, metadata_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            notif_id,
            event.event_type,
            event.category,
            event.severity,
            title,
            message,
            event.related_module,
            event.related_record_id,
            json.dumps({"action_url": action_url, **(event.payload or {})})
        ))
        conn.commit()
        conn.close()

        # 5. Resolve target recipients
        recipients = self.recipient_resolver.resolve_recipients(event)

        # 6. In-App Recipient Resolution & Storage
        conn = self.get_conn()
        cur = conn.cursor()
        for recip in recipients:
            user_id = recip["user_id"]
            user_role = recip["role"]
            if self.preference_manager.should_deliver(user_id, "in_app", event.category, event.severity):
                cur.execute("""
                    INSERT INTO notification_recipients (notification_id, recipient_id, role, is_read)
                    VALUES (?, ?, ?, 0)
                """, (notif_id, user_id, user_role))
                cur.execute("""
                    INSERT INTO notification_deliveries (
                        notification_id, recipient_id, channel, status, attempt_count, error_message, provider_response
                    ) VALUES (?, ?, 'in_app', 'delivered', 1, NULL, NULL)
                """, (notif_id, user_id))
            else:
                cur.execute("""
                    INSERT INTO notification_deliveries (
                        notification_id, recipient_id, channel, status, attempt_count, error_message, provider_response
                    ) VALUES (?, ?, 'in_app', 'skipped', 1, 'User opted out of in-app delivery for this category/severity.', NULL)
                """, (notif_id, user_id))
        conn.commit()
        conn.close()

        # 7. Real-Time Push & External Communication Channels (Email, WhatsApp, SMS)
        for recip in recipients:
            user_id = recip["user_id"]
            user_email = recip.get("email")

            # Push real-time alert via WebSocket if connected
            if self.preference_manager.should_deliver(user_id, "in_app", event.category, event.severity):
                try:
                    loop = asyncio.get_running_loop()
                    loop.create_task(ws_manager.send_personal_message(user_id, {
                        "type": "NEW_NOTIFICATION",
                        "notification": {
                            "id": notif_id,
                            "title": title,
                            "message": message,
                            "category": event.category,
                            "severity": event.severity,
                            "action_url": action_url,
                            "created_at": time.strftime("%Y-%m-%d %H:%M:%S")
                        }
                    }))
                except RuntimeError:
                    pass

            # Email Channel Dispatch
            if self.preference_manager.should_deliver(user_id, "email", event.category, event.severity):
                if user_email:
                    html_content = self.email_provider.render_cit_email_html(
                        title=title,
                        message=message,
                        category=event.category,
                        severity=event.severity,
                        record_id=event.related_record_id,
                        action_url=f"http://127.0.0.1:8000{action_url}"
                    )
                    email_res = self.email_provider.send_email(
                        recipient_email=user_email,
                        subject=email_subject,
                        html_body=html_content,
                        text_body=message
                    )
                    self.delivery_tracker.record_delivery(
                        notification_id=notif_id,
                        recipient_id=user_id,
                        channel="email",
                        status=email_res.get("status", "failed"),
                        error_message=email_res.get("error"),
                        provider_response=json.dumps(email_res)
                    )
                else:
                    self.delivery_tracker.record_delivery(
                        notification_id=notif_id,
                        recipient_id=user_id,
                        channel="email",
                        status="failed",
                        error_message="Recipient has no email registered."
                    )
            else:
                self.delivery_tracker.record_delivery(
                    notification_id=notif_id,
                    recipient_id=user_id,
                    channel="email",
                    status="skipped"
                )

            # WhatsApp Channel Dispatch (optional adapter)
            if self.preference_manager.should_deliver(user_id, "whatsapp", event.category, event.severity):
                wa_res = self.whatsapp_provider.send_whatsapp_message(
                    recipient_phone=recip.get("phone", ""),
                    message_text=f"[{title}]\n{message}"
                )
                self.delivery_tracker.record_delivery(
                    notification_id=notif_id,
                    recipient_id=user_id,
                    channel="whatsapp",
                    status=wa_res.get("status", "not_configured"),
                    error_message=wa_res.get("error"),
                    provider_response=json.dumps(wa_res)
                )

            # SMS Channel Dispatch (optional adapter)
            if self.preference_manager.should_deliver(user_id, "sms", event.category, event.severity):
                sms_res = self.sms_provider.send_sms(
                    recipient_phone=recip.get("phone", ""),
                    message_text=f"[CIT] {title}: {message[:120]}"
                )
                self.delivery_tracker.record_delivery(
                    notification_id=notif_id,
                    recipient_id=user_id,
                    channel="sms",
                    status=sms_res.get("status", "not_configured"),
                    error_message=sms_res.get("error"),
                    provider_response=json.dumps(sms_res)
                )

        # Audit log
        self.delivery_tracker.log_audit(
            user_id=event.published_by,
            action="notification_dispatched",
            details={"notification_id": notif_id, "recipients_count": len(recipients), "event_type": event.event_type}
        )

        return notif_id

    def get_user_notifications(
        self,
        user_id: str,
        category: Optional[str] = None,
        is_read: Optional[bool] = None,
        limit: int = 50,
        offset: int = 0,
        search: Optional[str] = None
    ) -> NotificationListResponse:
        """
        Returns notifications for the authenticated user only.
        Prevents unauthorized users from seeing other users' records.
        """
        conn = self.get_conn()
        cur = conn.cursor()

        base_query = """
            FROM notification_recipients nr
            JOIN notifications n ON nr.notification_id = n.id
            WHERE nr.recipient_id = ? AND nr.is_archived = 0
        """
        params = [user_id]

        if category:
            base_query += " AND n.category = ?"
            params.append(category)

        if is_read is not None:
            base_query += " AND nr.is_read = ?"
            params.append(1 if is_read else 0)

        if search:
            base_query += " AND (n.title LIKE ? OR n.message LIKE ?)"
            params.extend([f"%{search}%", f"%{search}%"])

        # Count total
        count_sql = f"SELECT COUNT(*) {base_query}"
        cur.execute(count_sql, params)
        total = cur.fetchone()[0]

        # Count unread for user
        cur.execute("""
            SELECT COUNT(*)
            FROM notification_recipients nr
            WHERE nr.recipient_id = ? AND nr.is_read = 0 AND nr.is_archived = 0
        """, (user_id,))
        unread_count = cur.fetchone()[0]

        # Fetch records
        select_sql = f"""
            SELECT n.id, n.event_type, n.category, n.severity, n.title, n.message,
                   n.related_module, n.related_record_id, n.metadata_json, n.created_at,
                   nr.is_read, nr.read_at, nr.is_archived
            {base_query}
            ORDER BY n.created_at DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        cur.execute(select_sql, params)
        rows = cur.fetchall()
        conn.close()

        items = []
        for r in rows:
            items.append(NotificationItem(
                id=r["id"],
                event_type=r["event_type"],
                category=r["category"],
                severity=r["severity"],
                title=r["title"],
                message=r["message"],
                related_module=r["related_module"],
                related_record_id=r["related_record_id"],
                metadata=json.loads(r["metadata_json"]) if r["metadata_json"] else None,
                created_at=str(r["created_at"]),
                is_read=bool(r["is_read"]),
                read_at=str(r["read_at"]) if r["read_at"] else None,
                is_archived=bool(r["is_archived"])
            ))

        return NotificationListResponse(
            total=total,
            unread_count=unread_count,
            notifications=items
        )

    def get_unread_count(self, user_id: str) -> UnreadCountResponse:
        conn = self.get_conn()
        cur = conn.cursor()

        cur.execute("""
            SELECT n.category, n.severity, COUNT(*)
            FROM notification_recipients nr
            JOIN notifications n ON nr.notification_id = n.id
            WHERE nr.recipient_id = ? AND nr.is_read = 0 AND nr.is_archived = 0
            GROUP BY n.category, n.severity
        """, (user_id,))
        rows = cur.fetchall()

        by_cat: Dict[str, int] = {}
        by_sev: Dict[str, int] = {}
        total_unread = 0

        for r in rows:
            cat, sev, cnt = r[0], r[1], r[2]
            by_cat[cat] = by_cat.get(cat, 0) + cnt
            by_sev[sev] = by_sev.get(sev, 0) + cnt
            total_unread += cnt

        conn.close()

        return UnreadCountResponse(
            user_id=user_id,
            unread_count=total_unread,
            by_category=by_cat,
            by_severity=by_sev
        )

    def get_notification_by_id(self, notification_id: str, user_id: str, user_role: str = "faculty") -> NotificationDetailResponse:
        conn = self.get_conn()
        cur = conn.cursor()

        # Check access: Admin can view any notification; non-admin can only view their own
        if user_role == "admin":
            cur.execute("""
                SELECT n.id, n.event_type, n.category, n.severity, n.title, n.message,
                       n.related_module, n.related_record_id, n.metadata_json, n.created_at,
                       COALESCE(nr.is_read, 0) as is_read, nr.read_at, COALESCE(nr.is_archived, 0) as is_archived
                FROM notifications n
                LEFT JOIN notification_recipients nr ON n.id = nr.notification_id AND nr.recipient_id = ?
                WHERE n.id = ?
            """, (user_id, notification_id))
        else:
            cur.execute("""
                SELECT n.id, n.event_type, n.category, n.severity, n.title, n.message,
                       n.related_module, n.related_record_id, n.metadata_json, n.created_at,
                       nr.is_read, nr.read_at, nr.is_archived
                FROM notifications n
                JOIN notification_recipients nr ON n.id = nr.notification_id
                WHERE n.id = ? AND nr.recipient_id = ?
            """, (notification_id, user_id))

        row = cur.fetchone()
        conn.close()

        if not row:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Notification not found or access denied.")

        deliveries = self.delivery_tracker.get_deliveries_for_notification(notification_id)

        item = NotificationItem(
            id=row["id"],
            event_type=row["event_type"],
            category=row["category"],
            severity=row["severity"],
            title=row["title"],
            message=row["message"],
            related_module=row["related_module"],
            related_record_id=row["related_record_id"],
            metadata=json.loads(row["metadata_json"]) if row["metadata_json"] else None,
            created_at=str(row["created_at"]),
            is_read=bool(row["is_read"]),
            read_at=str(row["read_at"]) if row["read_at"] else None,
            is_archived=bool(row["is_archived"])
        )

        return NotificationDetailResponse(notification=item, deliveries=deliveries)

    def mark_as_read(self, notification_id: str, user_id: str) -> MarkReadResponse:
        conn = self.get_conn()
        cur = conn.cursor()

        cur.execute("""
            UPDATE notification_recipients
            SET is_read = 1, read_at = CURRENT_TIMESTAMP
            WHERE notification_id = ? AND recipient_id = ? AND is_read = 0
        """, (notification_id, user_id))
        affected = cur.rowcount
        conn.commit()

        # Get updated unread count
        cur.execute("""
            SELECT COUNT(*) FROM notification_recipients
            WHERE recipient_id = ? AND is_read = 0 AND is_archived = 0
        """, (user_id,))
        unread_cnt = cur.fetchone()[0]
        conn.close()

        return MarkReadResponse(
            status="success",
            marked_count=affected,
            unread_count=unread_cnt
        )

    def mark_all_read(self, user_id: str, category: Optional[str] = None) -> MarkReadResponse:
        conn = self.get_conn()
        cur = conn.cursor()

        if category:
            cur.execute("""
                UPDATE notification_recipients
                SET is_read = 1, read_at = CURRENT_TIMESTAMP
                WHERE recipient_id = ? AND is_read = 0 AND notification_id IN (
                    SELECT id FROM notifications WHERE category = ?
                )
            """, (user_id, category))
        else:
            cur.execute("""
                UPDATE notification_recipients
                SET is_read = 1, read_at = CURRENT_TIMESTAMP
                WHERE recipient_id = ? AND is_read = 0
            """, (user_id,))

        marked = cur.rowcount
        conn.commit()
        conn.close()

        return MarkReadResponse(
            status="success",
            marked_count=marked,
            unread_count=0
        )

    def archive_notification(self, notification_id: str, user_id: str) -> bool:
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("""
            UPDATE notification_recipients
            SET is_archived = 1, archived_at = CURRENT_TIMESTAMP
            WHERE notification_id = ? AND recipient_id = ?
        """, (notification_id, user_id))
        affected = cur.rowcount
        conn.commit()
        conn.close()
        return affected > 0

    def test_communication_provider(self, channel: str, target: str, user_id: str) -> TestProviderResponse:
        """Allows authorized administrators to test communication providers."""
        if channel == "email":
            is_cfg = self.email_provider.is_configured()
            res = self.email_provider.send_email(
                recipient_email=target,
                subject="[CIT Test] Communication Gateway Probe",
                html_body=self.email_provider.render_cit_email_html(
                    title="Communication Gateway Test",
                    message="This is a test notification dispatched by CIT System Administration to verify SMTP connectivity.",
                    category="system",
                    severity="low"
                ),
                text_body="CIT Communication Gateway Test message."
            )
            return TestProviderResponse(
                channel="email",
                status=res.get("status", "unknown"),
                configured=is_cfg,
                details=f"Provider: {res.get('provider', 'SMTP')}, Result: {res.get('status')}, Error: {res.get('error', 'None')}"
            )
        elif channel == "whatsapp":
            is_cfg = self.whatsapp_provider.is_configured()
            res = self.whatsapp_provider.send_whatsapp_message(
                recipient_phone=target,
                message_text="[CIT Test] WhatsApp Gateway Probe from CIT Campus Platform."
            )
            return TestProviderResponse(
                channel="whatsapp",
                status=res.get("status", "not_configured"),
                configured=is_cfg,
                details=f"Configured: {is_cfg}. Error/Note: {res.get('error', 'Ready')}"
            )
        elif channel == "sms":
            is_cfg = self.sms_provider.is_configured()
            res = self.sms_provider.send_sms(
                recipient_phone=target,
                message_text="[CIT Test] SMS Gateway Probe from CIT Campus Platform."
            )
            return TestProviderResponse(
                channel="sms",
                status=res.get("status", "not_configured"),
                configured=is_cfg,
                details=f"Configured: {is_cfg}. Error/Note: {res.get('error', 'Ready')}"
            )
        else:
            return TestProviderResponse(
                channel=channel,
                status="invalid_channel",
                configured=False,
                details=f"Channel '{channel}' is not supported."
            )


# Global singleton instance
notification_service = NotificationService()
