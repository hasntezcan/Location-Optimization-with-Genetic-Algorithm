import numpy as np
import pytest

from location_platform.scenario.seed import (
    build_current_network_scenario,
    generate_current_network_scenario,
    load_existing_facility_seed_rows,
    write_scenario_json,
)
from location_platform.scenario.validation import validate_scenario


def write_csv(tmp_path, rows, header="id,lat,lon,existing_locker_count"):
    path = tmp_path / "candidate_points.csv"
    lines = [header] + rows
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


MIXED_ORDER_ROWS = [
    "5,1.5,2.5,1",  # non-sequential file order, count 1
    "1,1.1,2.1,2",  # multiplicity: physicalCount = 2
    "3,1.3,2.3,1",
    "2,1.2,2.2,0",  # zero count -> ignored
    "4,1.4,2.4,-1",  # negative count -> excluded (not selected), not an error
]


def test_zero_count_rows_ignored_and_positive_rows_included(tmp_path):
    csv_path = write_csv(tmp_path, MIXED_ORDER_ROWS)
    rows = load_existing_facility_seed_rows(csv_path)
    candidate_ids = [row["candidateId"] for row in rows]
    assert 2 not in candidate_ids  # zero-count row excluded
    assert 4 not in candidate_ids  # negative-count row excluded
    assert set(candidate_ids) == {1, 3, 5}


def test_candidate_ordering_is_deterministic_ascending(tmp_path):
    csv_path = write_csv(tmp_path, MIXED_ORDER_ROWS)
    rows = load_existing_facility_seed_rows(csv_path)
    assert [row["candidateId"] for row in rows] == [1, 3, 5]


def test_physical_count_aggregation_preserved(tmp_path):
    csv_path = write_csv(tmp_path, MIXED_ORDER_ROWS)
    rows = load_existing_facility_seed_rows(csv_path)
    by_id = {row["candidateId"]: row["physicalCount"] for row in rows}
    assert by_id == {1: 2, 3: 1, 5: 1}


def test_invalid_existing_locker_count_rejected(tmp_path):
    csv_path = write_csv(tmp_path, ["1,1.0,2.0,not-a-number"])
    with pytest.raises(ValueError):
        load_existing_facility_seed_rows(csv_path)


def test_missing_required_column_rejected(tmp_path):
    csv_path = write_csv(tmp_path, ["1,1.0,2.0"], header="id,lat,lon")
    with pytest.raises(ValueError, match="missing required field"):
        load_existing_facility_seed_rows(csv_path)


def test_no_qualifying_rows_rejected(tmp_path):
    csv_path = write_csv(tmp_path, ["1,1.0,2.0,0", "2,1.1,2.1,0"])
    with pytest.raises(ValueError, match="No rows found"):
        load_existing_facility_seed_rows(csv_path)


def test_build_current_network_scenario_from_preloaded_rows(tmp_path):
    csv_path = write_csv(tmp_path, MIXED_ORDER_ROWS)
    rows = load_existing_facility_seed_rows(csv_path)
    scenario = build_current_network_scenario(csv_path, rows)
    assert scenario["scenarioId"] == "kadikoy-parcel-locker-current-network"
    assert scenario["grid"]["candidateSource"] == csv_path.as_posix()


def test_scenario_totals_correct(tmp_path):
    csv_path = write_csv(tmp_path, MIXED_ORDER_ROWS)
    scenario = generate_current_network_scenario(csv_path)
    assert scenario["metadata"]["effectiveFacilityLocationCount"] == 3
    assert scenario["metadata"]["physicalFacilityCount"] == 4
    assert len(scenario["facilities"]) == 3


def test_generated_scenario_passes_package_validation(tmp_path):
    csv_path = write_csv(tmp_path, MIXED_ORDER_ROWS)
    scenario = generate_current_network_scenario(csv_path)

    # candidate_data shaped the way scenario.validation expects, built directly
    # from the same source rows (a full candidate CSV would normally include
    # every candidate, not just the seed subset, but candidate_ids only needs
    # to cover the candidate IDs referenced by the generated facilities).
    candidate_data = {
        "candidate_ids": {1, 2, 3, 4, 5},
        "candidate_count": 5,
        "seed_candidate_ids": {1, 3, 5},
        "seed_physical_count": 4,
    }

    facility_data, errors, warnings = validate_scenario(
        scenario, candidate_data, expect_current_network_seed=True
    )
    assert errors == []
    assert facility_data["facility_count"] == 3
    assert facility_data["physical_facility_count"] == 4


def test_write_scenario_json_roundtrip(tmp_path):
    csv_path = write_csv(tmp_path, MIXED_ORDER_ROWS)
    scenario = generate_current_network_scenario(csv_path)
    output_path = tmp_path / "out" / "scenario.json"

    write_scenario_json(output_path, scenario)

    assert output_path.is_file()
    written = output_path.read_text(encoding="utf-8")
    assert written.endswith("\n")


def test_never_reads_nearby_locker_count_column(tmp_path):
    # nearby_locker_count present but irrelevant/malformed; must not affect
    # selection or raise, since it is never read.
    csv_path = write_csv(
        tmp_path,
        ["1,1.0,2.0,1,not-a-number"],
        header="id,lat,lon,existing_locker_count,nearby_locker_count",
    )
    rows = load_existing_facility_seed_rows(csv_path)
    assert [row["candidateId"] for row in rows] == [1]
