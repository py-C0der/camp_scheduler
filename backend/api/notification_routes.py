"""
FastAPI REST & WebSocket Router for Module 6: CIT Campus Notification, Alerts and Communication Management System.
Implements all Section 12 endpoints with authentication, role enforcement, and real-time streaming.
"""

from typing import Dict, Any, List, Optional
import json
import asyncio
from fastapi import APIRouter, Depends, HTTPException, Query, Header, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse

from backend.notifications.notification_service import notification_service, NotificationService
from backend.notifications.websocket_manager import ws_manager
from backend.schemas.notification import (
    NotificationListResponse,
    UnreadCountResponse,
    NotificationDetailResponse,
    MarkReadResponse,
    AdminSummaryResponse,
    AdminDeliveryLogItem,
    TestProviderRequest,
    TestProviderResponse
)
from backend.schemas.notification_preference import (
    NotificationPreferenceResponse,
    NotificationPreferenceUpdate
)

router = APIRouter(prefix="/api/notifications", tags=["Notification Management (Module 6)"])
admin_router = APIRouter(prefix="/api/admin/notifications", tags=["Admin Notification Management (Module 6)"])


def get_current_user(
    x_user_id: Optional[str] = Header("admin_1"),
    x_user_role: Optional[str] = Header("admin"),
    x_user_name: Optional[str] = Header("Dean Academics (Admin)")
) -> Dict[str, Any]:
    """Extracts simulated authenticated user from headers."""
    return {
        "id": x_user_id or "admin_1",
        "role": x_user_role or "admin",
        "name": x_user_name or "Dean Academics (Admin)"
    }


# 1. GET /api/notifications
@router.get("", response_model=NotificationListResponse)
def get_user_notifications(
    category: Optional[str] = Query(None),
    is_read: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Returns the authenticated user's isolated notification inbox."""
    return notification_service.get_user_notifications(
        user_id=current_user["id"],
        category=category,
        is_read=is_read,
        limit=limit,
        offset=offset,
        search=search
    )


# 2. GET /api/notifications/unread-count
@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    user_id: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Returns unread notification count and categorical breakdown."""
    target_id = user_id or current_user["id"]
    # Allow user to check own count, or admin to check any
    if target_id != current_user["id"] and current_user["role"] != "admin":
        target_id = current_user["id"]
    return notification_service.get_unread_count(user_id=target_id)


# 3. GET /api/notifications/preferences
@router.get("/preferences", response_model=NotificationPreferenceResponse)
def get_preferences(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns authenticated user's notification preferences."""
    return notification_service.preference_manager.get_user_preferences(user_id=current_user["id"])


# 4. PATCH /api/notifications/preferences
@router.patch("/preferences", response_model=NotificationPreferenceResponse)
def update_preferences(
    updates: NotificationPreferenceUpdate,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Updates authenticated user's channel and category preferences."""
    return notification_service.preference_manager.update_user_preferences(
        user_id=current_user["id"],
        updates=updates
    )


# 5. POST /api/notifications/mark-all-read
@router.post("/mark-all-read", response_model=MarkReadResponse)
def mark_all_notifications_read(
    category: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Marks all eligible notifications as read for current user."""
    return notification_service.mark_all_read(user_id=current_user["id"], category=category)


# 6. GET /api/notifications/{notification_id}
@router.get("/{notification_id}", response_model=NotificationDetailResponse)
def get_notification_details(
    notification_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Returns notification details and delivery records."""
    return notification_service.get_notification_by_id(
        notification_id=notification_id,
        user_id=current_user["id"],
        user_role=current_user["role"]
    )


# 7. PATCH /api/notifications/{notification_id}/read
@router.patch("/{notification_id}/read", response_model=MarkReadResponse)
def mark_notification_read(
    notification_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Marks an individual notification as read."""
    return notification_service.mark_as_read(
        notification_id=notification_id,
        user_id=current_user["id"]
    )


# 8. DELETE /api/notifications/{notification_id} (Archive)
@router.delete("/{notification_id}")
def archive_notification(
    notification_id: str,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Archives or dismisses a notification from user's active view."""
    success = notification_service.archive_notification(
        notification_id=notification_id,
        user_id=current_user["id"]
    )
    if not success:
        raise HTTPException(status_code=404, detail="Notification not found.")
    return {"status": "success", "message": "Notification archived."}


# ----------------- Real-Time Communication Endpoints -----------------

# 9. WebSocket /api/notifications/ws
@router.websocket("/ws")
async def websocket_notifications(websocket: WebSocket, user_id: str = "admin_1"):
    """WebSocket connection for instant real-time notification alerts."""
    await ws_manager.connect(user_id, websocket)
    try:
        while True:
            data = await websocket.receive_text()
            # Echo heartbeat ping/pong
            if data == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        await ws_manager.disconnect(user_id, websocket)


# 10. Server-Sent Events (SSE) Fallback
@router.get("/stream")
async def sse_notifications(user_id: str = "admin_1"):
    """Server-Sent Events fallback for environments where WebSockets are unavailable."""
    async def event_generator():
        last_cnt = -1
        while True:
            cnt_res = notification_service.get_unread_count(user_id)
            if cnt_res.unread_count != last_cnt:
                last_cnt = cnt_res.unread_count
                yield f"data: {json.dumps(cnt_res.dict())}\n\n"
            await asyncio.sleep(5)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


# ----------------- Admin Analytics Endpoints -----------------

# 11. GET /api/admin/notifications/summary
@admin_router.get("/summary", response_model=AdminSummaryResponse)
def get_admin_summary(current_user: Dict[str, Any] = Depends(get_current_user)):
    """Returns administrative notification statistics and delivery health."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required.")
    return notification_service.delivery_tracker.get_admin_summary()


# 12. GET /api/admin/notifications/delivery-logs
@admin_router.get("/delivery-logs", response_model=List[AdminDeliveryLogItem])
def get_admin_delivery_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    channel: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Returns comprehensive delivery history for authorized administrators."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required.")
    return notification_service.delivery_tracker.get_delivery_logs(
        limit=limit,
        offset=offset,
        channel=channel,
        status=status
    )


# 13. POST /api/admin/notifications/test
@admin_router.post("/test", response_model=TestProviderResponse)
def test_communication_provider(
    req: TestProviderRequest,
    current_user: Dict[str, Any] = Depends(get_current_user)
):
    """Allows authorized administrators to test configured communication providers."""
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required.")
    return notification_service.test_communication_provider(
        channel=req.channel,
        target=req.target,
        user_id=current_user["id"]
    )
