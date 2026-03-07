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
        self._on_nudge: Callable[[str], None] | None = None
        self._nudge_channel = None
        self._publish_interval = 30
        self._last_publish = 0.0
        self._running = False
        self._thread: threading.Thread | None = None

    def set_on_member_update(self, callback: Callable[[list], None]):
        """Called when grove member states are received."""
        self._on_member_update = callback

    def set_on_nudge(self, callback: Callable[[str], None]):
        """Called when a grove nudge arrives for this user. Receives the message string."""
        self._on_nudge = callback

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
                today_focus_hours: float, in_sprint: bool, mushroom_mood: str):  # in_sprint kept for DB column compat
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
        """Handle realtime change event for focus_states."""
        try:
            records = payload.get("new") or payload.get("old") or []
            if not isinstance(records, list):
                records = [records] if records else []
            if self._on_member_update and records:
                self._on_member_update(records)
        except Exception as e:
            log.warning("Handle change error: %s", e)

    def _subscribe_nudges(self):
        """Subscribe to grove_nudges for this user (group + individual nudges)."""
        self._ensure_client()
        if not self._client or not self._grove_id or not self._user_id:
            return
        try:
            self._nudge_channel = self._client.channel(f"nudges:{self._grove_id}:{self._user_id}")
            # Individual nudges targeted at this user
            self._nudge_channel.on("postgres_changes", {
                "event": "INSERT",
                "schema": "public",
                "table": "grove_nudges",
                "filter": f"target_user_id=eq.{self._user_id}",
            }, self._handle_nudge)
            # Group nudges (target_user_id is null)
            self._nudge_channel.on("postgres_changes", {
                "event": "INSERT",
                "schema": "public",
                "table": "grove_nudges",
                "filter": f"grove_id=eq.{self._grove_id}",
            }, self._handle_nudge)
            self._nudge_channel.subscribe()
            log.info("Subscribed to grove_nudges for user %s", self._user_id)
        except Exception as e:
            log.warning("Grove nudge subscribe failed: %s", e)

    def _handle_nudge(self, payload):
        """Handle incoming grove nudge. Fires on_nudge callback with the message."""
        try:
            record = payload.get("new") or {}
            if not isinstance(record, dict):
                return
            # Skip nudges targeted at other users
            target = record.get("target_user_id")
            if target and target != self._user_id:
                return
            message = record.get("message", "").strip()
            if message and self._on_nudge:
                log.info("Grove nudge received: %s", message)
                self._on_nudge(message)
        except Exception as e:
            log.warning("Handle nudge error: %s", e)

    def start(self):
        """Start background publish loop and subscription."""
        if not self._url or not self._key:
            return
        self._running = True
        self._subscribe()
        self._subscribe_nudges()

        def publish_loop():
            while self._running:
                time.sleep(self._publish_interval)
                if self._running and self._last_publish > 0:
                    pass  # Actual publish done by orchestrator each loop

        self._thread = threading.Thread(target=publish_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        for ch in (self._channel, self._nudge_channel):
            if ch:
                try:
                    self._client.remove_channel(ch)
                except Exception:
                    pass
