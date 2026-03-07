# Enoki

**A networked AI mushroom companion that keeps you and your study group focused — powered by Claude, embodied in hardware, connected through the cloud.**

![glow in the dark mushrooms](./images/enoki.png)

---

## What Is Enoki?

Enoki is a physical desk companion shaped like a mushroom. It watches your focus through sensors and a camera, gives you gentle nudges when you drift, and physically reacts to your productivity — standing tall and glowing green when you're locked in, drooping and turning amber when you're distracted.

But Enoki isn't just a solo tool. Multiple Enokis connect through the cloud to form **Groves** — small study groups where students hold each other accountable. Your mushroom doesn't just reflect *your* focus. It reflects your *group's* focus. When the whole grove is working, every mushroom stands tall. When someone drifts, the group sees it. Social accountability through a physical object, not another notification on your phone.

Pair it with **Mentra Live smart glasses** and Enoki becomes conversational — it sees what you see, hears what you say, and whispers recommendations directly in your ear.

---

## Why Enoki?

Most productivity tools are apps on the screen you're already distracted by. Enoki is different:

1. **Physical presence** — A mushroom on your desk creates an emotional bond that an app notification never will. You feel bad when it droops. You feel proud when it's tall and green.
2. **Social accountability without surveillance** — Your grove sees abstracted focus state, not your screen or camera. It's "are you working?" not "what are you doing?" Privacy-preserving social pressure.
3. **Ambient, not interruptive** — You glance at the mushroom, you don't get a popup. The glasses whisper, they don't buzz your phone. Information is there when you want it and invisible when you don't.
4. **AI that adapts to you** — Claude learns your patterns, your personality, your response to different nudge styles. It's not one-size-fits-all productivity advice.
5. **Multiplayer productivity** — Studying alone is hard. Studying with a group where you can physically see everyone's commitment is powerful. The grove mechanic turns focus into a cooperative game.

---

## Hardware

Each student's Enoki setup consists of three layers:

### The Mushroom (desk unit)

| Component | Role |
|---|---|
| **Arduino UNO Q** | Dual-brain board (Qualcomm Cortex-A53 MPU + STM32 MCU). The MCU drives the motor, LEDs, and display. |
| **JGA25-371 DC gearmotor with encoder** | Lifts the mushroom body up and down via a rack-and-pinion mechanism. PID-controlled position tracking via quadrature encoder. |
| **L298N H-bridge motor driver** | Drives the DC motor with PWM speed control and bidirectional rotation. |
| **SK9822 SPI RGB LED strip (12 LEDs)** | APA102-compatible addressable LEDs driven via software SPI. Mood colors + individual grove member indicators + sprint pulse animation. |
| **Seeed Studio 1.69" IPS LCD (240×280, ST7789V2)** | Displays Enoki's current mood face, status messages, focus state, and grove member indicators. |
| **XIAO ESP32-S3 Sense** | Tiny camera module for face/eye presence detection at ~10Hz |
| **3D-printed shell** | Mushroom body — translucent cap for LED glow-through, solid stem and base |

### The Glasses (wearable, optional)

| Component | Role |
|---|---|
| **Mentra Live** | Open-source AI smart glasses ($299, 43g). HD camera, microphone, speakers, no display. |

The glasses add three capabilities the mushroom alone can't provide:
- **Vision context** — Sees what you're looking at (phone? textbook? YouTube?) via the 12MP camera
- **Voice input** — You can talk to Enoki ("How's my focus today?", "Start a 25-minute sprint") using the wake phrase "Hey Enoki"
- **Private audio** — Claude's responses are whispered in your ear, not spoken aloud on your desk

### The Brain (your laptop)

Your laptop runs all compute — no extra single-board computer needed:
- Python orchestrator (sensor fusion, state machine, Claude calls)
- MediaPipe vision processing (face mesh + iris tracking from webcam)
- MentraOS MiniApp server (TypeScript bridge for the glasses)
- Piper neural TTS
- SQLite database for pattern learning and study plan persistence
- Cloud sync client for grove state

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        ENOKI CLOUD                              │
│                                                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ Auth + Users  │  │ Grove State  │  │  Grove Claude         │ │
│  │ (Supabase)   │  │ (real-time)  │  │  (group reasoning)    │ │
│  └──────────────┘  └──────┬───────┘  └───────────┬───────────┘ │
│                           │                       │             │
└───────────────────────────┼───────────────────────┼─────────────┘
                            │ WebSocket             │
          ┌─────────────────┼───────────────────────┼──────┐
          │                 │      YOUR LAPTOP       │      │
          │                 ▼                        ▼      │
          │  ┌─────────────────────────────────────────┐   │
          │  │         Enoki Orchestrator (Python)      │   │
          │  │                                          │   │
          │  │  ┌─────────────┐  ┌───────────────────┐ │   │
          │  │  │ Personal    │  │ Vision Claude     │ │   │
          │  │  │ Claude      │  │ (photo analysis)  │ │   │
          │  │  │ (nudges,    │  │                   │ │   │
          │  │  │  convo,     │  └───────────────────┘ │   │
          │  │  │  tool_use)  │                        │   │
          │  │  └─────────────┘  ┌───────────────────┐ │   │
          │  │                   │ State Machine     │ │   │
          │  │  ┌─────────────┐  │ Pattern Learner   │ │   │
          │  │  │ Planner     │  │ PlanStore (SQLite)│ │   │
          │  │  │ Claude      │  └───────────────────┘ │   │
          │  │  └─────────────┘                        │   │
          │  │  ┌─────────────┐                        │   │
          │  │  │ MediaPipe   │                        │   │
          │  │  │ (webcam)    │                        │   │
          │  │  └─────────────┘                        │   │
          │  └──────────┬──────────────────┬───────────┘   │
          │             │                  │               │
          │  ┌──────────▼──────┐  ┌────────▼─────────┐    │
          │  │ MentraOS MiniApp│  │ TTS Engine       │    │
          │  │ (TypeScript)    │  │ (Piper/espeak)   │    │
          │  └────────┬────────┘  └──────────────────┘    │
          └───────────┼────────────────────┼───────────────┘
                      │                    │ USB Serial
        ┌─────────────▼──────┐    ┌────────▼───────────────────┐
        │  Mentra Live       │    │  Arduino UNO Q (MCU)       │
        │  Glasses           │    │  DC Motor + L298N (lift)   │
        │  (camera, mic,     │    │  SK9822 LEDs (mood/grove)  │
        │   speakers)        │    │  IPS LCD (face/status)     │
        └────────────────────┘    │  ◄── XIAO ESP32-S3 (face) │
                                  └────────────────────────────┘
```

### Data Flow

1. **Sensors → Laptop**: The XIAO ESP32-S3 streams face/eye presence at ~10Hz over serial. The laptop webcam feeds MediaPipe for gaze and eye-aspect-ratio tracking. The Mentra glasses capture photos and transcribe speech (wake-phrase filtered: "Hey Enoki").
2. **Laptop → Claude**: The orchestrator merges all sensor data, updates the state machine, and calls Claude when triggers fire (state changes, time intervals, voice commands). Personal Claude can invoke tools (start sprints, check grove status, take photos, set goals) via Anthropic's native tool_use API before returning a hardware response.
3. **Claude → Hardware**: Claude returns a structured JSON response specifying mushroom mood, height (motor position), LED color, brightness, display mood face, and an optional spoken message. The orchestrator routes this to the Arduino (motor/LEDs/LCD) and TTS engine (speech).
4. **Laptop → Cloud**: The orchestrator publishes abstracted focus state to the cloud every ~30 seconds. Grove members' states are pulled down and displayed on the mushroom's LED strip. LED brightness per member scales with accountability pact progress.

---

## Claude AI — Five Specialized Roles

Enoki doesn't use Claude as a simple chatbot. It runs **five distinct Claude contexts**, each with specialized system prompts, different input data, and separate conversation histories.

### 1. Personal Claude

The core Enoki personality. Runs on each user's laptop.

- **Persistent conversation history** — Maintains a rolling window of ~20 exchanges so it remembers what it told you 30 minutes ago
- **Tool use** (Anthropic native `tool_use` API) — Can call tools mid-response:
  - `start_sprint(minutes)` — Proposes a sprint to the grove and starts a local plan sprint
  - `set_goal(description)` — Sets the user's current study goal for progress tracking
  - `check_grove_status()` — Returns current grove member states
  - `take_photo()` — Triggers a photo capture via glasses
  - `update_mushroom(mood, height)` — Directly sets mushroom state
- **Adaptive personality** — Tracks nudge effectiveness (persisted to SQLite across sessions). If gentle nudges work for you, it stays gentle. If you need directness, it escalates.
- **Physical control** — Every response maps to hardware: motor position, LED colors, display face, speech. Claude isn't just generating text, it's controlling a physical object.
- **Plan-aware** — When a study plan is active, Claude knows the current sprint topic, progress toward daily goal, and pact status.

**Personality**: Wise, calm, slightly stoic. States one short fact about what the data shows, then one short encouragement or gentle observation. Maximum 2 sentences. Never lectures.

**Moods** (each maps to a physical state):

| Mood | Height | LED Color | When |
|---|---|---|---|
| Focused | 0.9–1.0 | Green [20,200,60] | User is locked in |
| Watchful | 0.7–0.9 | Warm white [200,180,120] | Monitoring, no concern |
| Concerned | 0.4–0.7 | Amber [255,140,0] | Drift detected |
| Gentle | 0.4–0.6 | Soft amber [220,120,0] | Gentle nudge |
| Urgent | 0.2–0.4 | Red pulse [200,30,10] | Repeated drift, escalating |

### 2. Vision Claude

Analyzes photos from the Mentra glasses to understand *what* the user is doing.

- Glasses capture a photo every ~5 minutes or on state-change triggers (automatic photo when focus state transitions)
- Photo is sent to Claude's vision API: "What is this person looking at? Is it related to their stated task?"
- Structured analysis feeds into Personal Claude's context
- Separate from Personal Claude to avoid burning vision tokens on every conversational exchange

**Example insight**: "User is looking at their phone, Instagram app visible" → Personal Claude can now say: "You've picked up your phone 3 times in 20 minutes. Each time costs you about 8 minutes of refocus time."

### 3. Grove Claude

Observes entire group dynamics. Runs in the cloud as a Supabase Edge Function.

- Receives aggregated state from all grove members every ~60 seconds
- Decides when to send group nudges vs. individual nudges
- Manages group sprints (coordinated focus sessions)
- Generates daily/weekly grove reports via a separate daily-digest function
- 2-minute cooldown between nudges to prevent spam

**Example decisions**:
- 3/4 members focused, 1 idle → Individual nudge: "Your grove is in a sprint. Join them."
- Everyone idle for 10 min → Group nudge: "The whole grove has drifted. Who wants to kick off the next sprint?"
- Sprint completed → Celebration: all mushrooms do a rainbow animation

### 4. Planning Claude

On-demand study session planning, activated by voice through glasses.

- "Hey Enoki, I have a midterm in 3 days. Help me plan."
- Multi-turn conversation — Claude asks clarifying questions before generating a plan
- Plan is broken into sprint-sized blocks (25–45 min) and persisted locally in SQLite
- Sprints integrate with grove sprints — can propose the first sprint to the group
- Automatic sprint advancement: when a sprint's time elapses, the next one starts
- "You planned 2 hours of linear algebra today. You've done 45 minutes. Ready for the next sprint?"

### 5. Insight Claude

Nightly batch analysis of long-term patterns. Not real-time.

- Input: Full day's focus history, glasses photo summaries, conversation history, grove data
- Output: Personalized insights delivered the next morning via daily-digest Edge Function
- "You're 40% more focused before 11am. Schedule hard tasks in the morning."
- "Your focus drops every time you check your phone. Average recovery: 8 minutes."
- "You focus better on days your grove is active. You had 0 grove sessions this week."

---

## The Grove Network

### What Gets Synced

Each Enoki publishes to the cloud every ~30 seconds:

```json
{
  "user_id": "abc123",
  "grove_id": "grove_6042",
  "timestamp": 1741300000,
  "state": "FOCUSED",
  "focus_score": 0.85,
  "session_minutes": 45,
  "today_focus_hours": 2.3,
  "in_sprint": true,
  "mushroom_mood": "focused"
}
```

**No raw sensor data, no photos, no audio leaves the laptop.** Only abstracted focus state. Privacy-first design — the cloud knows *that* you're focused, not *what* you're doing.

### How Mushrooms Reflect the Grove

The SK9822 LED strip on each mushroom has individually addressable LEDs. Each grove member gets a dedicated LED:

- **Green** — that member is focused
- **Amber** — idle or dozing
- **Dark** — away or offline
- **Brightness scaled by pact progress** — brighter = closer to daily goal

During an active sprint, the LEDs pulse a slow green to indicate the sprint is underway.

Glance at your mushroom and you instantly see your group's status. No app, no screen, no notification.

### Grove Features

| Feature | Description |
|---|---|
| **Group Sprints** | Any member proposes a sprint ("25 min focus, go"). Others accept via glasses voice or app. All mushrooms pulse green in sync. |
| **Accountability Pacts** | Grove sets a daily goal (e.g., 3 hours each, configurable via `daily_goal_hours`). Progress visible via mushroom LED brightness per member — brighter = closer to goal. |
| **Nudge Chains** | Idle during a group sprint? Your mushroom droops AND your grove members' mushrooms show amber on your LED slot. |
| **Celebrations** | Whole grove completes a sprint or hits a goal? All mushrooms do a celebration animation — rainbow chase LEDs, mushroom bounces. |
| **Daily Digest** | Insight Claude analyzes the day's data and sends a summary to every grove member. |

### Cloud Tech Stack

- **Supabase** — Authentication, Postgres database, real-time subscriptions via WebSocket
- **Supabase Realtime** — Each grove subscribes to channels for focus_states, grove_nudges, and sprints. State updates broadcast instantly.
- **Edge Functions** — `grove-claude` runs group-level decisions on a ~60-second schedule. `daily-digest` generates end-of-day summaries.

---

## State Machine

Deterministic rules that run locally, independent of Claude. These handle the fast, predictable decisions:

| State | Duration Threshold | Action |
|---|---|---|
| **DOZING** | > 90 seconds | Trigger Claude nudge |
| **IDLE** | > 5 minutes | Trigger Claude nudge |
| **FOCUSED** | > 25 minutes | Suggest a break via Claude |
| **AWAY** | > 10 minutes | Dim LEDs, suppress nudges |

The state machine also tracks recent history (last 20 state transitions) and feeds it to Claude for context. Claude handles the nuanced, adaptive decisions; the state machine handles the instant, deterministic ones.

State transitions trigger a photo capture via the glasses (if wearing) so Vision Claude can see what changed.

---

## Pattern Learning

Enoki logs every state tick to a local SQLite database and uses scikit-learn to find patterns:

- **Features**: Hour of day, minute, day of week, focus state
- **Model**: RandomForest classifier trained nightly via cron job (`train_pattern.py`)
- **Prediction**: Scans forward in 5-minute steps to predict the next high-slump window
- **Fallback**: If not enough data yet (< 200 samples), uses rule-based slump windows (post-lunch 1–3pm, late afternoon 5–6pm)

Pattern data is surfaced to Claude: *"Historically 70% slump rate at 14:xx on Tuesdays (342 samples)."* This lets Claude give preemptive advice, not just reactive nudges.

---

## Mentra Glasses Integration

The Mentra Live glasses connect to Enoki through a **MentraOS MiniApp** — a TypeScript server running on the laptop.

### MiniApp Capabilities

| Feature | MentraOS SDK Method | Purpose |
|---|---|---|
| **Voice input** | `session.events.onTranscription()` | User talks to Enoki hands-free (wake-phrase filtered) |
| **Photo capture** | `session.camera.requestPhoto()` | Capture what user is looking at for Vision Claude |
| **Speech output** | `session.audio.speak()` | Deliver Claude's response via ElevenLabs TTS in-ear |
| **Wake phrase** | "Hey Enoki" / "Enoki" prefix filter | Only transcriptions starting with wake phrase are forwarded |
| **Action polling** | `GET /glasses/actions` | Orchestrator can request a photo capture on state changes |

### What the Glasses Enable

| Without Glasses | With Glasses |
|---|---|
| "You've been idle for 3 minutes" | "You've been idle for 3 minutes. You're looking at Instagram again." |
| Mushroom droops silently | Mushroom droops + whispers: "Your grove is in a sprint. Come back." |
| No voice interaction | "Hey Enoki, how's my focus today?" → "72% — better than your Tuesday average." |
| TTS on desk speaker (everyone hears) | Private audio in your ear only |

---

## Tech Stack Summary

| Layer | Technology | Language |
|---|---|---|
| **AI** | Anthropic Claude (claude-sonnet-4-6) with tool_use | — |
| **Orchestrator** | Custom Python app (`orchestrator/`) | Python 3 |
| **Computer Vision** | MediaPipe face mesh + iris tracking | Python |
| **ML Patterns** | scikit-learn RandomForest | Python |
| **Database (local)** | SQLite (plans, nudge history, patterns) | SQL |
| **TTS** | Piper (primary), espeak-ng (fallback) | — |
| **Glasses MiniApp** | MentraOS SDK | TypeScript (Bun) |
| **Cloud Backend** | Supabase (auth, Postgres, realtime) | — |
| **Cloud Functions** | Supabase Edge Functions | TypeScript |
| **Firmware** | Arduino UNO Q (STM32 MCU side) | C++ |
| **Motor Driver** | L298N H-bridge with PID control | C++ |
| **LED Driver** | FastLED (APA102/SK9822 via software SPI) | C++ |
| **Display Driver** | st7789v2 (SPI, 240×280 IPS LCD) | C++ |
| **JSON Parsing** | ArduinoJson | C++ |
| **Face Detection** | XIAO ESP32-S3 Sense firmware | C++ |

### Python Dependencies

```
anthropic>=0.30.0
pyserial>=3.5
mediapipe>=0.10.0
opencv-python-headless>=4.9.0
numpy>=1.26.0
scikit-learn>=1.4.0
flask>=3.0.0
supabase>=2.0.0
python-dotenv>=1.0.0
```

---

## Repository Structure

```
enoki/
├── ABOUTME.md                     # This file
├── README.md                      # Project intro
├── .env.example                   # Environment variable template
├── .gitignore
│
├── orchestrator/                  # Laptop-side Python application
│   ├── main.py                    # Orchestrator — main loop, sensor fusion, tool execution
│   ├── config.py                  # Centralized configuration from .env
│   ├── run.py                     # Entry point (argparse + logging)
│   ├── train_pattern.py           # Nightly cron job to retrain the focus model
│   ├── requirements.txt           # Python dependencies
│   │
│   ├── claude/                    # All Claude AI roles
│   │   ├── base.py                # Shared client: retry, JSON parsing, tool-use loop
│   │   ├── personal.py            # Personal Claude: nudges, tools, conversation history
│   │   ├── vision_analyst.py      # Vision Claude: photo analysis
│   │   ├── planner.py             # Planning Claude: multi-turn study plans
│   │   ├── insight.py             # Insight Claude: nightly batch analysis
│   │   └── prompts.py             # All system prompts centralized
│   │
│   ├── brain/                     # Deterministic logic
│   │   ├── state_machine.py       # Focus state rules and transition tracking
│   │   └── pattern_learner.py     # SQLite logging + sklearn slump prediction
│   │
│   ├── hardware/                  # Physical output
│   │   ├── actuator.py            # Sends JSON commands to Arduino over serial
│   │   └── tts.py                 # Text-to-speech engine (Piper / espeak-ng)
│   │
│   ├── sensors/                   # Physical input
│   │   ├── webcam.py              # MediaPipe face mesh + eye/gaze tracking
│   │   ├── glasses_receiver.py    # HTTP server for MiniApp data + action requests
│   │   └── xiao.py                # XIAO ESP32-S3 serial reader
│   │
│   ├── network/                   # Cloud connectivity
│   │   ├── cloud_sync.py          # Supabase client: publish, subscribe, grove settings
│   │   └── grove.py               # Grove state, sprints, pact progress, LED mapping
│   │
│   └── planning/                  # Study plan persistence
│       └── plan_store.py          # SQLite-backed plans, sprints, nudge log
│
├── firmware/                      # Arduino UNO Q firmware (C++)
│   ├── enoki_mcu/                 # Main firmware sketch
│   │   ├── enoki_mcu.ino          # Main loop: serial JSON → motor/LED/display
│   │   ├── motor_controller.h/cpp # JGA25-371 DC motor with PID position control
│   │   ├── led_controller.h/cpp   # SK9822 LED strip via FastLED (mood, grove, sprint pulse)
│   │   ├── display_controller.h/cpp # ST7789V2 IPS LCD (mood faces, messages, state)
│   │   └── command_parser.h/cpp   # ArduinoJson command deserialization
│   ├── tests/                     # Standalone test sketches per component
│   │   ├── test_motor.ino
│   │   ├── test_leds.ino
│   │   └── test_display.ino
│   └── SETUP.md                   # Step-by-step hardware setup guide
│
├── miniapp/                       # MentraOS MiniApp (TypeScript)
│   ├── src/
│   │   ├── enoki-app.ts           # Main app: transcription, photo, TTS, wake phrase filter
│   │   ├── bridge.ts              # HTTP client: POST data, GET TTS/actions
│   │   ├── types.ts               # TypeScript interfaces
│   │   └── index.ts               # Entry point
│   ├── package.json
│   └── tsconfig.json
│
├── cloud/                         # Supabase cloud backend
│   ├── migrations/
│   │   ├── 001_initial.sql        # Users, groves, focus_states, sprints, nudges tables
│   │   └── 002_focus_history.sql  # Focus history + RPC for member fetches
│   ├── seed.sql                   # Dev seed data (3 users, 1 grove)
│   └── functions/
│       ├── grove-claude/index.ts  # Group reasoning: nudges, sprints, celebrations
│       └── daily-digest/index.ts  # Nightly insight summaries per grove
│
├── data/                          # SQLite database (enoki.db, gitignored)
│   └── .gitkeep
├── models/                        # Trained sklearn models (.pkl, gitignored)
│   └── .gitkeep
└── design/                        # 3D print files, CAD, design assets
    └── .gitkeep
```

---

## Hardware Bill of Materials

### Per Student (Minimum Setup — ~$110)

| Item | Est. Cost |
|---|---|
| Arduino UNO Q (2GB) | ~$70 |
| JGA25-371 DC gearmotor with encoder | ~$12 |
| L298N H-bridge motor driver | ~$5 |
| SK9822 SPI RGB LED strip (12 LEDs) | ~$8 |
| Seeed Studio 1.69" IPS LCD (240×280, ST7789V2) | ~$8 |
| 3D-printed mushroom shell | ~$5 filament |
| USB-C cable | ~$5 |

### Per Student (Full Setup — ~$410)

| Item | Est. Cost |
|---|---|
| Everything above | ~$110 |
| XIAO ESP32-S3 Sense | ~$15 |
| Mentra Live glasses | $299 |

The laptop and webcam the student already owns. Claude API cost is approximately $1–3/month at normal usage rates.

---

## Sponsor Prize Alignment

Enoki is designed to be competitive across multiple sponsor categories:

| Sponsor | Prize | Fit |
|---|---|---|
| **Anthropic** | $1,000 + $2,500 API credits | Five specialized Claude roles, native tool_use API, adaptive personality, feedback loops, vision analysis. Stress-tests LLM capabilities in real-world hardware. |
| **Qualcomm** | $1,000 + mentorship + ambassador | Built on Arduino UNO Q (Qualcomm Dragonwing processor). Vision, audio, agent behaviors, embodied sensing. |
| **Akamai** | $1,000 | Networked mushrooms (creative connected device), distributed grove architecture, specialized AI models. |
| **Seeed Studio** | Product assortment | Uses XIAO ESP32-S3 Sense for face/eye detection + Seeed Studio IPS LCD display. AI hardware in the real world. |
| **Bambu Lab** | $500 | 3D-printed mushroom with motor-driven mechanical lift and translucent LED cap. |

### Track Alignment

| Track | Fit |
|---|---|
| **LEARN** | Primary track. Adaptive study companion, generative study aids, grove study groups. |
| **CONNECT** | Strong secondary. Reduces isolation of solo studying, builds community through groves. |
| **REFLECT** | Pattern insights, daily reports, understanding your own focus habits. |
| **THRIVE** | Wearable integration (glasses), performance optimization, assistive tool. |

---

## How It Feels to Use Enoki

### Morning

You sit down at your desk. Your mushroom slowly rises and glows a soft warm white — Enoki sees you're here. The LCD shows a watchful face. Your glasses say: "Good morning. Your grove has a 3-hour pact today. Alex and Jordan are already online."

### Deep Focus

You've been coding for 20 minutes. The mushroom is tall and green. The LCD shows a big smile. Three bright green dots on the LED strip — your whole grove is locked in and near their daily goals. Nobody speaks. The mushroom just glows.

### The Drift

You pick up your phone. Your mushroom starts to lower. The green fades to amber. The LCD face turns concerned. Your glasses whisper: "You've been on your phone for 2 minutes. Your grove is still in a sprint — 8 minutes left."

You put the phone down. The mushroom rises again.

### The Nudge Escalation

You've been scrolling for 5 minutes now. The mushroom droops further. Amber turns to red. Your glasses: "Three of your four grove members are focused. You're the holdout." On Alex's desk across campus, your LED on their mushroom dims — your pact progress is falling behind.

You close the app. Get back to work. The mushroom straightens up. Green returns.

### End of Day

Your glasses: "Your grove focused for 11.2 combined hours today. You hit 3 hours 12 minutes — pact complete. Your best focus window was 10am to noon, same as last Tuesday."

All four mushrooms do a celebration animation. LEDs rainbow chase. Mushrooms bounce.

---

## License

MIT

---

*Named after the enoki mushroom — small, connected, and stronger in clusters.*
