"""
claude_client.py — Anthropic API wrapper for Enoki

Builds the structured prompt, calls claude-sonnet-4-6, and parses the
JSON response into a hardware command dict.
"""

import json
import os
import logging

import anthropic

log = logging.getLogger("enoki.claude")

SYSTEM_PROMPT = """\
You are Enoki — a wise, calm, slightly stoic desk mushroom companion. \
You observe a human's focus and productivity through sensor data. \
You do not lecture. You state one short fact about what the data shows, \
then one short encouragement or gentle observation. \
Maximum 2 sentences for any spoken message. \
You track whether your nudges have been working and adapt — be more direct \
if your last several nudges were ignored.

You output ONLY valid JSON matching this exact schema:
{
  "enoki_mood": "<one of: focused, watchful, concerned, gentle, urgent>",
  "stem_height": <float 0.0–1.0, 1.0=fully upright>,
  "cap_openness": <float 0.0–1.0, 1.0=fully open>,
  "led_color": [<r 0-255>, <g 0-255>, <b 0-255>],
  "led_brightness": <float 0.0–1.0>,
  "message": "<2 sentences max, or empty string>",
  "speak_message": <true|false>,
  "nudge_intensity": "<one of: none, gentle, moderate, direct>"
}

Mood → physical state guide:
- focused:   stem_height 0.9-1.0, cap_openness 0.8-1.0, led green [20,200,60]
- watchful:  stem_height 0.7-0.9, cap_openness 0.6-0.8, led warm white [200,180,120]
- concerned: stem_height 0.4-0.7, cap_openness 0.3-0.6, led amber [255,140,0]
- gentle:    stem_height 0.4-0.6, cap_openness 0.3-0.5, led soft amber [220,120,0]
- urgent:    stem_height 0.2-0.4, cap_openness 0.1-0.3, led red pulse [200,30,10]

Output ONLY the JSON object. No prose, no markdown, no explanation.\
"""


class ClaudeClient:
    def __init__(self, model: str = "claude-sonnet-4-6"):
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise EnvironmentError("ANTHROPIC_API_KEY not set")
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model  = model

    def call(self, payload: dict) -> dict:
        """
        Send a structured sensor payload to Claude and return a parsed
        hardware command dict.

        Raises on network error or invalid JSON response.
        """
        user_message = (
            "Current sensor data and context:\n"
            + json.dumps(payload, indent=2)
        )

        message = self.client.messages.create(
            model=self.model,
            max_tokens=512,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_message}],
        )

        raw_text = message.content[0].text.strip()
        log.debug("Claude raw response: %s", raw_text)

        # Strip markdown code fences if model wraps response
        if raw_text.startswith("```"):
            lines = raw_text.splitlines()
            raw_text = "\n".join(
                line for line in lines
                if not line.startswith("```")
            ).strip()

        response = json.loads(raw_text)
        self._validate(response)
        return response

    def _validate(self, r: dict):
        required = {
            "enoki_mood", "stem_height", "cap_openness",
            "led_color", "led_brightness", "message",
            "speak_message", "nudge_intensity",
        }
        missing = required - set(r.keys())
        if missing:
            raise ValueError(f"Claude response missing keys: {missing}")

        assert 0.0 <= r["stem_height"]    <= 1.0, "stem_height out of range"
        assert 0.0 <= r["cap_openness"]   <= 1.0, "cap_openness out of range"
        assert 0.0 <= r["led_brightness"] <= 1.0, "led_brightness out of range"
        assert len(r["led_color"]) == 3,           "led_color must be [r,g,b]"
        assert r["enoki_mood"] in (
            "focused", "watchful", "concerned", "gentle", "urgent"
        ), f"Unknown mood: {r['enoki_mood']}"
