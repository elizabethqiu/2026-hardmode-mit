"""
state_machine.py — Deterministic short-term rules for Enoki.

Refactored from pi/state_machine.py. Configurable thresholds.
Uses AWAY_SLEEP_THRESHOLD: when AWAY > threshold, suppress nudges.
Uses vision_data eye_aspect_ratio to help detect dozing.
"""

import logging
import time
from collections import deque
from typing import Any

log = logging.getLogger("enoki.brain.sm")


class StateMachine:
    def __init__(
        self,
        dozing_threshold: int = 90,
        idle_threshold: int = 300,
        focused_break_threshold: int = 25 * 60,
        away_sleep_threshold: int = 10 * 60,
        history_maxlen: int = 20,
    ):
        self._dozing_threshold = dozing_threshold
        self._idle_threshold = idle_threshold
        self._focused_break_threshold = focused_break_threshold
        self._away_sleep_threshold = away_sleep_threshold
        self._current_state = "AWAY"
        self._state_start = time.time()
        self._history = deque(maxlen=history_maxlen)
        self._nudge_fired = False
        self._away_since = time.time()

    def update(self, new_state: str, xiao_data: dict, vision_data: dict) -> float:
        """
        Called each second with fresh sensor state.
        Returns seconds the current state has been active.
        """
        now = time.time()

        if new_state == "AWAY":
            if self._current_state != "AWAY":
                self._away_since = now
        else:
            self._away_since = None

        if new_state != self._current_state:
            log.info(
                "State transition: %s → %s (was for %.0fs)",
                self._current_state,
                new_state,
                now - self._state_start,
            )
            self._history.append((now, self._current_state))
            self._current_state = new_state
            self._state_start = now
            self._nudge_fired = False

        return now - self._state_start

    def check_triggers(self, current_state: str, state_duration: float, vision_data: dict | None = None) -> str:
        """
        Returns "TRIGGER_CLAUDE" if a deterministic rule says Claude should be called now, else "NONE".
        When AWAY > away_sleep_threshold, return "NONE" (dim, no nudges).
        Uses eye_aspect_ratio < 0.2 to help detect dozing when state is IDLE.
        """
        if self._nudge_fired:
            return "NONE"

        # AWAY for too long — suppress all nudges
        if current_state == "AWAY" and state_duration >= self._away_sleep_threshold:
            return "NONE"

        should_trigger = False

        if current_state == "DOZING" and state_duration >= self._dozing_threshold:
            log.info("Trigger: DOZING >%ds", self._dozing_threshold)
            should_trigger = True

        elif current_state == "IDLE" and state_duration >= self._idle_threshold:
            # Optional: use low eye_aspect_ratio to treat IDLE as dozing
            ear = (vision_data or {}).get("eye_aspect_ratio", 1.0)
            if ear < 0.2:
                log.info("Trigger: IDLE with closed eyes (EAR=%.2f) >%ds", ear, self._idle_threshold)
            else:
                log.info("Trigger: IDLE >%ds", self._idle_threshold)
            should_trigger = True

        elif current_state == "FOCUSED" and state_duration >= self._focused_break_threshold:
            log.info("Trigger: FOCUSED >%ds, suggest break", self._focused_break_threshold)
            should_trigger = True

        if should_trigger:
            self._nudge_fired = True
            return "TRIGGER_CLAUDE"

        return "NONE"

    def recent_history(self, n: int = 6) -> list:
        """Return the n most recent state labels."""
        items = list(self._history)[-n:]
        result = [state for _, state in items]
        result.append(self._current_state)
        return result[-n:]

    @property
    def current_state(self) -> str:
        return self._current_state

    @property
    def state_duration(self) -> float:
        return time.time() - self._state_start
