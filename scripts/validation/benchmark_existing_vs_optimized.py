#!/usr/bin/env python3
"""Evaluate current existing lockers and optionally compare a GA archive.

The benchmark follows the Java runtime's sorted-candidate matrix alignment and
FitnessCalculator formulas. Physical placement comes exclusively from
``existing_locker_count``; the nearby/buffer count is never a facility source.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_BETA = 2.0
REQUIRED_COLUMNS = {
    "id",
    "lat",
    "lon",
    "Mahalle_Name_Turkish",
    "demand_final",
    "existing_locker_count",
}
SUMMARY_JSON_NAME = "existing_vs_optimized_benchmark_summary.json"
SUMMARY_CSV_NAME = "existing_vs_optimized_benchmark_summary.csv"
REPORT_NAME = "existing_vs_optimized_benchmark_report.md"
EXISTING_IDS_NAME = "existing_current_placement_ids.csv"


def resolve_path(value: str) -> Path:
    path = Path(value)
    return path.resolve() if path.is_absolute() else (PROJECT_ROOT / path).resolve()


def display_path(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def finite_float(value: Any, label: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid numeric value for {label}: {value!r}") from error
    if not math.isfinite(parsed):
        raise ValueError(f"Non-finite numeric value for {label}: {value!r}")
    return parsed


def nonnegative_integer(value: Any, label: str) -> int:
    parsed = finite_float(value, label)
    if parsed < 0 or not parsed.is_integer():
        raise ValueError(f"Expected non-negative integer for {label}: {value!r}")
    return int(parsed)


def load_candidates(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Candidate CSV not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Candidate CSV has no header: {path}")
        fields = {name.strip().lstrip("\ufeff") for name in reader.fieldnames}
        missing = sorted(REQUIRED_COLUMNS - fields)
        if missing:
            raise ValueError(f"Candidate CSV is missing required columns: {', '.join(missing)}")

        candidates = []
        for line_number, raw in enumerate(reader, start=2):
            row = {(key or "").strip().lstrip("\ufeff"): value for key, value in raw.items()}
            candidate_id = nonnegative_integer(row["id"], f"id at line {line_number}")
            existing_count = nonnegative_integer(
                row["existing_locker_count"], f"existing_locker_count at line {line_number}"
            )
            candidates.append(
                {
                    "id": candidate_id,
                    "lat": finite_float(row["lat"], f"lat at line {line_number}"),
                    "lon": finite_float(row["lon"], f"lon at line {line_number}"),
                    "neighborhood": row["Mahalle_Name_Turkish"].strip(),
                    "demand": finite_float(row["demand_final"], f"demand_final at line {line_number}"),
                    "existing_locker_count": existing_count,
                    "nearby_locker_count": nonnegative_integer(
                        row.get("nearby_locker_count") or 0,
                        f"nearby_locker_count at line {line_number}",
                    ),
                    "is_forbidden": nonnegative_integer(
                        row.get("is_forbidden") or 0, f"is_forbidden at line {line_number}"
                    ),
                }
            )

    if not candidates:
        raise ValueError("Candidate CSV contains no data rows.")
    ids = [row["id"] for row in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("Candidate IDs must be unique.")
    if any(not row["neighborhood"] for row in candidates):
        raise ValueError("Mahalle_Name_Turkish must not be blank.")
    if sum(row["demand"] for row in candidates) <= 0:
        raise ValueError("Total demand_final must be positive.")

    return sorted(candidates, key=lambda row: row["id"])


def companion_id_artifact(matrix_path: Path) -> Path:
    suffix = "_distance_meters_nxn.npy"
    if matrix_path.name.endswith(suffix):
        return matrix_path.with_name(matrix_path.name[: -len(suffix)] + "_candidate_ids_sorted.npy")
    return matrix_path.with_name(matrix_path.stem + "_candidate_ids_sorted.npy")


def load_and_validate_matrix(
    matrix_path: Path, candidates: list[dict[str, Any]]
) -> tuple[np.ndarray, str]:
    if not matrix_path.is_file():
        raise FileNotFoundError(f"Distance matrix not found: {matrix_path}")
    matrix = np.load(matrix_path, mmap_mode="r")
    expected_shape = (len(candidates), len(candidates))
    if matrix.shape != expected_shape:
        raise ValueError(f"Distance matrix shape {matrix.shape} does not match {expected_shape}.")
    if not np.issubdtype(matrix.dtype, np.number):
        raise ValueError(f"Distance matrix must be numeric, found {matrix.dtype}.")

    sorted_ids = np.asarray([row["id"] for row in candidates], dtype=np.int64)
    id_artifact = companion_id_artifact(matrix_path)
    if id_artifact.is_file():
        artifact_ids = np.asarray(np.load(id_artifact), dtype=np.int64)
        if artifact_ids.shape != sorted_ids.shape or not np.array_equal(artifact_ids, sorted_ids):
            raise ValueError(
                "Candidate IDs do not match the matrix companion ID artifact: "
                f"{id_artifact}"
            )
        alignment = f"validated against {display_path(id_artifact)}"
    else:
        alignment = "sorted by candidate ID ascending (companion ID artifact not found)"
    return matrix, alignment


def evaluate_facilities(
    facility_ids: list[int],
    candidates: list[dict[str, Any]],
    matrix: np.ndarray,
    beta: float,
) -> tuple[float, float]:
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


def clean_solution_for_json(solution: dict[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in solution.items()
        if key != "candidateIds"
    } | {"candidateIds": solution.get("candidateIds", [])}


def write_outputs(
    output_dir: Path,
    candidates: list[dict[str, Any]],
    existing_candidates: list[dict[str, Any]],
    physical_count: int,
    baseline_f1: float,
    baseline_f2: float,
    beta: float,
    alignment: str,
    archive: dict[str, Any],
    candidate_path: Path,
    matrix_path: Path,
    archive_path: Path,
    metadata_path: Path,
) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / SUMMARY_JSON_NAME
    csv_path = output_dir / SUMMARY_CSV_NAME
    report_path = output_dir / REPORT_NAME
    existing_ids_path = output_dir / EXISTING_IDS_NAME

    summary = {
        "generatedAt": datetime.now().astimezone().isoformat(timespec="seconds"),
        "beta": beta,
        "matrixAlignment": alignment,
        "inputs": {
            "candidateCsv": display_path(candidate_path),
            "distanceMatrix": display_path(matrix_path),
            "archive": display_path(archive_path),
            "metadata": display_path(metadata_path),
        },
        "dataSemantics": {
            "currentPlacementSource": "existing_locker_count > 0",
            "nearbyLockerCountRole": "300m buffer/proximity context only; not used as facilities",
        },
        "baseline": {
            "physicalExistingLockerCount": physical_count,
            "effectiveExistingCandidateCount": len(existing_candidates),
            "existingCandidateIds": [row["id"] for row in existing_candidates],
            "f1": baseline_f1,
            "f2": baseline_f2,
        },
        "optimizedArchive": archive,
    }
    json_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    csv_fields = [
        "placement",
        "solution_id",
        "archive_k",
        "f1",
        "f2",
        "improvement_f1_pct",
        "improvement_f2_pct",
        "valid_greenfield_k_physical_count",
    ]
    csv_rows = [
        {
            "placement": "existing_baseline",
            "solution_id": "",
            "archive_k": len(existing_candidates),
            "f1": f"{baseline_f1:.12f}",
            "f2": f"{baseline_f2:.12f}",
            "improvement_f1_pct": "",
            "improvement_f2_pct": "",
            "valid_greenfield_k_physical_count": "",
        }
    ]
    for name, solution in archive.get("representatives", {}).items():
        csv_rows.append(
            {
                "placement": name,
                "solution_id": solution["solutionId"],
                "archive_k": solution["k"],
                "f1": f"{solution['f1']:.12f}",
                "f2": f"{solution['f2']:.12f}",
                "improvement_f1_pct": f"{solution['improvementF1Pct']:.6f}",
                "improvement_f2_pct": f"{solution['improvementF2Pct']:.6f}",
                "valid_greenfield_k_physical_count": archive[
                    "validGreenfieldPhysicalCountComparison"
                ],
            }
        )
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=csv_fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(csv_rows)

    with existing_ids_path.open("w", encoding="utf-8", newline="") as handle:
        fields = [
            "candidate_id",
            "existing_locker_count",
            "lat",
            "lon",
            "candidate_neighborhood",
            "is_forbidden",
        ]
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in existing_candidates:
            writer.writerow(
                {
                    "candidate_id": row["id"],
                    "existing_locker_count": row["existing_locker_count"],
                    "lat": row["lat"],
                    "lon": row["lon"],
                    "candidate_neighborhood": row["neighborhood"],
                    "is_forbidden": row["is_forbidden"],
                }
            )

    archive_section = (
        f"- Arşiv türü: **{archive.get('archiveType', 'bilinmiyor')}**\n"
        f"- Arşiv K değeri: **{archive.get('archiveK', 'yok')}**\n"
        f"- Çözüm sayısı: **{archive.get('solutionCount', 0)}**\n"
        f"- Geçerli Existing OFF K={physical_count} karşılaştırması: "
        f"**{'Evet' if archive.get('validGreenfieldPhysicalCountComparison') else 'Hayır'}**\n"
    ) if archive.get("found") else "- Optimize edilmiş arşiv bulunamadı.\n"

    representative_lines = []
    for label, key in [
        ("En iyi F1", "bestF1"),
        ("En iyi F2", "bestF2"),
        ("Dengeli çözüm", "balancedCompromise"),
    ]:
        solution = archive.get("representatives", {}).get(key)
        if solution:
            representative_lines.append(
                f"| {label} | {solution['solutionId']} | {solution['f1']:.8f} | "
                f"{solution['f2']:.8f} | {solution['improvementF1Pct']:.2f}% | "
                f"{solution['improvementF2Pct']:.2f}% |"
            )
    representatives_table = "\n".join(representative_lines) or "| Karşılaştırma bekleniyor | - | - | - | - | - |"

    warning = archive.get("warning") or "Geçerli greenfield karşılaştırma arşivi bulundu."
    report = f"""# Mevcut Yerleşim ve Optimize Yerleşim Karşılaştırması

## Yönetici özeti

Mevcut **{physical_count} fiziksel dolap**, aday grid sisteminde **{len(existing_candidates)} efektif lokasyona** karşılık gelmektedir. Aynı candidate noktasına map edilen birden fazla fiziksel dolap mesafe kapsamasını değiştirmediği için F1/F2 hesabında unique candidate lokasyonları kullanılmıştır.

> **Durum:** {warning}

## Veri anlamı

- `existing_locker_count > 0`: mevcut fiziksel yerleşimin tek kaynağıdır.
- `nearby_locker_count`: yalnızca 300m buffer/yakınlık bağlamıdır; tesis setine dahil edilmemiştir.
- Matris hizalaması: {alignment}.
- Mesafe maliyeti: metre → kilometre, ardından `beta={beta}` kuvveti.

## Mevcut yerleşim baz çizgisi

- Fiziksel mevcut dolap sayısı: **{physical_count}**
- Efektif mevcut candidate lokasyonu: **{len(existing_candidates)}**
- Baseline F1 (erişilebilirlik maliyeti): **{baseline_f1:.12f}**
- Baseline F2 (mahalleler arası değişim katsayısı): **{baseline_f2:.12f}**

## Optimize arşiv durumu

{archive_section}
| Temsilci çözüm | Arşiv ID | F1 | F2 | F1 değişimi | F2 değişimi |
|---|---:|---:|---:|---:|---:|
{representatives_table}

Pozitif değişim yüzdesi optimize çözümün daha iyi, negatif değer daha kötü olduğunu gösterir. Geçerli ana kıyas için **Existing OFF ve K={physical_count}** arşivi gereklidir; farklı K değerleri yalnızca geçici/yardımcı karşılaştırmadır.

## Üretilen dosyalar

- `{display_path(json_path)}`
- `{display_path(csv_path)}`
- `{display_path(report_path)}`
- `{display_path(existing_ids_path)}`
"""
    report_path.write_text(report, encoding="utf-8")
    return [json_path, csv_path, report_path, existing_ids_path]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Benchmark current existing lockers against an optional optimized archive."
    )
    parser.add_argument("--candidate-csv", default="data/candidate_points.csv")
    parser.add_argument("--distance-matrix", default="data/kadikoy_distance_meters_nxn.npy")
    parser.add_argument("--archive", default="output/final_archive.csv")
    parser.add_argument("--metadata", default="output/run_metadata.json")
    parser.add_argument("--output-dir", default="output/validation")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    candidate_path = resolve_path(args.candidate_csv)
    matrix_path = resolve_path(args.distance_matrix)
    archive_path = resolve_path(args.archive)
    metadata_path = resolve_path(args.metadata)
    output_dir = resolve_path(args.output_dir)

    candidates = load_candidates(candidate_path)
    matrix, alignment = load_and_validate_matrix(matrix_path, candidates)
    existing_candidates = [row for row in candidates if row["existing_locker_count"] > 0]
    existing_ids = [row["id"] for row in existing_candidates]
    physical_count = sum(row["existing_locker_count"] for row in existing_candidates)
    if not existing_ids:
        raise ValueError("No existing placement found from existing_locker_count > 0.")

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
        candidates,
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
    )

    print(f"Physical existing lockers: {physical_count}")
    print(f"Effective existing candidate locations: {len(existing_candidates)}")
    print(f"Baseline F1: {baseline_f1:.12f}")
    print(f"Baseline F2: {baseline_f2:.12f}")
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
        print(f"Wrote: {display_path(path)}")


if __name__ == "__main__":
    main()
