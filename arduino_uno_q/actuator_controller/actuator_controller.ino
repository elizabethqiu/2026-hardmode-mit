/*
 * actuator_controller.ino — Arduino UNO Q actuator layer
 *
 * Receives JSON commands from Pi over USB Serial and drives:
 *   - PCA9685 servo driver (I2C) → stem tilt servo + cap gill servos
 *   - NeoPixel LED strip (GPIO)  → pot glow
 *   - Buzzer (GPIO)              → audio nudge
 *
 * Command JSON from Pi:
 *   {
 *     "stem_height":    0.0-1.0,
 *     "cap_openness":   0.0-1.0,
 *     "led_color":      [r, g, b],
 *     "led_brightness": 0.0-1.0,
 *     "nudge_intensity":"none|gentle|moderate|direct",
 *     "animate":        "celebrate"  (optional)
 *   }
 *
 * Wiring:
 *   PCA9685 → I2C (SDA/SCL), VCC 5V
 *   NeoPixel strip → D6, 5V, GND
 *   Buzzer         → D5
 *
 * Servo channel map (PCA9685):
 *   Ch 0 — stem tilt (base lean)
 *   Ch 1 — cap vertical (stepper proxy via servo for hackathon)
 *   Ch 2 — gill 1
 *   Ch 3 — gill 2
 *   Ch 4 — gill 3
 */

#include <Arduino.h>
#include <Wire.h>
#include <ArduinoJson.h>
#include <Adafruit_PWMServoDriver.h>
#include <Adafruit_NeoPixel.h>

// ── PCA9685 ────────────────────────────────────────────────────────────────
Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

#define SERVO_FREQ   50     // Hz
#define SERVO_MIN   150     // ~0°  pulse count
#define SERVO_MAX   600     // ~180° pulse count

// ── NeoPixel ───────────────────────────────────────────────────────────────
#define LED_PIN      6
#define LED_COUNT    16
Adafruit_NeoPixel strip(LED_COUNT, LED_PIN, NEO_GRB + NEO_KHZ800);

// ── Buzzer ─────────────────────────────────────────────────────────────────
#define BUZZER_PIN   5

// ── Current physical state (for smooth interpolation) ─────────────────────
float currentStemHeight  = 0.5f;
float currentCapOpenness = 0.5f;
float targetStemHeight   = 0.5f;
float targetCapOpenness  = 0.5f;

// ── Helpers ────────────────────────────────────────────────────────────────
uint16_t angleToPulse(float normalized) {
  // normalized 0.0-1.0 → servo pulse count
  return (uint16_t)(SERVO_MIN + normalized * (SERVO_MAX - SERVO_MIN));
}

void setServo(uint8_t channel, float normalized) {
  pwm.setPWM(channel, 0, angleToPulse(constrain(normalized, 0.0f, 1.0f)));
}

void setLEDs(uint8_t r, uint8_t g, uint8_t b, float brightness) {
  brightness = constrain(brightness, 0.0f, 1.0f);
  uint8_t br = (uint8_t)(r * brightness);
  uint8_t bg = (uint8_t)(g * brightness);
  uint8_t bb = (uint8_t)(b * brightness);
  strip.fill(strip.Color(br, bg, bb));
  strip.show();
}

void nudgeBuzzer(const char* intensity) {
  if (strcmp(intensity, "none") == 0) return;

  if (strcmp(intensity, "gentle") == 0) {
    tone(BUZZER_PIN, 440, 80);
  } else if (strcmp(intensity, "moderate") == 0) {
    tone(BUZZER_PIN, 440, 80); delay(150);
    tone(BUZZER_PIN, 523, 80);
  } else if (strcmp(intensity, "direct") == 0) {
    for (int i = 0; i < 3; i++) {
      tone(BUZZER_PIN, 660, 100); delay(180);
    }
  }
}

void animateCelebrate() {
  // Rainbow flash + cap rapid open/close x3
  for (int rep = 0; rep < 3; rep++) {
    for (int hue = 0; hue < 65536; hue += 2048) {
      strip.fill(strip.ColorHSV(hue, 255, 200));
      strip.show();
      delay(20);
    }
    setServo(2, 1.0f); setServo(3, 1.0f); setServo(4, 1.0f); delay(150);
    setServo(2, 0.1f); setServo(3, 0.1f); setServo(4, 0.1f); delay(150);
  }
}

// ── Setup ──────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Wire.begin();

  pwm.begin();
  pwm.setOscillatorFrequency(27000000);  // calibrate for PCA9685 crystal
  pwm.setPWMFreq(SERVO_FREQ);

  strip.begin();
  strip.setBrightness(80);
  strip.show();

  pinMode(BUZZER_PIN, OUTPUT);

  // Boot pose: neutral
  setServo(0, 0.5f);  // stem tilt
  setServo(1, 0.5f);  // cap height
  setServo(2, 0.5f);  // gill 1
  setServo(3, 0.5f);  // gill 2
  setServo(4, 0.5f);  // gill 3
  setLEDs(200, 180, 120, 0.6f);

  Serial.println("{\"status\":\"actuator_ready\"}");
}

// ── Smooth interpolation loop ──────────────────────────────────────────────
unsigned long lastLerpMs = 0;
#define LERP_INTERVAL_MS 50
#define LERP_RATE        0.08f  // fraction per tick (lower = smoother)

// ── Main loop ──────────────────────────────────────────────────────────────
void loop() {
  // Parse incoming command if available
  if (Serial.available()) {
    StaticJsonDocument<256> doc;
    DeserializationError err = deserializeJson(doc, Serial);

    if (!err) {
      if (doc.containsKey("stem_height"))
        targetStemHeight  = doc["stem_height"].as<float>();
      if (doc.containsKey("cap_openness"))
        targetCapOpenness = doc["cap_openness"].as<float>();

      // LED update is immediate
      if (doc.containsKey("led_color") && doc.containsKey("led_brightness")) {
        JsonArray color = doc["led_color"].as<JsonArray>();
        float bri = doc["led_brightness"].as<float>();
        setLEDs(color[0], color[1], color[2], bri);
      }

      // Nudge sound
      if (doc.containsKey("nudge_intensity")) {
        nudgeBuzzer(doc["nudge_intensity"]);
      }

      // Special animations
      if (doc.containsKey("animate")) {
        const char* anim = doc["animate"];
        if (strcmp(anim, "celebrate") == 0) animateCelebrate();
      }
    }
  }

  // Smooth servo interpolation
  unsigned long now = millis();
  if (now - lastLerpMs >= LERP_INTERVAL_MS) {
    lastLerpMs = now;

    currentStemHeight  += (targetStemHeight  - currentStemHeight)  * LERP_RATE;
    currentCapOpenness += (targetCapOpenness - currentCapOpenness) * LERP_RATE;

    // Stem tilt servo: 0=full droop lean, 1=upright
    setServo(0, currentStemHeight);
    // Cap height proxy servo
    setServo(1, currentStemHeight);
    // Gills: openness
    setServo(2, currentCapOpenness);
    setServo(3, currentCapOpenness);
    setServo(4, currentCapOpenness);
  }
}
