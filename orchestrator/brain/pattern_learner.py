"""
pattern_learner.py — SQLite logging + sklearn pattern detection.

Refactored from pi/pattern_learner.py. Config-based paths. import json at module level.
"""

import json
import logging
import os
import pickle
import sqlite3
import time
from datetime import datetime

log = logging.getLogger("enoki.brain.learner")

SLUMP_STATES = {"IDLE", "DOZING", "AWAY"}


class PatternLearner:
    def __init__(
        self,
        db_path: str,
        model_path: str,
        log_interval: int = 5,
        min_samples_train: int = 200,
        slump_prob_threshold: float = 0.65,
    ):
        self._db_path = db_path
        self._model_path = model_path
        self._log_interval = log_interval
        self._min_samples_train = min_samples_train
        self._slump_prob_threshold = slump_prob_threshold
        self._last_log_time = 0.0
        self._ensure_db()
        self._model = self._load_model()

    def _ensure_db(self):
        os.makedirs(os.path.dirname(self._db_path), exist_ok=True)
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
        return sqlite3.connect(self._db_path)

    def log_state(self, state: str, sensors: dict):
        now = time.time()
        if now - self._last_log_time < self._log_interval:
            return
        self._last_log_time = now

        dt = datetime.now()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO state_log (ts, hour, minute, dow, state, sensors) VALUES (?,?,?,?,?,?)",
                (int(now), dt.hour, dt.minute, dt.weekday(), state, json.dumps(sensors)),
            )

    def _load_model(self):
        if os.path.exists(self._model_path):
            try:
                with open(self._model_path, "rb") as f:
                    model = pickle.load(f)
                log.info("Loaded pattern model from %s", self._model_path)
                return model
            except Exception as e:
                log.warning("Could not load model: %s", e)
        return None

    def train_and_save(self):
        """Train RandomForest on historical data. Call from nightly cron."""
        try:
            import numpy as np
            from sklearn.ensemble import RandomForestClassifier
        except ImportError:
            log.error("scikit-learn not installed — skipping training")
            return

        with self._conn() as conn:
            rows = conn.execute("SELECT hour, minute, dow, state FROM state_log").fetchall()

        if len(rows) < self._min_samples_train:
            log.info("Not enough data to train (%d rows)", len(rows))
            return

        X = np.array([[h, m, d] for h, m, d, _ in rows])
        y = np.array([1 if s in SLUMP_STATES else 0 for _, _, _, s in rows])

        clf = RandomForestClassifier(n_estimators=50, random_state=42)
        clf.fit(X, y)

        os.makedirs(os.path.dirname(self._model_path), exist_ok=True)
        with open(self._model_path, "wb") as f:
            pickle.dump(clf, f)

        self._model = clf
        log.info("Pattern model trained on %d samples and saved.", len(rows))

    def get_context(self, current_state: str) -> tuple:
        """Returns (summary_string, predicted_slump_in_minutes)."""
        now = datetime.now()
        slump_min = self._predict_slump_minutes(now)
        summary = self._build_summary(now, current_state)
        return summary, slump_min

    def _predict_slump_minutes(self, now: datetime) -> int:
        if self._model is None:
            return self._rule_based_slump(now)

        import numpy as np

        for delta_min in range(0, 120, 5):
            future_hour = (now.hour + (now.minute + delta_min) // 60) % 24
            future_minute = (now.minute + delta_min) % 60
            prob = self._model.predict_proba(
                np.array([[future_hour, future_minute, now.weekday()]])
            )[0][1]
            if prob > self._slump_prob_threshold:
                return delta_min

        return 60

    def _rule_based_slump(self, now: datetime) -> int:
        h, m = now.hour, now.minute
        if 13 <= h < 15:
            return 0
        if 17 <= h < 18:
            return 0
        minutes_to_13 = ((13 - h) % 24) * 60 - m
        minutes_to_17 = ((17 - h) % 24) * 60 - m
        return min(minutes_to_13, minutes_to_17)

    def _build_summary(self, now: datetime, current_state: str) -> str:
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
