"""
state_machine.py — Deterministic short-term rules for Enoki

No AI required here. Rules are:
  DOZING  > 90s  → trigger Claude nudge
  IDLE    > 5min → trigger Claude nudge
  FOCUSED > 25min → suggest break (trigger Claude)
  AWAY    > 10min → dim completely, no nudges

Tracks state duration and recent history.
"""

import time
from collections import deque
import logging

log = logging.getLogger("enoki.sm")

# Thresholds in seconds
DOZING_NUDGE_THRESHOLD   =  90
IDLE_NUDGE_THRESHOLD     = 300   # 5 min
FOCUSED_BREAK_THRESHOLD  = 25 * 60  # 25 min
AWAY_SLEEP_THRESHOLD     = 10 * 60  # 10 min


class StateMachine:
    def __init__(self):
        self._current_state      = "AWAY"
        self._state_start        = time.time()
        self._history            = deque(maxlen=20)  # (timestamp, state)
        self._nudge_fired        = False  # prevent re-firing until state changes

    def update(self, new_state: str, xiao_data: dict, vision_data: dict) -> float:
        """
        Called each second with fresh sensor state.
        Returns seconds the current state has been active.
        """
        now = time.time()

        if new_state != self._current_state:
            log.info("State transition: %s → %s (was for %.0fs)",
                     self._current_state, new_state, now - self._state_start)
            self._history.append((now, self._current_state))
            self._current_state = new_state
            self._state_start   = now
            self._nudge_fired   = False

        return now - self._state_start

    def check_triggers(self, current_state: str, state_duration: float) -> str:
        """
        Returns "TRIGGER_CLAUDE" if a deterministic rule says Claude should
        be called now, else "NONE".
        """
        if self._nudge_fired:
            return "NONE"

        should_trigger = False

        if current_state == "DOZING" and state_duration >= DOZING_NUDGE_THRESHOLD:
            log.info("Trigger: DOZING >%ds", DOZING_NUDGE_THRESHOLD)
            should_trigger = True

        elif current_state == "IDLE" and state_duration >= IDLE_NUDGE_THRESHOLD:
            log.info("Trigger: IDLE >%ds", IDLE_NUDGE_THRESHOLD)
            should_trigger = True

        elif current_state == "FOCUSED" and state_duration >= FOCUSED_BREAK_THRESHOLD:
            log.info("Trigger: FOCUSED >%ds, suggest break", FOCUSED_BREAK_THRESHOLD)
            should_trigger = True

        if should_trigger:
            self._nudge_fired = True
            return "TRIGGER_CLAUDE"

        return "NONE"

    def recent_history(self, n: int = 6) -> list:
        """Return the n most recent state labels."""
        items = list(self._history)[-n:]
        result = [state for _, state in items]
        # Pad with current state at the end
        result.append(self._current_state)
        return result[-n:]

    @property
    def current_state(self) -> str:
        return self._current_state

    @property
    def state_duration(self) -> float:
        return time.time() - self._state_start
