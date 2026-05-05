"""
RQ Experiment Orchestrator.

Runs SPEA2 for each K × seed combination, extracts Pareto-optimal solutions,
evaluates them against baselines, runs statistical tests, and saves results.

Usage:
    python scripts/run_rq_experiments.py                     # full run
    python scripts/run_rq_experiments.py --k 3 --seeds 1     # quick test
    python scripts/run_rq_experiments.py --skip-ga            # re-analyze existing outputs
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import numpy as np

from evaluate_solution import ProblemData, compute_all_metrics, load_problem_data
from generate_baselines import greedy_demand_baseline, random_baseline, existing_locker_baseline
from statistical_tests import test_accessibility, test_equity

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "rq_analysis"

K_VALUES = [3, 6, 10]
SEEDS = [42, 123, 7, 256, 999]

# GA parameters (matching GAParameters.java defaults or tuned values)
POPULATION_SIZE = 200
MAX_GENERATIONS_MAP = {3: 150, 6: 250, 10: 400}  # FE-budget-aware
CROSSOVER_RATE = 0.9
MUTATION_RATE = 0.4
ARCHIVE_SIZE = 100


# ---------------------------------------------------------------------------
# Pareto front parsing
# ---------------------------------------------------------------------------


def parse_archive_csv(path: Path) -> List[dict]:
    """Parse a final_archive.csv file into a list of solution dicts."""
    solutions = []
    with open(path, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            chrom_str = row["chromosome"]
            ids = [int(x) for x in chrom_str.split("|")]
            solutions.append({
                "chromosome": ids,
                "f1": float(row["f1"]),
                "f2": float(row["f2"]),
                "raw_fitness": float(row["raw_fitness"]),
            })
    return solutions


def extract_nd_front(solutions: List[dict]) -> List[dict]:
    """Extract non-dominated solutions (raw_fitness == 0 or Pareto filter)."""
    # First try: use raw_fitness == 0 (SPEA2 non-dominated)
    nd = [s for s in solutions if s["raw_fitness"] == 0.0]
    if len(nd) == 0:
        # Fallback: manual Pareto filter
        nd = []
        for s in solutions:
            dominated = False
            for other in solutions:
                if (other["f1"] <= s["f1"] and other["f2"] <= s["f2"] and
                        (other["f1"] < s["f1"] or other["f2"] < s["f2"])):
                    dominated = True
                    break
            if not dominated:
                nd.append(s)
    return nd


def select_representative_solutions(nd_front: List[dict]) -> dict:
    """Select Best-f1, Best-f2, and Knee-point from the ND front.

    Knee-point: maximum perpendicular distance from the line connecting
    the extreme points of the front (in normalized objective space).
    """
    if len(nd_front) == 0:
        return {"best_f1": None, "best_f2": None, "knee": None}

    best_f1 = min(nd_front, key=lambda s: s["f1"])
    best_f2 = min(nd_front, key=lambda s: s["f2"])

    if len(nd_front) <= 2:
        knee = nd_front[0]  # fallback
    else:
        # Normalize f1, f2 to [0, 1] within the ND front
        f1s = np.array([s["f1"] for s in nd_front])
        f2s = np.array([s["f2"] for s in nd_front])

        f1_min, f1_max = f1s.min(), f1s.max()
        f2_min, f2_max = f2s.min(), f2s.max()

        f1_range = f1_max - f1_min if f1_max > f1_min else 1.0
        f2_range = f2_max - f2_min if f2_max > f2_min else 1.0

        norm_f1 = (f1s - f1_min) / f1_range
        norm_f2 = (f2s - f2_min) / f2_range

        # Line from best_f1 extreme (1, 0) to best_f2 extreme (0, 1) in norm space
        # Actually use the actual extremes of the normalized front
        p1 = np.array([norm_f1[np.argmin(f1s)], norm_f2[np.argmin(f1s)]])
        p2 = np.array([norm_f1[np.argmin(f2s)], norm_f2[np.argmin(f2s)]])

        line_vec = p2 - p1
        line_len = np.linalg.norm(line_vec)

        if line_len < 1e-10:
            knee = nd_front[0]
        else:
            max_dist = -1
            knee_idx = 0
            for i in range(len(nd_front)):
                point = np.array([norm_f1[i], norm_f2[i]])
                # Perpendicular distance from point to line p1-p2
                d = abs(np.cross(line_vec, p1 - point)) / line_len
                if d > max_dist:
                    max_dist = d
                    knee_idx = i
            knee = nd_front[knee_idx]

    return {"best_f1": best_f1, "best_f2": best_f2, "knee": knee}


# ---------------------------------------------------------------------------
# GA runner
# ---------------------------------------------------------------------------


def run_ga(k: int, seed: int, output_subdir: Path) -> Path:
    """Run Java SPEA2 via Maven and copy results to output_subdir."""
    output_subdir.mkdir(parents=True, exist_ok=True)

    max_gen = MAX_GENERATIONS_MAP.get(k, 200)

    cmd = [
        "mvn", "-q", "compile", "exec:java",
        f"-Dexec.args=--k {k} --populationSize {POPULATION_SIZE} "
        f"--maxGenerations {max_gen} --archiveSize {ARCHIVE_SIZE} "
        f"--crossoverRate {CROSSOVER_RATE} --mutationRate {MUTATION_RATE} "
        f"--randomSeed {seed}",
    ]

    print(f"    Running: K={k}, seed={seed}, maxGen={max_gen}, pop={POPULATION_SIZE}")
    start = time.time()

    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=600,  # 10 min timeout
    )

    elapsed = time.time() - start
    print(f"    Completed in {elapsed:.1f}s (exit={result.returncode})")

    if result.returncode != 0:
        err_path = output_subdir / "error.log"
        with open(err_path, "w") as f:
            f.write(result.stderr)
        print(f"    ⚠ GA failed! Error log: {err_path}")
        return output_subdir

    # Copy outputs
    for fname in ["final_archive.csv", "initial_archive.csv", "run_metadata.json"]:
        src = PROJECT_ROOT / "output" / fname
        if src.exists():
            import shutil
            shutil.copy2(src, output_subdir / fname)

    return output_subdir


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------


def run_experiments(
    k_values: List[int] = K_VALUES,
    seeds: List[int] = SEEDS,
    skip_ga: bool = False,
    data: ProblemData | None = None,
) -> dict:
    """Run all experiments and return aggregated results."""

    if data is None:
        print("Loading problem data...")
        data = load_problem_data()

    all_results = {
        "baselines": {},
        "experiments": {},
        "comparisons": {},
    }

    # 1. Generate baselines
    print("\n" + "=" * 60)
    print("PHASE 1: Generating baselines")
    print("=" * 60)

    existing = existing_locker_baseline(data)
    all_results["baselines"]["existing"] = {
        k: v for k, v in existing.items()
        if not isinstance(v, np.ndarray)
    }
    print(f"Existing network: {existing['n_locker_points']} points, "
          f"mean dist = {existing['mean_distance_m']:.0f}m")

    for k in k_values:
        greedy_ids = greedy_demand_baseline(data, k)
        greedy_m = compute_all_metrics(greedy_ids, data)
        all_results["baselines"][f"greedy_k{k}"] = {
            key: val for key, val in greedy_m.items()
            if not isinstance(val, np.ndarray)
        }
        # Store nearest distances separately for tests
        all_results["baselines"][f"greedy_k{k}_nearest"] = greedy_m["nearest_distances"]
        all_results["baselines"][f"greedy_k{k}_mahalle"] = greedy_m["mahalle_mean_distances"]

        rand_m = random_baseline(data, k)
        all_results["baselines"][f"random_k{k}"] = {
            key: val for key, val in rand_m.items()
            if not isinstance(val, np.ndarray)
        }

        print(f"K={k}: Greedy mean={greedy_m['mean_distance_m']:.0f}m, "
              f"Random mean={rand_m['mean_distance_m']:.0f}m")

    # 2. Run GA experiments
    print("\n" + "=" * 60)
    print("PHASE 2: Running SPEA2 optimization")
    print("=" * 60)

    experiments_dir = OUTPUT_DIR / "experiments"

    for k in k_values:
        all_results["experiments"][k] = {}
        print(f"\n--- K = {k} ---")

        for seed in seeds:
            exp_dir = experiments_dir / f"k{k}_seed{seed}"

            if not skip_ga:
                run_ga(k, seed, exp_dir)

            # Parse results
            archive_path = exp_dir / "final_archive.csv"
            if not archive_path.exists():
                print(f"    ⚠ No archive found for K={k}, seed={seed}")
                continue

            solutions = parse_archive_csv(archive_path)
            nd_front = extract_nd_front(solutions)
            reps = select_representative_solutions(nd_front)

            seed_result = {
                "nd_size": len(nd_front),
                "total_archive_size": len(solutions),
            }

            for label, sol in reps.items():
                if sol is None:
                    continue
                m = compute_all_metrics(sol["chromosome"], data)
                seed_result[label] = {
                    "chromosome": sol["chromosome"],
                    "f1": sol["f1"],
                    "f2": sol["f2"],
                    "mean_distance_m": m["mean_distance_m"],
                    "median_distance_m": m["median_distance_m"],
                    "coverage_500m": m["coverage_500m"],
                    "coverage_1000m": m["coverage_1000m"],
                    "coverage_2000m": m["coverage_2000m"],
                    "cv_equity": m["cv_equity"],
                    "variance_equity": m["variance_equity"],
                    "nearest_distances": m["nearest_distances"],
                    "mahalle_mean_distances": m["mahalle_mean_distances"],
                }

            all_results["experiments"][k][seed] = seed_result
            nd_sz = seed_result["nd_size"]
            if "knee" in seed_result:
                knee = seed_result["knee"]
                print(f"    Seed {seed}: ND={nd_sz}, "
                      f"knee mean={knee['mean_distance_m']:.0f}m, "
                      f"CV={knee['cv_equity']:.4f}")

    # 3. Statistical comparisons
    print("\n" + "=" * 60)
    print("PHASE 3: Statistical comparisons")
    print("=" * 60)

    for k in k_values:
        print(f"\n--- K = {k} ---")
        greedy_nearest = all_results["baselines"][f"greedy_k{k}_nearest"]
        greedy_mahalle = all_results["baselines"][f"greedy_k{k}_mahalle"]

        # Aggregate knee-point results across seeds
        knee_nearests = []
        knee_mahalles = []
        knee_metrics = []

        for seed in seeds:
            exp = all_results["experiments"].get(k, {}).get(seed, {})
            if "knee" not in exp:
                continue
            knee_nearests.append(exp["knee"]["nearest_distances"])
            knee_mahalles.append(exp["knee"]["mahalle_mean_distances"])
            knee_metrics.append({
                "seed": seed,
                "mean_distance_m": exp["knee"]["mean_distance_m"],
                "median_distance_m": exp["knee"]["median_distance_m"],
                "coverage_500m": exp["knee"]["coverage_500m"],
                "coverage_1000m": exp["knee"]["coverage_1000m"],
                "coverage_2000m": exp["knee"]["coverage_2000m"],
                "cv_equity": exp["knee"]["cv_equity"],
                "variance_equity": exp["knee"]["variance_equity"],
            })

        if len(knee_nearests) == 0:
            print(f"    ⚠ No knee solutions found for K={k}")
            continue

        # Use the BEST knee solution (lowest mean distance) for main comparison
        best_idx = np.argmin([m["mean_distance_m"] for m in knee_metrics])
        best_knee_nearest = knee_nearests[best_idx]
        best_knee_mahalle = knee_mahalles[best_idx]

        # VT1: Accessibility test
        acc_test = test_accessibility(greedy_nearest, best_knee_nearest, data.demand)
        print(f"  VT1 — Wilcoxon p={acc_test['wilcoxon_p']:.6f}, "
              f"mean improvement={acc_test['mean_improvement_m']:.1f}m, "
              f"Cohen's d={acc_test['cohens_d']:.4f}")

        # VT3: Equity test
        eq_test = test_equity(greedy_mahalle, best_knee_mahalle)
        print(f"  VT3 — Baseline CV={eq_test['baseline_cv']:.4f}, "
              f"Optimized CV={eq_test['optimized_cv']:.4f}, "
              f"Reduction={eq_test.get('cv_reduction_pct', 0):.1f}%")

        # Aggregate stats across seeds
        seed_summary = {
            "mean_distance": {
                "mean": np.mean([m["mean_distance_m"] for m in knee_metrics]),
                "std": np.std([m["mean_distance_m"] for m in knee_metrics]),
                "best": np.min([m["mean_distance_m"] for m in knee_metrics]),
            },
            "coverage_500m": {
                "mean": np.mean([m["coverage_500m"] for m in knee_metrics]),
                "std": np.std([m["coverage_500m"] for m in knee_metrics]),
                "best": np.max([m["coverage_500m"] for m in knee_metrics]),
            },
            "cv_equity": {
                "mean": np.mean([m["cv_equity"] for m in knee_metrics]),
                "std": np.std([m["cv_equity"] for m in knee_metrics]),
                "best": np.min([m["cv_equity"] for m in knee_metrics]),
            },
        }

        all_results["comparisons"][k] = {
            "accessibility_test": {
                key: val for key, val in acc_test.items()
                if not isinstance(val, np.ndarray)
            },
            "equity_test": eq_test,
            "seed_summary": _clean_for_json(seed_summary),
            "per_seed_metrics": knee_metrics,
        }

    # 4. Save results
    save_results(all_results)

    return all_results


def _clean_for_json(obj):
    """Recursively convert numpy types for JSON serialization."""
    if isinstance(obj, dict):
        return {k: _clean_for_json(v) for k, v in obj.items()
                if not isinstance(v, np.ndarray)}
    if isinstance(obj, list):
        return [_clean_for_json(x) for x in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


def save_results(results: dict):
    """Save analysis results to JSON and CSV."""
    metrics_dir = OUTPUT_DIR / "metrics"
    metrics_dir.mkdir(parents=True, exist_ok=True)

    # Clean numpy types
    clean = _clean_for_json(results)

    # Remove large arrays from the saved JSON
    def _remove_arrays(d):
        if isinstance(d, dict):
            return {
                k: _remove_arrays(v) for k, v in d.items()
                if not (isinstance(k, str) and k.endswith("_nearest")) and not isinstance(v, np.ndarray)
            }
        if isinstance(d, list):
            return [_remove_arrays(x) for x in d]
        return d

    json_path = metrics_dir / "rq_analysis_results.json"
    with open(json_path, "w") as f:
        json.dump(_remove_arrays(clean), f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {json_path}")

    # Summary CSV
    csv_path = metrics_dir / "comparison_summary.csv"
    rows = []
    for k in [3, 6, 10]:
        comp = results.get("comparisons", {}).get(k, {})
        baseline_key = f"greedy_k{k}"
        baseline = results.get("baselines", {}).get(baseline_key, {})

        seed_summary = comp.get("seed_summary", {})
        acc = comp.get("accessibility_test", {})
        eq = comp.get("equity_test", {})

        rows.append({
            "K": k,
            "baseline_mean_dist_m": baseline.get("mean_distance_m", ""),
            "optimized_mean_dist_m": seed_summary.get("mean_distance", {}).get("mean", ""),
            "optimized_std_dist_m": seed_summary.get("mean_distance", {}).get("std", ""),
            "baseline_coverage_500m": baseline.get("coverage_500m", ""),
            "optimized_coverage_500m": seed_summary.get("coverage_500m", {}).get("mean", ""),
            "baseline_cv": eq.get("baseline_cv", ""),
            "optimized_cv": eq.get("optimized_cv", ""),
            "cv_reduction_pct": eq.get("cv_reduction_pct", ""),
            "wilcoxon_p": acc.get("wilcoxon_p", ""),
            "cohens_d": acc.get("cohens_d", ""),
        })

    if rows:
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)
        print(f"Summary CSV: {csv_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(description="Run RQ experiments")
    parser.add_argument("--k", type=int, nargs="+", default=K_VALUES,
                        help="K values to test (default: 3 6 10)")
    parser.add_argument("--seeds", type=int, default=len(SEEDS),
                        help="Number of seeds to use (default: 5)")
    parser.add_argument("--skip-ga", action="store_true",
                        help="Skip GA runs, re-analyze existing outputs")
    args = parser.parse_args()

    seeds = SEEDS[:args.seeds]

    print(f"K values: {args.k}")
    print(f"Seeds: {seeds}")
    print(f"Skip GA: {args.skip_ga}")

    run_experiments(
        k_values=args.k,
        seeds=seeds,
        skip_ga=args.skip_ga,
    )


if __name__ == "__main__":
    main()
