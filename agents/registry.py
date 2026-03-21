from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AgentDefinition:
    name: str
    description: str


DEFAULT_AGENTS = [
    AgentDefinition(name="structure-agent", description="Parses structure files into JSON-ready residue and confidence summaries."),
    AgentDefinition(name="comparison-agent", description="Compares WT and mutant structure summaries."),
    AgentDefinition(name="prioritization-agent", description="Ranks candidates using transparent structural rules."),
    AgentDefinition(name="review-agent", description="Builds lightweight review summaries from ranked candidates."),
    AgentDefinition(name="review-coordinator", description="Coordinates recurring review workflows."),
    AgentDefinition(name="packet-builder", description="Builds decision and review packets."),
]
