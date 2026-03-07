# Enoki Firmware Setup Guide

Step-by-step guide to get the Enoki mushroom hardware fully working on the Arduino UNO Q.

---

## Hardware Bill of Materials

| Component | Purpose |
|---|---|
| Arduino UNO Q | Main controller (STM32 MCU side) |
| JGA25-371 DC gearmotor with encoder | Rack & pinion mushroom lift |
| L298N H-bridge motor driver | Motor direction and speed control |
| Seeed Studio 1.69" IPS LCD (240x280, ST7789V2) | Mood face, messages, status display |
| SK9822 SPI RGB LED strip (12 LEDs) | Mood colors, grove indicators, animations |
| 12V 2A DC power supply | Motor power via L298N |
| Jumper wires | Connections |
| USB-C cable | Arduino to laptop |

---

## 1. Software Setup

### Option A: Arduino App Lab (recommended)

1. Download Arduino App Lab from https://docs.arduino.cc/software/app-lab/
2. Install and launch it
3. Connect the UNO Q via USB-C
4. Wait for detection, select USB connection

### Option B: Arduino IDE

1. Open Arduino IDE
2. Go to **Tools > Board > Board Manager**
3. Search "Arduino UNO Q", install the board package
4. Select **Arduino UNO Q** as the board
5. Select the correct COM port (check Device Manager on Windows)

### Install Libraries

Three libraries are required. Install all three before uploading any sketch.

**ArduinoJson** (JSON parsing for serial commands):

1. Open **Sketch > Include Library > Manage Libraries**
2. Search "ArduinoJson" by Benoit Blanchon
3. Click Install

**FastLED** (SK9822 LED strip control):

1. Open **Sketch > Include Library > Manage Libraries**
2. Search "FastLED"
3. Click Install

**XIAO ST7789V2 LCD Display** (IPS display driver):

1. Go to https://github.com/limengdu/XIAO_ST7789V2_LCD_Display
2. Click **Code > Download ZIP**
3. In Arduino, go to **Sketch > Include Library > Add .ZIP Library**
4. Select the downloaded ZIP file

---

## 2. Pin Map

Reference this when wiring. Every pin on the UNO Q is accounted for below.

```
Arduino UNO Q Pin       Component               Function
─────────────────────────────────────────────────────────
D2                      Encoder (yellow wire)    Channel A (interrupt)
D3                      Encoder (green wire)     Channel B (interrupt)
D4                      L298N IN1               Motor direction
D5                      L298N IN2               Motor direction
D6                      L298N ENA               Motor speed (PWM)
D7                      LCD BL                  Backlight
D8                      LCD RST                 Reset
D9                      LCD DC                  Data/Command
D10                     LCD CS                  Chip select
D11                     LCD DIN                 SPI MOSI
D13                     LCD CLK                 SPI SCK
A3                      SK9822 DI               LED data (software SPI)
A4                      SK9822 CI               LED clock (software SPI)
5V                      LCD, Encoder, SK9822    Power
GND                     All components          Ground (shared)
```

---

## 3. Phase 1 — Motor Test

Test the motor in isolation first. This is the most likely component to need tuning.

### 3.1 Wiring

Connect **only** the motor, encoder, and L298N. Nothing else yet.

```
JGA25-371 Motor Wires:
  Red (motor+)     ──>  L298N OUT1
  White (motor-)   ──>  L298N OUT2
  Blue (enc VCC)   ──>  Arduino 5V
  Black (enc GND)  ──>  Arduino GND
  Yellow (enc A)   ──>  Arduino D2
  Green (enc B)    ──>  Arduino D3

L298N to Arduino:
  IN1              ──>  Arduino D4
  IN2              ──>  Arduino D5
  ENA              ──>  Arduino D6
  GND              ──>  Arduino GND (shared)

L298N Power:
  12V input        <──  External 12V supply (+)
  GND              <──  External 12V supply (-)

IMPORTANT: Remove the ENA jumper cap on the L298N board.
We control ENA from D6; the jumper bypasses that.
```

### 3.2 Upload

1. Open `firmware/tests/test_motor.ino`
2. If the IDE can't find `motor_controller.h` via the relative path, copy
   `motor_controller.h` and `motor_controller.cpp` from `firmware/enoki_mcu/`
   into the same folder as `test_motor.ino`
3. Upload to the board
4. Open Serial Monitor at **115200 baud**

### 3.3 Expected Output

```
=== Enoki Motor Test ===
Homing...
Homed. Encoder zero: 0
Auto-oscillate ON. Commands: u/d/h/0-9, a=toggle auto
pos=0.000  enc=0  state=holding
pos=0.025  enc=10  state=moving
...
```

The motor should:

1. Drive **downward** on boot (homing routine)
2. Stop when it hits the bottom of travel
3. Begin oscillating: up for 3 seconds, down for 3 seconds

### 3.4 Serial Commands

| Command | Action |
|---|---|
| `u` | Go to 100% (full up) |
| `d` | Go to 0% (full down) |
| `h` | Re-home (drive to bottom, reset zero) |
| `0`-`9` | Go to 0%-90% height |
| `a` | Toggle auto-oscillation on/off |

### 3.5 Troubleshooting

| Problem | Fix |
|---|---|
| Motor doesn't move | Check 12V supply is connected. Check ENA jumper is removed. |
| Motor spins but `enc=` stays 0 | Encoder VCC (blue) not on 5V, or yellow/green wires not on D2/D3 |
| Motor goes UP during homing (should go down) | Swap Red and White wires on L298N OUT1/OUT2 |
| Encoder counts backwards | Swap Yellow and Green wires (D2/D3) |
| Motor oscillates around target | Reduce `kp_` in `motor_controller.cpp` (default 2.0, try 1.0) |
| Motor is too slow reaching target | Increase `kp_` (try 3.0-4.0) |
| Motor buzzes/jitters when holding | Increase `DEAD_ZONE` in `motor_controller.h` (default 5, try 10-15) |

### 3.6 Calibrate MAX_PULSES

This is critical. The default `MAX_PULSES` is 400, but your rack and pinion
will have a different total travel distance.

1. Type `a` to turn off auto-oscillation
2. Type `u` to command full up
3. Watch the `enc=` value as the mushroom rises
4. When it reaches the physical top of travel, note the encoder value
5. Open `firmware/enoki_mcu/motor_controller.h`
6. Change `#define MAX_PULSES 400` to your measured value
7. Re-upload and test again

---

## 4. Phase 2 — Display Test

### 4.1 Wiring

Add the LCD to the existing motor wiring (or test it standalone).

```
Seeed 1.69" LCD:
  VCC   ──>  Arduino 5V
  GND   ──>  Arduino GND
  DIN   ──>  Arduino D11
  CLK   ──>  Arduino D13
  CS    ──>  Arduino D10
  DC    ──>  Arduino D9
  RST   ──>  Arduino D8
  BL    ──>  Arduino D7
```

### 4.2 Upload

1. Open `firmware/tests/test_display.ino`
2. If needed, copy `display_controller.h` and `display_controller.cpp` alongside
3. Upload, open Serial Monitor at 115200

### 4.3 Expected Output

The display should:

1. Turn on with backlight
2. Show a mushroom face (circles for eyes, lines for mouth)
3. Cycle through 5 moods every 3 seconds: focused, watchful, concerned, gentle, urgent
4. Show a text message below the face
5. Show a state bar ("FOCUSED 25m") and grove dots at the bottom

### 4.4 Serial Commands

| Command | Action |
|---|---|
| `1` | Focused face (green) |
| `2` | Watchful face (warm white) |
| `3` | Concerned face (amber) |
| `4` | Gentle face (soft amber) |
| `5` | Urgent face (red) |
| `a` | Toggle auto-cycling |

### 4.5 Troubleshooting

| Problem | Fix |
|---|---|
| Screen is completely dark | Check VCC and GND. Check BL is on D7. |
| Screen has backlight but no image | Check DIN (D11), CLK (D13), CS (D10), DC (D9), RST (D8) |
| Image is rotated/upside down | Change `lcd.SetRotate(0)` in `display_controller.cpp` to `90`, `180`, or `270` |
| Colors look inverted | May be a display variant issue; check library compatibility |

---

## 5. Phase 3 — LED Strip Test

### 5.1 Wiring

```
SK9822 LED Strip:
  DI (Data In)    ──>  Arduino A3
  CI (Clock In)   ──>  Arduino A4
  VCC             ──>  Arduino 5V
  GND             ──>  Arduino GND
```

If your strip has more than 12 LEDs, only the first 12 will be controlled.
Trim or fold the strip as needed for your mushroom cap.

### 5.2 Upload

1. Open `firmware/tests/test_leds.ino`
2. If needed, copy `led_controller.h` and `led_controller.cpp` alongside
3. Upload, open Serial Monitor at 115200

### 5.3 Expected Output

The strip cycles every 3 seconds through:

1. All green (focused)
2. All amber (concerned)
3. All red (urgent)
4. Rainbow chase (celebrate animation)
5. 4 individual colors (grove member test)
6. Red pulsing (breathe animation)

### 5.4 Serial Commands

| Command | Action |
|---|---|
| `1` | Green (focused) |
| `2` | Warm white (watchful) |
| `3` | Amber (concerned) |
| `4` | Red (urgent) |
| `c` | Celebrate animation |
| `b` | Breathe animation |
| `g` | Grove test (4 members) |
| `a` | Toggle auto-cycling |

### 5.5 Troubleshooting

| Problem | Fix |
|---|---|
| LEDs don't light up at all | Check 5V and GND. Verify DI is on A3 and CI is on A4. |
| Colors are wrong (blue instead of red, etc.) | Change `BGR` to `RGB` or `GBR` in `led_controller.cpp` line with `FastLED.addLeds<APA102, ...>` |
| Only first LED works | Check that the strip's data direction is correct (DI not DO) |
| LEDs flicker | Add a 1000uF capacitor across 5V and GND near the strip |

---

## 6. Full Integration

Once all three components pass their individual tests, wire everything together.

### 6.1 Complete Wiring

Connect all components as described in the pin map (Section 2). Use a breadboard
or proto-board to share the 5V and GND rails.

Power chain:
- 12V supply → L298N 12V input + GND
- Arduino USB-C → laptop (provides 5V for Arduino, LCD, encoder, LEDs)
- If LEDs at full brightness pull too much from USB, use L298N's 5V output
  (it has a built-in regulator) or a separate 5V supply

### 6.2 Upload

1. Open `firmware/enoki_mcu/enoki_mcu.ino` in your IDE
2. All `.h` and `.cpp` files in `firmware/enoki_mcu/` will compile together
3. Upload to the board
4. Open Serial Monitor at 115200

### 6.3 Boot Sequence

On power-up, the following should happen in order:

1. Motor drives down (homing), stops at bottom, resets encoder to 0
2. Display shows watchful face + "Enoki is waking up..."
3. LED strip glows warm white at 50%
4. Serial Monitor prints state JSON every second:

```json
{"height":0.000,"encoder_pos":0,"motor_state":"holding","homed":true}
```

### 6.4 Test Commands

Paste these into Serial Monitor (one at a time, press Enter):

**Focused — mushroom rises, green LEDs, happy face:**
```json
{"height":1.0,"led_color":[20,200,60],"led_brightness":1.0,"nudge_intensity":"none","enoki_mood":"focused","message":"Your gaze is steady. Strong session."}
```

**Urgent — mushroom drops, red LEDs pulsing, alarmed face:**
```json
{"height":0.1,"led_color":[200,30,10],"led_brightness":0.8,"nudge_intensity":"direct","enoki_mood":"urgent","message":"You have been idle for 10 minutes."}
```

**Watchful — mushroom mid-height, warm white, neutral face:**
```json
{"height":0.7,"led_color":[200,180,120],"led_brightness":0.7,"nudge_intensity":"none","enoki_mood":"watchful","message":"I see you working. Keep it up."}
```

**Celebrate — mushroom up, rainbow chase:**
```json
{"height":1.0,"led_color":[0,200,255],"led_brightness":1.0,"nudge_intensity":"none","enoki_mood":"focused","message":"Sprint complete!","animate":"celebrate"}
```

**Grove indicators — colored dots on LED strip:**
```json
{"grove_leds":[[20,200,60],[255,140,0],[200,30,10]]}
```

### 6.5 Verify

For each test command, confirm:

- [ ] Motor moves to the correct height
- [ ] LED strip shows the correct color
- [ ] Display face matches the mood
- [ ] Display message text appears
- [ ] State JSON keeps printing at 1Hz with updated height
- [ ] Celebrate animation runs rainbow chase for ~3 seconds
- [ ] "direct" nudge intensity triggers red breathing on LEDs

---

## 7. Connect to the Orchestrator

Once hardware works standalone with manual JSON commands:

1. Note which COM port the Arduino is on (Device Manager > Ports)
2. In the project root, create or edit `.env`:
   ```
   ARDUINO_PORT=COM3
   ```
   (Replace COM3 with your actual port)
3. Run the Python orchestrator:
   ```
   cd orchestrator
   python run.py
   ```
4. The orchestrator sends JSON commands automatically based on Claude's decisions
5. The mushroom will now respond to your focus state in real time

---

## Quick Reference: JSON Command Schema

```json
{
  "height":        0.0-1.0,
  "led_color":     [r, g, b],
  "led_brightness": 0.0-1.0,
  "nudge_intensity": "none|gentle|moderate|direct",
  "enoki_mood":    "focused|watchful|concerned|gentle|urgent",
  "message":       "Up to 64 chars for the display",
  "animate":       "celebrate",
  "grove_leds":    [[r,g,b], [r,g,b], ...]
}
```

## Quick Reference: State Response (1Hz from Arduino)

```json
{
  "height":       0.0-1.0,
  "encoder_pos":  raw pulse count,
  "motor_state":  "homing|moving|holding",
  "homed":        true|false
}
```
