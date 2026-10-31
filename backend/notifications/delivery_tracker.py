"""
Delivery Tracking, Audit Logging and Administrative Analytics Service.
"""

from typing import Dict, Any, List, Optional
import json
import sqlite3
from backend.db.database import get_connection
from backend.schemas.notification import AdminSummaryResponse, AdminDeliveryLogItem, DeliveryRecord


class DeliveryTracker:
    """
    Records and queries notification deliveries, retries, audit logs, and delivery metrics.
    """

    def __init__(self, db_conn_factory=get_connection):
        self.get_conn = db_conn_factory

    def record_delivery(
        self,
        notification_id: str,
        recipient_id: str,
        channel: str,
        status: str,
        attempt_count: int = 1,
        error_message: Optional[str] = None,
        provider_response: Optional[str] = None
    ) -> int:
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO notification_deliveries (
                notification_id, recipient_id, channel, status, attempt_count, error_message, provider_response
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            notification_id,
            recipient_id,
            channel,
            status,
            attempt_count,
            error_message,
            provider_response
        ))
        delivery_id = cur.lastrowid
        conn.commit()
        conn.close()
        return delivery_id

    def log_audit(self, user_id: str, action: str, details: Dict[str, Any]):
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO notification_audit_logs (user_id, action, details_json)
            VALUES (?, ?, ?)
        """, (user_id, action, json.dumps(details)))
        conn.commit()
        conn.close()

    def get_deliveries_for_notification(self, notification_id: str) -> List[DeliveryRecord]:
        conn = self.get_conn()
        cur = conn.cursor()
        cur.execute("""
            SELECT id, notification_id, recipient_id, channel, status, attempt_count, error_message, provider_response, sent_at
            FROM notification_deliveries
            WHERE notification_id = ?
            ORDER BY sent_at DESC
        """, (notification_id,))
        rows = cur.fetchall()
        conn.close()
        return [
            DeliveryRecord(
                id=r["id"],
                notification_id=r["notification_id"],
                recipient_id=r["recipient_id"],
                channel=r["channel"],
                status=r["status"],
                attempt_count=r["attempt_count"],
                error_message=r["error_message"],
                provider_response=r["provider_response"],
                sent_at=str(r["sent_at"])
            )
            for r in rows
        ]

    def get_admin_summary(self) -> AdminSummaryResponse:
        conn = self.get_conn()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) FROM notifications")
        total_notifs = cur.fetchone()[0]

        cur.execute("SELECT status, COUNT(*) FROM notification_deliveries GROUP BY status")
        status_counts = {r[0]: r[1] for r in cur.fetchall()}

        cur.execute("SELECT category, COUNT(*) FROM notifications GROUP BY category")
        cat_counts = {r[0]: r[1] for r in cur.fetchall()}

        cur.execute("SELECT severity, COUNT(*) FROM notifications GROUP BY severity")
        sev_counts = {r[0]: r[1] for r in cur.fetchall()}

        cur.execute("SELECT channel, COUNT(*) FROM notification_deliveries GROUP BY channel")
        chan_counts = {r[0]: r[1] for r in cur.fetchall()}

        # Recent critical and high alerts
        cur.execute("""
            SELECT id, event_type, category, severity, title, message, related_module, related_record_id, metadata_json, created_at
            FROM notifications
            WHERE severity IN ('critical', 'high')
            ORDER BY created_at DESC
            LIMIT 10
        """)
        alerts_rows = cur.fetchall()
        recent_alerts = []
        for r in alerts_rows:
            recent_alerts.append({
                "id": r["id"],
                "event_type": r["event_type"],
                "category": r["category"],
                "severity": r["severity"],
                "title": r["title"],
                "message": r["message"],
                "related_module": r["related_module"],
                "related_record_id": r["related_record_id"],
                "metadata": json.loads(r["metadata_json"]) if r["metadata_json"] else None,
                "created_at": str(r["created_at"]),
                "is_read": False,
                "read_at": None,
                "is_archived": False
            })

        conn.close()

        return AdminSummaryResponse(
            total_notifications=total_notifs,
            total_delivered=status_counts.get("delivered", 0),
            total_failed=status_counts.get("failed", 0),
            total_skipped=status_counts.get("skipped", 0),
            total_not_configured=status_counts.get("not_configured", 0),
            by_category=cat_counts,
            by_severity=sev_counts,
            by_channel=chan_counts,
            recent_alerts=recent_alerts
        )

    def get_delivery_logs(
        self,
        limit: int = 50,
        offset: int = 0,
        channel: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[AdminDeliveryLogItem]:
        conn = self.get_conn()
        cur = conn.cursor()

        query = """
            SELECT d.id, d.notification_id, d.recipient_id, u.name as recipient_name,
                   d.channel, d.status, d.attempt_count, d.error_message, d.sent_at,
                   n.title, n.category
            FROM notification_deliveries d
            LEFT JOIN users u ON d.recipient_id = u.id
            LEFT JOIN notifications n ON d.notification_id = n.id
            WHERE 1=1
        """
        params = []
        if channel:
            query += " AND d.channel = ?"
            params.append(channel)
        if status:
            query += " AND d.status = ?"
            params.append(status)

        query += " ORDER BY d.sent_at DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cur.execute(query, params)
        rows = cur.fetchall()
        conn.close()

        return [
            AdminDeliveryLogItem(
                id=r["id"],
                notification_id=r["notification_id"],
                recipient_id=r["recipient_id"],
                recipient_name=r["recipient_name"] or r["recipient_id"],
                channel=r["channel"],
                status=r["status"],
                attempt_count=r["attempt_count"],
                error_message=r["error_message"],
                sent_at=str(r["sent_at"]),
                title=r["title"],
                category=r["category"]
            )
            for r in rows
        ]
