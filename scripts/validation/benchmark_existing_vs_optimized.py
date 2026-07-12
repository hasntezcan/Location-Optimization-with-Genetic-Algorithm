#!/usr/bin/env python3
"""Evaluate a scenario-based current network and optionally compare a GA archive.

Thin CLI wrapper — all benchmark computation and report-writing logic lives
in ``location_platform.benchmark`` (``current_network``, ``evaluation``, and
``reporting``). This script only parses arguments, resolves paths, calls into
the package, and prints a summary.

The benchmark follows the Java runtime's sorted-candidate matrix alignment
and FitnessCalculator formulas. Current-network placement comes from
``scenario.facilities[]``; V0 ``existing_locker_count`` is only used by the
optional seed-match validation.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from location_platform.benchmark.current_network import (
    DEFAULT_SCENARIO,
    load_and_validate_matrix,
    load_candidates,
    load_current_network_from_scenario,
    validate_v0_seed_match,
)
from location_platform.benchmark.evaluation import (
    DEFAULT_BETA,
    evaluate_archive,
    evaluate_facilities,
    load_metadata,
)
from location_platform.benchmark.reporting import write_outputs
from location_platform.common.parsing import finite_float
from location_platform.common.paths import display_relative_path, resolve_path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark current existing lockers against an optional optimized archive."
    )
    parser.add_argument("--candidate-csv", default="data/candidate_points.csv")
    parser.add_argument("--distance-matrix", default="data/kadikoy_distance_meters_nxn.npy")
    parser.add_argument("--scenario", default=DEFAULT_SCENARIO)
    parser.add_argument("--archive", default="output/final_archive.csv")
    parser.add_argument("--metadata", default="output/run_metadata.json")
    parser.add_argument("--output-dir", default="output/validation")
    parser.add_argument(
        "--validate-v0-seed-match",
        action="store_true",
        help="Verify scenario active existing facilities match existing_locker_count > 0 seed rows.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidate_path = resolve_path(args.candidate_csv, PROJECT_ROOT)
    matrix_path = resolve_path(args.distance_matrix, PROJECT_ROOT)
    scenario_path = resolve_path(args.scenario, PROJECT_ROOT)
    archive_path = resolve_path(args.archive, PROJECT_ROOT)
    metadata_path = resolve_path(args.metadata, PROJECT_ROOT)
    output_dir = resolve_path(args.output_dir, PROJECT_ROOT)

    candidates = load_candidates(candidate_path)
    matrix, alignment = load_and_validate_matrix(matrix_path, candidates, PROJECT_ROOT)
    existing_candidates, existing_ids, physical_count, scenario_metadata = (
        load_current_network_from_scenario(scenario_path, candidates, PROJECT_ROOT)
    )
    v0_seed_match = None
    if args.validate_v0_seed_match:
        v0_seed_match = validate_v0_seed_match(existing_ids, physical_count, candidates)

    metadata = load_metadata(metadata_path)
    beta = finite_float(metadata.get("beta", DEFAULT_BETA), "beta") if metadata else DEFAULT_BETA
    baseline_f1, baseline_f2 = evaluate_facilities(
        existing_ids, candidates, matrix, beta
    )
    archive = evaluate_archive(
        archive_path,
        metadata_path,
        candidates,
        matrix,
        beta,
        baseline_f1,
        baseline_f2,
        physical_count,
    )
    outputs = write_outputs(
        output_dir,
        existing_candidates,
        physical_count,
        baseline_f1,
        baseline_f2,
        beta,
        alignment,
        archive,
        candidate_path,
        matrix_path,
        archive_path,
        metadata_path,
        scenario_metadata,
        v0_seed_match,
        PROJECT_ROOT,
    )

    print(f"Scenario source: {scenario_metadata['scenarioPath']}")
    print(f"Scenario ID: {scenario_metadata['scenarioId']}")
    print(f"Physical existing lockers: {physical_count}")
    print(f"Effective existing candidate locations: {len(existing_candidates)}")
    print(f"Baseline F1: {baseline_f1:.12f}")
    print(f"Baseline F2: {baseline_f2:.12f}")
    if v0_seed_match:
        print("V0 seed match validation: passed")
    if archive.get("found"):
        print(
            f"Archive: {archive['archiveType']}, K={archive['archiveK']}, "
            f"solutions={archive['solutionCount']}"
        )
        print(
            "Valid greenfield physical-count comparison: "
            f"{archive['validGreenfieldPhysicalCountComparison']}"
        )
        if archive.get("warning"):
            print(f"Warning: {archive['warning']}")
    else:
        print(f"Warning: {archive['warning']}")
    for path in outputs:
        print(f"Wrote: {display_relative_path(path, PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
