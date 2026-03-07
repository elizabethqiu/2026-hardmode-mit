"""
train_pattern.py — Nightly cron script to retrain the focus pattern model.

Run via cron on Pi:
  0 3 * * * /usr/bin/python3 /home/pi/enoki/pi/train_pattern.py

Or manually: python3 pi/train_pattern.py
"""

import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

from pattern_learner import PatternLearner

learner = PatternLearner()
learner.train_and_save()
