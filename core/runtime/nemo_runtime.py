from __future__ import annotations

from .base_runtime import BaseRuntime
from .execution_context import ExecutionContext
from core.orchestration.agent_runner import run_agent_pipeline
from core.policies.policy_gate import post_execution_policy, pre_execution_policy


class NemoRuntime(BaseRuntime):
    """This runtime will integrate with NVIDIA NemoClaw/OpenShell for agent execution, policy enforcement, and sandboxing."""

    def run(self, task_input: dict) -> dict:
        context = ExecutionContext(task_input)
        context.set_allowed_actions(
            [
                "parse_structure",
                "compare_structures",
                "prioritize_candidate",
                "apply_policy",
                "generate_review",
            ]
        )
        context.metadata["runtime"] = "nemo"

        try:
            context.log_stage("runtime", "started", "Starting Nemo runtime execution.")
            precheck = pre_execution_policy(context, task_input)
            if not precheck["allowed"]:
                context.log_stage("policy_gate", "blocked", precheck["reason"])
                return {
                    "status": "blocked",
                    "reason": precheck["reason"],
                    "logs": context.stage_logs,
                    "task_id": context.task_id,
                }

            context.log_stage("policy_gate", "success", "Pre-execution policy passed.")
            result = run_agent_pipeline(**task_input)

            for entry in result.get("logs", []):
                context.log_stage(
                    entry.get("stage", "pipeline"),
                    entry.get("status", "unknown"),
                    entry.get("message", ""),
                )

            if result.get("status") == "error":
                failure_entry = next(
                    (entry for entry in reversed(result.get("logs", [])) if entry.get("status") == "failure"),
                    None,
                )
                error_message = failure_entry.get("message") if failure_entry else "Pipeline execution failed."
                context.log_stage("runtime", "error", error_message)
                return {
                    "status": "error",
                    "error": error_message,
                    "logs": context.stage_logs,
                    "task_id": context.task_id,
                }

            postcheck = post_execution_policy(context, result)
            context.log_stage("policy_gate", "success", "Post-execution policy applied.")
            context.metadata["warnings"] = postcheck["warnings"]
            return {
                "status": "success",
                "result": postcheck["modified_output"],
                "warnings": postcheck["warnings"],
                "logs": context.stage_logs,
                "task_id": context.task_id,
            }
        except Exception as exc:
            context.log_stage("runtime", "error", str(exc))
            return {
                "status": "error",
                "error": str(exc),
                "logs": context.stage_logs,
                "task_id": context.task_id,
            }
