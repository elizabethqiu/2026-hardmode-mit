"""
tts.py — Text-to-speech engine for Enoki

Tries (in order):
  1. piper-tts  — fast, offline, good quality neural TTS for Pi
  2. espeak-ng  — always available on Raspberry Pi OS, robotic but reliable
  3. No-op      — silently skips if nothing available (dev mode)

Output goes to the default ALSA audio device (ReSpeaker / mono speaker).
"""

import logging
import shutil
import subprocess
import threading

log = logging.getLogger("enoki.tts")

# Piper model path — download and place here before hackathon
PIPER_MODEL = "/home/pi/tts_models/en_US-lessac-medium.onnx"


class TTSEngine:
    def __init__(self):
        self._lock   = threading.Lock()  # prevent overlapping speech
        self._backend = self._detect_backend()
        log.info("TTS backend: %s", self._backend)

    def _detect_backend(self) -> str:
        if shutil.which("piper") and __import__("os").path.exists(PIPER_MODEL):
            return "piper"
        if shutil.which("espeak-ng"):
            return "espeak"
        log.warning("No TTS backend found — speech disabled")
        return "none"

    def speak(self, text: str):
        """Non-blocking: fires TTS in a daemon thread."""
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
                ["piper", "--model", PIPER_MODEL, "--output-raw"],
                input=text.encode("utf-8"),
                capture_output=True,
                timeout=10,
            )
            # Pipe raw PCM to aplay
            subprocess.run(
                ["aplay", "-r", "22050", "-f", "S16_LE", "-t", "raw", "-"],
                input=proc.stdout,
                timeout=15,
            )
        except Exception as e:
            log.error("Piper TTS failed: %s", e)
            self._speak_espeak(text)  # fallback

    def _speak_espeak(self, text: str):
        try:
            subprocess.run(
                ["espeak-ng", "-v", "en-us", "-s", "150", "-p", "45", text],
                timeout=10,
            )
        except Exception as e:
            log.error("espeak-ng failed: %s", e)
