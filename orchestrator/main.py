"""
main.py — Enoki orchestrator. Merges sensors, brain, Claude, hardware, and grove network.

Runs on laptop. Connects to XIAO (face/eye), Arduino UNO Q (actuators), webcam (MediaPipe),
Mentra glasses (via MiniApp), and Supabase (grove sync).
"""

import argparse
import json
import logging
import threading
import time
from datetime import datetime
from typing import Any, Optional

from config import load_config

log = logging.getLogger("enoki.main")


class EnokiOrchestrator:
    def __init__(self, cfg=None, dev_flags=None):
        self.cfg = cfg or load_config()
        self.dev = dev_flags or argparse.Namespace(no_xiao=False, no_arduino=False, no_vision=False, no_cloud=False)
        self._stop = threading.Event()
        self._lock = threading.Lock()

        # Sensor state
        self.xiao_data = {"face": False, "eyes_open": False}
        self.arduino_data = {"state": "AWAY", "confidence": 0.0, "sensors": {}}
        self.vision_data = {"face_detected": False, "eye_aspect_ratio": 1.0, "gaze_score": 1.0}
        self.glasses_data: dict = {}

        # Serial connections (lazy)
        self._xiao_serial = None
        self._arduino_serial = None

        # Modules (lazy init in run)
        self.claude: Optional[Any] = None
        self.vision_claude: Optional[Any] = None
        self.planner_claude: Optional[Any] = None
        self.sm: Optional[Any] = None
        self.learner: Optional[Any] = None
        self.actuator: Optional[Any] = None
        self.vision: Optional[Any] = None
        self.tts: Optional[Any] = None
        self.glasses_receiver: Optional[Any] = None
        self.cloud_sync: Optional[Any] = None
        self.grove: Optional[Any] = None

        self.last_claude_call = 0.0
        self.enoki_pose = "full_droop"
        self.session_start = time.time()
        self.session_focus_seconds = 0.0
        self.nudge_history: list[tuple[float, bool]] = []
        self.pending_nudge_check: Optional[tuple[float, str]] = None

    def _init_modules(self):
        """Initialize all modules. Called at start of run()."""
        from claude.personal import PersonalClaude
        from claude.vision_analyst import VisionClaude
        from claude.planner import PlannerClaude
        from brain.state_machine import StateMachine
        from brain.pattern_learner import PatternLearner
        from hardware.actuator import ActuatorClient
        from hardware.tts import TTSEngine
        from sensors.webcam import VisionProcessor
        from sensors.glasses_receiver import GlassesReceiver
        from network.cloud_sync import CloudSync
        from network.grove import GroveManager

        c = self.cfg

        self.claude = PersonalClaude(
            api_key=c.ANTHROPIC_API_KEY,
            model=c.CLAUDE_MODEL,
            max_tokens=c.CLAUDE_MAX_TOKENS,
        )
        self.vision_claude = VisionClaude(
            api_key=c.ANTHROPIC_API_KEY,
            model=c.CLAUDE_MODEL,
            max_tokens=256,
        )
        self.planner_claude = PlannerClaude(
            api_key=c.ANTHROPIC_API_KEY,
            model=c.CLAUDE_MODEL,
            max_tokens=512,
        )
        self.sm = StateMachine(
            dozing_threshold=c.DOZING_NUDGE_THRESHOLD,
            idle_threshold=c.IDLE_NUDGE_THRESHOLD,
            focused_break_threshold=c.FOCUSED_BREAK_THRESHOLD,
            away_sleep_threshold=c.AWAY_SLEEP_THRESHOLD,
        )
        self.learner = PatternLearner(db_path=c.DB_PATH, model_path=c.MODEL_PATH, log_interval=c.LOG_INTERVAL)

        if not self.dev.no_arduino:
            try:
                import serial
                self._arduino_serial = serial.Serial(c.ARDUINO_PORT, c.BAUD, timeout=1)
                self.actuator = ActuatorClient(self._arduino_serial)
            except Exception as e:
                log.warning("Arduino not available: %s", e)
                self.actuator = None

        self.tts = TTSEngine(backend=c.TTS_BACKEND, piper_model_path=c.PIPER_MODEL_PATH)

        if not self.dev.no_vision:
            self.vision = VisionProcessor(
                camera_index=c.CAMERA_INDEX,
                fps_target=c.FPS_TARGET,
                min_detection_confidence=c.MEDIAPIPE_DETECTION_CONFIDENCE,
                min_tracking_confidence=c.MEDIAPIPE_TRACKING_CONFIDENCE,
            )
        else:
            self.vision = None

        self.glasses_receiver = GlassesReceiver(host=c.GLASSES_RECEIVER_HOST, port=c.GLASSES_RECEIVER_PORT)
        self.glasses_receiver.set_on_data(lambda d: self._on_glasses_data(d))

        if c.has_cloud and not self.dev.no_cloud:
            self.cloud_sync = CloudSync(c.SUPABASE_URL, c.SUPABASE_KEY, c.USER_ID, c.GROVE_ID)
            self.grove = GroveManager(c.USER_ID, c.GROVE_ID)
            self.cloud_sync.set_on_member_update(self.grove.update_members)
        else:
            self.cloud_sync = None
            self.grove = None

    def _on_glasses_data(self, data: dict):
        """Callback when glasses send data."""
        with self._lock:
            self.glasses_data.update(data)

    def _read_xiao(self):
        if self.dev.no_xiao or not self._xiao_serial:
            return
        while not self._stop.is_set():
            try:
                raw = self._xiao_serial.readline().decode("utf-8", errors="ignore").strip()
                if not raw:
                    continue
                data = json.loads(raw)
                with self._lock:
                    self.xiao_data = data
            except (json.JSONDecodeError, Exception) as e:
                log.debug("XIAO read error: %s", e)

    def _read_arduino(self):
        if not self._arduino_serial:
            return
        while not self._stop.is_set():
            try:
                raw = self._arduino_serial.readline().decode("utf-8", errors="ignore").strip()
                if not raw:
                    continue
                data = json.loads(raw)
                with self._lock:
                    self.arduino_data = data
            except (json.JSONDecodeError, Exception) as e:
                log.debug("Arduino read error: %s", e)

    def _run_vision(self):
        if not self.vision:
            return
        for frame_result in self.vision.stream():
            if self._stop.is_set():
                break
            with self._lock:
                self.vision_data = frame_result

    def _snapshot(self):
        with self._lock:
            return (
                dict(self.xiao_data),
                dict(self.arduino_data),
                dict(self.vision_data),
                dict(self.glasses_data),
            )

    def _session_focus_pct(self):
        elapsed = max(time.time() - self.session_start, 1)
        return round(100 * self.session_focus_seconds / elapsed)

    def _build_claude_payload(self, current_state: str, state_duration: float) -> dict:
        pattern_summary, slump_in_min = self.learner.get_context(current_state)
        recent = self.sm.recent_history(n=self.cfg.RECENT_HISTORY_N)
        payload = {
            "current_state": current_state,
            "state_duration_seconds": round(state_duration),
            "session_focus_percentage": self._session_focus_pct(),
            "session_duration_minutes": round((time.time() - self.session_start) / 60),
            "predicted_slump_in_minutes": slump_in_min,
            "historical_pattern_summary": pattern_summary,
            "time_of_day": datetime.now().strftime("%H:%M"),
            "recent_state_history": recent,
            "enoki_current_pose": self.enoki_pose,
            "nudge_effectiveness": self._nudge_effectiveness(),
        }
        if self.glasses_data:
            payload["glasses"] = {
                "last_transcription": self.glasses_data.get("transcription"),
                "last_photo_analysis": self.glasses_data.get("photo_analysis"),
                "wearing": self.glasses_data.get("wearing", False),
            }
        if self.grove:
            payload["grove"] = self.grove.get_context()
        return payload

    def _nudge_effectiveness(self) -> str:
        if not self.nudge_history:
            return "no data"
        recent = self.nudge_history[-5:]
        worked = sum(1 for _, ok in recent if ok)
        return f"{worked}/{len(recent)} recent nudges improved focus"

    def _apply_claude_response(self, response: dict):
        self.enoki_pose = response.get("enoki_mood", self.enoki_pose)
        if self.actuator:
            self.actuator.send_command(response)
        if response.get("speak_message") and response.get("message"):
            msg = response["message"]
            self.tts.speak(msg)
            if self.glasses_receiver:
                self.glasses_receiver.push_tts(msg)
        if self.grove and self.actuator:
            led_colors = self.grove.get_grove_leds()
            if led_colors:
                self.actuator.set_grove_leds(led_colors)

    def _record_nudge_outcome(self, state_before: str, state_after_60s: str):
        worked = state_before in ("IDLE", "DOZING") and state_after_60s == "FOCUSED"
        self.nudge_history.append((time.time(), worked))
        if len(self.nudge_history) > self.cfg.NUDGE_HISTORY_MAX:
            self.nudge_history.pop(0)

    def run(self):
        self.dev = self.dev or argparse.Namespace(no_xiao=False, no_arduino=False, no_vision=False, no_cloud=False)

        self._init_modules()

        # Start XIAO serial if enabled
        if not self.dev.no_xiao and self.cfg.XIAO_PORT:
            try:
                import serial
                self._xiao_serial = serial.Serial(self.cfg.XIAO_PORT, self.cfg.BAUD, timeout=1)
            except Exception as e:
                log.warning("XIAO not available: %s", e)

        # Start background threads
        threads = []
        if self._xiao_serial:
            t = threading.Thread(target=self._read_xiao, daemon=True)
            t.start()
            threads.append(t)
        if self._arduino_serial:
            t = threading.Thread(target=self._read_arduino, daemon=True)
            t.start()
            threads.append(t)
        if self.vision:
            t = threading.Thread(target=self._run_vision, daemon=True)
            t.start()
            threads.append(t)

        self.glasses_receiver.start()

        if self.cloud_sync:
            self.cloud_sync.start()

        log.info("Enoki orchestrator started.")

        while not self._stop.is_set():
            xiao, arduino, vision, glasses = self._snapshot()
            current_state = arduino.get("state", "AWAY")
            state_duration = self.sm.update(current_state, xiao, vision)

            if current_state == "FOCUSED":
                self.session_focus_seconds += 1

            self.learner.log_state(current_state, arduino.get("sensors", {}))

            if self.pending_nudge_check:
                trigger_time, state_at_trigger = self.pending_nudge_check
                if time.time() - trigger_time >= 60:
                    self._record_nudge_outcome(state_at_trigger, current_state)
                    self.pending_nudge_check = None

            sm_action = self.sm.check_triggers(current_state, state_duration, vision)

            # Handle glasses transcription -> Planner or Personal
            if glasses.get("transcription"):
                text = glasses["transcription"]
                with self._lock:
                    self.glasses_data.pop("transcription", None)
                if any(kw in text.lower() for kw in ["plan", "schedule", "study", "help me"]):
                    try:
                        payload = self._build_claude_payload(current_state, state_duration)
                        plan = self.planner_claude.plan(text, payload)
                        if plan.get("message"):
                            self.tts.speak(plan["message"])
                            if self.glasses_receiver:
                                self.glasses_receiver.push_tts(plan["message"])
                    except Exception as e:
                        log.error("Planner Claude failed: %s", e)
                else:
                    self.claude.add_user_message(text)

            # Handle glasses photo -> Vision Claude
            if glasses.get("photo_base64"):
                photo_b64 = glasses["photo_base64"]
                with self._lock:
                    self.glasses_data.pop("photo_base64", None)
                try:
                    analysis = self.vision_claude.analyze(photo_b64)
                    with self._lock:
                        self.glasses_data["photo_analysis"] = analysis
                except Exception as e:
                    log.error("Vision Claude failed: %s", e)

            now = time.time()
            time_since_claude = now - self.last_claude_call
            should_call = (
                time_since_claude >= self.cfg.CLAUDE_INTERVAL_SECONDS
                or (sm_action == "TRIGGER_CLAUDE" and time_since_claude >= self.cfg.MIN_CLAUDE_INTERVAL)
            )

            if should_call:
                payload = self._build_claude_payload(current_state, state_duration)
                log.info("Calling Claude. State=%s duration=%ds", current_state, state_duration)
                try:
                    response = self.claude.call(payload)
                    self._apply_claude_response(response)
                    self.last_claude_call = now
                    if sm_action == "TRIGGER_CLAUDE":
                        self.pending_nudge_check = (now, current_state)
                    log.info("Claude response applied: mood=%s", response.get("enoki_mood"))
                except Exception as e:
                    log.error("Claude call failed: %s", e)

            if self.cloud_sync:
                self.cloud_sync.publish(
                    state=current_state,
                    focus_score=vision.get("gaze_score", 1.0) * (1.0 if current_state == "FOCUSED" else 0.5),
                    session_minutes=round((time.time() - self.session_start) / 60),
                    today_focus_hours=round(self.session_focus_seconds / 3600, 1),
                    in_sprint=False,
                    mushroom_mood=self.enoki_pose,
                )

            self._stop.wait(1)

    def stop(self):
        self._stop.set()
