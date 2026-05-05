"""
Statistical tests for RQ validation.

VT1: Wilcoxon signed-rank + paired t-test on per-candidate nearest distances
VT3: Levene / Brown-Forsythe on neighborhood-level mean distances

Usage as library:
    from statistical_tests import test_accessibility, test_equity

Usage as CLI (self-test):
    python scripts/statistical_tests.py --self-test
"""

from __future__ import annotations

import argparse
from typing import Dict, List

import numpy as np
from scipy import stats


# ---------------------------------------------------------------------------
# VT1 — Accessibility comparison
# ---------------------------------------------------------------------------


def test_accessibility(
    baseline_nearest: np.ndarray,
    optimized_nearest: np.ndarray,
    demand: np.ndarray | None = None,
) -> dict:
    """Compare per-candidate nearest distances: baseline vs optimized.

    Primary test: Wilcoxon signed-rank (non-parametric, paired)
    Supplementary: Paired t-test (parametric)

    Parameters
    ----------
    baseline_nearest : (N,) nearest distances under baseline placement
    optimized_nearest : (N,) nearest distances under optimized placement
    demand : (N,) demand weights (optional, for effect size weighting)

    Returns
    -------
    dict with test statistics, p-values, and effect sizes
    """
    diff = baseline_nearest - optimized_nearest  # positive = improvement

    # Filter out zero differences for Wilcoxon
    nonzero_mask = diff != 0
    diff_nonzero = diff[nonzero_mask]

    results = {
        "n_candidates": len(diff),
        "n_improved": int((diff > 0).sum()),
        "n_worsened": int((diff < 0).sum()),
        "n_unchanged": int((diff == 0).sum()),
        "mean_improvement_m": float(diff.mean()),
        "median_improvement_m": float(np.median(diff)),
    }

    # Cohen's d (effect size)
    if diff.std() > 0:
        results["cohens_d"] = float(diff.mean() / diff.std())
    else:
        results["cohens_d"] = float("nan")

    # Wilcoxon signed-rank test (primary)
    if len(diff_nonzero) >= 10:
        try:
            stat, p_val = stats.wilcoxon(
                baseline_nearest[nonzero_mask],
                optimized_nearest[nonzero_mask],
                alternative="greater",  # H1: baseline > optimized (improvement)
            )
            results["wilcoxon_stat"] = float(stat)
            results["wilcoxon_p"] = float(p_val)
            results["wilcoxon_significant_005"] = p_val < 0.05
            results["wilcoxon_significant_001"] = p_val < 0.01
        except Exception as e:
            results["wilcoxon_stat"] = float("nan")
            results["wilcoxon_p"] = float("nan")
            results["wilcoxon_error"] = str(e)
    else:
        results["wilcoxon_stat"] = float("nan")
        results["wilcoxon_p"] = float("nan")
        results["wilcoxon_error"] = "Too few non-zero differences"

    # Paired t-test (supplementary)
    try:
        t_stat, t_p = stats.ttest_rel(baseline_nearest, optimized_nearest)
        # One-sided: baseline > optimized
        one_sided_p = t_p / 2 if t_stat > 0 else 1 - t_p / 2
        results["ttest_stat"] = float(t_stat)
        results["ttest_p_twosided"] = float(t_p)
        results["ttest_p_onesided"] = float(one_sided_p)
        results["ttest_significant_005"] = one_sided_p < 0.05
    except Exception as e:
        results["ttest_stat"] = float("nan")
        results["ttest_p_twosided"] = float("nan")
        results["ttest_error"] = str(e)

    return results


# ---------------------------------------------------------------------------
# VT3 — Equity comparison
# ---------------------------------------------------------------------------


def test_equity(
    baseline_mahalle_means: Dict[str, float],
    optimized_mahalle_means: Dict[str, float],
) -> dict:
    """Compare neighborhood-level equity: baseline vs optimized.

    Primary metrics: CV and variance comparison
    Supplementary: Levene's test / Brown-Forsythe

    Parameters
    ----------
    baseline_mahalle_means : {neighborhood -> weighted mean distance}
    optimized_mahalle_means : {neighborhood -> weighted mean distance}

    Returns
    -------
    dict with CV comparison, variance comparison, and test statistics
    """
    # Align neighborhoods
    common = sorted(
        set(baseline_mahalle_means.keys()) & set(optimized_mahalle_means.keys())
    )
    b_vals = np.array([baseline_mahalle_means[n] for n in common])
    o_vals = np.array([optimized_mahalle_means[n] for n in common])

    # Filter NaN
    valid = ~(np.isnan(b_vals) | np.isnan(o_vals))
    b_vals = b_vals[valid]
    o_vals = o_vals[valid]

    results = {
        "n_neighborhoods": len(b_vals),
    }

    if len(b_vals) < 2:
        results["error"] = "Too few neighborhoods for equity comparison"
        return results

    # CV comparison
    b_cv = float(b_vals.std(ddof=0) / b_vals.mean()) if b_vals.mean() != 0 else float("nan")
    o_cv = float(o_vals.std(ddof=0) / o_vals.mean()) if o_vals.mean() != 0 else float("nan")

    results["baseline_cv"] = b_cv
    results["optimized_cv"] = o_cv
    results["cv_reduction"] = b_cv - o_cv  # positive = improvement
    results["cv_reduction_pct"] = (
        float((b_cv - o_cv) / b_cv * 100) if b_cv != 0 else float("nan")
    )

    # Variance comparison
    b_var = float(b_vals.var(ddof=0))
    o_var = float(o_vals.var(ddof=0))
    results["baseline_variance"] = b_var
    results["optimized_variance"] = o_var
    results["variance_reduction"] = b_var - o_var
    results["variance_reduction_pct"] = (
        float((b_var - o_var) / b_var * 100) if b_var != 0 else float("nan")
    )

    # Levene's test (supplementary)
    try:
        lev_stat, lev_p = stats.levene(b_vals, o_vals, center="mean")
        results["levene_stat"] = float(lev_stat)
        results["levene_p"] = float(lev_p)
        results["levene_significant_005"] = lev_p < 0.05
    except Exception as e:
        results["levene_stat"] = float("nan")
        results["levene_p"] = float("nan")
        results["levene_error"] = str(e)

    # Brown-Forsythe (Levene with median)
    try:
        bf_stat, bf_p = stats.levene(b_vals, o_vals, center="median")
        results["brown_forsythe_stat"] = float(bf_stat)
        results["brown_forsythe_p"] = float(bf_p)
        results["brown_forsythe_significant_005"] = bf_p < 0.05
    except Exception as e:
        results["brown_forsythe_stat"] = float("nan")
        results["brown_forsythe_p"] = float("nan")
        results["brown_forsythe_error"] = str(e)

    return results


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------


def _self_test():
    """Run with synthetic data to verify functions work."""
    print("Running statistical tests self-test with synthetic data...\n")

    rng = np.random.RandomState(42)
    n = 500

    # Simulate: optimized is generally closer
    baseline_d = rng.exponential(2000, n) + 500
    optimized_d = baseline_d * rng.uniform(0.6, 1.0, n)

    acc_result = test_accessibility(baseline_d, optimized_d)
    print("=== VT1: Accessibility Test ===")
    print(f"  N candidates:     {acc_result['n_candidates']}")
    print(f"  N improved:       {acc_result['n_improved']}")
    print(f"  Mean improvement: {acc_result['mean_improvement_m']:.1f} m")
    print(f"  Cohen's d:        {acc_result['cohens_d']:.4f}")
    print(f"  Wilcoxon p:       {acc_result['wilcoxon_p']:.6f} "
          f"({'sig' if acc_result.get('wilcoxon_significant_005') else 'not sig'})")
    print(f"  t-test p (1-s):   {acc_result.get('ttest_p_onesided', 'N/A'):.6f}")

    # Equity test
    neighborhoods = [f"N{i}" for i in range(20)]
    b_mahalle = {n: rng.uniform(1000, 3000) for n in neighborhoods}
    o_mahalle = {n: v * rng.uniform(0.7, 0.95) for n, v in b_mahalle.items()}

    eq_result = test_equity(b_mahalle, o_mahalle)
    print(f"\n=== VT3: Equity Test ===")
    print(f"  N neighborhoods:     {eq_result['n_neighborhoods']}")
    print(f"  Baseline CV:         {eq_result['baseline_cv']:.6f}")
    print(f"  Optimized CV:        {eq_result['optimized_cv']:.6f}")
    print(f"  CV reduction:        {eq_result['cv_reduction_pct']:.2f}%")
    print(f"  Baseline variance:   {eq_result['baseline_variance']:.2f}")
    print(f"  Optimized variance:  {eq_result['optimized_variance']:.2f}")
    print(f"  Levene p:            {eq_result['levene_p']:.6f}")
    print(f"  Brown-Forsythe p:    {eq_result['brown_forsythe_p']:.6f}")

    print("\n✅ Self-test passed.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Statistical tests for RQ validation")
    parser.add_argument("--self-test", action="store_true", help="Run self-test")
    args = parser.parse_args()

    if args.self_test:
        _self_test()
    else:
        parser.print_help()
