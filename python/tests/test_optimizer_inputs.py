import json

from location_platform.scenario.optimizer_inputs import derive_optimizer_inputs


def build_scenario(
    run_type,
    *,
    existing_enabled=True,
    target_new=None,
    target_total=None,
    facilities=None,
    locked=None,
    disabled=None,
):
    return {
        "scenarioId": "test-scenario",
        "settings": {
            "runType": run_type,
            "includeExistingFacilities": existing_enabled,
            "targetNewFacilityCount": target_new,
            "targetTotalFacilityCount": target_total,
        },
        "facilities": facilities or [],
        "constraints": {
            "lockedCandidateIds": locked or [],
            "disabledCandidateIds": disabled or [],
        },
    }


def existing_facility(candidate_id, *, status="enabled", snap_status="snapped", physical_count=1, snap=True):
    facility = {
        "kind": "existing",
        "status": status,
        "metadata": {"physicalCount": physical_count},
    }
    if snap:
        facility["snap"] = {"candidateId": candidate_id, "snapStatus": snap_status}
    return facility


CANDIDATE_IDS = {1, 2, 3, 4, 5}


def test_current_network_short_circuit():
    scenario = build_scenario(
        "current_network",
        target_new=0,
        facilities=[existing_facility(1), existing_facility(2)],
    )
    result, errors, warnings = derive_optimizer_inputs(scenario, CANDIDATE_IDS)
    assert errors == []
    assert result["optimizerRunRequired"] is False
    assert result["resolvedK"] is None
    assert result["facilityCountMode"] == "current_network"
    assert result["javaCliArgs"] is None


def test_expansion_fixes_existing_and_uses_target_new_count():
    scenario = build_scenario(
        "expansion_optimization",
        target_new=5,
        facilities=[existing_facility(2), existing_facility(1)],  # unsorted input order
    )
    result, errors, warnings = derive_optimizer_inputs(scenario, CANDIDATE_IDS)
    assert errors == []
    assert result["optimizerRunRequired"] is True
    assert result["facilityCountMode"] == "targetNewFacilityCount"
    assert result["resolvedK"] == 5
    assert result["effectiveFixedCandidateIds"] == [1, 2]
    assert result["javaCliArgs"] == {"k": 5, "fixedFacilityIds": "1,2"}


def test_greenfield_no_fixed_existing_ids():
    scenario = build_scenario(
        "greenfield_optimization",
        existing_enabled=False,
        target_total=10,
        facilities=[existing_facility(1)],  # present but existing is OFF
    )
    result, errors, warnings = derive_optimizer_inputs(scenario, CANDIDATE_IDS)
    assert errors == []
    assert result["existingEnabled"] is False
    assert result["activeExistingCandidateIds"] == []
    assert result["effectiveFixedCandidateIds"] == []
    assert result["resolvedK"] == 10
    assert result["javaCliArgs"] == {"k": 10}


def test_force_existing_off_overrides_scenario_setting():
    scenario = build_scenario(
        "expansion_optimization",
        existing_enabled=True,
        target_new=3,
        facilities=[existing_facility(1)],
    )
    result, errors, warnings = derive_optimizer_inputs(scenario, CANDIDATE_IDS, force_existing_off=True)
    assert errors == []
    assert result["existingEnabled"] is False
    assert result["activeExistingCandidateIds"] == []
    assert any("force-existing-off" in warning for warning in warnings)


def test_target_total_override_subtracts_fixed_count():
    scenario = build_scenario(
        "current_network",
        target_new=0,
        facilities=[existing_facility(1), existing_facility(2)],
    )
    result, errors, warnings = derive_optimizer_inputs(
        scenario, CANDIDATE_IDS, override_target_total_facility_count=5
    )
    assert errors == []
    assert result["facilityCountMode"] == "targetTotalFacilityCountOverride"
    assert result["optimizerRunRequired"] is True
    # 5 total - 2 fixed existing = 3 new
    assert result["resolvedK"] == 3


def test_locked_candidates_included_in_fixed_ids():
    scenario = build_scenario("greenfield_optimization", existing_enabled=False, target_total=5, locked=[3])
    result, errors, warnings = derive_optimizer_inputs(scenario, CANDIDATE_IDS)
    assert errors == []
    assert result["lockedCandidateIds"] == [3]
    assert result["effectiveFixedCandidateIds"] == [3]
    assert result["resolvedK"] == 4  # 5 total - 1 locked


def test_locked_disabled_conflict_is_an_error():
    scenario = build_scenario(
        "greenfield_optimization", existing_enabled=False, target_total=5, locked=[3], disabled=[3]
    )
    result, errors, warnings = derive_optimizer_inputs(scenario, CANDIDATE_IDS)
    assert any("scenario conflict" in error for error in errors)


def test_disabled_candidate_ids_are_warnings_only_not_enforced():
    scenario = build_scenario("greenfield_optimization", existing_enabled=False, target_total=5, disabled=[4])
    result, errors, warnings = derive_optimizer_inputs(scenario, CANDIDATE_IDS)
    assert errors == []
    assert result["disabledCandidateIds"] == [4]
    assert any("NOT excluded from optimizer input" in warning for warning in warnings)


def test_unknown_candidate_id_in_constraints_is_an_error():
    scenario = build_scenario("greenfield_optimization", existing_enabled=False, target_total=5, locked=[999])
    result, errors, warnings = derive_optimizer_inputs(scenario, CANDIDATE_IDS)
    assert any("references unknown candidate ID 999" in error for error in errors)


def test_unknown_candidate_id_in_facility_snap_is_an_error():
    scenario = build_scenario(
        "expansion_optimization", target_new=2, facilities=[existing_facility(999)]
    )
    result, errors, warnings = derive_optimizer_inputs(scenario, CANDIDATE_IDS)
    assert any("references unknown candidate ID 999" in error for error in errors)


def test_disabled_removed_invalid_status_facilities_silently_excluded():
    scenario = build_scenario(
        "expansion_optimization",
        target_new=1,
        facilities=[
            existing_facility(1),
            existing_facility(2, status="disabled"),
            existing_facility(3, status="removed"),
            existing_facility(4, status="invalid"),
        ],
    )
    result, errors, warnings = derive_optimizer_inputs(scenario, CANDIDATE_IDS)
    assert errors == []
    assert result["activeExistingCandidateIds"] == [1]
    assert result["warnings"] == []


def test_unsnapped_facility_produces_warning_and_is_excluded():
    scenario = build_scenario(
        "expansion_optimization",
        target_new=1,
        facilities=[existing_facility(1, snap_status="unsnapped")],
    )
    result, errors, warnings = derive_optimizer_inputs(scenario, CANDIDATE_IDS)
    assert errors == []
    assert result["activeExistingCandidateIds"] == []
    assert any("not 'snapped'" in warning for warning in warnings)


def test_missing_snap_produces_warning_and_is_excluded():
    scenario = build_scenario(
        "expansion_optimization",
        target_new=1,
        facilities=[existing_facility(1, snap=False)],
    )
    result, errors, warnings = derive_optimizer_inputs(scenario, CANDIDATE_IDS)
    assert errors == []
    assert result["activeExistingCandidateIds"] == []
    assert any("no `snap` object" in warning for warning in warnings)


def test_physical_count_vs_effective_location_count():
    scenario = build_scenario(
        "expansion_optimization",
        target_new=1,
        facilities=[
            existing_facility(1, physical_count=1),
            existing_facility(1, physical_count=1),  # second physical facility, same candidate
        ],
    )
    result, errors, warnings = derive_optimizer_inputs(scenario, CANDIDATE_IDS)
    assert errors == []
    assert result["effectiveFacilityLocationCount"] == 1
    assert result["physicalFacilityCount"] == 2
    assert any("already an active existing facility" in warning for warning in warnings)


def test_deterministic_list_ordering_and_json_serialization():
    scenario = build_scenario(
        "greenfield_optimization",
        existing_enabled=False,
        target_total=10,
        locked=[5, 1, 3],
    )
    result, errors, warnings = derive_optimizer_inputs(scenario, CANDIDATE_IDS)
    assert errors == []
    assert result["lockedCandidateIds"] == [1, 3, 5]
    assert result["effectiveFixedCandidateIds"] == [1, 3, 5]

    serialized_once = json.dumps(result, indent=2, ensure_ascii=False)
    serialized_twice = json.dumps(result, indent=2, ensure_ascii=False)
    assert serialized_once == serialized_twice
    # Confirm the result round-trips through JSON with identical list contents.
    reparsed = json.loads(serialized_once)
    assert reparsed["lockedCandidateIds"] == [1, 3, 5]
