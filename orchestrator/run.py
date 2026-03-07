#!/usr/bin/env python3
"""
run.py — Entry point for Enoki orchestrator.

Usage:
  python -m orchestrator.run
  python orchestrator/run.py
"""

import argparse
import os

# Load .env from project root before any other imports
_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_env = os.path.join(_root, ".env")
if os.path.exists(_env):
    try:
        from dotenv import load_dotenv
        load_dotenv(_env)
    except ImportError:
        pass
import logging
import signal
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger("enoki")


def main():
    parser = argparse.ArgumentParser(description="Enoki focus companion orchestrator")
    parser.add_argument("--no-xiao", action="store_true", help="Disable XIAO serial (dev mode)")
    parser.add_argument("--no-arduino", action="store_true", help="Disable Arduino serial (dev mode)")
    parser.add_argument("--no-vision", action="store_true", help="Disable webcam vision (dev mode)")
    parser.add_argument("--no-cloud", action="store_true", help="Disable Supabase grove sync")
    args = parser.parse_args()

    from main import EnokiOrchestrator
    from config import load_config

    cfg = load_config()
    orch = EnokiOrchestrator(cfg, dev_flags=args)

    def shutdown(signum=None, frame=None):
        log.info("Shutting down...")
        orch.stop()
        sys.exit(0)

    signal.signal(signal.SIGINT, shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    try:
        orch.run()
    except KeyboardInterrupt:
        shutdown()


if __name__ == "__main__":
    main()
