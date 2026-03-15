from src.workflow_templates import get_workflow_template, list_workflow_templates


def test_workflow_templates_load() -> None:
    names = list_workflow_templates()
    assert "weekly_mutation_review" in names
    template = get_workflow_template("manager_escalation_packet")
    assert "decision" in template.recommended_packet_types
    assert template.packet_template == "manager_escalation"
