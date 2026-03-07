"""
cloud_sync.py — Supabase real-time publish/subscribe for grove state.

Publishes local focus state. Subscribes to grove channel for member updates
and grove_nudges for nudge delivery. Fetches initial member state on startup.
"""

import json
import logging
import threading
import time
from typing import Callable, Optional

log = logging.getLogger("enoki.network.cloud_sync")


class CloudSync:
    """
    Syncs focus state to Supabase and receives grove member updates + nudges.
    Gracefully degrades when Supabase is not configured.
    """

    def __init__(self, supabase_url: str, supabase_key: str, user_id: str, grove_id: str):
        self._url = supabase_url.strip()
        self._key = supabase_key.strip()
        self._user_id = user_id.strip()
        self._grove_id = grove_id.strip()
        self._client = None
        self._focus_channel = None
        self._nudge_channel = None
        self._sprint_channel = None
        self._on_member_update: Optional[Callable[[list], None]] = None
        self._on_grove_nudge: Optional[Callable[[dict], None]] = None
        self._on_sprint_change: Optional[Callable[[dict], None]] = None
        self._last_publish = 0.0
        self._last_history_insert = 0.0
        self._running = False
        self._thread: Optional[threading.Thread] = None

        self._grove_claude_url: Optional[str] = None
        self._last_grove_claude_call = 0.0
        self._grove_claude_interval = 60
        self._on_grove_settings: Optional[Callable[[dict], None]] = None

    def set_on_member_update(self, callback: Callable[[list], None]):
        self._on_member_update = callback

    def set_on_grove_nudge(self, callback: Callable[[dict], None]):
        self._on_grove_nudge = callback

    def set_on_sprint_change(self, callback: Callable[[dict], None]):
        self._on_sprint_change = callback

    def set_on_grove_settings(self, callback: Callable[[dict], None]):
        self._on_grove_settings = callback

    def set_grove_claude_url(self, url: str):
        self._grove_claude_url = url.strip() if url else None

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

    def _fetch_grove_settings(self):
        """Fetch grove-level settings like daily_goal_hours."""
        self._ensure_client()
        if not self._client or not self._grove_id:
            return
        try:
            result = (
                self._client.table("groves")
                .select("daily_goal_hours")
                .eq("id", self._grove_id)
                .limit(1)
                .execute()
            )
            if result.data and self._on_grove_settings:
                self._on_grove_settings(result.data[0])
                log.info("Loaded grove settings: %s", result.data[0])
        except Exception as e:
            log.debug("Grove settings fetch failed: %s", e)

    def _fetch_initial_members(self):
        """Fetch current grove member states with display names on startup."""
        self._ensure_client()
        if not self._client or not self._grove_id:
            return
        try:
            result = self._client.rpc("get_grove_members_with_names", {
                "p_grove_id": self._grove_id,
            }).execute()

            if result.data and self._on_member_update:
                self._on_member_update(result.data)
                log.info("Loaded %d grove members", len(result.data))
        except Exception:
            # Fallback: query without RPC if function doesn't exist
            try:
                result = (
                    self._client.table("focus_states")
                    .select("*, users!inner(display_name)")
                    .eq("grove_id", self._grove_id)
                    .execute()
                )
                if result.data and self._on_member_update:
                    records = []
                    for row in result.data:
                        r = dict(row)
                        user_info = r.pop("users", {})
                        r["display_name"] = user_info.get("display_name", "?") if user_info else "?"
                        records.append(r)
                    self._on_member_update(records)
                    log.info("Loaded %d grove members (fallback)", len(records))
            except Exception as e:
                log.warning("Initial member fetch failed: %s", e)

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

    def publish_history(self, state: str, focus_score: float):
        """Insert into focus_history (throttled to once per 60s)."""
        now = time.time()
        if now - self._last_history_insert < 60:
            return
        self._ensure_client()
        if not self._client or not self._user_id or not self._grove_id:
            return
        try:
            self._client.table("focus_history").insert({
                "user_id": self._user_id,
                "grove_id": self._grove_id,
                "state": state,
                "focus_score": focus_score,
            }).execute()
            self._last_history_insert = now
        except Exception as e:
            log.debug("History insert failed (table may not exist yet): %s", e)

    def propose_sprint(self, duration_minutes: int, proposed_by: str = None):
        """Insert a sprint proposal into the sprints table."""
        self._ensure_client()
        if not self._client or not self._grove_id:
            return
        try:
            row = {
                "grove_id": self._grove_id,
                "duration_minutes": duration_minutes,
                "status": "proposed",
            }
            if proposed_by:
                row["proposed_by"] = proposed_by
            self._client.table("sprints").insert(row).execute()
            log.info("Sprint proposed: %d min", duration_minutes)
        except Exception as e:
            log.warning("Sprint propose failed: %s", e)

    def accept_sprint(self, sprint_id: str):
        """Transition a proposed sprint to active."""
        self._ensure_client()
        if not self._client:
            return
        try:
            self._client.table("sprints").update({
                "status": "active",
                "started_at": "now()",
            }).eq("id", sprint_id).eq("status", "proposed").execute()
            log.info("Sprint %s accepted and started", sprint_id)
        except Exception as e:
            log.warning("Sprint accept failed: %s", e)

    def complete_sprint(self, sprint_id: str):
        """Mark an active sprint as completed."""
        self._ensure_client()
        if not self._client:
            return
        try:
            self._client.table("sprints").update({
                "status": "completed",
            }).eq("id", sprint_id).eq("status", "active").execute()
            log.info("Sprint %s completed", sprint_id)
        except Exception as e:
            log.warning("Sprint complete failed: %s", e)

    def invoke_grove_claude(self):
        """Call the grove-claude edge function if enough time has passed."""
        now = time.time()
        if now - self._last_grove_claude_call < self._grove_claude_interval:
            return
        if not self._grove_claude_url or not self._grove_id:
            return

        self._last_grove_claude_call = now
        try:
            import urllib.request
            req = urllib.request.Request(
                self._grove_claude_url,
                data=json.dumps({"grove_id": self._grove_id}).encode("utf-8"),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                body = json.loads(resp.read().decode())
                log.info("Grove Claude invoked: %s", body.get("action", "none"))
        except Exception as e:
            log.warning("Grove Claude invocation failed: %s", e)

    def _subscribe_focus_states(self):
        """Subscribe to focus_states changes for this grove."""
        self._ensure_client()
        if not self._client or not self._grove_id:
            return
        try:
            self._focus_channel = self._client.channel(f"grove:{self._grove_id}")
            self._focus_channel.on("postgres_changes", {
                "event": "*",
                "schema": "public",
                "table": "focus_states",
                "filter": f"grove_id=eq.{self._grove_id}",
            }, self._handle_focus_change)
            self._focus_channel.subscribe()
            log.info("Subscribed to focus_states for grove %s", self._grove_id)
        except Exception as e:
            log.warning("Focus subscribe failed: %s", e)

    def _subscribe_grove_nudges(self):
        """Subscribe to grove_nudges for this grove."""
        self._ensure_client()
        if not self._client or not self._grove_id:
            return
        try:
            self._nudge_channel = self._client.channel(f"nudges:{self._grove_id}")
            self._nudge_channel.on("postgres_changes", {
                "event": "INSERT",
                "schema": "public",
                "table": "grove_nudges",
                "filter": f"grove_id=eq.{self._grove_id}",
            }, self._handle_nudge)
            self._nudge_channel.subscribe()
            log.info("Subscribed to grove_nudges for grove %s", self._grove_id)
        except Exception as e:
            log.warning("Nudge subscribe failed: %s", e)

    def _subscribe_sprints(self):
        """Subscribe to sprints changes for this grove."""
        self._ensure_client()
        if not self._client or not self._grove_id:
            return
        try:
            self._sprint_channel = self._client.channel(f"sprints:{self._grove_id}")
            self._sprint_channel.on("postgres_changes", {
                "event": "*",
                "schema": "public",
                "table": "sprints",
                "filter": f"grove_id=eq.{self._grove_id}",
            }, self._handle_sprint_change)
            self._sprint_channel.subscribe()
            log.info("Subscribed to sprints for grove %s", self._grove_id)
        except Exception as e:
            log.warning("Sprint subscribe failed: %s", e)

    def _handle_focus_change(self, payload):
        try:
            records = payload.get("new") or payload.get("old") or []
            if not isinstance(records, list):
                records = [records] if records else []
            if self._on_member_update and records:
                self._on_member_update(records)
        except Exception as e:
            log.warning("Focus change error: %s", e)

    def _handle_nudge(self, payload):
        try:
            record = payload.get("new")
            if record and self._on_grove_nudge:
                self._on_grove_nudge(record)
        except Exception as e:
            log.warning("Nudge handler error: %s", e)

    def _handle_sprint_change(self, payload):
        try:
            record = payload.get("new")
            if record and self._on_sprint_change:
                self._on_sprint_change(record)
        except Exception as e:
            log.warning("Sprint change error: %s", e)

    def start(self):
        """Start subscriptions, fetch initial state, start background thread."""
        if not self._url or not self._key:
            return
        self._running = True

        self._fetch_grove_settings()
        self._fetch_initial_members()
        self._subscribe_focus_states()
        self._subscribe_grove_nudges()
        self._subscribe_sprints()

        def background_loop():
            while self._running:
                time.sleep(10)
                if self._running and self._grove_claude_url:
                    self.invoke_grove_claude()

        self._thread = threading.Thread(target=background_loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False
        for ch in [self._focus_channel, self._nudge_channel, self._sprint_channel]:
            if ch:
                try:
                    self._client.remove_channel(ch)
                except Exception:
                    pass
