"""Derive Java SPEA2 optimizer inputs from an already-loaded V1 scenario.

This module makes ``scenario.facilities[]`` (not ``candidate_points.csv``
existing-locker columns) the runtime source of truth for which candidates
are fixed into an optimizer run, while still producing values compatible
with the existing, unmodified Java CLI: ``--k`` and ``--fixedFacilityIds``.

It intentionally never produces an ``--includeExistingLockers``-equivalent
flag: that flag makes Java re-derive existing facilities from
``existing_locker_count`` in the candidate CSV, which is exactly the V0
path this module replaces. Active existing facilities are resolved from
``scenario.facilities[]`` here and surfaced through
``effectiveFixedCandidateIds``/``javaCliArgs.fixedFacilityIds``.

``nearby_locker_count`` is never read. ``existing_locker_count`` is never
read; it remains a V0 seed/compatibility concept owned by
``location_platform.scenario.seed`` and the seed-match check in
``location_platform.scenario.validation``.

Does not own:

- scenario JSON loading (``location_platform.scenario.loading``)
- candidate CSV loading (``location_platform.data.candidates``)
- full scenario schema validation (``location_platform.scenario.validation``)
  — this module's checks are a narrower, purpose-built subset, not a
  substitute for full validation
- CLI parsing, printing, or exit codes (the thin wrapper script)

This module never raises — every problem found becomes an entry in the
returned ``errors``/``warnings`` lists, matching the current script's
non-raising ``derive()`` design exactly.
"""

from __future__ import annotations

from typing import Any

from location_platform.common.parsing import require_mapping

# Must match app.Main's MAX_NEW_FACILITIES / k validation (K must be 1..30).
MIN_K = 1
MAX_K = 30

OPTIMIZER_RELEVANT_EXISTING_KINDS = {"existing"}


def _require_mapping(value: Any, label: str, errors: list[str]) -> dict[str, Any]:
    """Error-collecting adapter around the raising `common.parsing.require_mapping`.

    Preserves this module's "never raise, always collect" contract while
    reusing the shared validation message text.
    """
    try:
        return require_mapping(value, label)
    except ValueError as exc:
        errors.append(str(exc))
        return {}


def _resolve_include_existing_facilities(settings: dict[str, Any], errors: list[str]) -> bool:
    """Validate `settings.includeExistingFacilities` before using it as a flag.

    A missing/null value is treated as the existing-off default with no
    error (this module does not own full schema validation). Any other
    non-boolean value (a string, number, list, object, ...) is malformed:
    it is reported as an error and resolved to a safe `False`, instead of
    the previous `bool(value)` truthiness coercion, which silently accepted
    any truthy value as "existing on".
    """
    value = settings.get("includeExistingFacilities")
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    errors.append(f"`settings.includeExistingFacilities` must be a boolean, got {value!r}.")
    return False


def _validate_optional_nonnegative_int(value: Any, label: str, errors: list[str]) -> int | None:
    """Validate an optional facility-count value before it is used in arithmetic/comparison.

    Returns the value unchanged when it is a real (non-bool) non-negative
    int, ``None`` when the raw value was already ``None`` (a legitimate
    "not set"), and ``None`` with an appended error for anything else —
    wrong type, a bool, or a negative count. Never raises, matching this
    module's "collect errors" contract.
    """
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        errors.append(f"`{label}` must be an integer, got {value!r}.")
        return None
    if value < 0:
        errors.append(f"`{label}` must not be negative, got {value}.")
        return None
    return value


def resolve_active_existing_candidate_ids(
    facilities: list[Any],
    candidate_ids: set[int],
    errors: list[str],
    warnings: list[str],
) -> tuple[list[int], int]:
    """Return (sorted unique active existing candidate IDs, physical facility count).

    Lenient by design: an enabled `existing` facility with missing/invalid
    snap data is skipped with a warning, not treated as fatal — a
    scenario-driven optimizer run should surface problems without
    necessarily aborting on one bad facility. (Contrast with
    ``location_platform.benchmark.current_network``'s strict resolver,
    kept intentionally separate.)
    """
    active_ids: list[int] = []
    physical_count = 0
    seen_candidate_ids: set[int] = set()

    for index, facility in enumerate(facilities):
        label = f"facilities[{index}]"
        if not isinstance(facility, dict):
            errors.append(f"{label} must be an object.")
            continue

        kind = facility.get("kind")
        if kind not in OPTIMIZER_RELEVANT_EXISTING_KINDS:
            continue
        if facility.get("status") != "enabled":
            continue

        snap = facility.get("snap")
        if not isinstance(snap, dict):
            warnings.append(f"{label} is an enabled existing facility but has no `snap` object; skipped.")
            continue
        if snap.get("snapStatus") != "snapped":
            warnings.append(
                f"{label} is an enabled existing facility but snapStatus is "
                f"{snap.get('snapStatus')!r}, not 'snapped'; skipped."
            )
            continue

        candidate_id = snap.get("candidateId")
        if not isinstance(candidate_id, int) or isinstance(candidate_id, bool):
            warnings.append(f"{label} has no valid snap.candidateId; skipped.")
            continue
        if candidate_ids and candidate_id not in candidate_ids:
            errors.append(f"{label}.snap.candidateId references unknown candidate ID {candidate_id}.")
            continue

        if candidate_id in seen_candidate_ids:
            warnings.append(
                f"{label} maps to candidate ID {candidate_id}, which is already an active "
                "existing facility from another entry; physical count still accumulates."
            )
        else:
            seen_candidate_ids.add(candidate_id)
            active_ids.append(candidate_id)

        metadata = facility.get("metadata")
        physical = metadata.get("physicalCount") if isinstance(metadata, dict) else None
        if isinstance(physical, int) and not isinstance(physical, bool) and physical > 0:
            physical_count += physical
        else:
            physical_count += 1
            warnings.append(f"{label} has no positive metadata.physicalCount; counted as 1.")

    return sorted(active_ids), physical_count


def _resolve_constraint_ids(
    constraints: dict[str, Any],
    field: str,
    candidate_ids: set[int],
    errors: list[str],
) -> list[int]:
    values = constraints.get(field, [])
    if not isinstance(values, list):
        errors.append(f"`constraints.{field}` must be a list.")
        return []

    resolved: list[int] = []
    for index, value in enumerate(values):
        if not isinstance(value, int) or isinstance(value, bool):
            errors.append(f"`constraints.{field}[{index}]` must be an integer candidate ID.")
            continue
        if candidate_ids and value not in candidate_ids:
            errors.append(f"`constraints.{field}[{index}]` references unknown candidate ID {value}.")
            continue
        resolved.append(value)

    return sorted(set(resolved))


def _resolve_facility_count(
    run_type: Any,
    settings: dict[str, Any],
    fixed_count: int,
    errors: list[str],
    warnings: list[str],
    override_target_total: int | None = None,
) -> tuple[str, bool, int | None]:
    """Return (facilityCountMode, optimizerRunRequired, resolvedK).

    ``override_target_total`` must already be validated by the caller (a
    real, non-negative, non-bool int, or ``None``) — this function does not
    re-validate it, since it is not a scenario field.
    """

    if override_target_total is not None:
        if run_type == "current_network":
            warnings.append(
                "runType is 'current_network' but --override-target-total-facility-count "
                f"={override_target_total} was provided; deriving an optimizer run anyway "
                "because an explicit override was requested."
            )
        resolved_k = override_target_total - fixed_count
        if resolved_k < MIN_K or resolved_k > MAX_K:
            errors.append(
                "Resolved k from --override-target-total-facility-count is out of Java's "
                f"supported range [{MIN_K}, {MAX_K}]: override={override_target_total}, "
                f"fixedCandidateCount={fixed_count}, resolvedK={resolved_k}."
            )
            return "targetTotalFacilityCountOverride", True, None
        return "targetTotalFacilityCountOverride", True, resolved_k

    target_new = _validate_optional_nonnegative_int(
        settings.get("targetNewFacilityCount"), "settings.targetNewFacilityCount", errors
    )
    target_total = _validate_optional_nonnegative_int(
        settings.get("targetTotalFacilityCount"), "settings.targetTotalFacilityCount", errors
    )
    if target_new is not None and target_new > 0 and target_total is not None:
        errors.append(
            "settings.targetNewFacilityCount and settings.targetTotalFacilityCount are "
            f"both active ({target_new!r} and {target_total!r}); only one facility-count "
            "field may be active at a time."
        )

    if run_type == "current_network":
        if target_new not in (0, None):
            warnings.append(
                "runType is 'current_network' but settings.targetNewFacilityCount is "
                f"{target_new!r}; no optimizer run will be derived regardless."
            )
        return "current_network", False, None

    if target_total is not None:
        if run_type == "expansion_optimization":
            warnings.append(
                "settings.targetTotalFacilityCount is set on an 'expansion_optimization' "
                "scenario; targetNewFacilityCount is normally used for expansion. "
                "Using targetTotalFacilityCount as requested."
            )
        resolved_k = target_total - fixed_count
        if resolved_k < MIN_K or resolved_k > MAX_K:
            errors.append(
                "Resolved k from targetTotalFacilityCount is out of Java's supported "
                f"range [{MIN_K}, {MAX_K}]: targetTotalFacilityCount={target_total}, "
                f"fixedCandidateCount={fixed_count}, resolvedK={resolved_k}."
            )
            return "targetTotalFacilityCount", True, None
        return "targetTotalFacilityCount", True, resolved_k

    if target_new is not None and target_new > 0:
        resolved_k = target_new
        if resolved_k < MIN_K or resolved_k > MAX_K:
            errors.append(
                "settings.targetNewFacilityCount is out of Java's supported range "
                f"[{MIN_K}, {MAX_K}]: {resolved_k}."
            )
            return "targetNewFacilityCount", True, None
        return "targetNewFacilityCount", True, resolved_k

    warnings.append(
        "Could not resolve a facility count: settings.targetNewFacilityCount and "
        "settings.targetTotalFacilityCount are both null/zero and runType is not "
        "'current_network'. No optimizer input derived for k."
    )
    return "unsupported", False, None


def _build_java_cli_args(
    resolved_k: int | None,
    effective_fixed_candidate_ids: list[int],
) -> dict[str, Any] | None:
    if resolved_k is None:
        return None
    args: dict[str, Any] = {"k": resolved_k}
    if effective_fixed_candidate_ids:
        args["fixedFacilityIds"] = ",".join(str(cid) for cid in effective_fixed_candidate_ids)
    return args


def derive_optimizer_inputs(
    scenario: dict[str, Any],
    candidate_ids: set[int],
    *,
    force_existing_off: bool = False,
    override_target_total_facility_count: int | None = None,
) -> tuple[dict[str, Any], list[str], list[str]]:
    """Derive Java-CLI-compatible optimizer inputs from a parsed scenario dict.

    Returns ``(result, errors, warnings)``. Never raises.
    """
    errors: list[str] = []
    warnings: list[str] = []

    for field in ("scenarioId", "settings", "facilities", "constraints"):
        if field not in scenario:
            errors.append(f"Scenario is missing required field `{field}`.")

    settings = _require_mapping(scenario.get("settings"), "`settings`", errors)
    constraints = _require_mapping(scenario.get("constraints"), "`constraints`", errors)
    facilities = scenario.get("facilities")
    if not isinstance(facilities, list):
        errors.append("`facilities` must be a list.")
        facilities = []

    run_type = settings.get("runType")
    existing_enabled = _resolve_include_existing_facilities(settings, errors)
    if force_existing_off and existing_enabled:
        warnings.append(
            "settings.includeExistingFacilities is true, but --force-existing-off "
            "overrides it to false for this derivation."
        )
    if force_existing_off:
        existing_enabled = False

    if existing_enabled:
        active_existing_ids, physical_count = resolve_active_existing_candidate_ids(
            facilities, candidate_ids, errors, warnings
        )
    else:
        active_existing_ids, physical_count = [], 0

    locked_ids = _resolve_constraint_ids(constraints, "lockedCandidateIds", candidate_ids, errors)
    disabled_ids = _resolve_constraint_ids(constraints, "disabledCandidateIds", candidate_ids, errors)

    if disabled_ids:
        warnings.append(
            "constraints.disabledCandidateIds is non-empty, but the current Java CLI has "
            "no flag to exclude candidates from the selectable pool. These IDs are reported "
            "for review only and are NOT excluded from optimizer input by this adapter."
        )

    effective_fixed_ids = sorted(set(active_existing_ids) | set(locked_ids))
    conflict = sorted(set(effective_fixed_ids) & set(disabled_ids))
    if conflict:
        errors.append(
            "Candidate IDs are both fixed (existing/locked) and disabled, which is a "
            f"scenario conflict: {conflict}."
        )

    override_target_total_facility_count = _validate_optional_nonnegative_int(
        override_target_total_facility_count,
        "--override-target-total-facility-count",
        errors,
    )

    facility_count_mode, optimizer_run_required, resolved_k = _resolve_facility_count(
        run_type,
        settings,
        len(effective_fixed_ids),
        errors,
        warnings,
        override_target_total_facility_count,
    )

    java_cli_args = (
        _build_java_cli_args(resolved_k, effective_fixed_ids) if optimizer_run_required else None
    )

    result = {
        "scenarioId": scenario.get("scenarioId"),
        "runType": run_type,
        "existingEnabled": existing_enabled,
        "facilityCountMode": facility_count_mode,
        "optimizerRunRequired": optimizer_run_required,
        "targetNewFacilityCount": settings.get("targetNewFacilityCount"),
        "targetTotalFacilityCount": settings.get("targetTotalFacilityCount"),
        "resolvedK": resolved_k,
        "activeExistingCandidateIds": active_existing_ids,
        "lockedCandidateIds": locked_ids,
        "disabledCandidateIds": disabled_ids,
        "effectiveFixedCandidateIds": effective_fixed_ids,
        "physicalFacilityCount": physical_count,
        "effectiveFacilityLocationCount": len(active_existing_ids),
        "javaCliArgs": java_cli_args,
        "dataSemantics": {
            "existingFacilitySource": "scenario.facilities[] (kind=existing, status=enabled, snap.snapStatus=snapped)",
            "nearbyLockerCountRole": "not read by this adapter",
            "existingLockerCountRole": "not read by this adapter; V0 seed/compatibility only, owned by generate_default_current_network_scenario.py and validate_scenario.py --expect-current-network-seed",
            "includeExistingLockersCliFlag": "intentionally not used; existing candidates are passed via --fixedFacilityIds instead so scenario.facilities[] remains the source of truth",
        },
        "metadata": {
            "scenarioId": scenario.get("scenarioId"),
            "existingOnOff": existing_enabled,
            "facilityCountMode": facility_count_mode,
            "targetNewFacilityCount": settings.get("targetNewFacilityCount"),
            "targetTotalFacilityCount": settings.get("targetTotalFacilityCount"),
            "activeExistingCandidateCount": len(active_existing_ids),
            "physicalFacilityCount": physical_count,
            "effectiveFacilityLocationCount": len(active_existing_ids),
            "lockedCandidateCount": len(locked_ids),
            "disabledCandidateCount": len(disabled_ids),
        },
    }

    result["warnings"] = list(warnings)

    return result, errors, warnings
