"""Scenario schema/contract validation.

Owns full scenario shape validation (required fields, enums, facility/snap
shape, constraint conflicts) and the optional current-network V0 seed-match
check. This is the single implementation of scenario validation in
location_platform — no other module re-implements these checks.

Does not own:

- scenario JSON loading mechanics (``location_platform.scenario.loading``)
- candidate CSV loading mechanics (``location_platform.data.candidates``)
- distance matrix loading mechanics (``location_platform.data.matrix``)
- optimizer-input derivation (``location_platform.scenario.optimizer_inputs``, later batch)
- CLI parsing, printing, or exit codes (the thin wrapper script)

Every public function here returns errors/warnings as lists rather than
raising — a problem is reported, not thrown, matching the "collect
everything, then report" behavior scenario validation has always had.
``existing_locker_count`` is read only for the optional current-network
seed-match check; ``nearby_locker_count``/legacy ``locker_count`` are never
read or treated as facility presence.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from location_platform.common.parsing import is_integer, is_numeric, parse_float, parse_int
from location_platform.common.paths import display_path
from location_platform.data.candidates import load_candidate_rows
from location_platform.data.matrix import load_matrix, validate_matrix_shape
from location_platform.scenario.loading import load_scenario_json

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
REQUIRED_BENCHMARK_FIELDS = ("demandType", "coverageThresholdMeters")
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
# Only "ascending" is documented in docs/V1_DATA_CONTRACT.md's distance matrix
# alignment contract ("distance matrix rows/columns = candidate IDs sorted
# ascending") and docs/V1_SCENARIO_CONTRACT.md's example scenario.
ALLOWED_CANDIDATE_ID_ORDERS = {"ascending"}
ALLOWED_SNAP_STATUSES = {
    "snapped",
    "unsnapped",
    "ambiguous",
    "too_far",
    "invalid_geometry",
    "candidate_forbidden",
}
CURRENT_NETWORK_SCENARIO_ID = "kadikoy-parcel-locker-current-network"


def _add_missing_fields_errors(
    errors: list[str],
    container: dict[str, Any],
    required_fields: tuple[str, ...],
    label: str,
) -> None:
    for field in required_fields:
        if field not in container:
            errors.append(f"{label} is missing required field `{field}`.")


def _require_nonempty_string(container: dict[str, Any], field: str, label: str, errors: list[str]) -> None:
    """Append an error if `field` is present in `container` but not a non-empty string.

    Only validates type/content when the field exists — a missing field is
    already reported by ``_add_missing_fields_errors``, so this avoids
    double-reporting the same missing field two different ways.
    """
    if field not in container:
        return
    value = container[field]
    if not isinstance(value, str) or not value:
        errors.append(f"{label} must be a non-empty string, got {value!r}.")


def _load_candidate_data(csv_path: Path, errors: list[str]) -> dict[str, Any]:
    """Load candidate rows and track existing_locker_count seed info.

    Kept local to this module (not location_platform.data.candidates)
    because ``existing_locker_count``-based seed tracking is
    scenario-validation-specific business logic, not generic candidate
    loading.
    """
    result: dict[str, Any] = {
        "candidate_ids": set(),
        "candidate_count": 0,
        "seed_candidate_ids": set(),
        "seed_physical_count": 0,
    }

    try:
        rows = load_candidate_rows(csv_path, required_columns=REQUIRED_CANDIDATE_COLUMNS)
    except FileNotFoundError:
        errors.append(f"Candidate CSV does not exist: {display_path(csv_path)}")
        return result
    except ValueError as exc:
        errors.append(str(exc))
        return result

    seen_candidate_ids: set[int] = set()
    for row_number, row in enumerate(rows, start=2):
        try:
            candidate_id = parse_int(row["id"], f"Candidate CSV row {row_number} `id`")
        except ValueError as exc:
            errors.append(str(exc))
            continue

        for field in ("lat", "lon"):
            try:
                parse_float(row[field], f"Candidate CSV row {row_number} `{field}`")
            except ValueError as exc:
                errors.append(str(exc))

        try:
            existing_count = parse_int(
                row["existing_locker_count"], f"Candidate CSV row {row_number} `existing_locker_count`"
            )
        except ValueError as exc:
            errors.append(str(exc))
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


def _validate_distance_matrix(matrix_path: Path, candidate_count: int, errors: list[str]) -> int | None:
    try:
        matrix = load_matrix(matrix_path)
    except FileNotFoundError:
        errors.append(f"Distance matrix does not exist: {display_path(matrix_path)}")
        return None
    except Exception as exc:  # noqa: BLE001 - report any npy loading issue clearly.
        errors.append(f"Distance matrix could not be loaded: {exc}")
        return None

    try:
        dimension, _shape = validate_matrix_shape(matrix, candidate_count)
        return dimension
    except ValueError as exc:
        errors.append(str(exc))
        return None


def _validate_constraints(constraints: Any, candidate_ids: set[int], errors: list[str]) -> None:
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


def _validate_grid_and_settings(scenario: dict[str, Any], errors: list[str]) -> None:
    grid = scenario.get("grid")
    if not isinstance(grid, dict):
        errors.append("`grid` must be an object.")
    else:
        _add_missing_fields_errors(errors, grid, REQUIRED_GRID_FIELDS, "`grid`")
        _require_nonempty_string(grid, "candidateSource", "`grid.candidateSource`", errors)
        _require_nonempty_string(grid, "distanceMatrixSource", "`grid.distanceMatrixSource`", errors)
        if "candidateIdOrder" in grid:
            candidate_id_order = grid.get("candidateIdOrder")
            if candidate_id_order not in ALLOWED_CANDIDATE_ID_ORDERS:
                errors.append(
                    f"`grid.candidateIdOrder` must be one of {sorted(ALLOWED_CANDIDATE_ID_ORDERS)}, "
                    f"got {candidate_id_order!r}."
                )
        crs = grid.get("crs")
        if not isinstance(crs, dict):
            errors.append("`grid.crs` must be an object.")
        else:
            for field in ("display", "metric"):
                if field not in crs:
                    errors.append(f"`grid.crs.{field}` is required.")
                else:
                    _require_nonempty_string(crs, field, f"`grid.crs.{field}`", errors)

    settings = scenario.get("settings")
    if not isinstance(settings, dict):
        errors.append("`settings` must be an object.")
        return

    _add_missing_fields_errors(errors, settings, REQUIRED_SETTINGS_FIELDS, "`settings`")
    run_type = settings.get("runType")
    if run_type not in ALLOWED_RUN_TYPES:
        errors.append(f"`settings.runType` must be one of {sorted(ALLOWED_RUN_TYPES)}, got {run_type!r}.")
    if not isinstance(settings.get("includeExistingFacilities"), bool):
        errors.append("`settings.includeExistingFacilities` must be a boolean.")
    _require_nonempty_string(settings, "objectiveBundle", "`settings.objectiveBundle`", errors)

    target_new = settings.get("targetNewFacilityCount")
    target_new_valid: int | None = None
    if not is_integer(target_new):
        errors.append("`settings.targetNewFacilityCount` must be an integer.")
    elif target_new < 0:
        errors.append(f"`settings.targetNewFacilityCount` must not be negative, got {target_new}.")
    else:
        target_new_valid = target_new

    target_total = settings.get("targetTotalFacilityCount")
    target_total_valid: int | None = None
    if target_total is not None:
        if not is_integer(target_total):
            errors.append("`settings.targetTotalFacilityCount` must be an integer or null.")
        elif target_total < 0:
            errors.append(f"`settings.targetTotalFacilityCount` must not be negative, got {target_total}.")
        else:
            target_total_valid = target_total

    # Same active-field semantics as `optimizer_inputs._resolve_facility_count`:
    # a zero targetNewFacilityCount is a no-op, not an active request, so it
    # does not conflict with a set targetTotalFacilityCount.
    if target_new_valid is not None and target_new_valid > 0 and target_total_valid is not None:
        errors.append(
            "`settings.targetNewFacilityCount` and `settings.targetTotalFacilityCount` are "
            f"both active ({target_new_valid!r} and {target_total_valid!r}); only one "
            "facility-count field may be active at a time."
        )

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


def _validate_benchmark(scenario: dict[str, Any], errors: list[str]) -> None:
    benchmark = scenario.get("benchmark")
    if not isinstance(benchmark, dict):
        errors.append("`benchmark` must be an object.")
        return

    _add_missing_fields_errors(errors, benchmark, REQUIRED_BENCHMARK_FIELDS, "`benchmark`")
    _require_nonempty_string(benchmark, "demandType", "`benchmark.demandType`", errors)

    if "coverageThresholdMeters" in benchmark:
        threshold = benchmark["coverageThresholdMeters"]
        if not is_numeric(threshold):
            errors.append("`benchmark.coverageThresholdMeters` must be numeric.")
        elif threshold < 0:
            errors.append(f"`benchmark.coverageThresholdMeters` must not be negative, got {threshold}.")

    # compareAgainstScenarioId is optional (e.g. the seed-generated
    # current-network scenario omits it) — only validated when present.
    _require_nonempty_string(
        benchmark, "compareAgainstScenarioId", "`benchmark.compareAgainstScenarioId`", errors
    )


def _validate_facilities(
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

        _add_missing_fields_errors(errors, facility, REQUIRED_FACILITY_FIELDS, label)
        facility_id = facility.get("id")
        if not isinstance(facility_id, str) or not facility_id:
            errors.append(f"{label}.id must be a non-empty string.")
        elif facility_id in seen_facility_ids:
            errors.append(f"Duplicate facility id `{facility_id}`.")
        else:
            seen_facility_ids.add(facility_id)

        _require_nonempty_string(facility, "facilityType", f"{label}.facilityType", errors)
        _require_nonempty_string(facility, "label", f"{label}.label", errors)
        _require_nonempty_string(facility, "source", f"{label}.source", errors)

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
            else:
                _require_nonempty_string(coordinates, "crs", f"{label}.coordinates.crs", errors)

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
            else:
                snap_status = snap.get("snapStatus")
                if snap_status not in ALLOWED_SNAP_STATUSES:
                    errors.append(
                        f"{label}.snap.snapStatus must be one of {sorted(ALLOWED_SNAP_STATUSES)}, "
                        f"got {snap_status!r}."
                    )
            if "snapMethod" not in snap:
                errors.append(f"{label}.snap.snapMethod is required.")
            else:
                _require_nonempty_string(snap, "snapMethod", f"{label}.snap.snapMethod", errors)
            if "snapDistanceMeters" in snap:
                snap_distance = snap["snapDistanceMeters"]
                if not is_numeric(snap_distance):
                    errors.append(f"{label}.snap.snapDistanceMeters must be numeric.")
                elif snap_distance < 0:
                    errors.append(
                        f"{label}.snap.snapDistanceMeters must not be negative, got {snap_distance}."
                    )

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


def validate_current_network_seed_match(
    scenario: dict[str, Any],
    candidate_data: dict[str, Any],
    facility_data: dict[str, Any],
) -> list[str]:
    """Check the scenario's active existing facilities against `existing_locker_count > 0` seed rows.

    Returns a list of errors (empty if the scenario matches the V0 seed
    exactly). ``existing_locker_count`` is used here only for this optional
    compatibility check, never as a runtime source of truth.
    """
    errors: list[str] = []
    facilities = scenario.get("facilities")
    if not isinstance(facilities, list):
        return errors

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

    return errors


def validate_scenario(
    scenario: dict[str, Any],
    candidate_data: dict[str, Any],
    *,
    expect_current_network_seed: bool = False,
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Validate a parsed scenario dict's full shape/schema/contract.

    Returns ``(facility_data, errors, warnings)``. Never raises — every
    problem found becomes an entry in ``errors`` or ``warnings``.
    """
    errors: list[str] = []
    warnings: list[str] = []

    _add_missing_fields_errors(errors, scenario, REQUIRED_TOP_LEVEL_FIELDS, "Scenario")
    if scenario.get("schemaVersion") != "v1":
        errors.append(f"`schemaVersion` must be 'v1', got {scenario.get('schemaVersion')!r}.")
    for field in ("scenarioId", "name", "useCase"):
        _require_nonempty_string(scenario, field, f"`{field}`", errors)

    _validate_grid_and_settings(scenario, errors)
    _validate_constraints(scenario.get("constraints"), candidate_data["candidate_ids"], errors)
    _validate_benchmark(scenario, errors)
    facility_data = _validate_facilities(
        scenario.get("facilities"),
        candidate_data["candidate_ids"],
        scenario.get("scenarioId"),
        errors,
        warnings,
    )

    if expect_current_network_seed:
        errors.extend(validate_current_network_seed_match(scenario, candidate_data, facility_data))

    metadata = scenario.get("metadata")
    if "metadata" in scenario and not isinstance(metadata, dict):
        errors.append("`metadata` must be an object.")
    elif isinstance(metadata, dict):
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

    return facility_data, errors, warnings


def load_and_validate_scenario_file(
    scenario_path: Path,
    candidate_csv_path: Path,
    distance_matrix_path: Path,
    *,
    expect_current_network_seed: bool = False,
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Load a scenario/candidate CSV/distance matrix and validate them together.

    Returns ``(report, errors, warnings)``. ``report`` always contains
    ``candidateCount``, ``facilityCount``, ``physicalFacilityCount``, and
    ``matrixDimension`` (``None`` if the matrix could not be loaded/validated)
    so a CLI wrapper can print a summary regardless of pass/fail. Never
    raises — matches the "collect everything, then report" contract this
    validator has always had.
    """
    errors: list[str] = []
    warnings: list[str] = []

    scenario: dict[str, Any] | None
    try:
        scenario = load_scenario_json(scenario_path)
    except FileNotFoundError:
        errors.append(f"Scenario file does not exist: {display_path(scenario_path)}")
        scenario = None
    except json.JSONDecodeError as exc:
        errors.append(f"Scenario JSON is invalid: {exc}")
        scenario = None
    except ValueError as exc:
        errors.append(str(exc))
        scenario = None

    candidate_data = _load_candidate_data(candidate_csv_path, errors)
    matrix_dimension = _validate_distance_matrix(distance_matrix_path, candidate_data["candidate_count"], errors)

    facility_data = {"facility_count": 0, "physical_facility_count": 0, "facility_candidate_ids": []}
    if scenario is not None:
        facility_data, scenario_errors, scenario_warnings = validate_scenario(
            scenario, candidate_data, expect_current_network_seed=expect_current_network_seed
        )
        errors.extend(scenario_errors)
        warnings.extend(scenario_warnings)

    report = {
        "candidateCount": candidate_data["candidate_count"],
        "facilityCount": facility_data["facility_count"],
        "physicalFacilityCount": facility_data["physical_facility_count"],
        "matrixDimension": matrix_dimension,
    }
    return report, errors, warnings
