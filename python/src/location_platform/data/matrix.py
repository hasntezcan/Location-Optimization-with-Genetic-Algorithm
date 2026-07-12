"""Reusable distance-matrix loading and alignment validation.

Two distinct validation strengths are kept as separate functions because
existing callers genuinely need different strictness:

- ``validate_matrix_shape``: basic square/dimension validation.
- ``validate_matrix_candidate_id_alignment``: the stricter check that also
  cross-validates against a companion sorted-candidate-ID ``.npy`` artifact.

This module never reorders candidates, never rewrites matrix files, never
filters forbidden candidates, and never runs any optimizer logic — it only
loads and validates.
"""

from __future__ import annotations

from pathlib import Path
from typing import Sequence

import numpy as np


def load_matrix(matrix_path: Path) -> np.ndarray:
    """Load a ``.npy`` distance matrix (memory-mapped, read-only)."""
    if not matrix_path.is_file():
        raise FileNotFoundError(f"Distance matrix does not exist: {matrix_path}")
    return np.load(matrix_path, mmap_mode="r")


def validate_matrix_shape(matrix: np.ndarray, candidate_count: int) -> tuple[int, tuple[int, int]]:
    """Validate the matrix is 2D, square, and its dimension matches ``candidate_count``.

    Returns ``(dimension, shape)``. Raises ``ValueError`` on any violation.
    """
    shape = tuple(int(dimension) for dimension in matrix.shape)
    if matrix.ndim != 2:
        raise ValueError(f"Distance matrix must be 2-dimensional, got shape {shape}.")
    if shape[0] != shape[1]:
        raise ValueError(f"Distance matrix must be square, got shape {shape}.")
    if candidate_count and shape[0] != candidate_count:
        raise ValueError(
            "Distance matrix dimension must equal candidate count: "
            f"matrix={shape[0]}, candidates={candidate_count}."
        )
    return shape[0], (shape[0], shape[1])


def _companion_candidate_ids_path(matrix_path: Path) -> Path:
    """Derive the companion ``*_candidate_ids_sorted.npy`` path for a matrix file."""
    suffix = "_distance_meters_nxn.npy"
    if matrix_path.name.endswith(suffix):
        return matrix_path.with_name(matrix_path.name[: -len(suffix)] + "_candidate_ids_sorted.npy")
    return matrix_path.with_name(matrix_path.stem + "_candidate_ids_sorted.npy")


def validate_matrix_candidate_id_alignment(matrix_path: Path, sorted_candidate_ids: Sequence[int]) -> str:
    """Cross-check the matrix's companion sorted-candidate-ID artifact, if present.

    Returns a human-readable description of how alignment was determined.
    Raises ``ValueError`` if the companion artifact exists but does not match
    ``sorted_candidate_ids``. If no companion artifact exists, this is not an
    error — it returns a description noting alignment could not be verified
    against a companion artifact.
    """
    companion_path = _companion_candidate_ids_path(matrix_path)
    if not companion_path.is_file():
        return "sorted by candidate ID ascending (companion ID artifact not found)"

    artifact_ids = np.asarray(np.load(companion_path), dtype=np.int64)
    expected_ids = np.asarray(sorted_candidate_ids, dtype=np.int64)
    if artifact_ids.shape != expected_ids.shape or not np.array_equal(artifact_ids, expected_ids):
        raise ValueError(f"Candidate IDs do not match the matrix companion ID artifact: {companion_path}")
    return f"validated against {companion_path}"
