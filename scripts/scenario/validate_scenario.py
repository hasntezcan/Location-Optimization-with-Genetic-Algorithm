"""Validate a V1 scenario against the current Kadikoy V0 grid artifacts.

Thin CLI wrapper — all validation logic lives in
``location_platform.scenario.validation``. This script only parses
arguments, calls into the package, and formats/prints the result. It does
not retain a duplicate implementation of scenario validation.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from location_platform.common.paths import display_path
from location_platform.scenario.validation import load_and_validate_scenario_file

DEFAULT_SCENARIO = Path("data/scenarios/kadikoy_parcel_locker_current_network.json")
DEFAULT_CANDIDATE_CSV = Path("data/candidate_points.csv")
DEFAULT_DISTANCE_MATRIX = Path("data/kadikoy_distance_meters_nxn.npy")


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

    report, errors, warnings = load_and_validate_scenario_file(
        scenario_path,
        candidate_csv_path,
        distance_matrix_path,
        expect_current_network_seed=args.expect_current_network_seed,
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
    print(f"  candidate count: {report['candidateCount']}")
    print(f"  facility count: {report['facilityCount']}")
    print(f"  physical facility count: {report['physicalFacilityCount']}")
    if report["matrixDimension"] is not None:
        print(f"  matrix dimension: {report['matrixDimension']}")
    print(f"  warnings: {len(warnings)}")
    print_warnings(warnings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
