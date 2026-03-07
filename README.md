# enoki

![glow in the dark mushrooms](./images/enoki.png)

// currently TODO
- in phase 2, work on `focus_model_data.h` — the `sensor_fusion `sketch #includes this. train a TFLite model and convert it via: `xxd -i focus_classifier.tflite > arduino_uno_q/sensor_fusion/focus_model_data.h`
- test script for raspberry pi - 

// currently done
- raspberry pi modules
- arduino sensor fusion sketch
- arduino actuator controller sketch

// considerations
- continuous sensing loop instead of incremental/discrete growth

// links to supplementary stuff + demo
- youtube link tbd
- will post presentation link here when done

// design files - see figma, rhino3d
// structure of pipeline (hardware, software, etc)

enoki/
├── pi/
│   ├── main.py              ← orchestrator: threads, 1Hz loop, Claude trigger logic
│   ├── claude_client.py     ← Anthropic API wrapper, system prompt, response validation
│   ├── state_machine.py     ← deterministic rules (DOZING >90s → trigger, etc.)
│   ├── pattern_learner.py   ← SQLite logging + RandomForest slump prediction
│   ├── actuator_client.py   ← serial JSON commands to Arduino, named poses
│   ├── vision.py            ← MediaPipe face mesh, EAR, iris gaze score, generator
│   ├── tts.py               ← piper-tts → espeak-ng fallback, non-blocking threads
│   ├── train_pattern.py     ← nightly cron script to retrain the pattern model
│   └── requirements.txt
├── arduino_uno_q/
│   ├── sensor_fusion/       ← TFLite NPU inference, 5 sensors → state JSON at 1Hz
│   └── actuator_controller/ ← PCA9685 I2C servos + NeoPixel LEDs + buzzer + lerp
├── xiao_esp32s3/
│   └── presence_detector/   ← ESP-WHO face detection → {"face":bool,"eyes_open":bool} at 10Hz
├── models/.gitkeep
├── data/.gitkeep
├── design/.gitkeep
└── .gitignore









- serial ports and testing — /dev/ttyUSB0 (XIAO) and /dev/ttyUSB1 (Arduino) in main.py. Check with ls /dev/ttyUSB* after plugging in; order may differ. Use udevadm rules to make them stable by-id.

ANTHROPIC_API_KEY — must be set in environment before running main.py.

Piper TTS model — download en_US-lessac-medium.onnx to /home/pi/tts_models/ before the hackathon. Will fall back to espeak-ng automatically if missing.

Arduino libraries needed: ArduinoJson, Adafruit_PWMServoDriver, Adafruit_NeoPixel, Arduino_TensorFlowLite, ESP-WHO (for XIAO).





pi/test_servo.py — run on Pi after wiring servo to PCA9685. Sweeps 0°→180°→0° three times, prints each position. Pass = servo moves smoothly without jitter.

pi/test_claude.py — run anywhere with ANTHROPIC_API_KEY set. Sends a hardcoded IDLE payload, prints the full response, validates every field. Pass = JSON is valid and in-range.

Run order on hackathon day:


# Step 2 (on Pi, after wiring servo)
sudo i2cdetect -y 1        # confirm 0x40 appears
python3 pi/test_servo.py

# Step 4 (anywhere)
export ANTHROPIC_API_KEY=sk-ant-...
python3 pi/test_claude.py