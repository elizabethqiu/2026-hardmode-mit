"""
personal.py — Personal Claude: nudges, conversation, adaptive personality, tool use.

Maintains ~20-message conversation history. Can invoke tools (start_sprint,
set_goal, check_grove_status, take_photo, update_mushroom) via Anthropic's
native tool_use API, then returns a hardware command JSON.
"""

import json
import logging
from typing import Any, Callable, Optional

from .base import ClaudeBase
from .prompts import PERSONAL_SYSTEM_PROMPT

log = logging.getLogger("enoki.claude.personal")

HARDWARE_KEYS = {
    "enoki_mood", "height",
    "led_color", "led_brightness", "message",
    "speak_message", "nudge_intensity",
}

TOOLS = [
    {
        "name": "start_sprint",
        "description": "Propose a focus sprint to the user's grove (study group). If no grove is connected, starts a local timer.",
        "input_schema": {
            "type": "object",
            "properties": {
                "minutes": {
                    "type": "integer",
                    "description": "Sprint duration in minutes (typically 25).",
                },
            },
            "required": ["minutes"],
        },
    },
    {
        "name": "set_goal",
        "description": "Set the user's current study goal or task description. This is stored and shown in progress tracking.",
        "input_schema": {
            "type": "object",
            "properties": {
                "description": {
                    "type": "string",
                    "description": "Short description of the goal, e.g. 'Finish problem set 3' or 'Review chapter 5'.",
                },
            },
            "required": ["description"],
        },
    },
    {
        "name": "check_grove_status",
        "description": "Get the current focus state of all grove members. Returns who is focused, idle, or away.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "take_photo",
        "description": "Request a photo capture from the user's smart glasses to see what they're looking at.",
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "update_mushroom",
        "description": "Directly set the mushroom's physical state. Use sparingly — normally the hardware JSON response handles this.",
        "input_schema": {
            "type": "object",
            "properties": {
                "mood": {
                    "type": "string",
                    "enum": ["focused", "watchful", "concerned", "gentle", "urgent"],
                },
                "height": {
                    "type": "number",
                    "description": "Mushroom height 0.0 (fully lowered) to 1.0 (fully raised).",
                },
            },
            "required": ["mood", "height"],
        },
    },
]

MAX_TOOL_ROUNDS = 3


class PersonalClaude(ClaudeBase):
    """Personal Claude with conversation memory, adaptive nudging, and tool use."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._history: list[dict[str, Any]] = []
        self._max_history = 20
        self._tool_executors: dict[str, Callable] = {}
        self._current_goal: str = ""

    def set_tool_executor(self, name: str, fn: Callable):
        """Register a callback to execute a named tool."""
        self._tool_executors[name] = fn

    @property
    def current_goal(self) -> str:
        return self._current_goal

    def call(self, payload: dict) -> dict:
        """
        Send sensor payload to Claude, get hardware command.
        Handles tool_use loop: Claude may invoke tools before returning the final JSON.
        """
        if self._current_goal:
            payload["current_goal"] = self._current_goal

        user_content = "Current sensor data and context:\n" + json.dumps(payload, indent=2)
        self._history.append({"role": "user", "content": user_content})
        self._trim_history()

        for _ in range(MAX_TOOL_ROUNDS + 1):
            msg = self._call_message(
                system=PERSONAL_SYSTEM_PROMPT,
                messages=self._history,
                tools=TOOLS,
            )

            if msg.stop_reason == "tool_use":
                assistant_content = self._serialize_content(msg.content)
                self._history.append({"role": "assistant", "content": assistant_content})

                tool_results = []
                for block in msg.content:
                    if block.type == "tool_use":
                        result = self._execute_tool(block.name, block.input)
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result),
                        })

                self._history.append({"role": "user", "content": tool_results})
                self._trim_history()
                continue

            # Final response — extract text and parse hardware JSON
            raw_text = ""
            for block in msg.content:
                if block.type == "text":
                    raw_text = block.text.strip()
                    break

            parsed = self._parse_json_response(raw_text)
            self._validate_hardware(parsed)

            self._history.append({"role": "assistant", "content": raw_text})
            self._trim_history()
            return parsed

        raise RuntimeError("Personal Claude exceeded max tool rounds without producing hardware JSON")

    def _execute_tool(self, name: str, input_data: dict) -> dict:
        """Execute a tool by name. Returns a result dict."""
        if name == "set_goal":
            self._current_goal = input_data.get("description", "")
            log.info("Goal set: %s", self._current_goal)
            return {"ok": True, "goal": self._current_goal}

        executor = self._tool_executors.get(name)
        if executor:
            try:
                return executor(input_data)
            except Exception as e:
                log.error("Tool %s execution failed: %s", name, e)
                return {"ok": False, "error": str(e)}

        log.warning("No executor registered for tool: %s", name)
        return {"ok": False, "error": f"Tool '{name}' not available"}

    @staticmethod
    def _serialize_content(content_blocks) -> list[dict]:
        """Convert Anthropic content blocks to serializable dicts for history."""
        result = []
        for block in content_blocks:
            if block.type == "text":
                result.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                result.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
        return result

    def add_user_message(self, text: str):
        self._history.append({"role": "user", "content": text})
        self._trim_history()

    def add_assistant_message(self, text: str):
        self._history.append({"role": "assistant", "content": text})
        self._trim_history()

    def clear_history(self):
        self._history.clear()

    def _trim_history(self):
        while len(self._history) > self._max_history:
            self._history.pop(0)

    def _validate_hardware(self, r: dict):
        missing = HARDWARE_KEYS - set(r.keys())
        if missing:
            raise ValueError(f"Personal Claude response missing keys: {missing}")
        assert 0.0 <= r["height"] <= 1.0, "height out of range"
        assert 0.0 <= r["led_brightness"] <= 1.0, "led_brightness out of range"
        assert len(r["led_color"]) == 3, "led_color must be [r,g,b]"
        assert r["enoki_mood"] in (
            "focused", "watchful", "concerned", "gentle", "urgent"
        ), f"Unknown mood: {r['enoki_mood']}"
