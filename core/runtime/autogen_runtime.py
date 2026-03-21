from __future__ import annotations

from typing import Any
from uuid import uuid4

from agents import comparison_agent, prioritization_agent, review_agent, structure_agent

from .base_runtime import BaseRuntime


class StructureAgent:
    """Deterministic structure-parsing agent wrapper for AutoGenRuntime."""

    def run(self, message: dict[str, Any]) -> dict[str, Any]:
        wt_result = structure_agent.run({"structure_path": message["wt_file"]})
        mutant_result = structure_agent.run({"structure_path": message["mutant_file"]})
        return {
            "candidate_id": message["candidate_id"],
            "wt_structure": wt_result["output"],
            "mutant_structure": mutant_result["output"],
            "agent_trace": [self.__class__.__name__],
        }


class ComparisonAgent:
    """Deterministic comparison agent wrapper for AutoGenRuntime."""

    def run(self, message: dict[str, Any]) -> dict[str, Any]:
        comparison_result = comparison_agent.run(
            {
                "wt_structure": message["wt_structure"],
                "mutant_structure": message["mutant_structure"],
            }
        )
        return {
            **message,
            "comparison": comparison_result["output"],
            "agent_trace": [*message.get("agent_trace", []), self.__class__.__name__],
        }


class PrioritizationAgent:
    """Deterministic prioritization agent wrapper for AutoGenRuntime."""

    def run(self, message: dict[str, Any]) -> dict[str, Any]:
        prioritization_result = prioritization_agent.run(
            {
                "comparison_results": [
                    {
                        "candidate_id": message["candidate_id"],
                        "comparison": message["comparison"],
                    }
                ]
            }
        )
        return {
            **message,
            "ranking": prioritization_result["output"][0],
            "agent_trace": [*message.get("agent_trace", []), self.__class__.__name__],
        }


class ReviewAgent:
    """Deterministic review agent wrapper for AutoGenRuntime."""

    def run(self, message: dict[str, Any]) -> dict[str, Any]:
        review_result = review_agent.run(
            {
                "ranked_candidates": [message["ranking"]],
                "pipeline_output": {
                    "candidate_id": message["candidate_id"],
                    "wt_structure": message["wt_structure"],
                    "mutant_structure": message["mutant_structure"],
                    "comparison": message["comparison"],
                    "ranking": message["ranking"],
                },
            }
        )
        return {
            **message,
            "review": review_result["output"],
            "agent_trace": [*message.get("agent_trace", []), self.__class__.__name__],
        }


class AutoGenRuntime(BaseRuntime):
    """Multi-agent runtime for MHC Atlas OS using structured agent handoffs.

    This runtime simulates an AutoGen-style execution model while remaining fully
    deterministic. It differs from LocalRuntime by exposing explicit agent-to-agent
    communication and differs from NemoRuntime by focusing on multi-agent flow
    rather than governed policy enforcement.
    """

    def __init__(self) -> None:
        self.structure_agent = StructureAgent()
        self.comparison_agent = ComparisonAgent()
        self.prioritization_agent = PrioritizationAgent()
        self.review_agent = ReviewAgent()

    def run(self, task_input: dict) -> dict:
        task_id = str(uuid4())
        try:
            structure_message = self.structure_agent.run(task_input)
            comparison_message = self.comparison_agent.run(structure_message)
            prioritization_message = self.prioritization_agent.run(comparison_message)
            review_message = self.review_agent.run(prioritization_message)

            return {
                "status": "success",
                "result": {
                    "candidate_id": review_message["candidate_id"],
                    "status": "success",
                    "stages": {
                        "structure": {
                            "status": "success",
                            "agent": "StructureAgent",
                            "output": {
                                "wt": review_message["wt_structure"],
                                "mutant": review_message["mutant_structure"],
                            },
                        },
                        "comparison": {
                            "status": "success",
                            "agent": "ComparisonAgent",
                            "output": review_message["comparison"],
                        },
                        "prioritization": {
                            "status": "success",
                            "agent": "PrioritizationAgent",
                            "output": review_message["ranking"],
                        },
                        "policy": {
                            "status": "success",
                            "agent": "PrioritizationAgent",
                            "output": review_message["ranking"],
                        },
                        "review": {
                            "status": "success",
                            "agent": "ReviewAgent",
                            "output": review_message["review"],
                        },
                    },
                    "final_output": {
                        "ranking": review_message["ranking"],
                        "review": review_message["review"],
                    },
                    "logs": [
                        {
                            "stage": agent_name,
                            "status": "success",
                            "message": f"{agent_name} completed.",
                        }
                        for agent_name in review_message["agent_trace"]
                    ],
                },
                "warnings": [],
                "logs": [
                    {
                        "stage": agent_name,
                        "status": "success",
                        "message": f"{agent_name} completed.",
                    }
                    for agent_name in review_message["agent_trace"]
                ],
                "agent_trace": review_message["agent_trace"],
                "task_id": task_id,
            }
        except Exception as exc:
            return {
                "status": "error",
                "error": str(exc),
                "logs": [],
                "agent_trace": [],
                "task_id": task_id,
            }
