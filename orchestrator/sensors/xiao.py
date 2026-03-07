"""
xiao.py — XIAO ESP32-S3 serial reader thread.

Parses JSON lines from XIAO at ~10Hz into {"face": bool, "eyes_open": bool}.
"""

import json
import logging
import threading

import serial

log = logging.getLogger("enoki.sensors.xiao")


class XiaoReader:
    """Daemon thread that reads face/eye presence from XIAO ESP32-S3."""

    def __init__(self, port: str, baud: int = 115200, lock: threading.Lock | None = None):
        self._serial = serial.Serial(port, baud, timeout=1)
        self._lock = lock or threading.Lock()
        self._data = {"face": False, "eyes_open": False}
        self._thread: threading.Thread | None = None

    @property
    def data(self) -> dict:
        with self._lock:
            return dict(self._data)

    def start(self):
        """Start the reader thread."""
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        log.info("XIAO reader started on %s", self._serial.port)

    def _run(self):
        while True:
            try:
                raw = self._serial.readline().decode("utf-8", errors="ignore").strip()
                if not raw:
                    continue
                data = json.loads(raw)
                with self._lock:
                    self._data = data
            except (json.JSONDecodeError, serial.SerialException) as e:
                log.warning("XIAO read error: %s", e)
