from core.runtime.execution_context import ExecutionContext


def test_execution_context_logs_and_allows_actions() -> None:
    context = ExecutionContext({"candidate_id": "demo"})
    context.set_allowed_actions(["parse_structure", "compare_structures"])
    context.log_stage("structure", "success", "Parsed structure.")

    assert context.is_action_allowed("parse_structure") is True
    assert context.is_action_allowed("apply_policy") is False

    finalized = context.finalize()
    assert finalized["task_id"]
    assert finalized["start_time"]
    assert finalized["stage_logs"][0]["stage"] == "structure"
