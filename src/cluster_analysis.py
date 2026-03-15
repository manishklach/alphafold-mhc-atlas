from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from .config import ClusteringConfig


@dataclass(frozen=True)
class ClusteringResult:
    ran: bool
    notes: str
    distance_matrix: pd.DataFrame | None
    projection_df: pd.DataFrame | None
    plot_paths: list[Path]


def run_clustering(
    fingerprint_df: pd.DataFrame,
    clustering_config: ClusteringConfig,
    plot_dir: Path,
) -> ClusteringResult:
    if not clustering_config.enabled:
        return ClusteringResult(False, "Clustering disabled in config.", None, None, [])
    if fingerprint_df.empty:
        return ClusteringResult(False, "No fingerprint rows available.", None, None, [])

    feature_df = fingerprint_df[["variant_id", *clustering_config.features]].copy()
    feature_df = feature_df.dropna()
    if len(feature_df) < clustering_config.min_variants_required:
        return ClusteringResult(
            False,
            f"Need at least {clustering_config.min_variants_required} complete variants for clustering.",
            None,
            None,
            [],
        )

    matrix = feature_df[clustering_config.features].to_numpy(dtype=float)
    if clustering_config.standardize:
        means = matrix.mean(axis=0)
        stds = matrix.std(axis=0)
        stds[stds == 0.0] = 1.0
        matrix = (matrix - means) / stds

    distance_matrix = _pairwise_euclidean(matrix)
    distance_df = pd.DataFrame(distance_matrix, index=feature_df["variant_id"], columns=feature_df["variant_id"])

    projection_df = _project_features(feature_df["variant_id"].tolist(), matrix)
    plot_paths = _create_clustering_plots(feature_df, matrix, projection_df, plot_dir)
    return ClusteringResult(True, "Clustering completed.", distance_df, projection_df, plot_paths)


def _pairwise_euclidean(matrix: np.ndarray) -> np.ndarray:
    deltas = matrix[:, None, :] - matrix[None, :, :]
    return np.sqrt(np.sum(deltas * deltas, axis=2))


def _project_features(variant_ids: list[str], matrix: np.ndarray) -> pd.DataFrame:
    centered = matrix - matrix.mean(axis=0, keepdims=True)
    _, _, vh = np.linalg.svd(centered, full_matrices=False)
    components = vh[:2]
    if components.shape[0] < 2:
        projected = np.column_stack([centered[:, 0], np.zeros(centered.shape[0])])
    else:
        projected = centered @ components.T
    return pd.DataFrame({"variant_id": variant_ids, "pc1": projected[:, 0], "pc2": projected[:, 1]})


def _create_clustering_plots(
    feature_df: pd.DataFrame,
    matrix: np.ndarray,
    projection_df: pd.DataFrame,
    plot_dir: Path,
) -> list[Path]:
    plot_paths: list[Path] = []

    heatmap_path = plot_dir / "fingerprint_heatmap.png"
    plt.figure(figsize=(max(6, matrix.shape[1]), max(4, 0.5 * matrix.shape[0])))
    plt.imshow(matrix, aspect="auto", cmap="coolwarm")
    plt.colorbar(label="Feature value")
    plt.xticks(range(matrix.shape[1]), feature_df.columns[1:], rotation=45, ha="right")
    plt.yticks(range(matrix.shape[0]), feature_df["variant_id"])
    plt.title("Tolerance fingerprint heatmap")
    plt.tight_layout()
    plt.savefig(heatmap_path, dpi=150)
    plt.close()
    plot_paths.append(heatmap_path)

    projection_path = plot_dir / "fingerprint_projection.png"
    plt.figure(figsize=(6, 5))
    plt.scatter(projection_df["pc1"], projection_df["pc2"], color="#4C78A8")
    for _, row in projection_df.iterrows():
        plt.text(row["pc1"], row["pc2"], row["variant_id"], fontsize=8)
    plt.xlabel("PC1")
    plt.ylabel("PC2")
    plt.title("Tolerance fingerprint projection")
    plt.tight_layout()
    plt.savefig(projection_path, dpi=150)
    plt.close()
    plot_paths.append(projection_path)

    return plot_paths
