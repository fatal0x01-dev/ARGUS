"""
Orchestrator — central control loop.

Owns:
  - Global objective state
  - Task queue (via TaskManager)
  - Persistent history (via TaskStore)
  - Planner and Executor clients

Loop:
  1. Ask Planner what to do next
  2. Queue any new tasks
  3. Pull next pending task
  4. Send to Executor
  5. Save result
  6. Repeat until Planner signals goal_complete / goal_failed
     or the iteration cap is hit
"""

from __future__ import annotations

import sys
import time

import config.settings as cfg
from memory.task_store import TaskStore
from memory.rag_store import RAGStore
from tasks.task import Task, TaskStatus
from tasks.task_manager import TaskManager
from tasks.history import History
from planner.planner import Planner
from executor.executor import Executor
from utils.logger import get_logger
from utils.helpers import new_id, utcnow

log = get_logger(__name__)


class Orchestrator:
    def __init__(self):
        # ── Persistence ───────────────────────────────────────────────────
        self._store = TaskStore(cfg.TASK_DB_PATH)
        self._rag = RAGStore()                  # stub in Phase 1

        # ── Task management ───────────────────────────────────────────────
        self._manager = TaskManager(self._store)
        self._history = History(self._store)

        # ── AI clients ────────────────────────────────────────────────────
        self._planner = Planner()
        self._executor = Executor()

        # ── Runtime state ─────────────────────────────────────────────────
        self._goal: str = ""
        self._iteration: int = 0
        self._start_time: float = 0.0

    # ── Entry point ───────────────────────────────────────────────────────

    def run(self, goal: str):
        """Start the orchestration loop for a given goal."""
        self._goal = goal
        self._iteration = 0
        self._start_time = time.time()

        log.info("=" * 60)
        log.info("ORCHESTRATOR START")
        log.info("Goal: %s", goal)
        log.info("=" * 60)

        self._preflight_checks()

        try:
            self._loop()
        except KeyboardInterrupt:
            log.warning("Interrupted by user — state saved, resume any time.")
            sys.exit(0)

    # ── Pre-flight ────────────────────────────────────────────────────────

    def _preflight_checks(self):
        log.info("Checking executor availability...")
        if not self._executor.is_available():
            log.warning(
                "Executor LM Studio not reachable at %s — "
                "make sure it's running before tasks are dispatched.",
                cfg.EXECUTOR_API_URL,
            )
        else:
            log.info("Executor: OK")

        resumed = self._manager.pending_count()
        if resumed:
            log.info("Resuming session — %d pending task(s) in queue", resumed)

    # ── Main loop ─────────────────────────────────────────────────────────

    def _loop(self):
        while self._iteration < cfg.MAX_ITERATIONS:
            self._iteration += 1
            log.info("-" * 50)
            log.info("Iteration %d / %d", self._iteration, cfg.MAX_ITERATIONS)

            # ── Ask the Planner ───────────────────────────────────────────
            history_text = self._history.as_prompt_text(limit=20)
            pending_tasks = [
                t for t in self._manager.queue_snapshot()
                if t.status == TaskStatus.PENDING
            ]

            try:
                plan = self._planner.plan(
                    goal=self._goal,
                    history_text=history_text,
                    pending_tasks=pending_tasks,
                )
            except RuntimeError as e:
                log.error("Planner error: %s", e)
                log.info("Waiting 10s before retry...")
                time.sleep(10)
                continue

            action = plan.get("action")

            # ── Handle planner response ───────────────────────────────────
            if action == "goal_complete":
                self._finish(success=True, message=plan.get("summary", ""))
                return

            if action == "goal_failed":
                self._finish(success=False, message=plan.get("reason", ""))
                return

            if action == "create_tasks":
                self._enqueue_planner_tasks(plan.get("tasks", []))

            else:
                log.warning("Unknown planner action '%s' — skipping", action)

            # ── Execute next pending task ─────────────────────────────────
            task = self._manager.next_task()
            if task is None:
                log.info("No pending tasks — waiting for planner to create more...")
                time.sleep(2)
                continue

            self._run_task(task)

        # ── Iteration cap hit ─────────────────────────────────────────────
        log.error("Reached maximum iterations (%d) without completion.", cfg.MAX_ITERATIONS)
        self._finish(
            success=False,
            message=f"Stopped after {cfg.MAX_ITERATIONS} iterations without goal_complete signal.",
        )

    # ── Task execution ────────────────────────────────────────────────────

    def _run_task(self, task: Task):
        self._manager.mark_running(task)
        self._store.log_event(task.id, "started")

        try:
            result = self._executor.execute(task)
        except Exception as e:
            log.exception("Unexpected executor error for task %s", task.id)
            result = {"status": "failed", "error": str(e), "result": ""}

        status = result.get("status", "failed")
        result_text = result.get("result", "")
        error_text = result.get("error", "")

        if status == "completed":
            self._manager.mark_completed(task, result_text)
            self._store.log_event(task.id, "completed", result_text[:500])
        else:
            if task.retries < cfg.MAX_TASK_RETRIES:
                self._manager.mark_retry(task, error_text)
                self._store.log_event(task.id, "retry", error_text[:300])
            else:
                self._manager.mark_failed(task, error_text)
                self._store.log_event(task.id, "failed", error_text[:300])
                log.error(
                    "Task %s exhausted %d retries — marked FAILED",
                    task.id,
                    cfg.MAX_TASK_RETRIES,
                )

    # ── Helpers ───────────────────────────────────────────────────────────

    def _enqueue_planner_tasks(self, raw_tasks: list[dict]):
        for raw in raw_tasks:
            task = Task(
                id=raw.get("id") or new_id(),
                description=raw.get("description", ""),
                priority=int(raw.get("priority", 1)),
                created_at=utcnow(),
            )
            self._manager.add_task(task)

    def _finish(self, success: bool, message: str):
        elapsed = time.time() - self._start_time
        status = "COMPLETE" if success else "FAILED"
        log.info("=" * 60)
        log.info("GOAL %s after %d iterations (%.1fs)", status, self._iteration, elapsed)
        if message:
            log.info("Message: %s", message)
        log.info("=" * 60)

def main():
    """CLI entry point."""
    if len(sys.argv) > 1:
        goal = " ".join(sys.argv[1:])
    else:
        goal = input("Enter goal: ").strip()

    if not goal:
        print("No goal provided.")
        sys.exit(1)

    orchestrator = Orchestrator()
    orchestrator.run(goal)


if __name__ == "__main__":
    main()