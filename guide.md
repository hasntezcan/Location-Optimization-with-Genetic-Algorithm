# Kadikoy Parcel Locker Placement Optimization Guide

This document summarizes how the project currently works and how the components connect. The project solves a **SPEA2-based** bi-objective optimization for parcel locker placement in **Kadikoy**.

## Goal and Objectives

One solution (an individual) selects `k` locker locations (chromosome = a set of selected candidate IDs).

Two objectives are minimized:

### f1: Accessibility cost
- For each demand grid point, the minimum distance to any selected locker is used.
- The distance matrix is in metres; the evaluation converts to kilometres and applies the `beta` exponent.

Summary form:

```text
f1 = sum_i ( demand_i * (minDistKm_i ^ beta) ) / sum_i demand_i
```

Implementation: [FitnessCalculator.evaluateF1](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/src/main/java/service/FitnessCalculator.java)

### f2: Equity (fairness across neighborhoods)
- For each neighborhood (mahalle), a demand-weighted mean accessibility cost is computed.
- The **coefficient of variation** (CV = std / mean) across neighborhood means is used.

Implementation: [FitnessCalculator.evaluateF2](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/src/main/java/service/FitnessCalculator.java)

## High-Level Flow

### 1) Data preparation (Python)
- `scripts/prepare_demand.py` computes the `poi_score` and `demand_final` columns (overwrites the CSV).
- Details: [scripts/guide.md](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/scripts/guide.md)

### 2) Artifacts (distance matrix)
- `data/kadikoy_distance_meters_nxn.npy` is the distance matrix.
- The indexing order is **candidate id ascending**.
- The Java side maintains this alignment via [CandidateRepository.finalizeRepository](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/src/main/java/model/CandidateRepository.java).
- Forbidden candidates remain in the CSV and distance matrix as demand grid
  points. The GA selection universe is filtered with
  `CandidateRepository.getSelectableCandidateIds()`, so `is_forbidden = 1`
  rows cannot be chosen as locker locations.
- Details: [kadikoy_ARTIFACTS_GUIDE.md](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/data/kadikoy_ARTIFACTS_GUIDE.md)

### 3) SPEA2 optimization (Java)
Entry point: [app.Main](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/src/main/java/app/Main.java)

Flow (summary):
- Load CSV → finalize repository
- Load NPY distance matrix
- Initialize population (`PopulationInitializer`)
- Evaluate (merge population + archive):
  - objective evaluation ([FitnessCalculator](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/src/main/java/service/FitnessCalculator.java))
  - normalization for SPEA2 internals ([ObjectiveNormalizer](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/src/main/java/service/ObjectiveNormalizer.java))
  - strength/rawFitness/density/totalFitness ([Evaluate](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/src/main/java/algorithm/Evaluate.java))
- Survivor (archive selection) ([Survivor](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/src/main/java/algorithm/Survivor.java))
- Selection (binary tournament) ([Selection](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/src/main/java/algorithm/Selection.java))
- Variation (crossover/mutation/repair) ([Variation](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/src/main/java/algorithm/Variation.java))

## Normalization and Hypervolume

This project uses normalization in two different places:
- **SPEA2 internal normalization**: inside `Evaluate`, the merged set is normalized to compute density.
- **Run assessment normalization (archive export)**: `Main` normalizes archive
  snapshots with final-ND-based bounds so exported normalized coordinates share
  one objective space.

Current behavior:
- `Main` derives ideal/nadir bounds from the **final archive non-dominated set only**.
- Both archive CSVs are normalized with those final-ND bounds so the exported
  `norm_f1` and `norm_f2` columns share one coordinate system.
- Hypervolume is computed for the final archive in normalized space with a fixed
  reference point, typically `(1.1, 1.1)`.
- Initial-to-final improvement is assessed with raw-objective ND metrics and
  the C-metric in `scripts/plot_archives.py`, not by comparing initial HV to
  final HV.

Related code:
- [Main](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/src/main/java/app/Main.java)
- [HypervolumeIndicator](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/src/main/java/service/HypervolumeIndicator.java)

## Running

### SPEA2 single run

```bash
mvn -q compile exec:java
```

### Archive plot (single run)

```bash
python3 scripts/plot_archives.py
```

### Hyperparameter grid search

For [ParameterAnalyzer](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/src/main/java/app/ParameterAnalyzer.java):

```bash
mvn -q compile exec:java -Panalyze
```

Output: `output/parameter_analysis_results.csv`

Statistical analysis of grid search results:

```bash
python3 scripts/statistical_analysis.py
```

Output: `output/statistics/selected_configurations.csv`

## Related Guides

- Comprehensive technical guide: [General_GUIDE.md](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/General_GUIDE.md)
- Java package guide: [SRC_GUIDE.MD](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/src/main/java/SRC_GUIDE.MD)
- Python scripts (all): [scripts/guide.md](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/scripts/guide.md)
- Distance matrix contract: [kadikoy_ARTIFACTS_GUIDE.md](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/data/kadikoy_ARTIFACTS_GUIDE.md)
- ParameterAnalyzer guide: [analyse_guide.md](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/src/main/java/analyse_guide.md)
- Backend integration: [backend_guide.md](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/src/main/java/app/backend_guide.md)
- UI dashboard: [parcel-locker-ui/README.md](file:///Users/yigitpepe/Desktop/Location-Optimization-with-Genetic-Algorithm/parcel-locker-ui/README.md)
