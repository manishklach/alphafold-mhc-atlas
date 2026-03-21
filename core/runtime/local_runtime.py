from __future__ import annotations

from core.orchestration.agent_runner import run_agent_pipeline

from .base_runtime import BaseRuntime


class LocalRuntime(BaseRuntime):
    """Deterministic default runtime for MHC Atlas OS.

    This runtime calls the shared orchestration layer directly. It is intended for
    local development, API usage, and fast testing without extra execution controls.
    """

    def run(self, task_input: dict) -> dict:
        return run_agent_pipeline(**task_input)
