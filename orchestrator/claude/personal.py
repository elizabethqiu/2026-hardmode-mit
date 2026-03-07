"""
personal.py — Personal Claude: nudges, conversation, adaptive personality.

Maintains ~20-message conversation history. Returns hardware command schema.
"""

import json
import logging
from typing import Any

from .base import ClaudeBase
from .prompts import PERSONAL_SYSTEM_PROMPT

log = logging.getLogger("enoki.claude.personal")

HARDWARE_KEYS = {
    "enoki_mood", "stem_height", "cap_openness",
    "led_color", "led_brightness", "message",
    "speak_message", "nudge_intensity",
}


class PersonalClaude(ClaudeBase):
    """Personal Claude with conversation memory and adaptive nudging."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._history: list[dict[str, Any]] = []
        self._max_history = 20

    def call(self, payload: dict) -> dict:
        """
        Send sensor payload to Claude, get hardware command.
        Maintains conversation history for context.
        """
        user_content = "Current sensor data and context:\n" + json.dumps(payload, indent=2)
        self._history.append({"role": "user", "content": user_content})

        # Trim history to max size (keep pairs)
        while len(self._history) > self._max_history:
            self._history.pop(0)

        raw = self._call_raw(
            system=PERSONAL_SYSTEM_PROMPT,
            messages=self._history,
        )

        # Parse JSON from response
        parsed = self._parse_json_response(raw)
        self._validate_hardware(parsed)

        # Add assistant response to history
        self._history.append({"role": "assistant", "content": raw})

        return parsed

    def add_user_message(self, text: str):
        """Add a user voice/conversation message to history."""
        self._history.append({"role": "user", "content": text})
        while len(self._history) > self._max_history:
            self._history.pop(0)

    def add_assistant_message(self, text: str):
        """Add assistant response to history (e.g. after tool execution)."""
        self._history.append({"role": "assistant", "content": text})
        while len(self._history) > self._max_history:
            self._history.pop(0)

    def clear_history(self):
        """Reset conversation history."""
        self._history.clear()

    def _validate_hardware(self, r: dict):
        missing = HARDWARE_KEYS - set(r.keys())
        if missing:
            raise ValueError(f"Personal Claude response missing keys: {missing}")
        assert 0.0 <= r["stem_height"] <= 1.0, "stem_height out of range"
        assert 0.0 <= r["cap_openness"] <= 1.0, "cap_openness out of range"
        assert 0.0 <= r["led_brightness"] <= 1.0, "led_brightness out of range"
        assert len(r["led_color"]) == 3, "led_color must be [r,g,b]"
        assert r["enoki_mood"] in (
            "focused", "watchful", "concerned", "gentle", "urgent"
        ), f"Unknown mood: {r['enoki_mood']}"
