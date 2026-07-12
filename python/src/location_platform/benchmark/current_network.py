"""Current-network benchmark candidate loading, matrix alignment, and scenario resolution.

Sources current-network placement from ``scenario.facilities[]`` (never from
``existing_locker_count`` or ``nearby_locker_count`` as facility presence).
``existing_locker_count`` is read only by the optional V0 seed-match check.

This module's active-facility resolver (``load_current_network_from_scenario``)
is strict/raising by design and is kept intentionally separate from
``location_platform.scenario.optimizer_inputs``'s lenient resolver — a
benchmark computing baseline F1/F2 numbers must not silently proceed with a
wrong candidate set, whereas a scenario-driven optimizer run should surface
warnings and keep going. Do not merge these two resolvers.

Does not own:

- F1/F2 calculation, chromosome parsing, or archive evaluation
  (``location_platform.benchmark.evaluation``)
- output constants, path-display formatting, or report writing
  (``location_platform.benchmark.reporting``)
- optimizer facility selection (only ever evaluates a given candidate set,
  never chooses one)
- scenario schema validation beyond the narrow checks this benchmark needs
  (``location_platform.scenario.validation`` owns full schema validation)
- CLI parsing, printing, or exit codes (the thin wrapper script)

This module's functions are fail-fast/raising throughout, matching the
original script's style exactly — this is not converted to error-list style,
since that would be a behavior change beyond a code migration.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

from location_platform.common.parsing import finite_float, nonnegative_integer, require_mapping
from location_platform.common.paths import display_relative_path
from location_platform.data.candidates import load_candidate_rows
from location_platform.data.matrix import load_matrix, validate_matrix_shape
from location_platform.scenario.loading import load_scenario_json

DEFAULT_SCENARIO = "data/scenarios/kadikoy_parcel_locker_current_network.json"
REQUIRED_COLUMNS = (
    "id",
    "lat",
    "lon",
    "Mahalle_Name_Turkish",
    "demand_final",
    "existing_locker_count",
)


def _companion_id_artifact(matrix_path: Path) -> Path:
    """Derive the companion `*_candidate_ids_sorted.npy` path for a matrix file.

    Duplicates ``location_platform.data.matrix``'s private helper of the same
    shape (and, in turn, its public ``validate_matrix_candidate_id_alignment``)
    on purpose: that shared helper's success message formats the companion
    path with plain ``str(path)`` (OS-native, absolute), while the text
    produced here uses ``common.paths.display_relative_path`` (repo-relative,
    POSIX-style) because it is embedded verbatim into the committed JSON
    summary's ``matrixAlignment`` field and the Markdown report. Reusing the
    shared ``data.matrix`` helper would either change that committed text or
    require re-deriving the companion path locally anyway to reformat it —
    so this duplication stays, and only this comment documents why the two
    are not the same call.
    """
    suffix = "_distance_meters_nxn.npy"
    if matrix_path.name.endswith(suffix):
        return matrix_path.with_name(matrix_path.name[: -len(suffix)] + "_candidate_ids_sorted.npy")
    return matrix_path.with_name(matrix_path.stem + "_candidate_ids_sorted.npy")


def load_candidates(path: Path) -> list[dict[str, Any]]:
    """Load and validate the benchmark's richer candidate row shape.

    Uses ``location_platform.data.candidates.load_candidate_rows`` for the
    generic CSV-read/column-existence mechanics, then applies this
    benchmark's own business-specific parsing and validation (demand
    positivity, neighborhood non-blank, is_forbidden default) — these rules
    are benchmark-specific, not generic candidate-loading concerns, so they
    stay here rather than in ``data.candidates``.
    """
    if not path.is_file():
        raise FileNotFoundError(f"Candidate CSV not found: {path}")

    raw_rows = load_candidate_rows(path, required_columns=REQUIRED_COLUMNS)

    # Per-key whitespace stripping only; a leading BOM is already handled by
    # load_candidate_rows's utf-8-sig decoding, so no extra BOM-stripping is
    # needed here (the original script's redundant per-row BOM strip is not
    # reproduced).
    candidates = []
    for line_number, raw in enumerate(raw_rows, start=2):
        row = {(key or "").strip(): value for key, value in raw.items()}
        candidate_id = nonnegative_integer(row["id"], f"id at line {line_number}")
        existing_count = nonnegative_integer(
            row["existing_locker_count"], f"existing_locker_count at line {line_number}"
        )
        candidates.append(
            {
                "id": candidate_id,
                "lat": finite_float(row["lat"], f"lat at line {line_number}"),
                "lon": finite_float(row["lon"], f"lon at line {line_number}"),
                "neighborhood": row["Mahalle_Name_Turkish"].strip(),
                "demand": finite_float(row["demand_final"], f"demand_final at line {line_number}"),
                "existing_locker_count": existing_count,
                "is_forbidden": nonnegative_integer(
                    row.get("is_forbidden") or 0, f"is_forbidden at line {line_number}"
                ),
            }
        )

    if not candidates:
        raise ValueError("Candidate CSV contains no data rows.")
    ids = [row["id"] for row in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("Candidate IDs must be unique.")
    if any(not row["neighborhood"] for row in candidates):
        raise ValueError("Mahalle_Name_Turkish must not be blank.")
    if sum(row["demand"] for row in candidates) <= 0:
        raise ValueError("Total demand_final must be positive.")

    return sorted(candidates, key=lambda row: row["id"])


def load_and_validate_matrix(
    matrix_path: Path,
    candidates: list[dict[str, Any]],
    project_root: Path,
) -> tuple[np.ndarray, str]:
    """Load the distance matrix and validate shape + companion-ID alignment.

    Uses ``location_platform.data.matrix`` for the raw load and the
    2D/square/dimension checks; the companion-ID cross-check and alignment
    description stay local so the description text can use
    ``common.paths.display_relative_path`` (embedded directly in the committed report).
    """
    try:
        matrix = load_matrix(matrix_path)
    except FileNotFoundError as exc:
        raise FileNotFoundError(f"Distance matrix not found: {matrix_path}") from exc

    expected_shape = (len(candidates), len(candidates))
    if matrix.shape != expected_shape:
        raise ValueError(f"Distance matrix shape {matrix.shape} does not match {expected_shape}.")
    if not np.issubdtype(matrix.dtype, np.number):
        raise ValueError(f"Distance matrix must be numeric, found {matrix.dtype}.")
    # Reuse the shared shape/dimension check for parity with other modules
    # (redundant with the explicit checks above, which preserve the
    # original's exact error message text; validate_matrix_shape's own
    # messages would differ slightly and are not surfaced here).
    validate_matrix_shape(matrix, len(candidates))

    sorted_ids = np.asarray([row["id"] for row in candidates], dtype=np.int64)
    id_artifact = _companion_id_artifact(matrix_path)
    if id_artifact.is_file():
        artifact_ids = np.asarray(np.load(id_artifact), dtype=np.int64)
        if artifact_ids.shape != sorted_ids.shape or not np.array_equal(artifact_ids, sorted_ids):
            raise ValueError(
                "Candidate IDs do not match the matrix companion ID artifact: "
                f"{id_artifact}"
            )
        alignment = f"validated against {display_relative_path(id_artifact, project_root)}"
    else:
        alignment = "sorted by candidate ID ascending (companion ID artifact not found)"
    return matrix, alignment


def load_current_network_from_scenario(
    scenario_path: Path,
    candidates: list[dict[str, Any]],
    project_root: Path,
) -> tuple[list[dict[str, Any]], list[int], int, dict[str, Any]]:
    """Strictly resolve the active current-network existing facilities from a scenario.

    Raises on the first invalid facility rather than warning and continuing
    — intentionally distinct from
    ``location_platform.scenario.optimizer_inputs.resolve_active_existing_candidate_ids``,
    which is lenient by design. Do not merge these two resolvers.
    """
    scenario = load_scenario_json(scenario_path)
    for field in ("schemaVersion", "scenarioId", "grid", "settings", "facilities", "benchmark"):
        if field not in scenario:
            raise ValueError(f"Scenario is missing required field: {field}")
    if scenario["schemaVersion"] != "v1":
        raise ValueError(f"Unsupported scenario schemaVersion: {scenario['schemaVersion']!r}")

    settings = require_mapping(scenario["settings"], "scenario.settings")
    benchmark = require_mapping(scenario["benchmark"], "scenario.benchmark")
    facilities = scenario["facilities"]
    if not isinstance(facilities, list):
        raise ValueError("scenario.facilities must be a list.")

    candidate_by_id = {row["id"]: row for row in candidates}
    active_ids: list[int] = []
    physical_count_by_candidate_id: dict[int, int] = {}
    facility_ids_by_candidate_id: dict[int, list[str]] = {}

    for index, facility in enumerate(facilities):
        if not isinstance(facility, dict):
            raise ValueError(f"scenario.facilities[{index}] must be an object.")
        if facility.get("kind") != "existing":
            continue
        if facility.get("status") != "enabled":
            continue

        snap = require_mapping(facility.get("snap"), f"scenario.facilities[{index}].snap")
        if snap.get("snapStatus") != "snapped":
            continue
        candidate_id = snap.get("candidateId")
        if not isinstance(candidate_id, int) or isinstance(candidate_id, bool):
            raise ValueError(f"scenario.facilities[{index}].snap.candidateId must be an integer.")
        if candidate_id not in candidate_by_id:
            raise ValueError(
                f"scenario.facilities[{index}].snap.candidateId is absent from candidate CSV: {candidate_id}"
            )
        if candidate_id in physical_count_by_candidate_id:
            raise ValueError(
                "Current-network scenario has duplicate active existing facilities "
                f"for candidate ID {candidate_id}."
            )

        metadata = require_mapping(facility.get("metadata"), f"scenario.facilities[{index}].metadata")
        physical_count = nonnegative_integer(
            metadata.get("physicalCount"),
            f"scenario.facilities[{index}].metadata.physicalCount",
        )
        if physical_count <= 0:
            raise ValueError(
                f"scenario.facilities[{index}].metadata.physicalCount must be positive."
            )

        active_ids.append(candidate_id)
        physical_count_by_candidate_id[candidate_id] = physical_count
        facility_ids_by_candidate_id.setdefault(candidate_id, []).append(str(facility.get("id", "")))

    if not active_ids:
        raise ValueError("No active existing facilities found in scenario.facilities[].")

    existing_candidates = []
    for candidate_id in active_ids:
        row = dict(candidate_by_id[candidate_id])
        row["scenario_physical_count"] = physical_count_by_candidate_id[candidate_id]
        row["scenario_facility_ids"] = facility_ids_by_candidate_id[candidate_id]
        existing_candidates.append(row)

    scenario_metadata = {
        "currentNetworkSource": "scenario",
        "scenarioPath": display_relative_path(scenario_path, project_root),
        "scenarioId": scenario["scenarioId"],
        "activeExistingCandidateCount": len(active_ids),
        "physicalFacilityCount": sum(physical_count_by_candidate_id.values()),
        "demandType": benchmark.get("demandType"),
        "includeExistingFacilities": settings.get("includeExistingFacilities"),
        "runType": settings.get("runType"),
        "objectiveBundle": settings.get("objectiveBundle"),
        "coverageThresholdMeters": benchmark.get("coverageThresholdMeters"),
    }
    return existing_candidates, active_ids, scenario_metadata["physicalFacilityCount"], scenario_metadata


def validate_v0_seed_match(
    scenario_existing_ids: list[int],
    scenario_physical_count: int,
    candidates: list[dict[str, Any]],
) -> dict[str, Any]:
    seed_ids = [row["id"] for row in candidates if row["existing_locker_count"] > 0]
    seed_physical_count = sum(row["existing_locker_count"] for row in candidates)
    scenario_id_set = set(scenario_existing_ids)
    seed_id_set = set(seed_ids)
    missing = sorted(seed_id_set - scenario_id_set)
    extra = sorted(scenario_id_set - seed_id_set)
    matched = not missing and not extra and scenario_physical_count == seed_physical_count
    if not matched:
        raise ValueError(
            "Scenario current network does not match V0 existing_locker_count seed source: "
            f"missing={missing}, extra={extra}, "
            f"scenarioPhysicalCount={scenario_physical_count}, "
            f"v0PhysicalCount={seed_physical_count}."
        )
    return {
        "validated": True,
        "matched": True,
        "v0SeedCandidateCount": len(seed_ids),
        "v0SeedPhysicalFacilityCount": seed_physical_count,
    }
