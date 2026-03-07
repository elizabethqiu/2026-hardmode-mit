"""
actuator_client.py — Sends hardware commands to Arduino UNO Q over USB Serial

The Arduino is the ONLY thing touching actuators.
Commands are JSON lines terminated with \n.

Command schema sent to Arduino:
{
  "stem_height":   0.0-1.0,
  "cap_openness":  0.0-1.0,
  "led_color":     [r, g, b],
  "led_brightness": 0.0-1.0,
  "nudge_intensity": "none|gentle|moderate|direct"
}
"""

import json
import logging
import serial

log = logging.getLogger("enoki.actuator")


class ActuatorClient:
    def __init__(self, ser: serial.Serial):
        self._serial = ser

    def send_command(self, claude_response: dict):
        """
        Extract actuator fields from a Claude response dict and send to Arduino.
        Only sends the fields the Arduino needs — strips message/mood/etc.
        """
        cmd = {
            "stem_height":     self._clamp(claude_response.get("stem_height", 0.7)),
            "cap_openness":    self._clamp(claude_response.get("cap_openness", 0.5)),
            "led_color":       self._sanitize_color(claude_response.get("led_color", [200, 180, 120])),
            "led_brightness":  self._clamp(claude_response.get("led_brightness", 0.6)),
            "nudge_intensity": claude_response.get("nudge_intensity", "none"),
        }
        self._write(cmd)

    def send_raw(self, cmd: dict):
        """Send an arbitrary command dict directly."""
        self._write(cmd)

    def send_pose(self, pose: str):
        """
        Convenience: send a named pose.
        Useful for state machine to snap to known poses without Claude.
        """
        poses = {
            "upright_open":   {"stem_height": 1.0, "cap_openness": 1.0,  "led_color": [20, 200, 60],   "led_brightness": 1.0,  "nudge_intensity": "none"},
            "upright_neutral":{"stem_height": 0.8, "cap_openness": 0.65, "led_color": [200, 180, 120], "led_brightness": 0.75, "nudge_intensity": "none"},
            "half_droop":     {"stem_height": 0.5, "cap_openness": 0.4,  "led_color": [255, 140, 0],   "led_brightness": 0.6,  "nudge_intensity": "none"},
            "full_droop":     {"stem_height": 0.1, "cap_openness": 0.1,  "led_color": [180, 20, 10],   "led_brightness": 0.3,  "nudge_intensity": "none"},
            "celebration":    {"stem_height": 1.0, "cap_openness": 1.0,  "led_color": [0, 200, 255],   "led_brightness": 1.0,  "nudge_intensity": "none", "animate": "celebrate"},
        }
        if pose not in poses:
            log.warning("Unknown pose: %s", pose)
            return
        self._write(poses[pose])

    # ── Internal ──────────────────────────────────────────────────────────────

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
