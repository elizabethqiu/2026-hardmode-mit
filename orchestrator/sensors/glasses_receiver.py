"""
glasses_receiver.py — HTTP endpoint for MentraOS MiniApp data.

Receives: transcription, photo_base64, wearing, button_pressed.
Serves: pending TTS and action requests (photo capture).
Runs as a background thread. Callbacks for when data arrives.
"""

import json
import logging
import threading
from collections import deque
from typing import Callable

log = logging.getLogger("enoki.sensors.glasses")


class GlassesReceiver:
    """
    Lightweight HTTP server that the MentraOS MiniApp POSTs data to.
    Holds recent data and pending TTS/actions for the orchestrator to consume.
    """

    def __init__(self, host: str = "0.0.0.0", port: int = 8420):
        self._host = host
        self._port = port
        self._lock = threading.Lock()
        self._transcription: str | None = None
        self._photo_base64: str | None = None
        self._wearing = False
        self._button_pressed = False
        self._pending_tts: deque = deque(maxlen=5)
        self._pending_actions: deque = deque(maxlen=5)
        self._on_data: Callable[[dict], None] | None = None
        self._thread: threading.Thread | None = None

    def set_on_data(self, callback: Callable[[dict], None]):
        self._on_data = callback

    def get_snapshot(self) -> dict:
        with self._lock:
            out = {
                "transcription": self._transcription,
                "photo_base64": self._photo_base64,
                "wearing": self._wearing,
                "button_pressed": self._button_pressed,
            }
            self._transcription = None
            self._photo_base64 = None
            self._button_pressed = False
            return out

    def push_tts(self, text: str):
        with self._lock:
            self._pending_tts.append({"text": text})

    def pop_tts(self) -> dict | None:
        with self._lock:
            return self._pending_tts.popleft() if self._pending_tts else None

    def request_photo(self):
        """Queue a photo capture request for the MiniApp to pick up."""
        with self._lock:
            self._pending_actions.append({"action": "take_photo"})

    def pop_action(self) -> dict | None:
        with self._lock:
            return self._pending_actions.popleft() if self._pending_actions else None

    def start(self):
        """Start the Flask server in a daemon thread."""
        try:
            from flask import Flask, request, jsonify
        except ImportError:
            log.warning("Flask not installed — glasses receiver disabled")
            return

        app = Flask(__name__)

        @app.route("/glasses", methods=["POST"])
        def receive():
            try:
                data = request.get_json(force=True, silent=True) or {}
                with self._lock:
                    if "transcription" in data:
                        self._transcription = data.get("transcription", "")
                    if "photo_base64" in data:
                        self._photo_base64 = data.get("photo_base64", "")
                    if "wearing" in data:
                        self._wearing = bool(data.get("wearing"))
                    if "button_pressed" in data:
                        self._button_pressed = bool(data.get("button_pressed"))
                if self._on_data:
                    self._on_data(data)
                return jsonify({"ok": True})
            except Exception as e:
                log.error("Glasses receive error: %s", e)
                return jsonify({"ok": False, "error": str(e)}), 500

        @app.route("/glasses/tts", methods=["GET"])
        def tts():
            t = self.pop_tts()
            return jsonify(t if t else {})

        @app.route("/glasses/actions", methods=["GET"])
        def actions():
            a = self.pop_action()
            return jsonify(a if a else {})

        def run():
            app.run(host=self._host, port=self._port, threaded=True, use_reloader=False)

        self._thread = threading.Thread(target=run, daemon=True)
        self._thread.start()
        log.info("Glasses receiver started on %s:%d", self._host, self._port)
