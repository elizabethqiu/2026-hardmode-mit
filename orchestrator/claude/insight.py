"""
claude/insight.py — Insight Claude for nightly batch analysis.

Batch mode. Fetches the full day's SQLite log itself, then calls Claude.
Returns personalized insights delivered the next morning.
Called once per day via run_insight.py (cron or manual).
"""

import json
import logging
import sqlite3
from datetime import date, datetime, timedelta
from typing import Any

from .base import ClaudeBase
from .prompts import INSIGHT_SYSTEM_PROMPT

log = logging.getLogger("enoki.claude.insight")


class InsightClaude(ClaudeBase):
    """Nightly batch analysis. Fetches day's data from SQLite and generates insights."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6", max_tokens: int = 1024):
        super().__init__(api_key=api_key, model=model, max_tokens=max_tokens)

    def fetch_day_data(self, db_path: str, for_date: date | None = None) -> list[dict[str, Any]]:
        """
        Pull all state_log rows for a given date from SQLite.
        Defaults to yesterday (since this runs at night after the day is done).
        Returns list of dicts: {ts, hour, minute, dow, state, sensors}.
        """
        target = for_date or (datetime.now().date() - timedelta(days=1))
        day_start = int(datetime(target.year, target.month, target.day).timestamp())
        day_end = day_start + 86400

        try:
            conn = sqlite3.connect(db_path)
            rows = conn.execute(
                "SELECT ts, hour, minute, dow, state, sensors FROM state_log WHERE ts >= ? AND ts < ? ORDER BY ts",
                (day_start, day_end),
            ).fetchall()
            conn.close()
        except Exception as e:
            log.error("Failed to fetch day data from SQLite: %s", e)
            return []

        result = []
        for ts, hour, minute, dow, state, sensors_json in rows:
            entry: dict[str, Any] = {
                "ts": ts,
                "hour": hour,
                "minute": minute,
                "dow": dow,
                "state": state,
            }
            if sensors_json:
                try:
                    entry["sensors"] = json.loads(sensors_json)
                except json.JSONDecodeError:
                    pass
            result.append(entry)

        log.info("Fetched %d state records for %s", len(result), target.isoformat())
        return result

    def _summarize_day(self, day_data: list[dict[str, Any]]) -> dict[str, Any]:
        """Compute aggregate stats from raw state rows to give Claude richer context."""
        if not day_data:
            return {}

        state_counts: dict[str, int] = {}
        for row in day_data:
            s = row["state"]
            state_counts[s] = state_counts.get(s, 0) + 1

        total = len(day_data)
        # Each row is LOG_INTERVAL seconds apart (default 5s)
        log_interval_s = 5
        focused_seconds = state_counts.get("FOCUSED", 0) * log_interval_s
        idle_seconds = (state_counts.get("IDLE", 0) + state_counts.get("DOZING", 0)) * log_interval_s

        # Focus by hour bucket
        hour_focus: dict[int, list[int]] = {}
        for row in day_data:
            h = row["hour"]
            is_focused = 1 if row["state"] == "FOCUSED" else 0
            hour_focus.setdefault(h, []).append(is_focused)

        hour_pcts = {
            h: round(100 * sum(vals) / len(vals))
            for h, vals in hour_focus.items()
            if len(vals) >= 3
        }

        return {
            "total_focus_minutes": round(focused_seconds / 60),
            "total_idle_minutes": round(idle_seconds / 60),
            "state_distribution": {k: round(100 * v / total) for k, v in state_counts.items()},
            "focus_pct_by_hour": hour_pcts,
            "total_samples": total,
        }

    def analyze(
        self,
        db_path: str,
        for_date: date | None = None,
        grove_summary: str = "",
        photo_summaries: list[str] | None = None,
        conversation_snippets: list[str] | None = None,
    ) -> dict:
        """
        Fetch the day's SQLite data and analyze it with Claude.

        Args:
            db_path: Path to enoki.db
            for_date: Date to analyze (defaults to yesterday)
            grove_summary: Optional string summary of grove activity for the day
            photo_summaries: Optional list of Vision Claude descriptions from glasses photos
            conversation_snippets: Optional list of notable Personal Claude exchanges

        Returns:
            {"insights": [str], "recommendations": [str], "summary": str}
        """
        day_data = self.fetch_day_data(db_path, for_date)

        if not day_data:
            log.warning("No data found for analysis — skipping Claude call")
            return {
                "insights": ["No focus data recorded for this day."],
                "recommendations": [],
                "summary": "No session data available.",
            }

        stats = self._summarize_day(day_data)
        target_date = (for_date or (datetime.now().date() - timedelta(days=1))).isoformat()

        payload: dict[str, Any] = {
            "date": target_date,
            "aggregate_stats": stats,
            "raw_state_log": day_data,
        }
        if grove_summary:
            payload["grove_summary"] = grove_summary
        if photo_summaries:
            payload["glasses_photo_summaries"] = photo_summaries
        if conversation_snippets:
            payload["conversation_highlights"] = conversation_snippets

        messages = [{"role": "user", "content": json.dumps(payload, indent=2)}]
        raw = self._call_raw(INSIGHT_SYSTEM_PROMPT, messages)
        raw = self._strip_markdown_fences(raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"insights": [], "recommendations": [], "summary": raw}
