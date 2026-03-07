"""
pattern_learner.py — SQLite logging + sklearn pattern detection

Logs every state tick to SQLite. Provides:
  - get_context(current_state) → (summary_string, slump_in_minutes)

Uses a simple RandomForest trained nightly to predict slump probability.
Falls back to rule-based hour-matching if no model is trained yet.
"""

import os
import time
import sqlite3
import pickle
import logging
from datetime import datetime

log = logging.getLogger("enoki.learner")

DB_PATH    = os.path.join(os.path.dirname(__file__), "..", "data", "enoki.db")
MODEL_PATH = os.path.join(os.path.dirname(__file__), "..", "models", "focus_pattern.pkl")

# States considered non-focused
SLUMP_STATES = {"IDLE", "DOZING", "AWAY"}


class PatternLearner:
    def __init__(self):
        self._ensure_db()
        self._model = self._load_model()
        self._last_log_time = 0.0
        self._log_interval  = 5  # log every 5 seconds to avoid disk spam

    # ── DB setup ──────────────────────────────────────────────────────────────

    def _ensure_db(self):
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS state_log (
                    id        INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts        INTEGER NOT NULL,
                    hour      INTEGER NOT NULL,
                    minute    INTEGER NOT NULL,
                    dow       INTEGER NOT NULL,
                    state     TEXT    NOT NULL,
                    sensors   TEXT
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_ts ON state_log(ts)")

    def _conn(self):
        return sqlite3.connect(DB_PATH)

    # ── Logging ───────────────────────────────────────────────────────────────

    def log_state(self, state: str, sensors: dict):
        now = time.time()
        if now - self._last_log_time < self._log_interval:
            return
        self._last_log_time = now

        dt = datetime.now()
        import json
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO state_log (ts, hour, minute, dow, state, sensors) VALUES (?,?,?,?,?,?)",
                (int(now), dt.hour, dt.minute, dt.weekday(), state, json.dumps(sensors)),
            )

    # ── Model ─────────────────────────────────────────────────────────────────

    def _load_model(self):
        if os.path.exists(MODEL_PATH):
            try:
                with open(MODEL_PATH, "rb") as f:
                    model = pickle.load(f)
                log.info("Loaded pattern model from %s", MODEL_PATH)
                return model
            except Exception as e:
                log.warning("Could not load model: %s", e)
        return None

    def train_and_save(self):
        """
        Train a RandomForest on historical data to predict slump probability
        by hour-of-day and day-of-week. Call from a nightly cron.
        """
        try:
            from sklearn.ensemble import RandomForestClassifier
            import numpy as np
        except ImportError:
            log.error("scikit-learn not installed — skipping training")
            return

        with self._conn() as conn:
            rows = conn.execute(
                "SELECT hour, minute, dow, state FROM state_log"
            ).fetchall()

        if len(rows) < 200:
            log.info("Not enough data to train (%d rows)", len(rows))
            return

        X = np.array([[h, m, d] for h, m, d, _ in rows])
        y = np.array([1 if s in SLUMP_STATES else 0 for _, _, _, s in rows])

        clf = RandomForestClassifier(n_estimators=50, random_state=42)
        clf.fit(X, y)

        os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
        with open(MODEL_PATH, "wb") as f:
            pickle.dump(clf, f)

        self._model = clf
        log.info("Pattern model trained on %d samples and saved.", len(rows))

    # ── Context for Claude ────────────────────────────────────────────────────

    def get_context(self, current_state: str) -> tuple:
        """
        Returns (summary_string, predicted_slump_in_minutes).
        Uses trained model if available, else rule-based fallback.
        """
        now = datetime.now()
        slump_min = self._predict_slump_minutes(now)
        summary   = self._build_summary(now, current_state)
        return summary, slump_min

    def _predict_slump_minutes(self, now: datetime) -> int:
        """
        Scan forward in 5-min steps to find next predicted high-slump window.
        Returns minutes until that window (0 if currently in one).
        """
        if self._model is None:
            return self._rule_based_slump(now)

        import numpy as np
        for delta_min in range(0, 120, 5):
            future_hour   = (now.hour   + (now.minute + delta_min) // 60) % 24
            future_minute = (now.minute + delta_min) % 60
            prob = self._model.predict_proba(
                np.array([[future_hour, future_minute, now.weekday()]])
            )[0][1]
            if prob > 0.65:
                return delta_min

        return 60  # no slump predicted in next 2 hours — default 60

    def _rule_based_slump(self, now: datetime) -> int:
        """Fallback: well-known productivity slump windows."""
        h = now.hour
        m = now.minute
        # Post-lunch: 13:00-15:00, Late afternoon: 17:00-18:00
        if 13 <= h < 15:
            return 0
        if 17 <= h < 18:
            return 0
        minutes_to_13 = ((13 - h) % 24) * 60 - m
        minutes_to_17 = ((17 - h) % 24) * 60 - m
        return min(minutes_to_13, minutes_to_17)

    def _build_summary(self, now: datetime, current_state: str) -> str:
        """Build a human-readable pattern summary for the Claude prompt."""
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT state FROM state_log WHERE hour=? AND dow=?",
                (now.hour, now.weekday()),
            ).fetchall()

        if not rows:
            return "no historical data for this time window yet"

        slump_count = sum(1 for (s,) in rows if s in SLUMP_STATES)
        pct = round(100 * slump_count / len(rows))
        return (
            f"historically {pct}% slump rate at {now.hour:02d}:xx on "
            f"{now.strftime('%A')}s ({len(rows)} samples)"
        )
