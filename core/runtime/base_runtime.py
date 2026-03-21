from __future__ import annotations


class BaseRuntime:
    def run(self, task_input: dict) -> dict:
        raise NotImplementedError
