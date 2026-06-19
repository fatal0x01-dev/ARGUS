"""
Executor — sends a single task to the executor model on the desktop
and returns a structured result (completed | failed).

The executor model runs through LM Studio's MCP API endpoint and
can invoke MCP tools such as mcp/mcp-docker during execution.
"""

from __future__ import annotations

import json

import config.settings as cfg
from executor.prompts import SYSTEM_PROMPT, build_execute_prompt
from tasks.task import Task
from utils.helpers import parse_json_response
from utils.lmstudio_client import LMStudioClient
from utils.logger import get_logger

log = get_logger(__name__)


class Executor:
    def __init__(self):
        self._client = LMStudioClient(
            base_url=cfg.EXECUTOR_API_URL,
            model=cfg.EXECUTOR_MODEL,
            temperature=cfg.EXECUTOR_TEMPERATURE,
        )

        log.info(
            "Executor ready — %s model=%s",
            cfg.EXECUTOR_API_URL,
            cfg.EXECUTOR_MODEL,
        )

    # ──────────────────────────────────────────────────────────────
    # Public API
    # ──────────────────────────────────────────────────────────────

    def execute(self, task: Task) -> dict:
        """
        Execute a task through LM Studio MCP integration.

        Returns:
            {
                "status": "completed",
                "result": "..."
            }

        or

            {
                "status": "failed",
                "result": "",
                "error": "..."
            }
        """

        log.info(
            "Executing task %s: %s",
            task.id,
            task.description[:80],
        )

        prompt = f"""
{SYSTEM_PROMPT}

{build_execute_prompt(task.id, task.description)}
""".strip()

        try:
            response = self._client.chat_mcp(
                prompt=prompt,
                integrations=[
                    {
                        "type": "plugin",
                        "id": "mcp/mcp-docker",
                    }
                ],
            )

        except RuntimeError as e:
            log.error(
                "Executor API error for task %s: %s",
                task.id,
                e,
            )

            return {
                "status": "failed",
                "result": "",
                "error": str(e),
            }

        log.debug(
            "Executor MCP response:\n%s",
            json.dumps(response, indent=2),
        )

        # ----------------------------------------------------------
        # Extract assistant message(s) from LM Studio MCP response
        # ----------------------------------------------------------

        output = response.get("output", [])

        final_text_parts = []

        for item in output:
            if item.get("type") == "message":
                content = item.get("content", "")
                if content:
                    final_text_parts.append(content)

        final_text = "\n".join(final_text_parts).strip()

        # ----------------------------------------------------------
        # Fallback if no assistant message was returned
        # ----------------------------------------------------------

        if not final_text:
            log.warning(
                "No assistant message found in MCP response for task %s",
                task.id,
            )

            return {
                "status": "failed",
                "result": "",
                "error": "No assistant message returned from MCP response",
            }

        log.debug(
            "Executor final text for task %s:\n%s",
            task.id,
            final_text[:2000],
        )

        # ----------------------------------------------------------
        # Attempt to parse structured JSON response
        # ----------------------------------------------------------

        result = parse_json_response(final_text)

        if result is None:
            log.warning(
                "Executor returned non-JSON response for task %s",
                task.id,
            )

            return {
                "status": "completed",
                "result": final_text,
            }

        if "status" not in result:
            result["status"] = "completed"

        if "result" not in result:
            result["result"] = ""

        log.info(
            "Executor result for %s: status=%s",
            task.id,
            result.get("status"),
        )

        return result

    # ──────────────────────────────────────────────────────────────
    # Health check
    # ──────────────────────────────────────────────────────────────

    def is_available(self) -> bool:
        return self._client.health_check()