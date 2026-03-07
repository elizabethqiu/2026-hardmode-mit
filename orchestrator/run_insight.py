#!/usr/bin/env python3
"""
run_insight.py — Nightly Insight Claude batch analysis.

Fetches yesterday's focus data from SQLite, calls Insight Claude,
and prints the morning report to stdout (or saves to a file).

Run via cron (e.g. 11pm each night):
  0 23 * * * cd /path/to/project && python orchestrator/run_insight.py

Or manually:
  python orchestrator/run_insight.py
  python orchestrator/run_insight.py --date 2026-03-06
  python orchestrator/run_insight.py --out data/insight_latest.json
"""

import argparse
import json
import logging
import os
import sys
from datetime import date

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
log = logging.getLogger("enoki.insight")

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"))
except ImportError:
    pass

from config import load_config
from claude.insight import InsightClaude


def main():
    parser = argparse.ArgumentParser(description="Enoki nightly insight report")
    parser.add_argument(
        "--date",
        help="Date to analyze (YYYY-MM-DD). Defaults to yesterday.",
        default=None,
    )
    parser.add_argument(
        "--out",
        help="Optional path to write JSON output. Prints to stdout if omitted.",
        default=None,
    )
    parser.add_argument(
        "--grove-summary",
        dest="grove_summary",
        help="Optional grove activity summary string to include.",
        default="",
    )
    args = parser.parse_args()

    cfg = load_config()

    if not cfg.ANTHROPIC_API_KEY:
        log.error("ANTHROPIC_API_KEY not set — cannot run Insight Claude")
        sys.exit(1)

    for_date = None
    if args.date:
        try:
            for_date = date.fromisoformat(args.date)
        except ValueError:
            log.error("Invalid date format: %s (expected YYYY-MM-DD)", args.date)
            sys.exit(1)

    insight = InsightClaude(api_key=cfg.ANTHROPIC_API_KEY, model=cfg.CLAUDE_MODEL)

    log.info("Running Insight Claude for %s", for_date or "yesterday")
    result = insight.analyze(
        db_path=cfg.DB_PATH,
        for_date=for_date,
        grove_summary=args.grove_summary,
    )

    output = json.dumps(result, indent=2)

    if args.out:
        os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
        with open(args.out, "w") as f:
            f.write(output)
        log.info("Insight report saved to %s", args.out)
    else:
        print("\n=== Enoki Morning Report ===")
        for i, insight_str in enumerate(result.get("insights", []), 1):
            print(f"  {i}. {insight_str}")
        recs = result.get("recommendations", [])
        if recs:
            print("\nFor tomorrow:")
            for r in recs:
                print(f"  → {r}")
        print(f"\n{result.get('summary', '')}\n")


if __name__ == "__main__":
    main()
