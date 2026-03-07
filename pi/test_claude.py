"""
test_claude.py -- Phase 1 Step 4: verify Claude API call works end-to-end

Run: python3 pi/test_claude.py

What it does:
  1. Reads ANTHROPIC_API_KEY from environment
  2. Sends a hardcoded realistic payload to Claude
  3. Prints the full parsed response dict
  4. Confirms all required fields are present and in-range

If it fails: check your API key is exported:
  export ANTHROPIC_API_KEY=sk-ant-...
"""

import os
import sys
import json

# Make sure we can import from pi/ regardless of cwd
sys.path.insert(0, os.path.dirname(__file__))

if not os.environ.get("ANTHROPIC_API_KEY"):
    print("ERROR: ANTHROPIC_API_KEY not set.")
    print("Run: export ANTHROPIC_API_KEY=sk-ant-...")
    sys.exit(1)

print("Importing ClaudeClient...")
try:
    from claude_client import ClaudeClient
except ImportError as e:
    print(f"Import failed: {e}")
    print("Run: pip3 install anthropic")
    sys.exit(1)

# Hardcoded realistic payload -- same shape as main.py sends
TEST_PAYLOAD = {
    "current_state":              "IDLE",
    "state_duration_seconds":     480,
    "session_focus_percentage":   61,
    "session_duration_minutes":   47,
    "predicted_slump_in_minutes": 12,
    "historical_pattern_summary": "historically 68% slump rate at 14:xx on Saturdays (42 samples)",
    "time_of_day":                "14:23",
    "recent_state_history":       ["FOCUSED", "FOCUSED", "IDLE", "IDLE", "DOZING", "IDLE"],
    "enoki_current_pose":         "half_droop",
    "nudge_effectiveness":        "2/3 recent nudges improved focus",
}

print("\nSending payload to Claude:")
print(json.dumps(TEST_PAYLOAD, indent=2))
print("\nCalling Claude API...")

try:
    client = ClaudeClient()
    response = client.call(TEST_PAYLOAD)
except Exception as e:
    print(f"\nERROR: Claude call failed: {e}")
    sys.exit(1)

print("\n--- Claude Response ---")
print(json.dumps(response, indent=2))

# Spot-check a few fields
print("\n--- Validation ---")
checks = [
    ("enoki_mood",     lambda v: v in ("focused","watchful","concerned","gentle","urgent")),
    ("stem_height",    lambda v: 0.0 <= v <= 1.0),
    ("cap_openness",   lambda v: 0.0 <= v <= 1.0),
    ("led_color",      lambda v: len(v) == 3 and all(0 <= c <= 255 for c in v)),
    ("led_brightness", lambda v: 0.0 <= v <= 1.0),
    ("message",        lambda v: isinstance(v, str)),
    ("speak_message",  lambda v: isinstance(v, bool)),
    ("nudge_intensity",lambda v: v in ("none","gentle","moderate","direct")),
]

all_pass = True
for field, check in checks:
    val = response.get(field)
    ok = check(val) if val is not None else False
    status = "PASS" if ok else "FAIL"
    if not ok:
        all_pass = False
    print(f"  {status}  {field}: {val}")

print()
if all_pass:
    print("Phase 1 Step 4: PASS -- Claude API works and response is valid.")
else:
    print("Phase 1 Step 4: FAIL -- some fields are missing or out of range.")
    sys.exit(1)
