from __future__ import annotations

from dataclasses import dataclass

from .workflow_templates import WorkflowTemplate


@dataclass(frozen=True)
class PacketTemplate:
    name: str
    packet_type: str
    section_order: list[str]
    role_emphasis: list[str]
    include_tables: list[str]
    checklist_focus: list[str]


DEFAULT_PACKET_TEMPLATES: dict[str, PacketTemplate] = {
    "weekly_review_standard": PacketTemplate(
        name="weekly_review_standard",
        packet_type="review",
        section_order=[
            "meeting_snapshot",
            "change_summary",
            "current_priorities",
            "open_questions",
            "next_actions",
            "role_views",
            "scope",
        ],
        role_emphasis=["scientist", "comp_lead"],
        include_tables=["summary.csv", "variant_priority_table.csv", "optimized_mutation_panel.csv", "shortlist.csv"],
        checklist_focus=["evidence_reviewed", "uncertainty_reviewed", "missing_data_assessed"],
    ),
    "manager_escalation": PacketTemplate(
        name="manager_escalation",
        packet_type="decision",
        section_order=[
            "meeting_brief",
            "executive_summary",
            "change_summary",
            "open_questions",
            "next_actions",
            "caveats",
        ],
        role_emphasis=["manager"],
        include_tables=["shortlist.csv", "optimized_mutation_panel.csv", "open_questions.csv", "next_action_table.csv"],
        checklist_focus=["biological_caveats_acknowledged", "shortlist_rationale_documented"],
    ),
}


def resolve_packet_template(packet_type: str, workflow_template: WorkflowTemplate | None = None) -> PacketTemplate:
    if workflow_template and workflow_template.packet_template:
        template = DEFAULT_PACKET_TEMPLATES.get(workflow_template.packet_template)
        if template is not None:
            return template
    if packet_type == "decision":
        return DEFAULT_PACKET_TEMPLATES["manager_escalation"]
    return DEFAULT_PACKET_TEMPLATES["weekly_review_standard"]
