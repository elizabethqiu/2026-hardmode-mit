"""
actuator.py — Sends hardware commands to Arduino UNO Q over USB Serial.

Refactored from pi/actuator_client.py. Adds set_grove_leds for grove member indicators.
Commands are JSON lines terminated with \\n.
"""

import json
import logging
import serial

log = logging.getLogger("enoki.hardware.actuator")


class ActuatorClient:
    def __init__(self, ser: serial.Serial):
        self._serial = ser

    def send_command(self, claude_response: dict):
        """
        Extract actuator fields from a Claude response dict and send to Arduino.
        Forwards height, LEDs, mood, and message for display.
        """
        cmd = {
            "height": self._clamp(claude_response.get("height", 0.7)),
            "led_color": self._sanitize_color(claude_response.get("led_color", [200, 180, 120])),
            "led_brightness": self._clamp(claude_response.get("led_brightness", 0.6)),
            "nudge_intensity": claude_response.get("nudge_intensity", "none"),
            "enoki_mood": claude_response.get("enoki_mood", "watchful"),
            "message": claude_response.get("message", ""),
        }
        self._write(cmd)

    def send_raw(self, cmd: dict):
        """Send an arbitrary command dict directly."""
        self._write(cmd)

    def set_grove_leds(self, led_colors: list[list[int]]):
        """
        Send grove member LED colors for ring indicators.
        Each element: [r, g, b] 0-255.
        """
        self._write({"grove_leds": led_colors})

    def send_pose(self, pose: str):
        """
        Convenience: send a named pose.
        Useful for state machine to snap to known poses without Claude.
        """
        poses = {
            "upright_open": {"height": 1.0, "led_color": [20, 200, 60], "led_brightness": 1.0, "nudge_intensity": "none", "enoki_mood": "focused"},
            "upright_neutral": {"height": 0.8, "led_color": [200, 180, 120], "led_brightness": 0.75, "nudge_intensity": "none", "enoki_mood": "watchful"},
            "half_droop": {"height": 0.5, "led_color": [255, 140, 0], "led_brightness": 0.6, "nudge_intensity": "none", "enoki_mood": "concerned"},
            "full_droop": {"height": 0.1, "led_color": [180, 20, 10], "led_brightness": 0.3, "nudge_intensity": "none", "enoki_mood": "urgent"},
            "celebration": {"height": 1.0, "led_color": [0, 200, 255], "led_brightness": 1.0, "nudge_intensity": "none", "enoki_mood": "focused", "animate": "celebrate"},
        }
        if pose not in poses:
            log.warning("Unknown pose: %s", pose)
            return
        self._write(poses[pose])

    def _write(self, cmd: dict):
        try:
            line = json.dumps(cmd) + "\n"
            self._serial.write(line.encode("utf-8"))
            log.debug("→ Arduino: %s", line.strip())
        except serial.SerialException as e:
            log.error("Serial write failed: %s", e)

    @staticmethod
    def _clamp(v: float) -> float:
        return max(0.0, min(1.0, float(v)))

    @staticmethod
    def _sanitize_color(color) -> list:
        if not isinstance(color, (list, tuple)) or len(color) != 3:
            return [200, 180, 120]
        return [max(0, min(255, int(c))) for c in color]
