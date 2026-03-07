"""
grove.py — Grove state aggregation, sprint management, LED mapping, nudge handling.

Aggregates member states from cloud_sync. Maps members to LED positions.
Provides get_grove_context() for Claude payloads. Handles incoming nudges and sprints.
"""

import logging
import time
import threading
from typing import Any, Optional

log = logging.getLogger("enoki.network.grove")

# LED color per focus state
STATE_TO_LED = {
    "FOCUSED": [20, 200, 60],
    "IDLE": [255, 140, 0],
    "DOZING": [255, 100, 0],
    "AWAY": [0, 0, 0],
}


class GroveManager:
    """
    Aggregates grove member states, manages sprints, handles nudges.
    Thread-safe — called from realtime callbacks and main loop.
    """

    def __init__(self, user_id: str, grove_id: str):
        self._user_id = user_id
        self._grove_id = grove_id
        self._members: list[dict[str, Any]] = []
        self._display_names: dict[str, str] = {}  # user_id -> name cache
        self._lock = threading.Lock()

        # Sprint state
        self._sprint_active = False
        self._sprint_remaining_min = 0
        self._sprint_id: Optional[str] = None
        self._sprint_started_at: Optional[float] = None
        self._sprint_duration_min = 0

        # Pending nudge for the main loop to consume
        self._pending_nudge: Optional[dict] = None
        self._pending_celebration = False

    def update_members(self, records: list):
        """Update member state from cloud_sync callback (initial fetch or realtime)."""
        with self._lock:
            for r in records:
                uid = r.get("user_id")
                state = r.get("state", "AWAY")
                if not uid:
                    continue

                # Cache display_name if provided
                name = r.get("display_name")
                if name and name != "?":
                    self._display_names[uid] = name

                existing = next((m for m in self._members if m.get("user_id") == uid), None)
                if existing:
                    existing["state"] = state
                    existing["focus_score"] = r.get("focus_score", 0)
                    existing["today_focus_hours"] = r.get("today_focus_hours", 0)
                    existing["in_sprint"] = r.get("in_sprint", False)
                    existing["session_minutes"] = r.get("session_minutes", 0)
                    if uid in self._display_names:
                        existing["display_name"] = self._display_names[uid]
                else:
                    self._members.append({
                        "user_id": uid,
                        "display_name": self._display_names.get(uid, r.get("display_name", "?")),
                        "state": state,
                        "focus_score": r.get("focus_score", 0),
                        "today_focus_hours": r.get("today_focus_hours", 0),
                        "in_sprint": r.get("in_sprint", False),
                        "session_minutes": r.get("session_minutes", 0),
                    })

    def handle_nudge(self, nudge: dict):
        """
        Handle an incoming grove_nudge record.
        Group nudges go to everyone. Individual nudges only if target matches this user.
        """
        nudge_type = nudge.get("nudge_type", "")
        target = nudge.get("target_user_id")
        message = nudge.get("message", "")

        if nudge_type == "celebration":
            with self._lock:
                self._pending_celebration = True
            log.info("Grove celebration received")
            return

        if nudge_type == "group_nudge":
            with self._lock:
                self._pending_nudge = {"type": "group", "message": message}
            log.info("Group nudge: %s", message)
        elif nudge_type == "individual_nudge" and target == self._user_id:
            with self._lock:
                self._pending_nudge = {"type": "individual", "message": message}
            log.info("Individual nudge for me: %s", message)

    def handle_sprint_change(self, sprint: dict):
        """Handle a sprint insert/update from realtime."""
        status = sprint.get("status", "")
        sprint_id = sprint.get("id", "")
        duration = sprint.get("duration_minutes", 25)

        with self._lock:
            if status == "active":
                self._sprint_active = True
                self._sprint_id = sprint_id
                self._sprint_duration_min = duration
                self._sprint_started_at = time.time()
                self._sprint_remaining_min = duration
                log.info("Sprint started: %d min", duration)
            elif status in ("completed", "cancelled"):
                was_active = self._sprint_active
                self._sprint_active = False
                self._sprint_id = None
                self._sprint_remaining_min = 0
                if was_active and status == "completed":
                    self._pending_celebration = True
                log.info("Sprint %s", status)
            elif status == "proposed":
                self._proposed_sprint_id = sprint_id
                self._proposed_sprint_duration = duration
                log.info("Sprint proposed: %d min by %s", duration, sprint.get("proposed_by"))

    def get_proposed_sprint(self) -> Optional[tuple[str, int]]:
        """Return (sprint_id, duration_min) if there's a pending proposal."""
        with self._lock:
            sid = getattr(self, "_proposed_sprint_id", None)
            dur = getattr(self, "_proposed_sprint_duration", 25)
            return (sid, dur) if sid else None

    def clear_proposed_sprint(self):
        with self._lock:
            self._proposed_sprint_id = None
            self._proposed_sprint_duration = 0

    def check_sprint_expiry(self) -> Optional[str]:
        """Check if active sprint has expired. Returns sprint_id if expired, None otherwise."""
        with self._lock:
            if not self._sprint_active or not self._sprint_started_at:
                return None
            elapsed_min = (time.time() - self._sprint_started_at) / 60
            if elapsed_min >= self._sprint_duration_min:
                return self._sprint_id
            return None

    def consume_pending_nudge(self) -> Optional[dict]:
        """Pop and return any pending nudge. Called by main loop."""
        with self._lock:
            nudge = self._pending_nudge
            self._pending_nudge = None
            return nudge

    def consume_pending_celebration(self) -> bool:
        """Pop and return celebration flag. Called by main loop."""
        with self._lock:
            if self._pending_celebration:
                self._pending_celebration = False
                return True
            return False

    def get_grove_context(self) -> dict:
        """Return grove context dict for Claude payload."""
        with self._lock:
            # Update sprint countdown
            if self._sprint_active and self._sprint_started_at:
                elapsed_min = (time.time() - self._sprint_started_at) / 60
                self._sprint_remaining_min = max(0, self._sprint_duration_min - elapsed_min)

            focused = sum(1 for m in self._members if m.get("state") == "FOCUSED")
            total = len(self._members) or 1
            return {
                "members_focused": focused,
                "members_total": total,
                "grove_sprint_active": self._sprint_active,
                "grove_sprint_remaining_min": round(self._sprint_remaining_min),
                "member_states": [
                    {"name": m.get("display_name", "?"), "state": m.get("state", "AWAY")}
                    for m in self._members
                ],
            }

    def is_sprint_active(self) -> bool:
        with self._lock:
            return self._sprint_active

    def get_grove_leds(self) -> list[list[int]]:
        """Return [r,g,b] per member for LED strip."""
        with self._lock:
            return [STATE_TO_LED.get(m.get("state", "AWAY"), [0, 0, 0]) for m in self._members]

    def set_sprint(self, active: bool, remaining_min: int = 0):
        with self._lock:
            self._sprint_active = active
            self._sprint_remaining_min = remaining_min

    def get_context(self) -> dict:
        return self.get_grove_context()

    def get_member_led_states(self) -> list[list[int]]:
        return self.get_grove_leds()


GroveState = GroveManager
