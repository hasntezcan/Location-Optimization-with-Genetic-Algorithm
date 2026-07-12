import copy
import json

import numpy as np
import pytest

from location_platform.scenario.validation import (
    CURRENT_NETWORK_SCENARIO_ID,
    load_and_validate_scenario_file,
)


def build_valid_scenario():
    return {
        "schemaVersion": "v1",
        "scenarioId": "test-scenario",
        "name": "Test Scenario",
        "useCase": "parcel_locker",
        "grid": {
            "candidateSource": "data/candidate_points.csv",
            "distanceMatrixSource": "data/matrix.npy",
            "candidateIdOrder": "ascending",
            "crs": {"display": "EPSG:4326", "metric": "EPSG:32635"},
        },
        "settings": {
            "runType": "manual_scenario",
            "includeExistingFacilities": True,
            "targetNewFacilityCount": 0,
            "targetTotalFacilityCount": None,
            "objectiveBundle": "test_bundle",
        },
        "facilities": [
            {
                "id": "existing-001",
                "kind": "existing",
                "status": "enabled",
                "facilityType": "parcel_locker",
                "label": "Existing 001",
                "source": "csv_import",
                "coordinates": {"lat": 1.0, "lon": 2.0, "crs": "EPSG:4326"},
                "snap": {
                    "candidateId": 1,
                    "snapDistanceMeters": 0,
                    "snapMethod": "nearest_candidate",
                    "snapStatus": "snapped",
                },
                "metadata": {"physicalCount": 1},
            }
        ],
        "constraints": {"lockedCandidateIds": [], "disabledCandidateIds": []},
        "benchmark": {"demandType": "proxy", "coverageThresholdMeters": 500},
        "metadata": {},
    }


def write_fixture(tmp_path, scenario, *, matrix_size=3):
    scenario_path = tmp_path / "scenario.json"
    scenario_path.write_text(json.dumps(scenario), encoding="utf-8")

    csv_path = tmp_path / "candidate_points.csv"
    csv_path.write_text(
        "id,lat,lon,existing_locker_count\n"
        "1,1.0,2.0,1\n"
        "2,1.1,2.1,0\n"
        "3,1.2,2.2,0\n",
        encoding="utf-8",
    )

    matrix_path = tmp_path / "matrix.npy"
    np.save(matrix_path, np.zeros((matrix_size, matrix_size)))

    return scenario_path, csv_path, matrix_path


def run(tmp_path, scenario, *, matrix_size=3, expect_current_network_seed=False):
    scenario_path, csv_path, matrix_path = write_fixture(tmp_path, scenario, matrix_size=matrix_size)
    return load_and_validate_scenario_file(
        scenario_path,
        csv_path,
        matrix_path,
        expect_current_network_seed=expect_current_network_seed,
    )


def test_valid_scenario_passes(tmp_path):
    report, errors, warnings = run(tmp_path, build_valid_scenario())
    assert errors == []
    assert report["candidateCount"] == 3
    assert report["facilityCount"] == 1
    assert report["physicalFacilityCount"] == 1
    assert report["matrixDimension"] == 3


def test_missing_required_top_level_field_rejected(tmp_path):
    scenario = build_valid_scenario()
    del scenario["useCase"]
    _report, errors, _warnings = run(tmp_path, scenario)
    assert any("useCase" in error for error in errors)


def test_duplicate_facility_ids_rejected(tmp_path):
    scenario = build_valid_scenario()
    second = copy.deepcopy(scenario["facilities"][0])
    second["snap"]["candidateId"] = 2
    scenario["facilities"].append(second)
    _report, errors, _warnings = run(tmp_path, scenario)
    assert any("Duplicate facility id" in error for error in errors)


def test_invalid_kind_and_status_rejected(tmp_path):
    scenario = build_valid_scenario()
    scenario["facilities"][0]["kind"] = "not-a-real-kind"
    scenario["facilities"][0]["status"] = "not-a-real-status"
    _report, errors, _warnings = run(tmp_path, scenario)
    assert any("kind must be one of" in error for error in errors)
    assert any("status must be one of" in error for error in errors)


def test_missing_snap_rejected(tmp_path):
    scenario = build_valid_scenario()
    del scenario["facilities"][0]["snap"]
    _report, errors, _warnings = run(tmp_path, scenario)
    assert any("snap must be an object" in error for error in errors)


def test_invalid_snap_candidate_id_rejected(tmp_path):
    scenario = build_valid_scenario()
    scenario["facilities"][0]["snap"]["candidateId"] = "not-an-int"
    _report, errors, _warnings = run(tmp_path, scenario)
    assert any("snap.candidateId must be an integer" in error for error in errors)


def test_unknown_candidate_id_rejected(tmp_path):
    scenario = build_valid_scenario()
    scenario["facilities"][0]["snap"]["candidateId"] = 999
    _report, errors, _warnings = run(tmp_path, scenario)
    assert any("references unknown candidate ID 999" in error for error in errors)


def test_locked_disabled_conflict_rejected(tmp_path):
    scenario = build_valid_scenario()
    scenario["constraints"]["lockedCandidateIds"] = [2]
    scenario["constraints"]["disabledCandidateIds"] = [2]
    _report, errors, _warnings = run(tmp_path, scenario)
    assert any("Locked and disabled candidate IDs conflict" in error for error in errors)


def test_matrix_count_mismatch_rejected(tmp_path):
    scenario = build_valid_scenario()
    _report, errors, _warnings = run(tmp_path, scenario, matrix_size=2)
    assert any("dimension must equal candidate" in error for error in errors)


def test_current_network_seed_mismatch_rejected(tmp_path):
    scenario = build_valid_scenario()
    scenario["scenarioId"] = CURRENT_NETWORK_SCENARIO_ID
    scenario["settings"]["runType"] = "current_network"
    scenario["settings"]["targetNewFacilityCount"] = 0
    scenario["settings"]["targetTotalFacilityCount"] = None
    scenario["facilities"][0]["source"] = "seed_from_v0_data"
    scenario["facilities"][0]["snap"]["snapMethod"] = "seed_from_existing_locker_count"
    # Candidate CSV seeds candidate 1 only; point the facility at candidate 2 instead,
    # so the seed-match check must fail.
    scenario["facilities"][0]["snap"]["candidateId"] = 2

    _report, errors, _warnings = run(tmp_path, scenario, expect_current_network_seed=True)
    assert any("seed candidate IDs do not match" in error for error in errors)


def test_current_network_seed_match_passes(tmp_path):
    scenario = build_valid_scenario()
    scenario["scenarioId"] = CURRENT_NETWORK_SCENARIO_ID
    scenario["settings"]["runType"] = "current_network"
    scenario["settings"]["targetNewFacilityCount"] = 0
    scenario["settings"]["targetTotalFacilityCount"] = None
    scenario["facilities"][0]["source"] = "seed_from_v0_data"
    scenario["facilities"][0]["snap"]["snapMethod"] = "seed_from_existing_locker_count"
    scenario["facilities"][0]["snap"]["candidateId"] = 1

    _report, errors, _warnings = run(tmp_path, scenario, expect_current_network_seed=True)
    assert errors == []
