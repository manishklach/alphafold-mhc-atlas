from __future__ import annotations


class BaseRuntime:
    """Base interface for MHC Atlas OS runtime backends.

    A runtime is responsible for deciding how the orchestration layer is executed.
    Local, governed, and multi-agent runtimes share this interface so the rest of
    the system can remain runtime-agnostic.
    """

    def run(self, task_input: dict) -> dict:
        raise NotImplementedError
