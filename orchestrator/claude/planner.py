"""
claude/planner.py — Planning Claude for study session planning.

Conversational. Takes user voice input + current task context.
Returns structured study plans with sprint blocks.
"""

import json
import logging
from typing import Any

from .base import ClaudeBase
from .prompts import PLANNER_SYSTEM_PROMPT

log = logging.getLogger("enoki.claude.planner")


class PlannerClaude(ClaudeBase):
    """Study session planning. Activated by voice through glasses."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6", max_tokens: int = 1024):
        super().__init__(api_key=api_key, model=model, max_tokens=max_tokens)

    def plan(self, user_input: str, context_payload: dict | None = None) -> dict:
        """
        Generate a study plan from user input.
        context_payload: optional dict with current_state, session_focus_percentage, etc.
        Returns {"plan_summary": str, "sprints": [...], "message": str}.
        """
        payload = context_payload or {}
        context = {
            "user_input": user_input,
            "current_state": payload.get("current_state", ""),
            "session_focus_percentage": payload.get("session_focus_percentage", 0),
            "session_duration_minutes": payload.get("session_duration_minutes", 0),
            "today_focus_hours": payload.get("session_duration_minutes", 0) / 60,
        }
        user_msg = "User request and context:\n" + json.dumps(context, indent=2)
        messages = [{"role": "user", "content": user_msg}]

        raw = self._call_raw(PLANNER_SYSTEM_PROMPT, messages)
        raw = self._strip_markdown_fences(raw)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"plan_summary": "", "sprints": [], "message": raw}
