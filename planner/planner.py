"""
Planner — sends goal + history to the planning model on the laptop
and returns a structured action (create_tasks | goal_complete | goal_failed).
"""

from __future__ import annotations

from typing import Optional

import httpx

import config.settings as cfg
from planner.prompts import SYSTEM_PROMPT, build_plan_prompt
from tasks.task import Task
from utils.logger import get_logger
from utils.helpers import parse_json_response, new_id, utcnow

log = get_logger(__name__)


class Planner:
    def __init__(self):
        self._base_url = cfg.PLANNER_API_URL.rstrip("/")
        self._model = cfg.PLANNER_MODEL
        log.info("Planner ready — %s  model=%s", self._base_url, self._model)

    # ── Public API ────────────────────────────────────────────────────────

    def plan(
        self,
        goal: str,
        history_text: str,
        pending_tasks: list[Task],
    ) -> dict:
        """
        Ask the planner what to do next.

        Returns one of:
          {"action": "create_tasks",  "tasks": [...]}
          {"action": "goal_complete", "summary": "..."}
          {"action": "goal_failed",   "reason":  "..."}
        """
        pending_dicts = [
            {"id": t.id, "description": t.description, "priority": t.priority}
            for t in pending_tasks
        ]
        user_prompt = build_plan_prompt(goal, history_text, pending_dicts)

        log.debug("Planner prompt (user):\n%s", user_prompt[:600])

        raw = self._call_lmstudio(user_prompt)
        log.debug("Planner raw response:\n%s", raw[:600])

        result = parse_json_response(raw)
        if result is None:
            log.error("Planner returned unparseable response: %s", raw[:300])
            return {
                "action": "goal_failed",
                "reason": f"Planner returned non-JSON response: {raw[:200]}",
            }

        # Normalise tasks — ensure each has an id
        if result.get("action") == "create_tasks":
            for task in result.get("tasks", []):
                if not task.get("id"):
                    task["id"] = new_id()

        log.info("Planner action: %s", result.get("action"))
        return result

    # ── LM Studio client ──────────────────────────────────────────────────

    def _call_lmstudio(self, user_prompt: str) -> str:
        payload = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": cfg.PLANNER_TEMPERATURE,
            "max_tokens": cfg.MAX_TOKENS,
        }

        try:
            with httpx.Client(timeout=cfg.REQUEST_TIMEOUT) as client:
                response = client.post(
                    f"{self._base_url}/chat/completions",
                    json=payload,
                )
                response.raise_for_status()
                data = response.json()
                return data["choices"][0]["message"]["content"]
        except httpx.TimeoutException:
            raise RuntimeError(
                f"Planner request timed out after {cfg.REQUEST_TIMEOUT}s"
            )
        except httpx.HTTPStatusError as e:
            raise RuntimeError(
                f"Planner HTTP error {e.response.status_code}: {e.response.text[:200]}"
            )
        except Exception as e:
            raise RuntimeError(f"Planner call failed: {e}") from e