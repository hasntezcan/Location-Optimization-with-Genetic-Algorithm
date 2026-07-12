"""Derive Java SPEA2 optimizer inputs from a V1 scenario JSON.

Thin CLI wrapper — all derivation logic lives in
``location_platform.scenario.optimizer_inputs``. This script only parses
arguments, loads the scenario/candidate data, calls into the package, and
prints/writes the result.

Critical stdout contract: stdout contains machine-readable JSON only (one
``json.dumps(...)`` call, nothing else, ever). All diagnostics (warnings,
errors) go to stderr. ``parcel-locker-ui/src/lib/server/scenario-adapter.ts``
parses this script's entire stdout as JSON, so nothing may print to stdout
before or after the JSON document.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from location_platform.common.paths import display_path
from location_platform.data.candidates import load_candidate_ids
from location_platform.scenario.loading import load_scenario_json
from location_platform.scenario.optimizer_inputs import derive_optimizer_inputs

DEFAULT_SCENARIO = Path("data/scenarios/kadikoy_parcel_locker_current_network.json")
DEFAULT_CANDIDATE_CSV = Path("data/candidate_points.csv")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Translate a V1 scenario JSON into Java SPEA2 CLI inputs "
            "(--k / --fixedFacilityIds), using scenario.facilities[] as the "
            "source of truth for active existing facilities."
        )
    )
    parser.add_argument(
        "--scenario",
        default=str(DEFAULT_SCENARIO),
        help="Scenario JSON path.",
    )
    parser.add_argument(
        "--candidate-csv",
        default=str(DEFAULT_CANDIDATE_CSV),
        help="Candidate CSV path, used only to validate candidate ID existence.",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Optional path to also write the derived JSON output.",
    )
    parser.add_argument(
        "--force-existing-off",
        action="store_true",
        help=(
            "Override scenario.settings.includeExistingFacilities to false, "
            "for ad hoc greenfield testing of a scenario built for current-network "
            "or expansion use."
        ),
    )
    parser.add_argument(
        "--override-target-total-facility-count",
        type=int,
        default=None,
        help=(
            "Override settings.targetTotalFacilityCount for this derivation only "
            "(does not modify the scenario file). Takes precedence over both "
            "settings.targetTotalFacilityCount and settings.targetNewFacilityCount."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    scenario_path = Path(args.scenario)
    candidate_csv_path = Path(args.candidate_csv)

    try:
        scenario = load_scenario_json(scenario_path)
        candidate_ids = set(load_candidate_ids(candidate_csv_path))
    except (FileNotFoundError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    result, errors, warnings = derive_optimizer_inputs(
        scenario,
        candidate_ids,
        force_existing_off=args.force_existing_off,
        override_target_total_facility_count=args.override_target_total_facility_count,
    )
    result["scenarioPath"] = display_path(scenario_path)
    result["metadata"]["scenarioPath"] = display_path(scenario_path)
    if args.override_target_total_facility_count is not None:
        result["overrideTargetTotalFacilityCount"] = args.override_target_total_facility_count
        result["metadata"]["overrideTargetTotalFacilityCount"] = args.override_target_total_facility_count

    for warning in warnings:
        print(f"warning: {warning}", file=sys.stderr)

    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1

    output_json = json.dumps(result, indent=2, ensure_ascii=False)
    print(output_json)

    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_json + "\n", encoding="utf-8")
        print(f"Wrote: {display_path(output_path)}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
