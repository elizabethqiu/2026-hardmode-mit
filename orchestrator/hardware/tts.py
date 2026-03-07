"""
tts.py — Text-to-speech engine for Enoki.

Refactored from pi/tts.py. Config-based model path.
Tries: piper → espeak-ng → no-op.
Output goes to default ALSA audio device.
"""

import logging
import os
import shutil
import subprocess
import threading

log = logging.getLogger("enoki.hardware.tts")


class TTSEngine:
    def __init__(self, piper_model_path: str = "", backend: str = "auto"):
        self._piper_path = piper_model_path or "/home/pi/tts_models/en_US-lessac-medium.onnx"
        self._backend_override = backend
        self._lock = threading.Lock()
        self._backend = self._detect_backend()
        self._glasses_tts_callback = None
        log.info("TTS backend: %s", self._backend)

    def _detect_backend(self) -> str:
        if self._backend_override and self._backend_override != "auto":
            if self._backend_override == "none":
                return "none"
            if self._backend_override == "piper" and shutil.which("piper") and os.path.exists(self._piper_path):
                return "piper"
            if self._backend_override == "espeak" and shutil.which("espeak-ng"):
                return "espeak"
            return self._backend_override
        if shutil.which("piper") and os.path.exists(self._piper_path):
            return "piper"
        if shutil.which("espeak-ng"):
            return "espeak"
        log.warning("No TTS backend found — speech disabled")
        return "none"

    def set_glasses_tts_callback(self, callback):
        """Set callback(text) to route TTS to glasses when available."""
        self._glasses_tts_callback = callback

    def speak(self, text: str, prefer_glasses: bool = False):
        """
        Non-blocking: fires TTS in a daemon thread.
        If prefer_glasses and callback set, routes to glasses instead of local speaker.
        """
        if prefer_glasses and self._glasses_tts_callback:
            self._glasses_tts_callback(text)
            return
        t = threading.Thread(target=self._speak_sync, args=(text,), daemon=True)
        t.start()

    def _speak_sync(self, text: str):
        with self._lock:
            if self._backend == "piper":
                self._speak_piper(text)
            elif self._backend == "espeak":
                self._speak_espeak(text)

    def _speak_piper(self, text: str):
        try:
            proc = subprocess.run(
                ["piper", "--model", self._piper_path, "--output-raw"],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=10,
            )
            subprocess.run(
                ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"],
                input=proc.stdout,
                timeout=15,
            )
        except Exception as e:
            log.error("Piper TTS failed: %s", e)
            self._speak_espeak(text)

    def _speak_espeak(self, text: str):
        try:
            subprocess.run(
                ["espeak-ng", "-v", "en-us", "-s", "150", "-p", "45", text],
                timeout=10,
            )
        except Exception as e:
            log.error("espeak-ng failed: %s", e)
