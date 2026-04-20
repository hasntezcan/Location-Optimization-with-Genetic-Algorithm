# Parameter Analysis Guide (`analyse_guide.md`)

## Overview

This document explains the **Hyperparameter Grid Search** framework implemented for the Kadıköy Parcel Locker SPEA2 optimization project. 

The primary goal of this analysis was to investigate two main concerns systematically:
1. **Premature Convergence**: Did the genetic algorithm lose diversity too quickly or fail to explore? Was the shared-gene crossover operator too greedy, or was the mutation rate simply too low?
2. **Hypervolume Sensitivity**: How do hypervolume metrics vary across different random seeds and hyperparameters?

This guide acts as a manual for running, interpreting, and extending the hyperparameter search without modifying the core optimization pipeline.

---

## 1. Technical Implementation Strategy

We designed an independent **Parameter Analyzer** that bypasses the single-run configuration located in `GAParameters.java` and instead executes a predefined configuration grid.

### 1.1 Independence from Main Flow
- The main pipeline (`app.Main`) remains untouched and continues to use fixed values from `config.GAParameters`.
- The evaluation loop logic is identical, ensuring true representation of the running codebase.
- The new tester is isolated in `app.ParameterAnalyzer.java`. 

### 1.2 "Constant Budget" Fair Comparison
A core challenge in hyperparameter testing is **fair comparison**. A population of 200 will naturally find better solutions than a population of 50 if given the same number of generations—but it requires 4x more computational effort. 

To eliminate this bias, we implemented a **Constant Total Evaluations Deadline**.
Regardless of `Population Size` or `Archive Size`, each algorithm configuration is guaranteed roughly `15,200` total function evaluations.
```java
// Budget = initial_population + generations * (population + archive)
int maxGenerations = (TOTAL_BUDGET - popSize) / (popSize + archiveSize);
```
- Pop=50, Arc=25 → 202 Generations
- Pop=100, Arc=50 → 101 Generations
- Pop=200, Arc=100 → 50 Generations

### 1.3 Per-run Normalization
To prevent anomalies when comparing hypervolume metrics, the normalizer dynamically extracts the global **minimum and maximum** bounds across *the entire duration of the specific run*, pads them by 10%, and maps the fitness values for that specific run to `[0, 1]`. 

This guarantees:
- HV values remain mathematically sound (`0.0` to `~1.21` against reference point `(1.1, 1.1)`)
- Differences in Hypervolume ratios across runs strictly correlate to how widespread and optimal the Pareto front is.

---

## 2. Experimental Grid Setup

The comprehensive hyperparameter grid included the following dimensions:

| Parameter | Values Examined | Rationale for Testing |
|:---|:---|:---|
| **Locker Count (`K`)** | 3, 5, 7 | This dictates the combinatorial search space size. Larger K requires significantly more exploration. |
| **Population Size** | 50, 100, 200 | Regulates the balance between wide horizontal search coverage versus generation depth. |
| **Mutation Rate** | 0.05, 0.10, 0.20, 0.30, 0.40 | **CRUCIAL METRIC**: Because the Shared-Gene Crossover restricts exploration, mutation must provide diversity. Is 0.10 too low? Testing up to 0.40 reveals the breaking point. |
| **Crossover Rate** | 0.70, 0.90 | Determines how frequently we invoke the conservative shared-gene inheritance. |
| **Random Seed** | 42, 123, 7 | Standard experimental redundancy. Each config is run 3 times to average out stochastic noise. |

**Total Execution Runs = 270** -> `3 (K) × 3 (Pop) × 5 (Mut) × 2 (Cross) × 3 (Seeds)`

---

## 3. How to Run the Analysis

We've registered a dedicated Maven profile for the analyzer so that your `pom.xml` defaults still execute the regular `Main.java` program without requiring hard-coded overrides.

To execute the parameter grid search:

```powershell
# Compile and run via the designated 'analyze' Maven profile
mvn compile exec:java -Panalyze
```

*Note: Generating all 270 runs sequentially at ~5 seconds per run takes ~20 to 25 minutes depending on CPU performance.*

### 3.1 Output Structure
The analyzer writes its data strictly to the following file:
- `output/parameter_analysis_results.csv`

---

## 4. How to Interpret the CSV Results

The output CSV file contains 15 columns representing configuration flags and final output measurements.

### Evaluation Metrics to Focus On:

1. `Final_HV` (Hypervolume): The single most reliable measure of simultaneous proximity (closeness to the ideal) and diversity (spread across the front).
2. `Final_ND_Count` (Non-dominated Solution Count): Indicates archive density. If ND count is low, the population likely collapsed to a single local optimal location (evidence of Premature Convergence).
3. `Final_Best_F1` / `Final_Best_F2`: The raw best extremes discovered in the entire run. Did a high mutation rate find a dramatically better F1 at the expense of ignoring F2?

### Diagnosis Validation Techniques:
**Addressing the "Premature Convergence" Suspicion:**
Sort your spreadsheet by `Mutation_Rate` (x-axis) vs `Final_HV` (y-axis) or `Final_ND_Count`. 
- If runs with `Mut=0.30` or `0.40` consistently report higher ND counts and wider Hypervolume metrics than `0.05 / 0.10`, the original hypothesis was **true**—the crossover was excessively converging and higher mutation fixed it.
- If high mutation causes HV to decrease, then the baseline algorithm was correctly optimizing, and excessive mutation is acting destructively.

**Analyzing 'K' Impact:**
Separate the data physically based on `K` before comparing HVs. Hypervolume values for K=3 will intrinsically behave differently than K=7 due to scale differences in total distance costs.

---

## 5. Next Steps for Optimization

After analyzing the CSV trends in Excel or Pandas, adjust `GAParameters.java` permanently to lock in the optimal parameters for production runs.

If you decide to refine the scope later, simply modify the static arrays embedded inside `ParameterAnalyzer.java`:
```java
private static final int[] K_VALUES = {5};
private static final double[] MUTATION_RATES = {0.15, 0.20, 0.25};
```
And execute with `mvn compile exec:java -Panalyze` once more.
