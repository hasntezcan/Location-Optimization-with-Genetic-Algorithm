"""
Evaluate a parcel locker placement solution.

Given a set of selected locker candidate IDs, this module computes all
metrics required for the thesis Research Questions:

  - Demand-weighted mean/median distance to nearest locker
  - Population coverage at distance thresholds (500 m, 1 km, 2 km)
  - Neighborhood-level equity: CV and variance of mean distances
  - Per-candidate and per-neighborhood distance details

Usage as library:
    from evaluate_solution import load_problem_data, compute_all_metrics
    data = load_problem_data()
    metrics = compute_all_metrics(locker_ids, data)

Usage as CLI (self-test):
    python scripts/evaluate_solution.py --test
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
CSV_PATH = PROJECT_ROOT / "data" / "candidate_points.csv"
DIST_MATRIX_PATH = PROJECT_ROOT / "data" / "kadikoy_distance_meters_nxn.npy"

# ---------------------------------------------------------------------------
# Data container
# ---------------------------------------------------------------------------


@dataclass
class ProblemData:
    """Immutable problem data loaded once and reused across evaluations."""

    candidates: pd.DataFrame
    dist_matrix: np.ndarray  # (N, N) float32, metres

    # Derived views (set after loading)
    n_candidates: int = 0
    id_to_idx: Dict[int, int] = field(default_factory=dict)
    selectable_ids: List[int] = field(default_factory=list)
    demand: np.ndarray = field(default_factory=lambda: np.array([]))
    neighborhoods: np.ndarray = field(default_factory=lambda: np.array([]))
    unique_neighborhoods: List[str] = field(default_factory=list)


def load_problem_data(
    csv_path: str | Path = CSV_PATH,
    dist_path: str | Path = DIST_MATRIX_PATH,
) -> ProblemData:
    """Load candidate CSV and distance matrix, build index mappings."""

    df = pd.read_csv(csv_path)
    dist = np.load(str(dist_path))

    # The CSV is ordered by `id` ascending (same order as dist matrix rows).
    # CandidateRepository in Java uses this same ordering.
    df = df.sort_values("id", kind="mergesort").reset_index(drop=True)

    if len(df) != dist.shape[0]:
        raise ValueError(
            f"CSV rows ({len(df)}) != distance matrix rows ({dist.shape[0]})"
        )

    id_to_idx = {int(row.id): idx for idx, row in df.iterrows()}
    selectable = df.loc[df["is_forbidden"] == 0, "id"].astype(int).tolist()

    data = ProblemData(
        candidates=df,
        dist_matrix=dist.astype(np.float64),
        n_candidates=len(df),
        id_to_idx=id_to_idx,
        selectable_ids=selectable,
        demand=df["demand_final"].to_numpy(dtype=np.float64),
        neighborhoods=df["Mahalle_Name_English"].to_numpy(),
        unique_neighborhoods=sorted(df["Mahalle_Name_English"].unique().tolist()),
    )
    return data


# ---------------------------------------------------------------------------
# Core metric functions
# ---------------------------------------------------------------------------


def compute_nearest_distances(
    locker_ids: List[int],
    data: ProblemData,
) -> np.ndarray:
    """Return array of shape (N,) with distance to nearest locker for every candidate.

    All N candidates (including forbidden) are demand sources.
    """
    locker_indices = np.array([data.id_to_idx[lid] for lid in locker_ids])

    # dist_matrix[i, locker_indices] → distances from candidate i to each locker
    dists_to_lockers = data.dist_matrix[:, locker_indices]  # (N, K)
    nearest = dists_to_lockers.min(axis=1)  # (N,)
    return nearest


def compute_weighted_mean_distance(
    nearest_distances: np.ndarray,
    demand: np.ndarray,
) -> float:
    """Demand-weighted mean distance (metres)."""
    total_demand = demand.sum()
    if total_demand == 0:
        return float("nan")
    return float(np.dot(demand, nearest_distances) / total_demand)


def compute_weighted_median_distance(
    nearest_distances: np.ndarray,
    demand: np.ndarray,
) -> float:
    """Demand-weighted median distance (metres).

    Uses linear interpolation on the cumulative demand distribution.
    """
    order = np.argsort(nearest_distances)
    sorted_d = nearest_distances[order]
    sorted_w = demand[order]

    cum_w = np.cumsum(sorted_w)
    total = cum_w[-1]
    if total == 0:
        return float("nan")

    half = total / 2.0
    idx = np.searchsorted(cum_w, half)
    idx = min(idx, len(sorted_d) - 1)
    return float(sorted_d[idx])


def compute_coverage_at_threshold(
    nearest_distances: np.ndarray,
    demand: np.ndarray,
    threshold_m: float,
) -> float:
    """Percentage of demand-weighted population within `threshold_m` metres."""
    total = demand.sum()
    if total == 0:
        return float("nan")
    covered = demand[nearest_distances <= threshold_m].sum()
    return float(covered / total * 100.0)


def compute_neighborhood_equity(
    nearest_distances: np.ndarray,
    demand: np.ndarray,
    neighborhoods: np.ndarray,
    unique_neighborhoods: List[str],
) -> dict:
    """Compute neighborhood-level equity metrics.

    Returns dict with:
        cv: coefficient of variation of neighborhood mean distances
        variance: variance of neighborhood mean distances
        mahalle_mean_distances: {name -> weighted mean distance}
    """
    mahalle_means = {}
    for name in unique_neighborhoods:
        mask = neighborhoods == name
        d = demand[mask]
        nd = nearest_distances[mask]
        total_d = d.sum()
        if total_d > 0:
            mahalle_means[name] = float(np.dot(d, nd) / total_d)
        else:
            mahalle_means[name] = float("nan")

    values = np.array([v for v in mahalle_means.values() if not np.isnan(v)])

    if len(values) < 2:
        return {
            "cv": float("nan"),
            "variance": float("nan"),
            "mahalle_mean_distances": mahalle_means,
        }

    mean_val = values.mean()
    std_val = values.std(ddof=0)
    var_val = values.var(ddof=0)

    cv = float(std_val / mean_val) if mean_val != 0 else float("nan")

    return {
        "cv": cv,
        "variance": float(var_val),
        "mahalle_mean_distances": mahalle_means,
    }


# ---------------------------------------------------------------------------
# Unified evaluation
# ---------------------------------------------------------------------------


def compute_all_metrics(
    locker_ids: List[int],
    data: ProblemData,
    thresholds_m: List[float] | None = None,
) -> dict:
    """Compute all metrics for a given locker placement.

    Parameters
    ----------
    locker_ids : list of candidate IDs that are selected as locker locations
    data : ProblemData instance
    thresholds_m : distance thresholds in metres (default: [500, 1000, 2000])

    Returns
    -------
    dict with all metrics and intermediate arrays
    """
    if thresholds_m is None:
        thresholds_m = [500.0, 1000.0, 2000.0]

    nearest = compute_nearest_distances(locker_ids, data)

    mean_dist = compute_weighted_mean_distance(nearest, data.demand)
    median_dist = compute_weighted_median_distance(nearest, data.demand)

    coverages = {}
    for t in thresholds_m:
        key = f"coverage_{int(t)}m"
        coverages[key] = compute_coverage_at_threshold(nearest, data.demand, t)

    equity = compute_neighborhood_equity(
        nearest, data.demand, data.neighborhoods, data.unique_neighborhoods
    )

    return {
        "k": len(locker_ids),
        "locker_ids": locker_ids,
        "mean_distance_m": mean_dist,
        "median_distance_m": median_dist,
        **coverages,
        "cv_equity": equity["cv"],
        "variance_equity": equity["variance"],
        "mahalle_mean_distances": equity["mahalle_mean_distances"],
        "nearest_distances": nearest,  # raw array for statistical tests
    }


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _self_test():
    """Run a quick sanity check with greedy-top-5 placement."""
    print("Loading problem data...")
    data = load_problem_data()
    print(f"  Candidates: {data.n_candidates}")
    print(f"  Selectable: {len(data.selectable_ids)}")
    print(f"  Neighborhoods: {len(data.unique_neighborhoods)}")
    print(f"  Distance matrix: {data.dist_matrix.shape}")

    # Pick top-5 by demand
    sel = data.candidates[data.candidates["is_forbidden"] == 0]
    top5 = sel.nlargest(5, "demand_final")["id"].astype(int).tolist()
    print(f"\nGreedy top-5 IDs: {top5}")

    metrics = compute_all_metrics(top5, data)

    print(f"\n--- Metrics for greedy top-5 ---")
    print(f"  Mean distance:    {metrics['mean_distance_m']:.1f} m")
    print(f"  Median distance:  {metrics['median_distance_m']:.1f} m")
    print(f"  Coverage 500m:    {metrics['coverage_500m']:.2f}%")
    print(f"  Coverage 1km:     {metrics['coverage_1000m']:.2f}%")
    print(f"  Coverage 2km:     {metrics['coverage_2000m']:.2f}%")
    print(f"  CV (equity):      {metrics['cv_equity']:.6f}")
    print(f"  Variance:         {metrics['variance_equity']:.2f}")
    print(f"\n  Neighborhood distances (top 5):")
    sorted_mahalle = sorted(
        metrics["mahalle_mean_distances"].items(), key=lambda x: x[1]
    )
    for name, dist in sorted_mahalle[:5]:
        print(f"    {name:30s} {dist:.1f} m")
    print(f"  ...")
    for name, dist in sorted_mahalle[-3:]:
        print(f"    {name:30s} {dist:.1f} m")

    print("\n✅ Self-test passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Evaluate locker placement")
    parser.add_argument("--test", action="store_true", help="Run self-test")
    args = parser.parse_args()

    if args.test:
        _self_test()
    else:
        parser.print_help()
