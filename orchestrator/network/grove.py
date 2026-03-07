"""
grove.py — Grove state aggregation, session management, LED mapping.

Aggregates member states from cloud_sync. Maps members to LED positions.
Provides get_grove_context() for Claude payloads.
"""

import logging
from typing import Any

log = logging.getLogger("enoki.network.grove")

# LED position per grove member (0-based index on NeoPixel ring)
# focused=green, idle=amber, away=dark
STATE_TO_LED = {"FOCUSED": [20, 200, 60], "IDLE": [255, 140, 0], "DOZING": [255, 100, 0], "AWAY": [0, 0, 0]}


class GroveManager:
    """
    Aggregates grove member states and provides context for Claude.
    Manages session state (propose, accept, active, complete).
    """

    def __init__(self, user_id: str, grove_id: str):
        self._user_id = user_id
        self._grove_id = grove_id
        self._members: list[dict[str, Any]] = []  # [{user_id, display_name, state, ...}]
        self._lock = __import__("threading").Lock()
        self._session_active = False
        self._session_remaining_min = 0

    def update_members(self, records: list):
        """Update member state from cloud_sync callback."""
        with self._lock:
            for r in records:
                uid = r.get("user_id")
                state = r.get("state", "AWAY")
                if uid:
                    existing = next((m for m in self._members if m.get("user_id") == uid), None)
                    if existing:
                        existing["state"] = state
                        existing["focus_score"] = r.get("focus_score", 0)
                        existing["today_focus_hours"] = r.get("today_focus_hours", 0)
                        existing["in_session"] = r.get("in_session", False)
                    else:
                        self._members.append({
                            "user_id": uid,
                            "display_name": r.get("display_name", "?"),
                            "state": state,
                            "focus_score": r.get("focus_score", 0),
                            "today_focus_hours": r.get("today_focus_hours", 0),
                            "in_session": r.get("in_session", False),
                        })

    def get_grove_context(self) -> dict:
        """Return grove context dict for Claude payload."""
        with self._lock:
            focused = sum(1 for m in self._members if m.get("state") == "FOCUSED")
            total = len(self._members) or 1
            return {
                "members_focused": focused,
                "members_total": total,
                "grove_session_active": self._session_active,
                "grove_session_remaining_min": self._session_remaining_min,
                "member_states": [m.get("state", "AWAY") for m in self._members],
            }

    def get_grove_leds(self) -> list[list[int]]:
        """Return list of [r,g,b] per member for LED ring."""
        with self._lock:
            return [STATE_TO_LED.get(m.get("state", "AWAY"), [0, 0, 0]) for m in self._members]

    def set_session(self, active: bool, remaining_min: int = 0):
        self._session_active = active
        self._session_remaining_min = remaining_min

    def get_context(self) -> dict:
        """Alias for get_grove_context."""
        return self.get_grove_context()

    def get_member_led_states(self) -> list[list[int]]:
        """Alias for get_grove_leds. Returns list of [r,g,b] per member."""
        return self.get_grove_leds()


# Alias for main orchestrator
GroveState = GroveManager
