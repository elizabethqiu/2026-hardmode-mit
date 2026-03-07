"""
vision_analyst.py — Vision Claude: analyzes photos from glasses camera.

Returns structured analysis: activity, on_task, description.
"""

import base64
import json
import logging
from typing import Any

from .base import ClaudeBase
from .prompts import VISION_SYSTEM_PROMPT

log = logging.getLogger("enoki.claude.vision")


class VisionClaude(ClaudeBase):
    """Analyzes photos from Mentra glasses to understand what the user is doing."""

    def analyze(self, photo_base64: str, context: str = "") -> dict[str, Any]:
        """
        Analyze a base64-encoded photo. Returns:
        {"activity": str, "on_task": bool, "description": str}
        """
        content: list[dict] = []
        if photo_base64:
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": photo_base64,
                },
            })
        text = f"Analyze this image. {context}" if context else "Analyze this image."
        content.append({"type": "text", "text": text})

        raw = self._call_raw(
            system=VISION_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": content}],
        )

        parsed = self._parse_json_response(raw)
        for key in ("activity", "on_task", "description"):
            if key not in parsed:
                parsed[key] = "" if key != "on_task" else False
        return parsed
