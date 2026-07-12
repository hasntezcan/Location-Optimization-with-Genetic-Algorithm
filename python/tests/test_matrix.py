import numpy as np
import pytest

from location_platform.data.matrix import (
    load_matrix,
    validate_matrix_candidate_id_alignment,
    validate_matrix_shape,
)


def test_square_matrix_accepted(tmp_path):
    matrix = np.zeros((3, 3))
    path = tmp_path / "matrix.npy"
    np.save(path, matrix)
    loaded = load_matrix(path)
    dimension, shape = validate_matrix_shape(loaded, candidate_count=3)
    assert dimension == 3
    assert shape == (3, 3)


def test_non_square_matrix_rejected(tmp_path):
    matrix = np.zeros((3, 4))
    path = tmp_path / "matrix.npy"
    np.save(path, matrix)
    loaded = load_matrix(path)
    with pytest.raises(ValueError, match="square"):
        validate_matrix_shape(loaded, candidate_count=3)


def test_candidate_count_mismatch_rejected(tmp_path):
    matrix = np.zeros((3, 3))
    path = tmp_path / "matrix.npy"
    np.save(path, matrix)
    loaded = load_matrix(path)
    with pytest.raises(ValueError, match="dimension must equal candidate count"):
        validate_matrix_shape(loaded, candidate_count=5)


def test_missing_matrix_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_matrix(tmp_path / "does_not_exist.npy")


def test_strict_candidate_id_order_match_accepted(tmp_path):
    matrix_path = tmp_path / "kadikoy_distance_meters_nxn.npy"
    np.save(matrix_path, np.zeros((3, 3)))
    companion_path = tmp_path / "kadikoy_candidate_ids_sorted.npy"
    np.save(companion_path, np.array([10, 20, 30], dtype=np.int64))

    description = validate_matrix_candidate_id_alignment(matrix_path, [10, 20, 30])
    assert "validated against" in description


def test_strict_candidate_id_order_mismatch_rejected(tmp_path):
    matrix_path = tmp_path / "kadikoy_distance_meters_nxn.npy"
    np.save(matrix_path, np.zeros((3, 3)))
    companion_path = tmp_path / "kadikoy_candidate_ids_sorted.npy"
    np.save(companion_path, np.array([10, 20, 30], dtype=np.int64))

    with pytest.raises(ValueError, match="do not match"):
        validate_matrix_candidate_id_alignment(matrix_path, [10, 20, 99])


def test_missing_companion_artifact_is_not_an_error(tmp_path):
    matrix_path = tmp_path / "some_matrix.npy"
    np.save(matrix_path, np.zeros((2, 2)))

    description = validate_matrix_candidate_id_alignment(matrix_path, [1, 2])
    assert "not found" in description
