"""
main.py — Enoki orchestrator running on Raspberry Pi 5

Reads from two serial ports:
  - XIAO ESP32-S3: face/eye presence at 10Hz
  - Arduino UNO Q: fused state label at 1Hz (also receives actuation commands)

Every 15 minutes or on a state-change trigger, calls Claude API.
Claude response is parsed and forwarded to Arduino as a command JSON.
"""

import json
import time
import threading
import logging
from datetime import datetime

import serial

from claude_client import ClaudeClient
from state_machine import StateMachine
from pattern_learner import PatternLearner
from actuator_client import ActuatorClient
from vision import VisionProcessor
from tts import TTSEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("enoki")

# ── Serial port config ────────────────────────────────────────────────────────
XIAO_PORT   = "/dev/ttyUSB0"   # XIAO ESP32-S3 Sense — face detection
ARDUINO_PORT = "/dev/ttyUSB1"  # Arduino UNO Q — sensor fusion + actuation
BAUD = 115200

# ── Timing ────────────────────────────────────────────────────────────────────
CLAUDE_INTERVAL_SECONDS = 15 * 60   # 15 minutes baseline
MIN_CLAUDE_INTERVAL     = 60        # never call faster than 1/min even on triggers


class EnokiOrchestrator:
    def __init__(self):
        self.xiao_serial    = serial.Serial(XIAO_PORT,   BAUD, timeout=1)
        self.arduino_serial = serial.Serial(ARDUINO_PORT, BAUD, timeout=1)

        self.claude   = ClaudeClient()
        self.sm       = StateMachine()
        self.learner  = PatternLearner()
        self.actuator = ActuatorClient(self.arduino_serial)
        self.vision   = VisionProcessor()
        self.tts      = TTSEngine()

        # Shared state — written by reader threads, read by main loop
        self._lock          = threading.Lock()
        self.xiao_data      = {"face": False, "eyes_open": False}
        self.arduino_data   = {"state": "AWAY", "confidence": 0.0, "sensors": {}}
        self.vision_data    = {"eye_aspect_ratio": 1.0, "gaze_score": 1.0}

        self.last_claude_call = 0.0
        self.last_state       = "AWAY"
        self.enoki_pose       = "full_droop"
        self.session_start    = time.time()
        self.session_focus_seconds = 0.0
        self.nudge_history    = []   # [(timestamp, nudge_worked: bool)]

    # ── Background reader threads ─────────────────────────────────────────────

    def _read_xiao(self):
        """Parse JSON lines from XIAO at 10Hz into self.xiao_data."""
        while True:
            try:
                raw = self.xiao_serial.readline().decode("utf-8", errors="ignore").strip()
                if not raw:
                    continue
                data = json.loads(raw)
                with self._lock:
                    self.xiao_data = data
            except (json.JSONDecodeError, serial.SerialException) as e:
                log.warning("XIAO read error: %s", e)

    def _read_arduino(self):
        """Parse JSON lines from Arduino at 1Hz into self.arduino_data."""
        while True:
            try:
                raw = self.arduino_serial.readline().decode("utf-8", errors="ignore").strip()
                if not raw:
                    continue
                data = json.loads(raw)
                with self._lock:
                    self.arduino_data = data
            except (json.JSONDecodeError, serial.SerialException) as e:
                log.warning("Arduino read error: %s", e)

    def _run_vision(self):
        """Continuously update vision_data from MediaPipe webcam loop."""
        for frame_result in self.vision.stream():
            with self._lock:
                self.vision_data = frame_result

    # ── State helpers ─────────────────────────────────────────────────────────

    def _snapshot(self):
        """Return a consistent snapshot of all sensor state."""
        with self._lock:
            return (
                dict(self.xiao_data),
                dict(self.arduino_data),
                dict(self.vision_data),
            )

    def _session_focus_pct(self):
        elapsed = max(time.time() - self.session_start, 1)
        return round(100 * self.session_focus_seconds / elapsed)

    def _build_claude_payload(self, current_state, state_duration):
        pattern_summary, slump_in_min = self.learner.get_context(current_state)
        recent = self.sm.recent_history(n=6)
        return {
            "current_state":               current_state,
            "state_duration_seconds":      round(state_duration),
            "session_focus_percentage":    self._session_focus_pct(),
            "session_duration_minutes":    round((time.time() - self.session_start) / 60),
            "predicted_slump_in_minutes":  slump_in_min,
            "historical_pattern_summary":  pattern_summary,
            "time_of_day":                 datetime.now().strftime("%H:%M"),
            "recent_state_history":        recent,
            "enoki_current_pose":          self.enoki_pose,
            "nudge_effectiveness":         self._nudge_effectiveness(),
        }

    def _nudge_effectiveness(self):
        if not self.nudge_history:
            return "no data"
        recent = self.nudge_history[-5:]
        worked = sum(1 for _, ok in recent if ok)
        return f"{worked}/{len(recent)} recent nudges improved focus"

    def _apply_claude_response(self, response: dict):
        """Send Claude's command to Arduino and TTS."""
        self.enoki_pose = response.get("enoki_mood", self.enoki_pose)
        self.actuator.send_command(response)
        if response.get("speak_message") and response.get("message"):
            self.tts.speak(response["message"])

    def _record_nudge_outcome(self, state_before, state_after_60s):
        worked = state_before in ("IDLE", "DOZING") and state_after_60s == "FOCUSED"
        self.nudge_history.append((time.time(), worked))
        if len(self.nudge_history) > 50:
            self.nudge_history.pop(0)

    # ── Main loop ─────────────────────────────────────────────────────────────

    def run(self):
        # Start background threads
        for target in (self._read_xiao, self._read_arduino, self._run_vision):
            t = threading.Thread(target=target, daemon=True)
            t.start()

        log.info("Enoki orchestrator started.")
        pending_nudge_check = None   # (trigger_time, state_at_trigger)

        while True:
            xiao, arduino, vision = self._snapshot()
            current_state    = arduino.get("state", "AWAY")
            state_duration   = self.sm.update(current_state, xiao, vision)

            # Accumulate focus time
            if current_state == "FOCUSED":
                self.session_focus_seconds += 1  # called ~1Hz

            # Log to SQLite
            self.learner.log_state(current_state, arduino.get("sensors", {}))

            # Check if a nudge outcome can be recorded (60s after nudge)
            if pending_nudge_check:
                trigger_time, state_at_trigger = pending_nudge_check
                if time.time() - trigger_time >= 60:
                    self._record_nudge_outcome(state_at_trigger, current_state)
                    pending_nudge_check = None

            # Deterministic nudge rules from state machine
            sm_action = self.sm.check_triggers(current_state, state_duration)

            # Decide whether to call Claude
            now = time.time()
            time_since_claude = now - self.last_claude_call
            should_call = (
                time_since_claude >= CLAUDE_INTERVAL_SECONDS
                or (sm_action == "TRIGGER_CLAUDE" and time_since_claude >= MIN_CLAUDE_INTERVAL)
            )

            if should_call:
                payload = self._build_claude_payload(current_state, state_duration)
                log.info("Calling Claude. State=%s duration=%ds", current_state, state_duration)
                try:
                    response = self.claude.call(payload)
                    self._apply_claude_response(response)
                    self.last_claude_call = now
                    if sm_action == "TRIGGER_CLAUDE":
                        pending_nudge_check = (now, current_state)
                    log.info("Claude response applied: mood=%s", response.get("enoki_mood"))
                except Exception as e:
                    log.error("Claude call failed: %s", e)

            self.last_state = current_state
            time.sleep(1)


if __name__ == "__main__":
    EnokiOrchestrator().run()
