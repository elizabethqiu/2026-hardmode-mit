"""
claude/base.py — Shared Claude client with retry, JSON parsing, conversation history.

Adds exponential backoff retry (3 attempts), conversation history management
(rolling window), response validation, and tool-use loop support.
"""

import json
import logging
import time
from typing import Any, Optional

import anthropic

log = logging.getLogger("enoki.claude.base")


class ClaudeBase:
    """Base class for all Claude roles. Handles API calls, retries, and response parsing."""

    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-6",
        max_tokens: int = 512,
        max_retries: int = 3,
    ):
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY not set")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        self.max_tokens = max_tokens
        self.max_retries = max_retries

    def _call_raw(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict]] = None,
    ) -> str:
        """Call Claude API with retry logic. Returns raw text response."""
        msg = self._call_message(system, messages, tools)
        for block in msg.content:
            if block.type == "text":
                return block.text.strip()
        return ""

    def _call_message(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict]] = None,
    ) -> Any:
        """Call Claude API with retry logic. Returns the full Message object."""
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "system": system,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools

        last_error = None
        for attempt in range(self.max_retries):
            try:
                message = self.client.messages.create(**kwargs)
                log.debug("Claude response (attempt %d): stop=%s blocks=%d",
                          attempt + 1, message.stop_reason, len(message.content))
                return message
            except Exception as e:
                last_error = e
                if attempt < self.max_retries - 1:
                    delay = 2 ** attempt
                    log.warning("Claude call failed (attempt %d): %s. Retrying in %ds",
                                attempt + 1, e, delay)
                    time.sleep(delay)
        raise last_error

    def _strip_markdown_fences(self, raw_text: str) -> str:
        """Remove markdown code fences if model wraps response."""
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            return "\n".join(line for line in lines if not line.startswith("```")).strip()
        return raw_text

    def call_json(
        self,
        system: str,
        messages: list[dict[str, Any]],
        tools: Optional[list[dict]] = None,
        validate_fn: Optional[callable] = None,
    ) -> dict:
        """Call Claude and parse response as JSON."""
        raw = self._call_raw(system, messages, tools)
        raw = self._strip_markdown_fences(raw)
        response = json.loads(raw)
        if validate_fn:
            validate_fn(response)
        return response

    def _parse_json_response(self, raw_text: str) -> dict:
        """Strip markdown fences and parse as JSON."""
        return json.loads(self._strip_markdown_fences(raw_text))

    def append_message(
        self,
        history: list[dict[str, Any]],
        role: str,
        content: str | list[dict],
        max_messages: int = 20,
    ) -> list[dict[str, Any]]:
        """Append a message to history and trim to max_messages (rolling window)."""
        new_msg = {"role": role, "content": content}
        updated = history + [new_msg]
        if len(updated) > max_messages:
            updated = updated[-max_messages:]
        return updated
