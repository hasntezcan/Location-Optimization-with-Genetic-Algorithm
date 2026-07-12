"""Tests for location_platform.benchmark.current_network.

NOTE: per Phase 1E's task instructions, these tests are written but not
executed in this session (no pytest run performed). Expected values below
were derived by hand from the fixtures defined in this file; they have not
been confirmed by an actual test run. Treat this file as ready-to-run, not
as already-verified.
"""

import json

import numpy as np
import pytest

from location_platform.benchmark.current_network import (
    load_and_validate_matrix,
    load_current_network_from_scenario,
    validate_v0_seed_match,
)
from location_platform.benchmark.evaluation import evaluate_archive, evaluate_facilities
from location_platform.benchmark.reporting import write_outputs

# Three candidates, two neighborhoods, chosen so F1/F2 reduce to clean
# fractions when candidate 1 alone is the facility set:
#   f1 = 140/60 = 7/3
#   f2 = 5/7
CANDIDATES = [
    {"id": 1, "lat": 1.0, "lon": 2.0, "neighborhood": "A", "demand": 10.0, "existing_locker_count": 1, "is_forbidden": 0},
    {"id": 2, "lat": 1.1, "lon": 2.1, "neighborhood": "A", "demand": 20.0, "existing_locker_count": 0, "is_forbidden": 0},
    {"id": 3, "lat": 1.2, "lon": 2.2, "neighborhood": "B", "demand": 30.0, "existing_locker_count": 0, "is_forbidden": 0},
]

MATRIX = np.array(
    [
        [0.0, 1000.0, 2000.0],
        [1000.0, 0.0, 1500.0],
        [2000.0, 1500.0, 0.0],
    ]
)

BETA = 2.0


def build_scenario(facilities, run_type="current_network"):
    return {
        "schemaVersion": "v1",
        "scenarioId": "test-scenario",
        "grid": {},
        "settings": {"runType": run_type, "includeExistingFacilities": True, "objectiveBundle": "test"},
        "facilities": facilities,
        "benchmark": {"demandType": "proxy", "coverageThresholdMeters": 500},
    }


def existing_facility(facility_id, candidate_id, *, status="enabled", snap_status="snapped", physical_count=1, snap=True):
    facility = {
        "id": facility_id,
        "kind": "existing",
        "status": status,
        "metadata": {"physicalCount": physical_count},
    }
    if snap:
        facility["snap"] = {"candidateId": candidate_id, "snapStatus": snap_status}
    return facility


# --- F1/F2 calculation -------------------------------------------------


def test_f1_calculation_matches_hand_derived_value():
    f1, _f2 = evaluate_facilities([1], CANDIDATES, MATRIX, BETA)
    assert f1 == pytest.approx(7 / 3, abs=1e-9)


def test_f2_calculation_matches_hand_derived_value():
    _f1, f2 = evaluate_facilities([1], CANDIDATES, MATRIX, BETA)
    assert f2 == pytest.approx(5 / 7, abs=1e-9)


def test_unknown_facility_id_rejected():
    with pytest.raises(ValueError, match="absent from candidate data"):
        evaluate_facilities([999], CANDIDATES, MATRIX, BETA)


def test_empty_facility_set_rejected():
    with pytest.raises(ValueError, match="must not be empty"):
        evaluate_facilities([], CANDIDATES, MATRIX, BETA)


# --- numeric tolerance (determinism) -----------------------------------


def test_evaluate_facilities_is_deterministic_within_tight_tolerance():
    first_f1, first_f2 = evaluate_facilities([1], CANDIDATES, MATRIX, BETA)
    second_f1, second_f2 = evaluate_facilities([1], CANDIDATES, MATRIX, BETA)
    assert abs(first_f1 - second_f1) < 1e-9
    assert abs(first_f2 - second_f2) < 1e-9


# --- strict active-facility resolution ----------------------------------


def test_strict_resolution_of_valid_scenario(tmp_path):
    scenario = build_scenario(
        [
            existing_facility("existing-001", 1, physical_count=3),
            existing_facility("existing-002", 2, physical_count=1),
        ]
    )
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario), encoding="utf-8")

    existing_candidates, active_ids, physical_count, scenario_metadata = load_current_network_from_scenario(
        scenario_path, CANDIDATES, tmp_path
    )
    assert sorted(active_ids) == [1, 2]
    assert physical_count == 4  # physical vs effective counts: 3 + 1 = 4 physical, 2 effective
    assert scenario_metadata["activeExistingCandidateCount"] == 2
    assert len(existing_candidates) == 2


def test_unknown_candidate_id_in_facility_snap_rejected(tmp_path):
    scenario = build_scenario([existing_facility("existing-001", 999)])
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario), encoding="utf-8")

    with pytest.raises(ValueError, match="absent from candidate CSV"):
        load_current_network_from_scenario(scenario_path, CANDIDATES, tmp_path)


def test_missing_snap_object_rejected(tmp_path):
    scenario = build_scenario([existing_facility("existing-001", 1, snap=False)])
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario), encoding="utf-8")

    with pytest.raises(ValueError, match="snap"):
        load_current_network_from_scenario(scenario_path, CANDIDATES, tmp_path)


def test_unsnapped_facility_silently_excluded_not_an_error(tmp_path):
    scenario = build_scenario(
        [
            existing_facility("existing-001", 1, snap_status="unsnapped"),
            existing_facility("existing-002", 2),
        ]
    )
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario), encoding="utf-8")

    existing_candidates, active_ids, physical_count, _metadata = load_current_network_from_scenario(
        scenario_path, CANDIDATES, tmp_path
    )
    assert active_ids == [2]  # candidate 1's unsnapped facility silently excluded, no error


def test_duplicate_active_facility_for_same_candidate_rejected(tmp_path):
    scenario = build_scenario(
        [
            existing_facility("existing-001", 1),
            existing_facility("existing-002", 1),  # same candidate again
        ]
    )
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario), encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate active existing facilities"):
        load_current_network_from_scenario(scenario_path, CANDIDATES, tmp_path)


def test_no_active_facilities_rejected(tmp_path):
    scenario = build_scenario([existing_facility("existing-001", 1, status="disabled")])
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario), encoding="utf-8")

    with pytest.raises(ValueError, match="No active existing facilities"):
        load_current_network_from_scenario(scenario_path, CANDIDATES, tmp_path)


# --- V0 seed match -------------------------------------------------------


def test_v0_seed_match_passes_when_aligned():
    # CANDIDATES has existing_locker_count=1 only for id=1.
    result = validate_v0_seed_match([1], 1, CANDIDATES)
    assert result["matched"] is True


def test_v0_seed_match_fails_when_misaligned():
    with pytest.raises(ValueError, match="does not match V0"):
        validate_v0_seed_match([2], 1, CANDIDATES)


# --- candidate/matrix alignment ------------------------------------------


def test_matrix_alignment_with_matching_companion_artifact(tmp_path):
    matrix_path = tmp_path / "kadikoy_distance_meters_nxn.npy"
    np.save(matrix_path, MATRIX)
    companion_path = tmp_path / "kadikoy_candidate_ids_sorted.npy"
    np.save(companion_path, np.array([1, 2, 3], dtype=np.int64))

    matrix, alignment = load_and_validate_matrix(matrix_path, CANDIDATES, tmp_path)
    assert "validated against" in alignment
    assert matrix.shape == (3, 3)


def test_matrix_alignment_with_mismatched_companion_artifact_rejected(tmp_path):
    matrix_path = tmp_path / "kadikoy_distance_meters_nxn.npy"
    np.save(matrix_path, MATRIX)
    companion_path = tmp_path / "kadikoy_candidate_ids_sorted.npy"
    np.save(companion_path, np.array([1, 2, 99], dtype=np.int64))

    with pytest.raises(ValueError, match="do not match"):
        load_and_validate_matrix(matrix_path, CANDIDATES, tmp_path)


def test_matrix_alignment_without_companion_artifact(tmp_path):
    matrix_path = tmp_path / "some_matrix.npy"
    np.save(matrix_path, MATRIX)

    _matrix, alignment = load_and_validate_matrix(matrix_path, CANDIDATES, tmp_path)
    assert "not found" in alignment


def test_matrix_shape_mismatch_rejected(tmp_path):
    matrix_path = tmp_path / "wrong_size.npy"
    np.save(matrix_path, np.zeros((2, 2)))

    with pytest.raises(ValueError, match="does not match"):
        load_and_validate_matrix(matrix_path, CANDIDATES, tmp_path)


# --- archive comparison ---------------------------------------------------


def write_archive_csv(tmp_path, rows):
    path = tmp_path / "final_archive.csv"
    lines = ["archive_index,chromosome"] + [f"{i},{chromosome}" for i, chromosome in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def test_archive_comparison_identifies_best_representatives(tmp_path):
    # facility=[1] -> f1=7/3≈2.333 (baseline == solution 1, lowest f2)
    # facility=[2] -> lowest f1 of the three
    # facility=[3] -> neither best
    archive_path = write_archive_csv(tmp_path, [(1, "1"), (2, "2"), (3, "3")])
    metadata_path = tmp_path / "run_metadata.json"
    metadata_path.write_text(
        json.dumps({"k": 1, "includeExistingLockers": False, "effectiveFixedFacilityIdsCount": 0}),
        encoding="utf-8",
    )

    baseline_f1, baseline_f2 = evaluate_facilities([1], CANDIDATES, MATRIX, BETA)
    archive = evaluate_archive(
        archive_path, metadata_path, CANDIDATES, MATRIX, BETA, baseline_f1, baseline_f2, physical_existing_count=1
    )

    assert archive["found"] is True
    assert archive["archiveType"] == "greenfield"
    assert archive["archiveK"] == 1
    assert archive["solutionCount"] == 3
    assert archive["validGreenfieldPhysicalCountComparison"] is True
    assert archive["representatives"]["bestF1"]["solutionId"] == 2
    assert archive["representatives"]["bestF2"]["solutionId"] == 1


def test_archive_not_found_returns_warning_without_raising(tmp_path):
    archive_path = tmp_path / "does_not_exist.csv"
    metadata_path = tmp_path / "run_metadata.json"
    archive = evaluate_archive(archive_path, metadata_path, CANDIDATES, MATRIX, BETA, 1.0, 1.0, physical_existing_count=1)
    assert archive["found"] is False
    assert "warning" in archive


def test_archive_inconsistent_chromosome_lengths_rejected(tmp_path):
    archive_path = write_archive_csv(tmp_path, [(1, "1"), (2, "2|3")])
    metadata_path = tmp_path / "run_metadata.json"
    with pytest.raises(ValueError, match="inconsistent lengths"):
        evaluate_archive(archive_path, metadata_path, CANDIDATES, MATRIX, BETA, 1.0, 1.0, physical_existing_count=1)


# --- report/schema construction -------------------------------------------


def test_write_outputs_creates_expected_files_and_json_schema(tmp_path):
    scenario_metadata = {
        "currentNetworkSource": "scenario",
        "scenarioPath": "data/scenarios/test.json",
        "scenarioId": "test-scenario",
        "activeExistingCandidateCount": 1,
        "physicalFacilityCount": 1,
        "demandType": "proxy",
        "includeExistingFacilities": True,
        "runType": "current_network",
        "objectiveBundle": "test",
        "coverageThresholdMeters": 500,
    }
    existing_candidates = [
        {
            "id": 1,
            "lat": 1.0,
            "lon": 2.0,
            "neighborhood": "A",
            "scenario_physical_count": 1,
            "scenario_facility_ids": ["existing-001"],
            "is_forbidden": 0,
        }
    ]
    archive = {"found": False, "warning": "no archive", "representatives": {}}

    output_dir = tmp_path / "out"
    outputs = write_outputs(
        output_dir,
        existing_candidates,
        1,
        7 / 3,
        5 / 7,
        BETA,
        "sorted by candidate ID ascending (companion ID artifact not found)",
        archive,
        tmp_path / "candidate_points.csv",
        tmp_path / "matrix.npy",
        tmp_path / "final_archive.csv",
        tmp_path / "run_metadata.json",
        scenario_metadata,
        None,
        tmp_path,
    )

    assert len(outputs) == 4
    for path in outputs:
        assert path.is_file()

    summary = json.loads((output_dir / "existing_vs_optimized_benchmark_summary.json").read_text(encoding="utf-8"))
    assert set(summary.keys()) == {
        "generatedAt",
        "beta",
        "matrixAlignment",
        "inputs",
        "dataSemantics",
        "scenarioMetadata",
        "baseline",
        "optimizedArchive",
    }
    assert summary["baseline"]["physicalExistingLockerCount"] == 1
    assert summary["baseline"]["effectiveExistingCandidateCount"] == 1

    report_text = (output_dir / "existing_vs_optimized_benchmark_report.md").read_text(encoding="utf-8")
    assert "Mevcut Yerleşim ve Optimize Yerleşim Karşılaştırması" in report_text
