"""Benchmark output constants, path-display formatting, and report writing.

Takes already-computed baseline/archive results and writes the committed
JSON/CSV/Markdown benchmark outputs. Never recomputes F1/F2, never re-derives
existing facilities, and never loads candidate/matrix/scenario data itself —
it is a pure formatting and I/O layer over values callers already have.

Does not own:

- candidate/matrix loading or scenario resolution
  (``location_platform.benchmark.current_network``)
- F1/F2 calculation, chromosome parsing, or archive evaluation
  (``location_platform.benchmark.evaluation``)
"""

from __future__ import annotations

import csv
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from location_platform.common.paths import display_relative_path

SUMMARY_JSON_NAME = "existing_vs_optimized_benchmark_summary.json"
SUMMARY_CSV_NAME = "existing_vs_optimized_benchmark_summary.csv"
REPORT_NAME = "existing_vs_optimized_benchmark_report.md"
EXISTING_IDS_NAME = "existing_current_placement_ids.csv"


def write_outputs(
    output_dir: Path,
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
    scenario_metadata: dict[str, Any],
    v0_seed_match: dict[str, Any] | None,
    project_root: Path,
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
            "candidateCsv": display_relative_path(candidate_path, project_root),
            "distanceMatrix": display_relative_path(matrix_path, project_root),
            "scenario": scenario_metadata["scenarioPath"],
            "archive": display_relative_path(archive_path, project_root),
            "metadata": display_relative_path(metadata_path, project_root),
        },
        "dataSemantics": {
            "currentPlacementSource": "scenario.facilities[] active enabled existing facilities",
            "currentNetworkSource": "scenario",
            "nearbyLockerCountRole": "300m buffer/proximity context only; not used as facilities",
            "existingLockerCountRole": (
                "V0 seed source only; used here only when --validate-v0-seed-match is provided"
            ),
        },
        "scenarioMetadata": scenario_metadata | {"v0SeedMatch": v0_seed_match},
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
            "scenario_facility_ids",
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
                    "existing_locker_count": row["scenario_physical_count"],
                    "scenario_facility_ids": "|".join(row["scenario_facility_ids"]),
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

- Mevcut ağ kaynağı: `{scenario_metadata["scenarioPath"]}` içindeki `scenario.facilities[]`.
- Aktif mevcut tesis filtresi: `kind == "existing"`, `status == "enabled"`, `snap.snapStatus == "snapped"`.
- `existing_locker_count`: yalnızca V0 seed doğrulaması için kullanılır; benchmark tesis kaynağı değildir.
- `nearby_locker_count`: yalnızca 300m buffer/yakınlık bağlamıdır; tesis setine dahil edilmemiştir.
- Matris hizalaması: {alignment}.
- Mesafe maliyeti: metre → kilometre, ardından `beta={beta}` kuvveti.
- Senaryo ID: `{scenario_metadata["scenarioId"]}`
- Talep tipi: `{scenario_metadata.get("demandType")}`
- Run type: `{scenario_metadata.get("runType")}`

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

- `{display_relative_path(json_path, project_root)}`
- `{display_relative_path(csv_path, project_root)}`
- `{display_relative_path(report_path, project_root)}`
- `{display_relative_path(existing_ids_path, project_root)}`
"""
    report_path.write_text(report, encoding="utf-8")
    return [json_path, csv_path, report_path, existing_ids_path]
