"""
Centralized Event Bus for CIT Campus Platform.
Enables Modules 1-5 to publish domain events without coupling to notification delivery.
"""

import asyncio
from typing import Callable, List, Dict, Any
from backend.notifications.events import NotificationEvent
from backend.notifications.notification_service import notification_service


class EventBus:
    """
    Decoupled publish-subscribe event broker.
    Modules 2-5 publish events after business transactions succeed.
    """

    def __init__(self):
        self.subscribers: List[Callable[[NotificationEvent], None]] = [
            notification_service.process_event
        ]

    def subscribe(self, callback: Callable[[NotificationEvent], None]):
        self.subscribers.append(callback)

    def publish(self, event: NotificationEvent):
        """Dispatches event to all subscribers synchronously or in background."""
        for sub in self.subscribers:
            try:
                sub(event)
            except Exception as ex:
                # Never let notification failures crash main business logic
                print(f"[EventBus Error] Failed to process event {event.event_type}: {ex}")


event_bus = EventBus()
