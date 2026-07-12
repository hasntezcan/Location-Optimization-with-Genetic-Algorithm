"""F1/F2 objective evaluation, chromosome parsing, and archive comparison.

Given a facility candidate set (never chooses one itself), computes the same
F1 (demand-weighted accessibility cost) and F2 (neighborhood equity cost)
formulas the Java FitnessCalculator uses, and compares an optional optimizer
archive against a baseline. Formulas and archive representative-selection
tie-breaking must never change as part of a code migration.

Does not own:

- candidate/matrix loading or scenario resolution
  (``location_platform.benchmark.current_network``)
- output constants, path-display formatting, or report writing
  (``location_platform.benchmark.reporting``)
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from location_platform.common.parsing import nonnegative_integer

DEFAULT_BETA = 2.0


def evaluate_facilities(
    facility_ids: list[int],
    candidates: list[dict[str, Any]],
    matrix: np.ndarray,
    beta: float,
) -> tuple[float, float]:
    """Compute F1 (demand-weighted accessibility cost) and F2 (neighborhood equity cost).

    This is the one truly benchmark-exclusive computation in the package —
    it must never move anywhere else and its formula/tolerance must never
    change as part of a code migration.
    """
    if not facility_ids:
        raise ValueError("Facility set must not be empty.")
    id_to_index = {row["id"]: index for index, row in enumerate(candidates)}
    unknown = sorted(set(facility_ids) - set(id_to_index))
    if unknown:
        raise ValueError(f"Facility IDs are absent from candidate data: {unknown[:10]}")

    facility_indexes = np.asarray([id_to_index[candidate_id] for candidate_id in facility_ids])
    nearest_metres = np.asarray(matrix[:, facility_indexes].min(axis=1), dtype=np.float64)
    distance_costs = np.power(nearest_metres / 1000.0, beta)
    demand = np.asarray([row["demand"] for row in candidates], dtype=np.float64)

    f1 = float(np.sum(demand * distance_costs) / np.sum(demand))

    weighted_cost_by_neighborhood: dict[str, float] = {}
    demand_by_neighborhood: dict[str, float] = {}
    for row, row_demand, distance_cost in zip(candidates, demand, distance_costs):
        neighborhood = row["neighborhood"]
        weighted_cost_by_neighborhood[neighborhood] = (
            weighted_cost_by_neighborhood.get(neighborhood, 0.0)
            + float(row_demand * distance_cost)
        )
        demand_by_neighborhood[neighborhood] = (
            demand_by_neighborhood.get(neighborhood, 0.0) + float(row_demand)
        )

    neighborhood_means = np.asarray(
        [
            weighted_cost_by_neighborhood[name] / demand_by_neighborhood[name]
            for name in weighted_cost_by_neighborhood
        ],
        dtype=np.float64,
    )
    mean_of_means = float(np.mean(neighborhood_means))
    f2 = float(np.std(neighborhood_means, ddof=0) / mean_of_means) if mean_of_means > 0 else 0.0
    return f1, f2


def parse_chromosome(raw: str, row_label: str) -> list[int]:
    values = []
    for token in raw.split("|"):
        token = token.strip()
        if token:
            values.append(nonnegative_integer(token, f"chromosome in {row_label}"))
    if not values:
        raise ValueError(f"Empty chromosome in {row_label}.")
    if len(values) != len(set(values)):
        raise ValueError(f"Duplicate candidate ID inside chromosome in {row_label}.")
    return values


def improvement_percent(baseline: float, optimized: float) -> float | None:
    if baseline == 0:
        return None
    return ((baseline - optimized) / baseline) * 100.0


def load_metadata(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    with path.open("r", encoding="utf-8") as handle:
        value = json.load(handle)
    if not isinstance(value, dict):
        raise ValueError(f"Run metadata must be a JSON object: {path}")
    return value


def evaluate_archive(
    archive_path: Path,
    metadata_path: Path,
    candidates: list[dict[str, Any]],
    matrix: np.ndarray,
    beta: float,
    baseline_f1: float,
    baseline_f2: float,
    physical_existing_count: int,
) -> dict[str, Any]:
    if not archive_path.is_file():
        return {
            "found": False,
            "metadataFound": metadata_path.is_file(),
            "validGreenfieldPhysicalCountComparison": False,
            "warning": (
                f"Optimize edilmiş arşiv bulunamadı. Existing OFF ve K={physical_existing_count} "
                "ile optimizer çalıştırılmalıdır."
            ),
            "representatives": {},
        }

    metadata = load_metadata(metadata_path)
    with archive_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None or "chromosome" not in reader.fieldnames:
            raise ValueError(f"Archive CSV must contain chromosome: {archive_path}")
        archive_rows = list(reader)
    if not archive_rows:
        raise ValueError(f"Archive CSV contains no solutions: {archive_path}")

    evaluated = []
    chromosome_lengths = set()
    for position, row in enumerate(archive_rows, start=1):
        solution_id = int(row.get("archive_index") or position)
        chromosome = parse_chromosome(row["chromosome"], f"archive row {position}")
        chromosome_lengths.add(len(chromosome))
        f1, f2 = evaluate_facilities(chromosome, candidates, matrix, beta)
        evaluated.append(
            {
                "solutionId": solution_id,
                "candidateIds": chromosome,
                "k": len(chromosome),
                "f1": f1,
                "f2": f2,
                "improvementF1Pct": improvement_percent(baseline_f1, f1),
                "improvementF2Pct": improvement_percent(baseline_f2, f2),
            }
        )

    if len(chromosome_lengths) != 1:
        raise ValueError(f"Archive chromosomes have inconsistent lengths: {sorted(chromosome_lengths)}")
    archive_k = next(iter(chromosome_lengths))
    metadata_k = int(metadata["k"]) if metadata and metadata.get("k") is not None else None
    if metadata_k is not None and metadata_k != archive_k:
        raise ValueError(f"Archive K={archive_k} does not match metadata K={metadata_k}.")

    include_existing = bool(metadata.get("includeExistingLockers")) if metadata else None
    effective_fixed_count = (
        int(metadata.get("effectiveFixedFacilityIdsCount") or 0) if metadata else None
    )
    greenfield = metadata is not None and not include_existing and effective_fixed_count == 0
    valid_k = archive_k == physical_existing_count
    valid_main_comparison = greenfield and valid_k

    if metadata is None:
        archive_type = "unknown"
        warning = "run_metadata.json bulunamadığı için arşivin greenfield olduğu doğrulanamadı."
    elif include_existing or effective_fixed_count:
        archive_type = "existing-aware"
        warning = "Arşiv mevcut dolapları içeriyor; greenfield karşılaştırması için kullanılamaz."
    else:
        archive_type = "greenfield"
        warning = "" if valid_k else (
            f"Greenfield arşiv K={archive_k}. Ana fiziksel karşılaştırma için Existing OFF ve "
            f"K={physical_existing_count} arşivi gereklidir."
        )

    best_f1 = min(evaluated, key=lambda row: (row["f1"], row["f2"], row["solutionId"]))
    best_f2 = min(evaluated, key=lambda row: (row["f2"], row["f1"], row["solutionId"]))
    min_f1 = min(row["f1"] for row in evaluated)
    max_f1 = max(row["f1"] for row in evaluated)
    min_f2 = min(row["f2"] for row in evaluated)
    max_f2 = max(row["f2"] for row in evaluated)
    for row in evaluated:
        norm_f1 = (row["f1"] - min_f1) / (max_f1 - min_f1) if max_f1 > min_f1 else 0.0
        norm_f2 = (row["f2"] - min_f2) / (max_f2 - min_f2) if max_f2 > min_f2 else 0.0
        row["balancedScore"] = 0.5 * norm_f1 + 0.5 * norm_f2
    balanced = min(
        evaluated,
        key=lambda row: (row["balancedScore"], row["f1"], row["f2"], row["solutionId"]),
    )

    return {
        "found": True,
        "metadataFound": metadata is not None,
        "archiveType": archive_type,
        "includeExistingLockers": include_existing,
        "effectiveFixedFacilityIdsCount": effective_fixed_count,
        "archiveK": archive_k,
        "solutionCount": len(evaluated),
        "validGreenfieldPhysicalCountComparison": valid_main_comparison,
        "warning": warning,
        "representatives": {
            "bestF1": best_f1,
            "bestF2": best_f2,
            "balancedCompromise": balanced,
        },
    }
