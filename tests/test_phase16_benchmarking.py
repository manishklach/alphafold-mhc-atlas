from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest
import yaml

from src.workspace import load_workspace_config
from src.benchmarking import run_benchmark_comparison

@pytest.fixture
def mock_workspace_benchmark(tmp_path: Path) -> Path:
    project_dir = tmp_path / "project_bench"
    project_dir.mkdir()
    analysis_dir = project_dir / "analysis"
    analysis_dir.mkdir()
    
    # Internal Evidence
    pd.DataFrame([
        {"variant_id": "var1", "allele_name": "A0201", "total_contacts": 50, "contact_delta_wt": -5},
        {"variant_id": "var2", "allele_name": "A0201", "total_contacts": 40, "contact_delta_wt": -15},
    ]).to_csv(analysis_dir / "summary_table.csv", index=False)

    # Workspace Config
    workspace_file = tmp_path / "workspace_bench.yaml"
    workspace_file.write_text(yaml.dump({
        "workspace_id": "test_ws_bench",
        "name": "Test Benchmarking",
        "output_dir": str(tmp_path / "outputs"),
        "projects": [{"project_id": "bench_proj", "path": str(project_dir)}]
    }))
    
    return workspace_file

@pytest.fixture
def mock_external_data(tmp_path: Path) -> Path:
    data_path = tmp_path / "iedb_data.csv"
    pd.DataFrame([
        {"peptide_id": "var1", "allele": "A0201", "binding_class": "Positive"},
        {"peptide_id": "var2", "allele": "A0201", "binding_class": "Negative"},
    ]).to_csv(data_path, index=False)
    return data_path


def test_benchmarking_comparison(mock_workspace_benchmark: Path, mock_external_data: Path):
    results = run_benchmark_comparison(mock_workspace_benchmark, "iedb_binding_subset", mock_external_data)
    
    assert results["benchmark_comparison.csv"].exists()
    assert results["benchmark_report.md"].exists()
    
    df = pd.read_csv(results["benchmark_comparison.csv"])
    assert len(df) == 2
    assert "binding_class" in df.columns
    assert "total_contacts" in df.columns
