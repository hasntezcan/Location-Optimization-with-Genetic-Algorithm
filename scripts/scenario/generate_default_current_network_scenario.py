"""Generate the default Kadikoy current-network scenario from V0 data.

Thin CLI wrapper — all generation logic lives in
``location_platform.scenario.seed``. This script only parses arguments,
calls into the package, writes the result, and prints a summary.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from location_platform.common.paths import display_path
from location_platform.scenario.seed import (
    build_current_network_scenario,
    load_existing_facility_seed_rows,
    write_scenario_json,
)

DEFAULT_CANDIDATE_CSV = Path("data/candidate_points.csv")
DEFAULT_OUTPUT = Path("data/scenarios/kadikoy_parcel_locker_current_network.json")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a V1 current-network scenario JSON from "
            "data/candidate_points.csv existing_locker_count values."
        )
    )
    parser.add_argument(
        "--candidate-csv",
        default=str(DEFAULT_CANDIDATE_CSV),
        help="Candidate CSV to read. Defaults to data/candidate_points.csv.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=(
            "Scenario JSON output path. Defaults to "
            "data/scenarios/kadikoy_parcel_locker_current_network.json."
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidate_csv = Path(args.candidate_csv)
    output_path = Path(args.output)

    facility_rows = load_existing_facility_seed_rows(candidate_csv)
    scenario = build_current_network_scenario(candidate_csv, facility_rows)
    write_scenario_json(output_path, scenario)

    print("Generated default current-network scenario:")
    print(f"  output: {display_path(output_path)}")
    print(f"  effective facility locations: {scenario['metadata']['effectiveFacilityLocationCount']}")
    print(f"  physical facilities: {scenario['metadata']['physicalFacilityCount']}")
    print(f"  source: {display_path(candidate_csv)}")


if __name__ == "__main__":
    main()
