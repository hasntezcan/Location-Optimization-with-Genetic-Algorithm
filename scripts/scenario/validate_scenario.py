"""Validate a V1 scenario against the current Kadikoy V0 grid artifacts."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any


DEFAULT_SCENARIO = Path("data/scenarios/kadikoy_parcel_locker_current_network.json")
DEFAULT_CANDIDATE_CSV = Path("data/candidate_points.csv")
DEFAULT_DISTANCE_MATRIX = Path("data/kadikoy_distance_meters_nxn.npy")

REQUIRED_TOP_LEVEL_FIELDS = (
    "schemaVersion",
    "scenarioId",
    "name",
    "useCase",
    "grid",
    "settings",
    "facilities",
    "constraints",
    "benchmark",
    "metadata",
)
REQUIRED_GRID_FIELDS = (
    "candidateSource",
    "distanceMatrixSource",
    "candidateIdOrder",
)
REQUIRED_SETTINGS_FIELDS = (
    "runType",
    "includeExistingFacilities",
    "targetNewFacilityCount",
    "targetTotalFacilityCount",
    "objectiveBundle",
)
REQUIRED_FACILITY_FIELDS = (
    "id",
    "kind",
    "status",
    "facilityType",
    "label",
    "source",
    "coordinates",
    "snap",
    "metadata",
)
REQUIRED_CANDIDATE_COLUMNS = ("id", "lat", "lon", "existing_locker_count")
ALLOWED_RUN_TYPES = {
    "current_network",
    "greenfield_optimization",
    "expansion_optimization",
    "reduction_analysis",
    "manual_scenario",
    "scenario_comparison",
}
ALLOWED_FACILITY_KINDS = {"existing", "manual", "proposed", "imported", "reference"}
ALLOWED_FACILITY_STATUSES = {"enabled", "disabled", "removed", "draft", "invalid"}
OPTIMIZER_RELEVANT_KINDS = {"existing", "manual", "proposed", "imported"}
CURRENT_NETWORK_SCENARIO_ID = "kadikoy-parcel-locker-current-network"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate a V1 scenario JSON against candidate and distance matrix artifacts."
    )
    parser.add_argument(
        "--scenario",
        default=str(DEFAULT_SCENARIO),
        help="Scenario JSON path.",
    )
    parser.add_argument(
        "--candidate-csv",
        default=str(DEFAULT_CANDIDATE_CSV),
        help="Candidate CSV path.",
    )
    parser.add_argument(
        "--distance-matrix",
        default=str(DEFAULT_DISTANCE_MATRIX),
        help="Distance matrix .npy path.",
    )
    parser.add_argument(
        "--expect-current-network-seed",
        action="store_true",
        help="Validate the scenario against existing_locker_count > 0 seed rows.",
    )
    return parser.parse_args()


def display_path(path: Path) -> str:
    return path.as_posix()


def add_missing_fields_errors(
    errors: list[str],
    container: dict[str, Any],
    required_fields: tuple[str, ...],
    label: str,
) -> None:
    for field in required_fields:
        if field not in container:
            errors.append(f"{label} is missing required field `{field}`.")


def is_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def is_numeric(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def parse_csv_int(value: str, field: str, row_number: int, errors: list[str]) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        errors.append(f"Candidate CSV row {row_number}: `{field}` must be an integer, got {value!r}.")
        return None


def parse_csv_float(value: str, field: str, row_number: int, errors: list[str]) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        errors.append(f"Candidate CSV row {row_number}: `{field}` must be a float, got {value!r}.")
        return None


def load_json(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.exists():
        errors.append(f"Scenario file does not exist: {display_path(path)}")
        return None

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.append(f"Scenario JSON is invalid: {exc}")
        return None

    if not isinstance(data, dict):
        errors.append("Scenario JSON root must be an object.")
        return None

    return data


def load_candidate_csv(path: Path, errors: list[str]) -> dict[str, Any]:
    result: dict[str, Any] = {
        "candidate_ids": set(),
        "candidate_count": 0,
        "seed_candidate_ids": set(),
        "seed_physical_count": 0,
    }

    if not path.exists():
        errors.append(f"Candidate CSV does not exist: {display_path(path)}")
        return result

    with path.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = reader.fieldnames or []
        for column in REQUIRED_CANDIDATE_COLUMNS:
            if column not in fieldnames:
                errors.append(f"Candidate CSV is missing required column `{column}`.")

        if any(column not in fieldnames for column in REQUIRED_CANDIDATE_COLUMNS):
            return result

        seen_candidate_ids: set[int] = set()
        for row_number, row in enumerate(reader, start=2):
            candidate_id = parse_csv_int(row["id"], "id", row_number, errors)
            parse_csv_float(row["lat"], "lat", row_number, errors)
            parse_csv_float(row["lon"], "lon", row_number, errors)
            existing_count = parse_csv_int(
                row["existing_locker_count"],
                "existing_locker_count",
                row_number,
                errors,
            )

            if candidate_id is None or existing_count is None:
                continue

            if candidate_id in seen_candidate_ids:
                errors.append(f"Candidate CSV row {row_number}: duplicate candidate id {candidate_id}.")
            seen_candidate_ids.add(candidate_id)

            if existing_count > 0:
                result["seed_candidate_ids"].add(candidate_id)
                result["seed_physical_count"] += existing_count

            result["candidate_count"] += 1

        result["candidate_ids"] = seen_candidate_ids

    return result


def validate_distance_matrix(
    path: Path,
    candidate_count: int,
    errors: list[str],
) -> tuple[int | None, tuple[int, ...] | None]:
    if not path.exists():
        errors.append(f"Distance matrix does not exist: {display_path(path)}")
        return None, None

    try:
        import numpy as np
    except ImportError:
        errors.append("NumPy is required to validate the .npy distance matrix, but it could not be imported.")
        return None, None

    try:
        matrix = np.load(path, mmap_mode="r")
    except Exception as exc:  # noqa: BLE001 - report any npy loading issue clearly.
        errors.append(f"Distance matrix could not be loaded: {exc}")
        return None, None

    shape = tuple(int(dimension) for dimension in matrix.shape)
    if matrix.ndim != 2:
        errors.append(f"Distance matrix must be 2-dimensional, got shape {shape}.")
        return None, shape
    if shape[0] != shape[1]:
        errors.append(f"Distance matrix must be square, got shape {shape}.")
        return None, shape
    if candidate_count and shape[0] != candidate_count:
        errors.append(
            "Distance matrix dimension must equal candidate CSV row count: "
            f"matrix={shape[0]}, candidates={candidate_count}."
        )

    return shape[0], shape


def validate_constraints(
    constraints: Any,
    candidate_ids: set[int],
    errors: list[str],
) -> None:
    if not isinstance(constraints, dict):
        errors.append("`constraints` must be an object.")
        return

    for field in ("lockedCandidateIds", "disabledCandidateIds"):
        if field not in constraints:
            errors.append(f"`constraints.{field}` is required.")
            continue
        values = constraints[field]
        if not isinstance(values, list):
            errors.append(f"`constraints.{field}` must be a list.")
            continue
        for index, value in enumerate(values):
            if not is_integer(value):
                errors.append(f"`constraints.{field}[{index}]` must be an integer candidate ID.")
            elif candidate_ids and value not in candidate_ids:
                errors.append(f"`constraints.{field}[{index}]` references unknown candidate ID {value}.")

    locked = constraints.get("lockedCandidateIds")
    disabled = constraints.get("disabledCandidateIds")
    if isinstance(locked, list) and isinstance(disabled, list):
        locked_set = {value for value in locked if is_integer(value)}
        disabled_set = {value for value in disabled if is_integer(value)}
        overlap = sorted(locked_set & disabled_set)
        if overlap:
            errors.append(f"Locked and disabled candidate IDs conflict: {overlap}.")


def validate_grid_and_settings(scenario: dict[str, Any], errors: list[str]) -> None:
    grid = scenario.get("grid")
    if not isinstance(grid, dict):
        errors.append("`grid` must be an object.")
    else:
        add_missing_fields_errors(errors, grid, REQUIRED_GRID_FIELDS, "`grid`")
        crs = grid.get("crs")
        if not isinstance(crs, dict):
            errors.append("`grid.crs` must be an object.")
        else:
            for field in ("display", "metric"):
                if field not in crs:
                    errors.append(f"`grid.crs.{field}` is required.")

    settings = scenario.get("settings")
    if not isinstance(settings, dict):
        errors.append("`settings` must be an object.")
        return

    add_missing_fields_errors(errors, settings, REQUIRED_SETTINGS_FIELDS, "`settings`")
    run_type = settings.get("runType")
    if run_type not in ALLOWED_RUN_TYPES:
        errors.append(f"`settings.runType` must be one of {sorted(ALLOWED_RUN_TYPES)}, got {run_type!r}.")
    if not isinstance(settings.get("includeExistingFacilities"), bool):
        errors.append("`settings.includeExistingFacilities` must be a boolean.")
    if not is_integer(settings.get("targetNewFacilityCount")):
        errors.append("`settings.targetNewFacilityCount` must be an integer.")
    target_total = settings.get("targetTotalFacilityCount")
    if target_total is not None and not is_integer(target_total):
        errors.append("`settings.targetTotalFacilityCount` must be an integer or null.")

    if scenario.get("scenarioId") == CURRENT_NETWORK_SCENARIO_ID:
        expected = {
            "runType": "current_network",
            "includeExistingFacilities": True,
            "targetNewFacilityCount": 0,
            "targetTotalFacilityCount": None,
        }
        for field, expected_value in expected.items():
            if settings.get(field) != expected_value:
                errors.append(
                    f"Current-network scenario expects `settings.{field}` = "
                    f"{expected_value!r}, got {settings.get(field)!r}."
                )


def validate_facilities(
    facilities: Any,
    candidate_ids: set[int],
    scenario_id: Any,
    errors: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "facility_count": 0,
        "physical_facility_count": 0,
        "facility_candidate_ids": [],
    }

    if not isinstance(facilities, list):
        errors.append("`facilities` must be a list.")
        return result

    result["facility_count"] = len(facilities)
    seen_facility_ids: set[str] = set()
    snapped_candidate_ids: list[int] = []

    for index, facility in enumerate(facilities):
        label = f"`facilities[{index}]`"
        if not isinstance(facility, dict):
            errors.append(f"{label} must be an object.")
            continue

        add_missing_fields_errors(errors, facility, REQUIRED_FACILITY_FIELDS, label)
        facility_id = facility.get("id")
        if not isinstance(facility_id, str) or not facility_id:
            errors.append(f"{label}.id must be a non-empty string.")
        elif facility_id in seen_facility_ids:
            errors.append(f"Duplicate facility id `{facility_id}`.")
        else:
            seen_facility_ids.add(facility_id)

        kind = facility.get("kind")
        status = facility.get("status")
        if kind not in ALLOWED_FACILITY_KINDS:
            errors.append(f"{label}.kind must be one of {sorted(ALLOWED_FACILITY_KINDS)}, got {kind!r}.")
        if status not in ALLOWED_FACILITY_STATUSES:
            errors.append(f"{label}.status must be one of {sorted(ALLOWED_FACILITY_STATUSES)}, got {status!r}.")

        coordinates = facility.get("coordinates")
        if not isinstance(coordinates, dict):
            errors.append(f"{label}.coordinates must be an object.")
        else:
            if not is_numeric(coordinates.get("lat")):
                errors.append(f"{label}.coordinates.lat must be numeric.")
            if not is_numeric(coordinates.get("lon")):
                errors.append(f"{label}.coordinates.lon must be numeric.")
            if "crs" not in coordinates:
                errors.append(f"{label}.coordinates.crs is required.")

        snap = facility.get("snap")
        candidate_id: int | None = None
        if not isinstance(snap, dict):
            errors.append(f"{label}.snap must be an object.")
        else:
            candidate_id_value = snap.get("candidateId")
            if not is_integer(candidate_id_value):
                errors.append(f"{label}.snap.candidateId must be an integer.")
            else:
                candidate_id = candidate_id_value
                snapped_candidate_ids.append(candidate_id)
                if candidate_ids and candidate_id not in candidate_ids:
                    errors.append(f"{label}.snap.candidateId references unknown candidate ID {candidate_id}.")

            if "snapStatus" not in snap:
                errors.append(f"{label}.snap.snapStatus is required.")
            if "snapMethod" not in snap:
                errors.append(f"{label}.snap.snapMethod is required.")

            if kind in OPTIMIZER_RELEVANT_KINDS and status == "enabled":
                if snap.get("snapStatus") != "snapped":
                    errors.append(f"{label} is enabled and optimizer-relevant, so snapStatus must be `snapped`.")

        metadata = facility.get("metadata")
        if not isinstance(metadata, dict):
            errors.append(f"{label}.metadata must be an object.")
        elif kind == "existing":
            physical_count = metadata.get("physicalCount")
            if not is_integer(physical_count) or physical_count <= 0:
                errors.append(f"{label}.metadata.physicalCount must be a positive integer for existing facilities.")
            else:
                result["physical_facility_count"] += physical_count
        elif kind in OPTIMIZER_RELEVANT_KINDS and status == "enabled" and candidate_id is None:
            warnings.append(f"{label} is optimizer-relevant but has no valid candidate ID yet.")

    result["facility_candidate_ids"] = snapped_candidate_ids

    if scenario_id == CURRENT_NETWORK_SCENARIO_ID:
        duplicate_candidate_ids = sorted(
            candidate_id
            for candidate_id in set(snapped_candidate_ids)
            if snapped_candidate_ids.count(candidate_id) > 1
        )
        if duplicate_candidate_ids:
            errors.append(
                "Current generated scenario must have unique snapped candidate IDs; "
                f"duplicates: {duplicate_candidate_ids}."
            )

    return result


def validate_current_network_seed(
    scenario: dict[str, Any],
    candidate_data: dict[str, Any],
    facility_data: dict[str, Any],
    errors: list[str],
) -> None:
    facilities = scenario.get("facilities")
    if not isinstance(facilities, list):
        return

    seed_candidate_ids = candidate_data["seed_candidate_ids"]
    facility_candidate_ids = set(facility_data["facility_candidate_ids"])

    if len(facilities) != len(seed_candidate_ids):
        errors.append(
            "Current-network seed facility count mismatch: "
            f"scenario={len(facilities)}, candidate CSV seed rows={len(seed_candidate_ids)}."
        )

    if facility_data["physical_facility_count"] != candidate_data["seed_physical_count"]:
        errors.append(
            "Current-network seed physical count mismatch: "
            f"scenario={facility_data['physical_facility_count']}, "
            f"candidate CSV={candidate_data['seed_physical_count']}."
        )

    if facility_candidate_ids != seed_candidate_ids:
        missing = sorted(seed_candidate_ids - facility_candidate_ids)
        extra = sorted(facility_candidate_ids - seed_candidate_ids)
        errors.append(
            "Current-network seed candidate IDs do not match existing_locker_count > 0 rows: "
            f"missing={missing}, extra={extra}."
        )

    for index, facility in enumerate(facilities):
        label = f"`facilities[{index}]`"
        if not isinstance(facility, dict):
            continue
        expected_fields = {
            "kind": "existing",
            "status": "enabled",
            "source": "seed_from_v0_data",
        }
        for field, expected_value in expected_fields.items():
            if facility.get(field) != expected_value:
                errors.append(f"{label}.{field} must be {expected_value!r} for current-network seed validation.")

        snap = facility.get("snap")
        if isinstance(snap, dict):
            if snap.get("snapMethod") != "seed_from_existing_locker_count":
                errors.append(f"{label}.snap.snapMethod must be 'seed_from_existing_locker_count'.")
            if snap.get("snapStatus") != "snapped":
                errors.append(f"{label}.snap.snapStatus must be 'snapped'.")


def validate_scenario(
    scenario: dict[str, Any],
    candidate_data: dict[str, Any],
    expect_current_network_seed: bool,
    errors: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    add_missing_fields_errors(errors, scenario, REQUIRED_TOP_LEVEL_FIELDS, "Scenario")
    if scenario.get("schemaVersion") != "v1":
        errors.append(f"`schemaVersion` must be 'v1', got {scenario.get('schemaVersion')!r}.")

    validate_grid_and_settings(scenario, errors)
    validate_constraints(scenario.get("constraints"), candidate_data["candidate_ids"], errors)
    facility_data = validate_facilities(
        scenario.get("facilities"),
        candidate_data["candidate_ids"],
        scenario.get("scenarioId"),
        errors,
        warnings,
    )

    if expect_current_network_seed:
        validate_current_network_seed(scenario, candidate_data, facility_data, errors)

    metadata = scenario.get("metadata")
    if isinstance(metadata, dict):
        effective_count = metadata.get("effectiveFacilityLocationCount")
        physical_count = metadata.get("physicalFacilityCount")
        if effective_count is not None and effective_count != facility_data["facility_count"]:
            warnings.append(
                "`metadata.effectiveFacilityLocationCount` does not match facility count: "
                f"metadata={effective_count}, actual={facility_data['facility_count']}."
            )
        if physical_count is not None and physical_count != facility_data["physical_facility_count"]:
            warnings.append(
                "`metadata.physicalFacilityCount` does not match facility metadata sum: "
                f"metadata={physical_count}, actual={facility_data['physical_facility_count']}."
            )

    return facility_data


def print_warnings(warnings: list[str]) -> None:
    if warnings:
        print("Warnings:")
        for warning in warnings:
            print(f"  - {warning}")


def main() -> int:
    args = parse_args()
    scenario_path = Path(args.scenario)
    candidate_csv_path = Path(args.candidate_csv)
    distance_matrix_path = Path(args.distance_matrix)

    errors: list[str] = []
    warnings: list[str] = []

    scenario = load_json(scenario_path, errors)
    candidate_data = load_candidate_csv(candidate_csv_path, errors)
    matrix_dimension, _ = validate_distance_matrix(
        distance_matrix_path,
        candidate_data["candidate_count"],
        errors,
    )

    facility_data = {
        "facility_count": 0,
        "physical_facility_count": 0,
        "facility_candidate_ids": [],
    }
    if scenario is not None:
        facility_data = validate_scenario(
            scenario,
            candidate_data,
            args.expect_current_network_seed,
            errors,
            warnings,
        )

    if errors:
        print("Scenario validation failed:")
        for error in errors:
            print(f"  - {error}")
        print_warnings(warnings)
        return 1

    print("Scenario validation passed:")
    print(f"  scenario: {display_path(scenario_path)}")
    print(f"  candidate csv: {display_path(candidate_csv_path)}")
    print(f"  distance matrix: {display_path(distance_matrix_path)}")
    print(f"  candidate count: {candidate_data['candidate_count']}")
    print(f"  facility count: {facility_data['facility_count']}")
    print(f"  physical facility count: {facility_data['physical_facility_count']}")
    if matrix_dimension is not None:
        print(f"  matrix dimension: {matrix_dimension}")
    print(f"  warnings: {len(warnings)}")
    print_warnings(warnings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
