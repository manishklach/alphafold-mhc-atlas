from __future__ import annotations

import json
import os
from typing import Any
from urllib import error, request

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
    st.caption("Minimal UI for parsing structures, comparing WT vs mutant, and viewing rankings.")

    st.sidebar.markdown("### Navigation")
    page = st.sidebar.radio(
        "Page",
        ["Upload Structures", "Compare WT vs Mutant", "View Rankings"],
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

    if page == "Upload Structures":
        render_parse_page()
    elif page == "Compare WT vs Mutant":
        render_compare_page()
    else:
        render_rankings_page()


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


if __name__ == "__main__":
    main()
