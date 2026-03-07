"""
claude/insight.py — Insight Claude for nightly batch analysis.

Batch mode. Takes full day's data dump. Returns daily/weekly insight strings.
Called once per day or on demand.
"""

import json
import logging
from typing import Any

from .base import ClaudeBase
from .prompts import INSIGHT_SYSTEM_PROMPT

log = logging.getLogger("enoki.claude.insight")


class InsightClaude(ClaudeBase):
    """Nightly batch analysis. Generates pattern insights and recommendations."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6", max_tokens: int = 1024):
        super().__init__(api_key=api_key, model=model, max_tokens=max_tokens)

    def analyze(
        self,
        day_data: list[dict[str, Any]],
        grove_summary: str = "",
    ) -> dict:
        """
        Analyze a day's worth of focus data.
        Returns {"insights": [str], "recommendations": [str], "summary": str}.
        """
        payload = {
            "day_data": day_data,
            "grove_summary": grove_summary,
        }
        messages = [{"role": "user", "content": json.dumps(payload, indent=2)}]
        raw = self._call_raw(INSIGHT_SYSTEM_PROMPT, messages)
        raw = self._strip_markdown_fences(raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"insights": [], "recommendations": [], "summary": raw}
