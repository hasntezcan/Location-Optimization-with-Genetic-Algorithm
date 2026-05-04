# Parameter Analysis Guide V2 (`analyse_guide.md`)

## Overview

This document describes the **academically rigorous** hyperparameter grid search framework
(V2) for the Kadıköy Parcel Locker SPEA2 optimization project.

The V2 analyzer addresses four critical methodological flaws found in V1:

1. **Unfair budgeting**: Configurations were not receiving comparable computational effort.
2. **Missing demand parameter**: The lambda (λ) POI influence weight was not tested.
3. **Per-run HV normalization**: Each run was scaled to its own bounds, making cross-run
   HV comparison meaningless.
4. **Incomplete metrics**: Output lacked key quality indicators for thorough analysis.

---

## 1. Design Principles

### 1.1 RULE 1 — Fair Function Evaluation (FE) Budgeting

Comparing a run with 5,000 evaluations to one with 50,000 evaluations is methodologically
unsound. All configurations within the same K group receive the **same FE budget**.

**Formula:**
```
FunctionEvals = populationSize × (maxGenerations + 1)
maxGenerations = (TARGET_FE / populationSize) - 1
```

**K-Dependent Budgets** (based on empirical convergence observations):

| K  | TARGET_FE | Pop=50 → Gen | Pop=100 → Gen | Pop=200 → Gen | Rationale |
|:--:|:---------:|:------------:|:-------------:|:-------------:|:----------|
| 3  | 30,000    | 599          | 299           | 149           | Small search space; 300 gen sufficient |
| 6  | 50,000    | 999          | 499           | 249           | Medium space; 500 gen needed for convergence |
| 10 | 80,000    | 1,599        | 799           | 399           | Large space; 800+ gen required |

### 1.2 RULE 2 — Lambda (λ) Parameter in Grid

The lambda parameter controls the influence of POI score on demand:
```
demand = population × (1 + λ × poiScore)
```

This is computed **dynamically in Java** via the `FitnessCalculator(distanceMatrix, repository, beta, lambda)`
constructor, without needing to re-run the Python preprocessing.

**Grid values:** `λ ∈ {0.4, 0.5, 0.6}`

### 1.3 RULE 3 — Calibration-Phase Fixed HV Bounds (CRITICAL)

Per-run HV normalization (V1 approach) is fundamentally flawed because each run
normalizes to its own min/max, making HV values incomparable.

**The Calibration Phase:**

For each (K, λ) pair, **before** the grid search begins:
1. Run 5 SPEA2 runs with standard parameters (pop=100, standard crossover/mutation rates).
2. Collect all 500 final archive individuals from these calibration runs.
3. Compute global min/max for f1 and f2 across the entire union.
4. Apply a 2% margin to these bounds.
5. **Lock these bounds** for ALL subsequent grid search runs with this (K, λ).

This ensures every run in the same (K, λ) group is normalized to exactly the same
coordinate system, making HV values directly comparable.

### 1.4 RULE 4 — Rich Output Metrics

Output CSV columns:
```
K, Lambda, PopSize, ArchiveSize, MaxGen, MutRate, CrossRate,
FunctionEvals, Runtime_ms, ND_Count, Best_f1, Best_f2, Mean_f1, Mean_f2, Final_HV
```

Primary comparison metric: **Final_HV** (computed using locked calibration bounds).

---

## 2. Experimental Grid

| Parameter | Values | Count |
|:----------|:-------|:-----:|
| **K** (locker count) | 3, 6, 10 | 3 |
| **Lambda** (POI weight) | 0.4, 0.5, 0.6 | 3 |
| **Population Size** | 50, 100, 200 | 3 |
| **Mutation Rate** | 0.05, 0.10, 0.20, 0.30, 0.40 | 5 |
| **Crossover Rate** | 0.70, 0.90 | 2 |
| **Seeds** | 42, 123, 7 | 3 |

**Archive Size** = Population Size (1:1 ratio, standard SPEA2).

**Calibration runs:** 3 K × 3 Lambda × 5 runs = **45 runs**  
**Grid search runs:** 3 × 3 × 3 × 5 × 2 × 3 = **810 runs**  
**Grand total:** **855 SPEA2 executions**

---

## 3. How to Run

```powershell
# Full grid search (recommended: run overnight)
mvn compile exec:java -Panalyze
```

**Estimated runtime:** ~3-5 hours depending on CPU.

### 3.1 Output
- `output/parameter_analysis_results.csv` — Full results with 15 columns.

---

## 4. Interpreting Results

### Key Metrics

1. **Final_HV** — The hypervolume computed with locked calibration bounds. This is the
   **primary** metric for comparing configurations. Higher is better.
2. **ND_Count** — Number of non-dominated solutions in the final archive. Low counts
   suggest premature convergence.
3. **Best_f1 / Best_f2** — Extreme values on each objective. Useful for identifying
   configurations that specialize in one objective.
4. **Mean_f1 / Mean_f2** — Average quality of the Pareto front.

### Analysis Approach

**Step 1: Separate by K.** HV values across different K values use different calibration
bounds and are NOT directly comparable.

**Step 2: Within each K, compare across Lambda values.** This reveals whether POI influence
significantly impacts solution quality.

**Step 3: For each (K, Lambda) group, analyze parameter effects:**
- Sort by `MutRate` vs `Final_HV` to find the optimal mutation rate.
- Check if high mutation (0.30-0.40) improves ND_Count (combats premature convergence).
- Compare `PopSize` groups to understand exploration vs. exploitation tradeoff.

---

## 5. Architecture Notes

- `FitnessCalculator` has two constructors:
  - 3-arg: reads demand from CSV `demandScore` (used by `Main.java`).
  - 4-arg: computes demand dynamically with lambda (used by `ParameterAnalyzer`).
- `Main.java` is completely untouched and unaffected by these changes.
- The calibration phase reuses the same `runSPEA2()` method as the grid search.
