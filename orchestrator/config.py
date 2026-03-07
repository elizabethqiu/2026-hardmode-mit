"""
config.py — Central configuration for Enoki orchestrator.

Loads from environment variables with sensible defaults.
OS-aware defaults for serial ports (Linux / Windows / macOS).
"""

import os
import sys
import platform

# Project root (parent of orchestrator/)
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def _default_serial_ports():
    """Return (xiao_port, arduino_port) based on OS."""
    system = platform.system()
    if system == "Linux":
        return "/dev/ttyUSB0", "/dev/ttyUSB1"
    if system == "Windows":
        return "COM3", "COM4"
    if system == "Darwin":
        return "/dev/cu.usbserial-0001", "/dev/cu.usbserial-0002"
    return "/dev/ttyUSB0", "/dev/ttyUSB1"


def _env_int(key: str, default: int) -> int:
    val = os.environ.get(key)
    return int(val) if val is not None and val.strip() else default


def _env_float(key: str, default: float) -> float:
    val = os.environ.get(key)
    return float(val) if val is not None and val.strip() else default


def _env_str(key: str, default: str) -> str:
    val = os.environ.get(key)
    return val.strip() if val is not None and val.strip() else default


def _env_bool(key: str, default: bool) -> bool:
    val = os.environ.get(key, "").lower().strip()
    if val in ("1", "true", "yes"):
        return True
    if val in ("0", "false", "no"):
        return False
    return default


# ── Config object ─────────────────────────────────────────────────────────────

class Config:
    """Central config. Access via config.X or load_config()."""

    # Serial
    XIAO_PORT: str
    ARDUINO_PORT: str
    BAUD: int

    # Claude
    ANTHROPIC_API_KEY: str
    CLAUDE_MODEL: str
    CLAUDE_MAX_TOKENS: int
    CLAUDE_INTERVAL_SECONDS: int
    MIN_CLAUDE_INTERVAL: int

    # Vision
    CAMERA_INDEX: int
    FPS_TARGET: int
    MEDIAPIPE_DETECTION_CONFIDENCE: float
    MEDIAPIPE_TRACKING_CONFIDENCE: float

    # TTS
    TTS_BACKEND: str  # auto | piper | espeak | none
    PIPER_MODEL_PATH: str

    # Paths (absolute)
    DB_PATH: str
    MODEL_PATH: str

    # Network / Grove
    SUPABASE_URL: str
    SUPABASE_KEY: str
    USER_ID: str
    GROVE_ID: str

    # Glasses receiver
    GLASSES_RECEIVER_PORT: int
    GLASSES_RECEIVER_HOST: str

    # State machine thresholds (seconds)
    DOZING_NUDGE_THRESHOLD: int
    IDLE_NUDGE_THRESHOLD: int
    FOCUSED_BREAK_THRESHOLD: int
    AWAY_SLEEP_THRESHOLD: int

    # Pattern learner
    LOG_INTERVAL: int
    NUDGE_HISTORY_MAX: int
    RECENT_HISTORY_N: int

    def __init__(self):
        dxiao, darduino = _default_serial_ports()
        self.XIAO_PORT = _env_str("XIAO_PORT", dxiao)
        self.ARDUINO_PORT = _env_str("ARDUINO_PORT", darduino)
        self.BAUD = _env_int("BAUD", 115200)

        self.ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "").strip()
        self.CLAUDE_MODEL = _env_str("CLAUDE_MODEL", "claude-sonnet-4-6")
        self.CLAUDE_MAX_TOKENS = _env_int("CLAUDE_MAX_TOKENS", 512)
        self.CLAUDE_INTERVAL_SECONDS = _env_int("CLAUDE_INTERVAL_SECONDS", 900)
        self.MIN_CLAUDE_INTERVAL = _env_int("MIN_CLAUDE_INTERVAL", 60)

        self.CAMERA_INDEX = _env_int("CAMERA_INDEX", 0)
        self.FPS_TARGET = _env_int("FPS_TARGET", 10)
        self.MEDIAPIPE_DETECTION_CONFIDENCE = _env_float("MEDIAPIPE_DETECTION_CONFIDENCE", 0.5)
        self.MEDIAPIPE_TRACKING_CONFIDENCE = _env_float("MEDIAPIPE_TRACKING_CONFIDENCE", 0.5)

        self.TTS_BACKEND = _env_str("TTS_BACKEND", "auto")
        self.PIPER_MODEL_PATH = _env_str(
            "PIPER_MODEL_PATH",
            "/home/pi/tts_models/en_US-lessac-medium.onnx",
        )

        db_rel = _env_str("DB_PATH", "data/enoki.db")
        model_rel = _env_str("MODEL_PATH", "models/focus_pattern.pkl")
        self.DB_PATH = os.path.join(_PROJECT_ROOT, db_rel) if not os.path.isabs(db_rel) else db_rel
        self.MODEL_PATH = os.path.join(_PROJECT_ROOT, model_rel) if not os.path.isabs(model_rel) else model_rel

        self.SUPABASE_URL = _env_str("SUPABASE_URL", "")
        self.SUPABASE_KEY = _env_str("SUPABASE_KEY", "")
        self.USER_ID = _env_str("USER_ID", "")
        self.GROVE_ID = _env_str("GROVE_ID", "")

        self.GLASSES_RECEIVER_PORT = _env_int("GLASSES_RECEIVER_PORT", 8420)
        self.GLASSES_RECEIVER_HOST = _env_str("GLASSES_RECEIVER_HOST", "0.0.0.0")

        self.DOZING_NUDGE_THRESHOLD = _env_int("DOZING_NUDGE_THRESHOLD", 90)
        self.IDLE_NUDGE_THRESHOLD = _env_int("IDLE_NUDGE_THRESHOLD", 300)
        self.FOCUSED_BREAK_THRESHOLD = _env_int("FOCUSED_BREAK_THRESHOLD", 25 * 60)
        self.AWAY_SLEEP_THRESHOLD = _env_int("AWAY_SLEEP_THRESHOLD", 10 * 60)

        self.LOG_INTERVAL = _env_int("LOG_INTERVAL", 5)
        self.NUDGE_HISTORY_MAX = _env_int("NUDGE_HISTORY_MAX", 50)
        self.RECENT_HISTORY_N = _env_int("RECENT_HISTORY_N", 6)

    @property
    def has_cloud(self) -> bool:
        return bool(self.SUPABASE_URL and self.SUPABASE_KEY)

    @property
    def has_grove(self) -> bool:
        return self.has_cloud and bool(self.USER_ID and self.GROVE_ID)


# Singleton
_config: Config | None = None


def load_config() -> Config:
    """Load config from env. Cached after first call."""
    global _config
    if _config is None:
        _config = Config()
    return _config
