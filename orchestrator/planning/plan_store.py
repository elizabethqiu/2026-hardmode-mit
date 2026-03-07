"""
plan_store.py — SQLite-backed study plan persistence and progress tracking.

Stores structured study plans with sprint-level status tracking.
Plans are keyed by date so each day can have one active plan.
"""

import json
import logging
import sqlite3
import time
from dataclasses import dataclass, field, asdict
from datetime import date, datetime
from typing import Optional

log = logging.getLogger("enoki.planning.plan_store")


@dataclass
class StudySprint:
    topic: str
    duration_minutes: int
    order: int
    status: str = "pending"  # pending | active | completed | skipped
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    actual_minutes: float = 0.0


@dataclass
class StudyPlan:
    plan_summary: str
    sprints: list[StudySprint]
    created_at: float = field(default_factory=time.time)
    plan_date: str = field(default_factory=lambda: date.today().isoformat())

    @property
    def total_planned_minutes(self) -> int:
        return sum(s.duration_minutes for s in self.sprints)

    @property
    def completed_minutes(self) -> float:
        return sum(s.actual_minutes for s in self.sprints if s.status == "completed")

    @property
    def completed_count(self) -> int:
        return sum(1 for s in self.sprints if s.status == "completed")

    @property
    def next_sprint(self) -> Optional[StudySprint]:
        return next((s for s in self.sprints if s.status == "pending"), None)

    @property
    def active_sprint(self) -> Optional[StudySprint]:
        return next((s for s in self.sprints if s.status == "active"), None)


class PlanStore:
    """SQLite-backed store for study plans with progress tracking."""

    def __init__(self, db_path: str = "data/enoki.db"):
        self._db_path = db_path
        self._conn: Optional[sqlite3.Connection] = None
        self._ensure_tables()

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    def _ensure_tables(self):
        try:
            conn = self._get_conn()
            conn.execute("""
                CREATE TABLE IF NOT EXISTS study_plans (
                    plan_date TEXT PRIMARY KEY,
                    plan_summary TEXT NOT NULL,
                    sprints_json TEXT NOT NULL,
                    created_at REAL NOT NULL
                )
            """)
            conn.commit()
        except Exception as e:
            log.warning("Plan store table init failed: %s", e)

    def save_plan(self, plan: StudyPlan):
        """Save or replace today's plan."""
        try:
            conn = self._get_conn()
            sprints_data = [asdict(s) for s in plan.sprints]
            conn.execute(
                """INSERT OR REPLACE INTO study_plans
                   (plan_date, plan_summary, sprints_json, created_at)
                   VALUES (?, ?, ?, ?)""",
                (plan.plan_date, plan.plan_summary,
                 json.dumps(sprints_data), plan.created_at),
            )
            conn.commit()
            log.info("Saved plan for %s: %d sprints", plan.plan_date, len(plan.sprints))
        except Exception as e:
            log.warning("Failed to save plan: %s", e)

    def get_today_plan(self) -> Optional[StudyPlan]:
        """Load today's plan from the DB."""
        return self._load_plan(date.today().isoformat())

    def _load_plan(self, plan_date: str) -> Optional[StudyPlan]:
        try:
            conn = self._get_conn()
            row = conn.execute(
                "SELECT * FROM study_plans WHERE plan_date = ?",
                (plan_date,),
            ).fetchone()
            if not row:
                return None
            sprints_data = json.loads(row["sprints_json"])
            sprints = [StudySprint(**s) for s in sprints_data]
            return StudyPlan(
                plan_summary=row["plan_summary"],
                sprints=sprints,
                created_at=row["created_at"],
                plan_date=row["plan_date"],
            )
        except Exception as e:
            log.warning("Failed to load plan for %s: %s", plan_date, e)
            return None

    def _save_current(self, plan: StudyPlan):
        """Persist current in-memory plan state back to DB."""
        self.save_plan(plan)

    def get_next_sprint(self) -> Optional[StudySprint]:
        """Return the first pending sprint from today's plan."""
        plan = self.get_today_plan()
        return plan.next_sprint if plan else None

    def start_sprint(self, order: int) -> bool:
        """Mark a sprint as active. Returns True if found and updated."""
        plan = self.get_today_plan()
        if not plan:
            return False
        for s in plan.sprints:
            if s.order == order and s.status == "pending":
                s.status = "active"
                s.started_at = time.time()
                self._save_current(plan)
                log.info("Sprint %d started: %s", order, s.topic)
                return True
        return False

    def complete_sprint(self, order: int) -> bool:
        """Mark a sprint as completed, recording actual time spent."""
        plan = self.get_today_plan()
        if not plan:
            return False
        for s in plan.sprints:
            if s.order == order and s.status == "active":
                s.status = "completed"
                s.completed_at = time.time()
                if s.started_at:
                    s.actual_minutes = round((s.completed_at - s.started_at) / 60, 1)
                else:
                    s.actual_minutes = s.duration_minutes
                self._save_current(plan)
                log.info("Sprint %d completed: %s (%.1f min)",
                         order, s.topic, s.actual_minutes)
                return True
        return False

    def skip_sprint(self, order: int) -> bool:
        """Mark a sprint as skipped."""
        plan = self.get_today_plan()
        if not plan:
            return False
        for s in plan.sprints:
            if s.order == order and s.status in ("pending", "active"):
                s.status = "skipped"
                self._save_current(plan)
                log.info("Sprint %d skipped: %s", order, s.topic)
                return True
        return False

    def auto_complete_active(self) -> Optional[int]:
        """If an active sprint has exceeded its duration, complete it. Returns order or None."""
        plan = self.get_today_plan()
        if not plan:
            return None
        active = plan.active_sprint
        if not active or not active.started_at:
            return None
        elapsed_min = (time.time() - active.started_at) / 60
        if elapsed_min >= active.duration_minutes:
            self.complete_sprint(active.order)
            return active.order
        return None

    def get_progress(self) -> dict:
        """Return a summary dict suitable for Claude payload context."""
        plan = self.get_today_plan()
        if not plan:
            return {"has_plan": False}

        active = plan.active_sprint
        nxt = plan.next_sprint
        return {
            "has_plan": True,
            "plan_summary": plan.plan_summary,
            "total_sprints": len(plan.sprints),
            "completed_sprints": plan.completed_count,
            "planned_hours": round(plan.total_planned_minutes / 60, 1),
            "completed_hours": round(plan.completed_minutes / 60, 1),
            "active_sprint": {
                "topic": active.topic,
                "duration_minutes": active.duration_minutes,
                "elapsed_minutes": round((time.time() - active.started_at) / 60)
                    if active.started_at else 0,
            } if active else None,
            "next_sprint": {
                "topic": nxt.topic,
                "duration_minutes": nxt.duration_minutes,
                "order": nxt.order,
            } if nxt else None,
        }

    def get_plan_for_planner_context(self) -> Optional[dict]:
        """Return existing plan in a format suitable for the planner prompt."""
        plan = self.get_today_plan()
        if not plan:
            return None
        return {
            "plan_summary": plan.plan_summary,
            "sprints": [
                {
                    "order": s.order,
                    "topic": s.topic,
                    "duration_minutes": s.duration_minutes,
                    "status": s.status,
                }
                for s in plan.sprints
            ],
            "completed_count": plan.completed_count,
            "total_planned_minutes": plan.total_planned_minutes,
        }
