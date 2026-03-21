from __future__ import annotations

from .base_runtime import BaseRuntime


class NemoRuntime(BaseRuntime):
    """This runtime will integrate with NVIDIA NemoClaw/OpenShell for agent execution, policy enforcement, and sandboxing."""

    def run(self, task_input: dict) -> dict:
        raise NotImplementedError("NemoClaw integration not yet implemented")
