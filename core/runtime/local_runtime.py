from __future__ import annotations

from .base_runtime import BaseRuntime
from core.orchestration.agent_runner import run_agent_pipeline


class LocalRuntime(BaseRuntime):
    def run(self, task_input: dict) -> dict:
        return run_agent_pipeline(**task_input)
