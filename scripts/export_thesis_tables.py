"""
Export thesis tables in LaTeX and Markdown format.

Reads results from output/rq_analysis/metrics/rq_analysis_results.json
and produces formatted tables ready for insertion into the thesis document.

Usage:
    python scripts/export_thesis_tables.py
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_PATH = PROJECT_ROOT / "output" / "rq_analysis" / "metrics" / "rq_analysis_results.json"
TABLES_DIR = PROJECT_ROOT / "output" / "rq_analysis" / "tables"

K_VALUES = [3, 6, 10]


def load_results() -> dict:
    with open(RESULTS_PATH) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Table 1: Main comparison summary
# ---------------------------------------------------------------------------


def export_table1_summary(results: dict):
    """K × Metric summary table — main results."""

    lines_md = []
    lines_md.append("# Table 1: Performance Comparison Summary")
    lines_md.append("")
    lines_md.append("| K | Strategy | Mean Dist (m) | Median Dist (m) | Cov 500m (%) | Cov 1km (%) | Cov 2km (%) | CV | Variance |")
    lines_md.append("|---|----------|--------------|----------------|-------------|------------|------------|------|---------|")

    lines_tex = []
    lines_tex.append(r"\begin{table}[htbp]")
    lines_tex.append(r"\centering")
    lines_tex.append(r"\caption{Performance comparison between greedy baseline and optimized solutions.}")
    lines_tex.append(r"\label{tab:performance_summary}")
    lines_tex.append(r"\begin{tabular}{ccrrrrrrr}")
    lines_tex.append(r"\toprule")
    lines_tex.append(r"K & Strategy & Mean Dist & Median Dist & Cov 500m & Cov 1km & Cov 2km & CV & Variance \\")
    lines_tex.append(r"  &          & (m)       & (m)         & (\%)     & (\%)    & (\%)    &    &          \\")
    lines_tex.append(r"\midrule")

    for k in K_VALUES:
        # Greedy row
        g = results["baselines"].get(f"greedy_k{k}", {})
        lines_md.append(
            f"| {k} | Greedy | {g.get('mean_distance_m', 0):.1f} | "
            f"{g.get('median_distance_m', 0):.1f} | "
            f"{g.get('coverage_500m', 0):.2f} | "
            f"{g.get('coverage_1000m', 0):.2f} | "
            f"{g.get('coverage_2000m', 0):.2f} | "
            f"{g.get('cv_equity', 0):.4f} | "
            f"{g.get('variance_equity', 0):.0f} |"
        )
        lines_tex.append(
            f"{k} & Greedy & {g.get('mean_distance_m', 0):.1f} & "
            f"{g.get('median_distance_m', 0):.1f} & "
            f"{g.get('coverage_500m', 0):.2f} & "
            f"{g.get('coverage_1000m', 0):.2f} & "
            f"{g.get('coverage_2000m', 0):.2f} & "
            f"{g.get('cv_equity', 0):.4f} & "
            f"{g.get('variance_equity', 0):.0f} \\\\"
        )

        # Optimized row (mean ± std across seeds)
        comp = results.get("comparisons", {}).get(str(k), {})
        per_seed = comp.get("per_seed_metrics", [])
        if per_seed:
            def _fmt(key):
                vals = [m.get(key, 0) for m in per_seed]
                return f"{np.mean(vals):.1f} ± {np.std(vals):.1f}"

            def _fmt_pct(key):
                vals = [m.get(key, 0) for m in per_seed]
                return f"{np.mean(vals):.2f} ± {np.std(vals):.2f}"

            def _fmt_cv(key):
                vals = [m.get(key, 0) for m in per_seed]
                return f"{np.mean(vals):.4f} ± {np.std(vals):.4f}"

            lines_md.append(
                f"| {k} | **Optimized** | {_fmt('mean_distance_m')} | "
                f"{_fmt('median_distance_m')} | "
                f"{_fmt_pct('coverage_500m')} | "
                f"{_fmt_pct('coverage_1000m')} | "
                f"{_fmt_pct('coverage_2000m')} | "
                f"{_fmt_cv('cv_equity')} | "
                f"{_fmt('variance_equity')} |"
            )

            mean_vals = {key: np.mean([m.get(key, 0) for m in per_seed])
                         for key in ["mean_distance_m", "median_distance_m",
                                     "coverage_500m", "coverage_1000m", "coverage_2000m",
                                     "cv_equity", "variance_equity"]}
            lines_tex.append(
                f"{k} & Optimized & {mean_vals['mean_distance_m']:.1f} & "
                f"{mean_vals['median_distance_m']:.1f} & "
                f"{mean_vals['coverage_500m']:.2f} & "
                f"{mean_vals['coverage_1000m']:.2f} & "
                f"{mean_vals['coverage_2000m']:.2f} & "
                f"{mean_vals['cv_equity']:.4f} & "
                f"{mean_vals['variance_equity']:.0f} \\\\"
            )

        lines_tex.append(r"\midrule")

    lines_tex.append(r"\bottomrule")
    lines_tex.append(r"\end{tabular}")
    lines_tex.append(r"\end{table}")

    # Write
    (TABLES_DIR / "table1_summary.md").write_text("\n".join(lines_md), encoding="utf-8")
    (TABLES_DIR / "table1_summary.tex").write_text("\n".join(lines_tex), encoding="utf-8")
    print("  Table 1 saved (md + tex)")


# ---------------------------------------------------------------------------
# Table 2: Statistical test results
# ---------------------------------------------------------------------------


def export_table2_stats(results: dict):
    """Statistical test results table."""

    lines_md = []
    lines_md.append("# Table 2: Statistical Test Results")
    lines_md.append("")
    lines_md.append("| K | Test | Statistic | p-value | Significant (α=0.05) | Effect Size |")
    lines_md.append("|---|------|-----------|---------|---------------------|-------------|")

    lines_tex = []
    lines_tex.append(r"\begin{table}[htbp]")
    lines_tex.append(r"\centering")
    lines_tex.append(r"\caption{Statistical significance tests for accessibility and equity comparisons.}")
    lines_tex.append(r"\label{tab:statistical_tests}")
    lines_tex.append(r"\begin{tabular}{ccrrcr}")
    lines_tex.append(r"\toprule")
    lines_tex.append(r"K & Test & Statistic & $p$-value & Sig. ($\alpha$=0.05) & Effect Size \\")
    lines_tex.append(r"\midrule")

    for k in K_VALUES:
        comp = results.get("comparisons", {}).get(str(k), {})
        acc = comp.get("accessibility_test", {})
        eq = comp.get("equity_test", {})

        # VT1: Wilcoxon
        w_stat = acc.get("wilcoxon_stat", "N/A")
        w_p = acc.get("wilcoxon_p", "N/A")
        w_sig = "Yes" if acc.get("wilcoxon_significant_005") else "No"
        d = acc.get("cohens_d", "N/A")

        w_stat_str = f"{w_stat:.1f}" if isinstance(w_stat, float) else str(w_stat)
        w_p_str = f"{w_p:.2e}" if isinstance(w_p, float) else str(w_p)
        d_str = f"{d:.4f}" if isinstance(d, float) else str(d)

        lines_md.append(f"| {k} | Wilcoxon (VT1) | {w_stat_str} | {w_p_str} | {w_sig} | d={d_str} |")
        lines_tex.append(f"{k} & Wilcoxon & {w_stat_str} & {w_p_str} & {w_sig} & $d$={d_str} \\\\")

        # VT1: t-test
        t_stat = acc.get("ttest_stat", "N/A")
        t_p = acc.get("ttest_p_onesided", "N/A")
        t_sig = "Yes" if acc.get("ttest_significant_005") else "No"

        t_stat_str = f"{t_stat:.2f}" if isinstance(t_stat, float) else str(t_stat)
        t_p_str = f"{t_p:.2e}" if isinstance(t_p, float) else str(t_p)

        lines_md.append(f"| {k} | Paired t-test (VT1) | {t_stat_str} | {t_p_str} | {t_sig} | — |")
        lines_tex.append(f"{k} & Paired $t$ & {t_stat_str} & {t_p_str} & {t_sig} & --- \\\\")

        # VT3: Levene
        l_stat = eq.get("levene_stat", "N/A")
        l_p = eq.get("levene_p", "N/A")
        l_sig = "Yes" if eq.get("levene_significant_005") else "No"

        l_stat_str = f"{l_stat:.2f}" if isinstance(l_stat, float) else str(l_stat)
        l_p_str = f"{l_p:.4f}" if isinstance(l_p, float) else str(l_p)

        cv_red = eq.get("cv_reduction_pct", "N/A")
        cv_str = f"ΔCV={cv_red:.1f}%" if isinstance(cv_red, float) else str(cv_red)

        lines_md.append(f"| {k} | Levene (VT3) | {l_stat_str} | {l_p_str} | {l_sig} | {cv_str} |")
        lines_tex.append(f"{k} & Levene & {l_stat_str} & {l_p_str} & {l_sig} & $\\Delta$CV={cv_red:.1f}\\% \\\\")

        lines_tex.append(r"\midrule")

    lines_tex.append(r"\bottomrule")
    lines_tex.append(r"\end{tabular}")
    lines_tex.append(r"\end{table}")

    (TABLES_DIR / "table2_statistical_tests.md").write_text("\n".join(lines_md), encoding="utf-8")
    (TABLES_DIR / "table2_statistical_tests.tex").write_text("\n".join(lines_tex), encoding="utf-8")
    print("  Table 2 saved (md + tex)")


# ---------------------------------------------------------------------------
# Table 3: Marginal improvement
# ---------------------------------------------------------------------------


def export_table3_marginal(results: dict):
    """Marginal improvement table for VT2."""

    transitions = [("3 → 6", 3, 6), ("6 → 10", 6, 10)]

    lines_md = []
    lines_md.append("# Table 3: Marginal Improvement Analysis (VT2)")
    lines_md.append("")
    lines_md.append("| Transition | Strategy | ΔMean Dist (m) | ΔCov 500m (pp) | ΔCov 1km (pp) | ΔCV |")
    lines_md.append("|------------|----------|---------------|----------------|---------------|-----|")

    for label, k_from, k_to in transitions:
        for strategy in ["Greedy", "Optimized"]:
            if strategy == "Greedy":
                m_from = results["baselines"].get(f"greedy_k{k_from}", {})
                m_to = results["baselines"].get(f"greedy_k{k_to}", {})

                d_mean = m_from.get("mean_distance_m", 0) - m_to.get("mean_distance_m", 0)
                d_cov5 = m_to.get("coverage_500m", 0) - m_from.get("coverage_500m", 0)
                d_cov1k = m_to.get("coverage_1000m", 0) - m_from.get("coverage_1000m", 0)
                d_cv = m_from.get("cv_equity", 0) - m_to.get("cv_equity", 0)
            else:
                comp_from = results.get("comparisons", {}).get(str(k_from), {})
                comp_to = results.get("comparisons", {}).get(str(k_to), {})

                ps_from = comp_from.get("per_seed_metrics", [])
                ps_to = comp_to.get("per_seed_metrics", [])

                def _avg(ps, key):
                    return np.mean([m.get(key, 0) for m in ps]) if ps else 0

                d_mean = _avg(ps_from, "mean_distance_m") - _avg(ps_to, "mean_distance_m")
                d_cov5 = _avg(ps_to, "coverage_500m") - _avg(ps_from, "coverage_500m")
                d_cov1k = _avg(ps_to, "coverage_1000m") - _avg(ps_from, "coverage_1000m")
                d_cv = _avg(ps_from, "cv_equity") - _avg(ps_to, "cv_equity")

            lines_md.append(
                f"| {label} | {strategy} | {d_mean:+.1f} | {d_cov5:+.2f} | "
                f"{d_cov1k:+.2f} | {d_cv:+.4f} |"
            )

    (TABLES_DIR / "table3_marginal_improvement.md").write_text(
        "\n".join(lines_md), encoding="utf-8"
    )
    print("  Table 3 saved (md)")


# ---------------------------------------------------------------------------
# Table 4: Existing network reference
# ---------------------------------------------------------------------------


def export_table4_existing(results: dict):
    """Contextual reference: existing locker network coverage."""
    ex = results.get("baselines", {}).get("existing", {})

    lines_md = []
    lines_md.append("# Table 4: Existing Locker Network — Contextual Reference")
    lines_md.append("")
    lines_md.append("| Metric | Value |")
    lines_md.append("|--------|-------|")
    lines_md.append(f"| Number of locker points | {ex.get('n_locker_points', 'N/A')} |")
    lines_md.append(f"| Total locker count | {ex.get('total_locker_count', 'N/A')} |")
    lines_md.append(f"| Mean distance (m) | {ex.get('mean_distance_m', 0):.1f} |")
    lines_md.append(f"| Median distance (m) | {ex.get('median_distance_m', 0):.1f} |")
    lines_md.append(f"| Coverage 500m (%) | {ex.get('coverage_500m', 0):.2f} |")
    lines_md.append(f"| Coverage 1km (%) | {ex.get('coverage_1000m', 0):.2f} |")
    lines_md.append(f"| Coverage 2km (%) | {ex.get('coverage_2000m', 0):.2f} |")
    lines_md.append(f"| CV (equity) | {ex.get('cv_equity', 0):.4f} |")
    lines_md.append(f"| Variance | {ex.get('variance_equity', 0):.0f} |")
    lines_md.append("")
    lines_md.append("*Note: This is provided as a contextual reference describing the existing spatial")
    lines_md.append("distribution. It is not used as the main baseline for the K-location comparison.*")

    (TABLES_DIR / "table4_existing_reference.md").write_text(
        "\n".join(lines_md), encoding="utf-8"
    )
    print("  Table 4 saved (md)")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main():
    TABLES_DIR.mkdir(parents=True, exist_ok=True)

    if not RESULTS_PATH.exists():
        print(f"Results not found: {RESULTS_PATH}")
        print("Run 'python scripts/run_rq_experiments.py' first.")
        return

    print("Loading results...")
    results = load_results()

    print("\nExporting tables...")
    export_table1_summary(results)
    export_table2_stats(results)
    export_table3_marginal(results)
    export_table4_existing(results)

    print(f"\nAll tables saved to: {TABLES_DIR}")


if __name__ == "__main__":
    main()
