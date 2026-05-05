"""
Generate baseline locker placements for RQ comparison.

Baselines:
  1. Greedy Demand — top-K feasible candidates by demand_final
  2. Random — average of multiple random K-selections
  3. Existing (contextual) — all locker_count > 0 locations

Usage:
    python scripts/generate_baselines.py
    python scripts/generate_baselines.py --validate
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import List

import numpy as np

from evaluate_solution import ProblemData, compute_all_metrics, load_problem_data

PROJECT_ROOT = Path(__file__).resolve().parent.parent
OUTPUT_DIR = PROJECT_ROOT / "output" / "rq_analysis" / "baselines"

K_VALUES = [3, 6, 10]
RANDOM_REPS = 30
RANDOM_SEED_BASE = 1000


# ---------------------------------------------------------------------------
# Baseline generators
# ---------------------------------------------------------------------------


def greedy_demand_baseline(data: ProblemData, k: int) -> List[int]:
    """Select top-K feasible candidates by demand_final (descending)."""
    sel = data.candidates[data.candidates["is_forbidden"] == 0].copy()
    top_k = sel.nlargest(k, "demand_final")["id"].astype(int).tolist()
    return top_k


def random_baseline(
    data: ProblemData, k: int, n_reps: int = RANDOM_REPS, seed_base: int = RANDOM_SEED_BASE
) -> dict:
    """Generate n_reps random K-placements and return averaged metrics.

    Returns a dict with mean metrics and the list of per-rep metrics.
    """
    rng = np.random.RandomState(seed_base)
    selectable = np.array(data.selectable_ids)

    all_metrics = []
    for _ in range(n_reps):
        chosen = rng.choice(selectable, size=k, replace=False).tolist()
        m = compute_all_metrics(chosen, data)
        all_metrics.append(m)

    # Average scalar metrics
    avg = {
        "k": k,
        "n_reps": n_reps,
        "mean_distance_m": np.mean([m["mean_distance_m"] for m in all_metrics]),
        "median_distance_m": np.mean([m["median_distance_m"] for m in all_metrics]),
        "coverage_500m": np.mean([m["coverage_500m"] for m in all_metrics]),
        "coverage_1000m": np.mean([m["coverage_1000m"] for m in all_metrics]),
        "coverage_2000m": np.mean([m["coverage_2000m"] for m in all_metrics]),
        "cv_equity": np.mean([m["cv_equity"] for m in all_metrics]),
        "variance_equity": np.mean([m["variance_equity"] for m in all_metrics]),
        "std_mean_distance": np.std([m["mean_distance_m"] for m in all_metrics]),
        "std_cv_equity": np.std([m["cv_equity"] for m in all_metrics]),
    }

    # Average nearest distances across reps (for statistical tests)
    avg["nearest_distances"] = np.mean(
        [m["nearest_distances"] for m in all_metrics], axis=0
    )

    return avg


def existing_locker_baseline(data: ProblemData) -> dict:
    """Report metrics for the existing locker network (contextual reference).

    Uses all candidates with locker_count > 0 as locker locations.
    """
    existing_ids = (
        data.candidates.loc[data.candidates["locker_count"] > 0, "id"]
        .astype(int)
        .tolist()
    )
    metrics = compute_all_metrics(existing_ids, data)
    metrics["label"] = "Existing network (contextual)"
    metrics["n_locker_points"] = len(existing_ids)
    metrics["total_locker_count"] = int(
        data.candidates.loc[data.candidates["locker_count"] > 0, "locker_count"].sum()
    )
    return metrics


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def generate_all_baselines(data: ProblemData) -> dict:
    """Generate all baselines for all K values."""
    results = {"greedy": {}, "random": {}, "existing": None}

    # Existing (contextual, K-independent)
    print("Computing existing locker coverage (contextual reference)...")
    results["existing"] = existing_locker_baseline(data)
    ex = results["existing"]
    print(f"  Existing: {ex['n_locker_points']} points, {ex['total_locker_count']} lockers")
    print(f"  Mean distance: {ex['mean_distance_m']:.1f} m")
    print(f"  Coverage 500m: {ex['coverage_500m']:.2f}%")
    print(f"  CV: {ex['cv_equity']:.6f}")

    for k in K_VALUES:
        print(f"\n--- K = {k} ---")

        # Greedy
        greedy_ids = greedy_demand_baseline(data, k)
        greedy_metrics = compute_all_metrics(greedy_ids, data)
        greedy_metrics["label"] = f"Greedy demand (K={k})"
        results["greedy"][k] = greedy_metrics
        print(f"  Greedy IDs: {greedy_ids}")
        print(f"  Mean dist: {greedy_metrics['mean_distance_m']:.1f} m | "
              f"Coverage 500m: {greedy_metrics['coverage_500m']:.2f}% | "
              f"CV: {greedy_metrics['cv_equity']:.6f}")

        # Random
        print(f"  Computing random baseline ({RANDOM_REPS} reps)...")
        random_metrics = random_baseline(data, k)
        random_metrics["label"] = f"Random (K={k}, {RANDOM_REPS} reps)"
        results["random"][k] = random_metrics
        print(f"  Random mean dist: {random_metrics['mean_distance_m']:.1f} m ± "
              f"{random_metrics['std_mean_distance']:.1f} | "
              f"Coverage 500m: {random_metrics['coverage_500m']:.2f}%")

    return results


def save_baselines(results: dict):
    """Save baseline results to JSON (without numpy arrays)."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def _clean(obj):
        """Remove numpy arrays for JSON serialization."""
        if isinstance(obj, dict):
            return {
                k: _clean(v) for k, v in obj.items()
                if not isinstance(v, np.ndarray)
            }
        if isinstance(obj, (np.integer,)):
            return int(obj)
        if isinstance(obj, (np.floating,)):
            return float(obj)
        if isinstance(obj, list):
            return [_clean(x) for x in obj]
        return obj

    out_path = OUTPUT_DIR / "baseline_results.json"
    with open(out_path, "w") as f:
        json.dump(_clean(results), f, indent=2, ensure_ascii=False)
    print(f"\nBaseline results saved to: {out_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate baseline placements")
    parser.add_argument("--validate", action="store_true", help="Run validation checks")
    args = parser.parse_args()

    data = load_problem_data()
    results = generate_all_baselines(data)
    save_baselines(results)

    if args.validate:
        print("\n--- Validation ---")
        for k in K_VALUES:
            gm = results["greedy"][k]
            rm = results["random"][k]
            # Greedy should be better than random on mean distance
            if gm["mean_distance_m"] > rm["mean_distance_m"]:
                print(f"  ⚠ K={k}: Greedy mean dist ({gm['mean_distance_m']:.0f}m) "
                      f"> random ({rm['mean_distance_m']:.0f}m) — unexpected but possible")
            else:
                print(f"  ✅ K={k}: Greedy ({gm['mean_distance_m']:.0f}m) "
                      f"<= random ({rm['mean_distance_m']:.0f}m)")
        print("Validation complete.")


if __name__ == "__main__":
    main()
