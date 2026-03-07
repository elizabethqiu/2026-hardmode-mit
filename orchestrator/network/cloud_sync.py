"""
cloud_sync.py — Supabase real-time publish/subscribe for grove state.

Publishes local focus state every ~30s. Subscribes to grove channel for member updates.
"""

import json
import logging
import threading
import time
from typing import Callable

log = logging.getLogger("enoki.network.cloud_sync")


class CloudSync:
    """
    Syncs focus state to Supabase and receives grove member updates.
    Gracefully degrades when Supabase is not configured.
    """

    def __init__(self, supabase_url: str, supabase_key: str, user_id: str, grove_id: str):
        self._url = supabase_url.strip()
        self._key = supabase_key.strip()
        self._user_id = user_id.strip()
        self._grove_id = grove_id.strip()
        self._client = None
        self._channel = None
        self._on_member_update: Callable[[list], None] | None = None
        self._publish_interval = 30
        self._last_publish = 0.0
        self._running = False
        self._thread: threading.Thread | None = None

    def set_on_member_update(self, callback: Callable[[list], None]):
        """Called when grove member states are received."""
        self._on_member_update = callback

    def _ensure_client(self):
        if self._client is None and self._url and self._key:
            try:
                from supabase import create_client
                self._client = create_client(self._url, self._key)
                log.info("Supabase client connected")
            except ImportError:
                log.warning("supabase-py not installed — cloud sync disabled")
            except Exception as e:
                log.warning("Supabase init failed: %s", e)

    def publish(self, state: str, focus_score: float, session_minutes: int,
                today_focus_hours: float, in_sprint: bool, mushroom_mood: str):
        """Upsert focus state to focus_states table."""
        self._ensure_client()
        if not self._client or not self._user_id or not self._grove_id:
            return
        try:
            self._client.table("focus_states").upsert({
                "user_id": self._user_id,
                "grove_id": self._grove_id,
                "state": state,
                "focus_score": focus_score,
                "session_minutes": session_minutes,
                "today_focus_hours": today_focus_hours,
                "in_sprint": in_sprint,
                "mushroom_mood": mushroom_mood,
            }, on_conflict="user_id").execute()
            self._last_publish = time.time()
        except Exception as e:
            log.warning("Cloud publish failed: %s", e)

    def _subscribe(self):
        """Subscribe to grove channel for real-time member updates."""
        self._ensure_client()
        if not self._client or not self._grove_id:
            return
        try:
            self._channel = self._client.channel(f"grove:{self._grove_id}")
            self._channel.on("postgres_changes", {
                "event": "*",
                "schema": "public",
                "table": "focus_states",
                "filter": f"grove_id=eq.{self._grove_id}",
            }, self._handle_change)
            self._channel.subscribe()
            log.info("Subscribed to grove channel %s", self._grove_id)
        except Exception as e:
            log.warning("Grove subscribe failed: %s", e)

    def _handle_change(self, payload):
        """Handle realtime change event."""
        try:
            records = payload.get("new") or payload.get("old") or []
            if not isinstance(records, list):
                records = [records] if records else []
            if self._on_member_update and records:
                self._on_member_update(records)
        except Exception as e:
            log.warning("Handle change error: %s", e)

    def start(self):
        """Start background publish loop and subscription."""
        if not self._url or not self._key:
            return
        self._running = True
        self._subscribe()

        def publish_loop():
            while self._running:
                time.sleep(self._publish_interval)
                if self._running and self._last_publish > 0:
                    pass  # Actual publish done by orchestrator each loop

        self._thread = threading.Thread(target=publish_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        if self._channel:
            try:
                self._client.remove_channel(self._channel)
            except Exception:
                pass
