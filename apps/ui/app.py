from __future__ import annotations

import json
import os
from io import StringIO
from typing import Any
from urllib import error, request

import pandas as pd
import streamlit as st


API_BASE_URL = os.getenv("UI_API_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
DEFAULT_WT_FILE = "data/demo_structures/wt_example.pdb"
DEFAULT_MUTANT_FILE = "data/demo_structures/mutant_example_a.pdb"


def api_get(path: str) -> dict[str, Any]:
    return _api_request("GET", path)


def api_post(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    return _api_request("POST", path, payload)


def _api_request(method: str, path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    target = f"{API_BASE_URL}{path}"
    data = None
    headers = {"Content-Type": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
    req = request.Request(target, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=30) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API request failed: {exc.code} {body}") from exc
    except error.URLError as exc:
        raise RuntimeError(
            "API request failed. Start the FastAPI server with "
            "`uvicorn apps.api.main:app --reload` and try again."
        ) from exc


def main() -> None:
    st.set_page_config(page_title="MHC Atlas OS", layout="wide")
    st.title("MHC Atlas OS")
    st.caption("Peptide-MHC Decision Platform for Structure-Guided Experimental Prioritization")
    st.caption("Explainable • Multi-factor • Runtime-agnostic • Agent-driven")

    st.sidebar.markdown("### Navigation")
    page = st.sidebar.radio(
        "Page",
        ["Upload Structures", "Compare WT vs Mutant", "View Rankings", "Batch Analysis", "Decision History"],
    )
    st.sidebar.caption(f"API: {API_BASE_URL}")

    if "parsed_structure" not in st.session_state:
        st.session_state["parsed_structure"] = None
    if "comparison_result" not in st.session_state:
        st.session_state["comparison_result"] = None
    if "ranking_result" not in st.session_state:
        st.session_state["ranking_result"] = None
    if "pipeline_result" not in st.session_state:
        st.session_state["pipeline_result"] = None
    if "batch_result" not in st.session_state:
        st.session_state["batch_result"] = None
    if "decision_history" not in st.session_state:
        st.session_state["decision_history"] = None
    if "report_download" not in st.session_state:
        st.session_state["report_download"] = None

    if page == "Upload Structures":
        render_parse_page()
    elif page == "Compare WT vs Mutant":
        render_compare_page()
    elif page == "View Rankings":
        render_rankings_page()
    elif page == "Batch Analysis":
        render_batch_page()
    else:
        render_decision_history_page()


def render_parse_page() -> None:
    st.subheader("Upload Structures")
    st.write("Parse an existing PDB or mmCIF file through the FastAPI backend.")

    file_path = st.text_input("Structure file path", value=DEFAULT_WT_FILE)

    if st.button("Parse structure", type="primary"):
        if not file_path.strip():
            st.error("A structure file path is required.")
            return
        try:
            response = api_post("/parse", {"file_path": file_path.strip()})
        except RuntimeError as exc:
            st.error(str(exc))
            return
        st.session_state["parsed_structure"] = response
        st.success("Structure parsed successfully.")

    parsed = st.session_state.get("parsed_structure")
    if parsed:
        st.markdown("### Parsed Structure")
        st.write(f"Chains: {', '.join(parsed.get('chains', [])) or 'None'}")
        st.dataframe(parsed.get("residues", []), use_container_width=True)
        st.dataframe(parsed.get("coordinates", []), use_container_width=True)
        st.json(parsed.get("confidence_summary", {}))


def render_compare_page() -> None:
    st.subheader("Compare WT vs Mutant")
    st.write("Compare two structure files and inspect residue-level changes and shift metrics.")

    wt_file = st.text_input("WT file", value=DEFAULT_WT_FILE)
    mutant_file = st.text_input("Mutant file", value=DEFAULT_MUTANT_FILE)

    if st.button("Compare structures", type="primary"):
        if not wt_file.strip() or not mutant_file.strip():
            st.error("Both WT and mutant file paths are required.")
            return
        try:
            response = api_post(
                "/compare",
                {
                    "wt_file": wt_file.strip(),
                    "mutant_file": mutant_file.strip(),
                },
            )
        except RuntimeError as exc:
            st.error(str(exc))
            return
        st.session_state["comparison_result"] = response
        st.success("Comparison complete.")

    comparison = st.session_state.get("comparison_result")
    if comparison:
        st.markdown("### Comparison Result")
        st.metric("Average Shift", f"{comparison.get('avg_shift', 0.0):.3f} Å")
        st.metric("Max Shift", f"{comparison.get('max_shift', 0.0):.3f} Å")
        st.metric("Large Shift Count", int(comparison.get("large_shift_count", 0)))
        st.metric("Confidence Delta", f"{comparison.get('confidence_delta', 0.0):.2f}")
        st.dataframe(comparison.get("residue_changes", []), use_container_width=True)
        if comparison.get("flags"):
            st.write("Flags:", comparison["flags"])


def render_rankings_page() -> None:
    st.subheader("View Rankings")
    st.write("Run the full parse → compare → rank pipeline and inspect explanations.")

    wt_file = st.text_input("WT file path", value=DEFAULT_WT_FILE, key="ranking_wt_file")
    mutant_file = st.text_input("Mutant file path", value=DEFAULT_MUTANT_FILE, key="ranking_mutant_file")
    candidate_id = st.text_input("Candidate ID", value="demo")
    runtime_mode = st.selectbox(
        "Execution Mode",
        ["Local", "Nemo (Governed)", "AutoGen (Multi-Agent)"],
        key="ranking_runtime_mode",
    )

    if st.button("Run pipeline", type="primary"):
        if not wt_file.strip() or not mutant_file.strip() or not candidate_id.strip():
            st.error("WT file, mutant file, and candidate ID are required.")
            return
        try:
            response = api_post(
                "/pipeline",
                {
                    "wt_file": wt_file.strip(),
                    "mutant_file": mutant_file.strip(),
                    "candidate_id": candidate_id.strip(),
                    "runtime": _runtime_value(runtime_mode),
                },
            )
        except RuntimeError as exc:
            st.error(str(exc))
            return
        st.session_state["pipeline_result"] = response
        st.session_state["ranking_result"] = {"ranked_candidates": [response["ranking"]]}
        st.success("Pipeline complete.")

    pipeline_result = st.session_state.get("pipeline_result")
    if pipeline_result:
        ranking = pipeline_result["ranking"]
        st.markdown("### Top Ranking")
        st.dataframe([ranking], use_container_width=True)
        st.markdown("### Interpretation")
        st.caption("Readable summary")
        st.markdown(ranking.get("explanation", ""))
        st.markdown("### Why this matters")
        st.write(_why_this_matters(ranking.get("priority_label", "")))
        if ranking.get("flags"):
            st.write("Flags:", ranking["flags"])

        st.markdown("### Comparison Summary")
        comparison = pipeline_result.get("comparison", {})
        wt_confidence = pipeline_result.get("wt_structure", {}).get("confidence_summary", {}).get("avg")
        mutant_confidence = pipeline_result.get("mutant_structure", {}).get("confidence_summary", {}).get("avg")
        confidence_delta = comparison.get("confidence_delta", 0.0)
        st.metric("Average Shift", f"{comparison.get('avg_shift', 0.0):.3f} Å")
        st.metric("Max Shift", f"{comparison.get('max_shift', 0.0):.3f} Å")
        st.metric("Priority Label", ranking.get("priority_label", ""))
        st.markdown("### Confidence")
        st.write(f"WT Confidence: {_format_confidence(wt_confidence)}")
        st.write(f"Mutant Confidence: {_format_confidence(mutant_confidence)}")
        st.write(f"Δ Confidence: {confidence_delta:.1f}")
        if _runtime_value(runtime_mode) in {"nemo", "autogen"}:
            _render_runtime_details(pipeline_result)
        if st.button("Download Report"):
            try:
                report_response = api_get(f"/report?candidate_id={candidate_id.strip()}")
            except RuntimeError as exc:
                st.error(str(exc))
            else:
                st.session_state["report_download"] = report_response
                st.success(f"Report ready: {report_response['file_name']}")

        report_download = st.session_state.get("report_download")
        if report_download and report_download.get("candidate_id") == candidate_id.strip():
            st.caption(f"File: {report_download['file_name']}")
            st.download_button(
                "Save Markdown Report",
                data=report_download["content"],
                file_name=report_download["file_name"],
                mime="text/markdown",
            )


def render_batch_page() -> None:
    st.subheader("Batch Analysis")
    st.write(
        "Evaluate multiple candidates simultaneously and receive a ranked shortlist for experimental prioritization."
    )
    runtime_mode = st.selectbox(
        "Execution Mode",
        ["Local", "Nemo (Governed)", "AutoGen (Multi-Agent)"],
        key="batch_runtime_mode",
    )
    upload = st.file_uploader("Upload candidate CSV", type=["csv"], key="batch_csv_upload")

    csv_candidates: list[dict[str, str]] = []
    if upload is not None:
        try:
            csv_candidates = _parse_batch_csv(upload.getvalue().decode("utf-8"))
            st.markdown("### CSV Preview")
            st.dataframe(csv_candidates, use_container_width=True, hide_index=True)
        except ValueError as exc:
            st.error(str(exc))

    batch_count = st.number_input("Number of candidates", min_value=1, max_value=10, value=2, step=1)

    candidates: list[dict[str, str]] = []
    for index in range(int(batch_count)):
        st.markdown(f"#### Candidate {index + 1}")
        cols = st.columns(3)
        default_wt = "data/wt.pdb" if index < 2 else DEFAULT_WT_FILE
        default_mutant = f"data/mut{index + 1}.pdb" if index < 2 else DEFAULT_MUTANT_FILE
        candidate_id = cols[0].text_input(
            "candidate_id",
            value=f"mut{index + 1}",
            key=f"batch_candidate_id_{index}",
        )
        wt_file = cols[1].text_input(
            "WT file",
            value=default_wt,
            key=f"batch_wt_file_{index}",
        )
        mutant_file = cols[2].text_input(
            "mutant file",
            value=default_mutant,
            key=f"batch_mutant_file_{index}",
        )
        candidates.append(
            {
                "candidate_id": candidate_id.strip(),
                "wt_file": wt_file.strip(),
                "mutant_file": mutant_file.strip(),
            }
        )

    effective_candidates = csv_candidates or candidates
    if effective_candidates:
        st.markdown("### Candidate Preview")
        st.dataframe(effective_candidates, use_container_width=True, hide_index=True)

    if st.button("Run Batch Analysis", type="primary"):
        if any(
            not item["candidate_id"] or not item["wt_file"] or not item["mutant_file"]
            for item in effective_candidates
        ):
            st.error("Each batch candidate requires candidate_id, WT file, and mutant file.")
            return
        try:
            response = api_post(
                "/batch_pipeline",
                {"runtime": _runtime_value(runtime_mode), "candidates": effective_candidates},
            )
        except RuntimeError as exc:
            st.error(str(exc))
            return
        st.session_state["batch_result"] = response
        st.success("Batch analysis complete.")

    batch_result = st.session_state.get("batch_result")
    if not batch_result:
        return

    display_rows = _build_batch_display_rows(batch_result.get("results", []))
    if display_rows:
        st.markdown("### Ranked Leaderboard")
        dataframe = pd.DataFrame(display_rows)
        styled = (
            dataframe.style.apply(_highlight_top_candidates, axis=1)
            .map(
                _priority_label_style,
                subset=["priority_label"],
            )
            .hide(axis="columns", subset=["_is_top_candidate", "_is_top_one", "explanation"])
        )
        st.dataframe(
            styled,
            use_container_width=True,
            hide_index=True,
        )
        for row in display_rows:
            with st.expander(f"#{row['rank']} {row['candidate_id']}"):
                st.write(row["explanation"])

    error_rows = [row for row in batch_result.get("results", []) if row.get("error")]
    if error_rows:
        st.markdown("### Candidate Errors")
        st.dataframe(error_rows, use_container_width=True, hide_index=True)

    if _runtime_value(runtime_mode) in {"nemo", "autogen"}:
        successful_rows = [row for row in batch_result.get("results", []) if not row.get("error")]
        for row in successful_rows:
            if row.get("warnings"):
                st.warning(f"{row['candidate_id']}: " + " | ".join(row["warnings"]))
            if row.get("task_id"):
                st.caption(f"{row['candidate_id']} task_id: {row['task_id']}")
            if row.get("agent_trace"):
                st.caption(f"{row['candidate_id']} trace: {' → '.join(row['agent_trace'])}")
            if row.get("log_summary"):
                with st.expander(f"Execution Logs: {row['candidate_id']}"):
                    for entry in row["log_summary"]:
                        st.write(f"- {entry}")


def render_decision_history_page() -> None:
    st.subheader("Decision History")
    st.write("Review stored prioritization decisions and filter by candidate ID.")

    candidate_filter = st.text_input("Filter by candidate_id", value="", key="decision_history_filter")

    if st.button("Load Decision History", type="primary"):
        path = "/decisions"
        if candidate_filter.strip():
            path = f"/decisions?candidate_id={candidate_filter.strip()}"
        try:
            response = api_get(path)
        except RuntimeError as exc:
            st.error(str(exc))
            return
        st.session_state["decision_history"] = response

    decision_history = st.session_state.get("decision_history")
    if not decision_history:
        return

    rows = decision_history.get("decisions", [])
    if rows:
        table_rows = [
            {
                "candidate_id": row.get("candidate_id"),
                "priority_score": row.get("priority_score"),
                "priority_label": row.get("priority_label"),
                "timestamp": row.get("timestamp"),
            }
            for row in rows
        ]
        st.dataframe(table_rows, use_container_width=True, hide_index=True)
        for row in rows:
            with st.expander(f"{row.get('candidate_id')} • {row.get('timestamp') or 'no timestamp'}"):
                st.write(row.get("explanation") or "No explanation recorded.")
                if row.get("flags"):
                    st.write("Flags:", row["flags"])
    else:
        st.info("No decision history found for the current filter.")


def _format_confidence(value: Any) -> str:
    if value is None:
        return "N/A"
    return f"{float(value):.1f}"


def _why_this_matters(priority_label: str) -> str:
    if priority_label == "HIGH":
        return "Significant structural deviation suggests mutation could alter stability or binding."
    if priority_label == "MEDIUM":
        return "Moderate structural change suggests mutation may impact local behavior."
    return "Minimal structural deviation suggests mutation is unlikely to significantly alter function."


def _build_batch_display_rows(results: list[dict[str, Any]]) -> list[dict[str, Any]]:
    successful_rows = [
        {
            "rank": index + 1,
            "candidate_id": row.get("candidate_id", ""),
            "priority_score": float(row.get("priority_score", 0.0)),
            "priority_label": row.get("priority_label", ""),
            "flags": ", ".join(row.get("flags", [])),
            "explanation": row.get("explanation", ""),
            "_is_top_candidate": index < 3,
            "_is_top_one": index == 0,
        }
        for index, row in enumerate(
            sorted(
                [result for result in results if result.get("error") is None],
                key=lambda item: (-float(item.get("priority_score", 0.0)), str(item.get("candidate_id", ""))),
            )
        )
    ]
    return successful_rows


def _highlight_top_candidates(row: pd.Series) -> list[str]:
    if bool(row.get("_is_top_one")):
        highlight = "background-color: #ffe9a8; font-weight: 700;"
    elif bool(row.get("_is_top_candidate")):
        highlight = "background-color: #fff7cc;"
    else:
        highlight = ""
    return [highlight] * len(row)


def _priority_label_style(value: Any) -> str:
    if value == "HIGH":
        return "background-color: #f8d7da; color: #7a1020; font-weight: 600;"
    if value == "MEDIUM":
        return "background-color: #fff3cd; color: #8a6d00; font-weight: 600;"
    if value == "LOW":
        return "background-color: #d4edda; color: #155724; font-weight: 600;"
    return ""


def _runtime_value(label: str) -> str:
    if label == "Nemo (Governed)":
        return "nemo"
    if label == "AutoGen (Multi-Agent)":
        return "autogen"
    return "local"


def _render_runtime_details(pipeline_result: dict[str, Any]) -> None:
    warnings = pipeline_result.get("warnings") or []
    if warnings:
        for warning in warnings:
            st.warning(warning)
    task_id = pipeline_result.get("task_id")
    if task_id:
        st.caption(f"Task ID: {task_id}")
    agent_trace = pipeline_result.get("agent_trace") or []
    if agent_trace:
        st.caption("Agent Trace: " + " → ".join(agent_trace))
    logs = pipeline_result.get("logs") or []
    if logs:
        with st.expander("Execution Logs"):
            st.dataframe(logs, use_container_width=True, hide_index=True)


def _parse_batch_csv(content: str) -> list[dict[str, str]]:
    dataframe = pd.read_csv(StringIO(content))
    required = ("candidate_id", "wt_file", "mutant_file")
    if not set(required).issubset(set(dataframe.columns)):
        raise ValueError("CSV must contain candidate_id, wt_file, mutant_file columns.")
    rows = dataframe[list(required)].fillna("").to_dict(orient="records")
    if not rows:
        raise ValueError("CSV contains no candidate rows.")
    return [
        {
            "candidate_id": str(row["candidate_id"]).strip(),
            "wt_file": str(row["wt_file"]).strip(),
            "mutant_file": str(row["mutant_file"]).strip(),
        }
        for row in rows
    ]


if __name__ == "__main__":
    main()
