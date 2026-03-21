from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


class ExecutionContext:
    def __init__(self, task_input: dict[str, Any]) -> None:
        self.task_id = str(uuid4())
        self.start_time = self._now()
        self.task_input = dict(task_input)
        self.stage_logs: list[dict[str, Any]] = []
        self.allowed_actions: list[str] = []
        self.metadata: dict[str, Any] = {}

    def log_stage(self, stage: str, status: str, message: str = "") -> None:
        self.stage_logs.append(
            {
                "stage": stage,
                "status": status,
                "message": message,
                "timestamp": self._now(),
            }
        )

    def set_allowed_actions(self, actions: list[str]) -> None:
        self.allowed_actions = [str(action) for action in actions]

    def is_action_allowed(self, action: str) -> bool:
        return action in self.allowed_actions

    def finalize(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "start_time": self.start_time,
            "stage_logs": self.stage_logs,
            "metadata": self.metadata,
        }

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()
