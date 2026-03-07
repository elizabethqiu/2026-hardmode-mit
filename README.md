# Enoki

A physical mushroom companion + smart glasses that keeps you and your study group focused — powered by Claude AI, connected through the cloud.

![glow in the dark mushrooms](./images/enoki.png)

## Quick Start

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env — set ANTHROPIC_API_KEY at minimum
```

### 2. Run the orchestrator (laptop)

```bash
cd orchestrator
pip install -r requirements.txt
python run.py
```

Dev mode (no hardware) — run this from inside `orchestrator/`:

```bash
cd orchestrator
python run.py --no-xiao --no-arduino --no-vision --no-cloud
```

### 3. Train the pattern model (nightly cron)

```bash
cd orchestrator
python train_pattern.py
```

### 4. Mentra glasses MiniApp (optional)

```bash
cd miniapp
bun install
bun run dev
# Register at console.mentraglass.com with your ngrok URL
```

### 5. Arduino firmware

Open `firmware/enoki_mcu/enoki_mcu.ino` in Arduino App Lab. Upload to UNO Q MCU.

## Project structure

- `orchestrator/` — Python orchestrator (runs on laptop)
- `miniapp/` — MentraOS TypeScript MiniApp for glasses
- `firmware/` — Arduino UNO Q MCU sketch
- `cloud/` — Supabase migrations and edge functions

See [ABOUTME.md](ABOUTME.md) for the full vision.