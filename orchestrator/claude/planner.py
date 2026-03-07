"""
claude/planner.py — Planning Claude for study session planning.

Multi-turn conversational planner. Takes user voice input + full orchestrator context.
Returns structured study plans with sprint blocks, or asks clarifying questions.
"""

import json
import logging
from typing import Any, Optional

from .base import ClaudeBase
from .prompts import PLANNER_SYSTEM_PROMPT

log = logging.getLogger("enoki.claude.planner")

DEFAULTS = {
    "needs_more_info": False,
    "question": "",
    "plan_summary": "",
    "sprints": [],
    "message": "",
    "propose_to_grove": False,
}


class PlannerClaude(ClaudeBase):
    """Multi-turn study session planner. Activated by voice through glasses."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-6", max_tokens: int = 1024):
        super().__init__(api_key=api_key, model=model, max_tokens=max_tokens)
        self._history: list[dict[str, Any]] = []
        self._max_history = 10
        self._in_conversation = False

    @property
    def awaiting_response(self) -> bool:
        return self._in_conversation

    def plan(self, user_input: str, context_payload: Optional[dict] = None,
             existing_plan: Optional[dict] = None) -> dict:
        """
        Generate or refine a study plan from user input.

        Args:
            user_input: Voice transcription from the user.
            context_payload: Full orchestrator payload (state, patterns, grove, etc.)
            existing_plan: Current plan from PlanStore, if one exists.

        Returns dict with keys: needs_more_info, question, plan_summary, sprints, message, propose_to_grove
        """
        payload = context_payload or {}

        context = {
            "user_input": user_input,
            "current_state": payload.get("current_state", ""),
            "session_focus_percentage": payload.get("session_focus_percentage", 0),
            "session_duration_minutes": payload.get("session_duration_minutes", 0),
            "today_focus_hours": payload.get("today_focus_hours", 0),
            "time_of_day": payload.get("time_of_day", ""),
            "historical_pattern_summary": payload.get("historical_pattern_summary", ""),
            "predicted_slump_in_minutes": payload.get("predicted_slump_in_minutes"),
        }

        if payload.get("grove"):
            context["grove"] = payload["grove"]

        if existing_plan:
            context["existing_plan"] = existing_plan

        user_msg = "User request and context:\n" + json.dumps(context, indent=2)
        self._history = self.append_message(
            self._history, "user", user_msg, self._max_history
        )

        raw = self._call_raw(PLANNER_SYSTEM_PROMPT, self._history)
        clean = self._strip_markdown_fences(raw)

        self._history = self.append_message(
            self._history, "assistant", raw, self._max_history
        )

        try:
            parsed = json.loads(clean)
        except json.JSONDecodeError:
            self._in_conversation = False
            return {**DEFAULTS, "message": raw}

        result = {**DEFAULTS, **parsed}

        if result["needs_more_info"]:
            self._in_conversation = True
        else:
            self._in_conversation = False

        return result

    def follow_up(self, user_input: str) -> dict:
        """Continue a multi-turn planning conversation with the user's follow-up answer."""
        self._history = self.append_message(
            self._history, "user", user_input, self._max_history
        )

        raw = self._call_raw(PLANNER_SYSTEM_PROMPT, self._history)
        clean = self._strip_markdown_fences(raw)

        self._history = self.append_message(
            self._history, "assistant", raw, self._max_history
        )

        try:
            parsed = json.loads(clean)
        except json.JSONDecodeError:
            self._in_conversation = False
            return {**DEFAULTS, "message": raw}

        result = {**DEFAULTS, **parsed}

        if result["needs_more_info"]:
            self._in_conversation = True
        else:
            self._in_conversation = False

        return result

    def reset_conversation(self):
        """Clear planning conversation history."""
        self._history.clear()
        self._in_conversation = False
