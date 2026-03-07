#!/usr/bin/env python3
"""
train_pattern.py — Nightly cron script to retrain the focus pattern model.

Run via cron:
  0 3 * * * cd /path/to/project && python orchestrator/train_pattern.py

Or manually: python orchestrator/train_pattern.py
"""

import logging
import os
import sys

# Add project root for config
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))

from config import load_config
from brain.pattern_learner import PatternLearner

cfg = load_config()
learner = PatternLearner(
    db_path=cfg.DB_PATH,
    model_path=cfg.MODEL_PATH,
    log_interval=cfg.LOG_INTERVAL,
)
learner.train_and_save()
