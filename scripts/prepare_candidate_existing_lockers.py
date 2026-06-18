"""Map physical existing lockers to nearest candidate centers in EPSG:32635.

This preparation step intentionally uses plain CSV input and Python's standard
library only. It does not read GeoPackage data or depend on a GIS package.
"""

from __future__ import annotations

import csv
import json
import math
import shutil
import tempfile
from collections import Counter
from datetime import datetime
from pathlib import Path
from statistics import fmean


PROJECT_ROOT = Path(__file__).resolve().parents[1]
CANDIDATE_CSV = PROJECT_ROOT / "data" / "candidate_points.csv"
LOCKER_CSV = PROJECT_ROOT / "data" / "raw" / "existing_lockers_32635.csv"
ARCHIVE_DIR = PROJECT_ROOT / "data" / "archive"
AUDIT_DIR = PROJECT_ROOT / "output" / "data_audit"
SNAP_AUDIT_CSV = AUDIT_DIR / "existing_locker_snap_audit.csv"
SUMMARY_JSON = AUDIT_DIR / "existing_locker_mapping_summary.json"
REPORT_MD = AUDIT_DIR / "existing_locker_mapping_report.md"

REQUIRED_CANDIDATE_COLUMNS = {
    "id",
    "left",
    "right",
    "top",
    "bottom",
    "lat",
    "lon",
}
REQUIRED_LOCKER_COLUMNS = {"x_32635", "y_32635"}
AUDIT_COLUMNS = [
    "locker_source_index",
    "locker_name",
    "locker_code",
    "locker_source",
    "locker_address",
    "source_x_32635",
    "source_y_32635",
    "source_lat",
    "source_lon",
    "candidate_id",
    "candidate_center_x_32635",
    "candidate_center_y_32635",
    "candidate_lat",
    "candidate_lon",
    "snap_distance_m",
    "candidate_neighborhood",
]


def relative_path(path: Path) -> str:
    return path.relative_to(PROJECT_ROOT).as_posix()


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        raise FileNotFoundError(f"Required input file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"CSV has no header: {path}")
        fieldnames = [name.strip().lstrip("\ufeff") for name in reader.fieldnames]
        rows = []
        for raw_row in reader:
            rows.append({(key or "").strip().lstrip("\ufeff"): value for key, value in raw_row.items()})
    return fieldnames, rows


def require_columns(fieldnames: list[str], required: set[str], path: Path) -> None:
    missing = sorted(required.difference(fieldnames))
    if missing:
        raise ValueError(f"Missing required columns in {path}: {', '.join(missing)}")


def finite_float(value: str | None, label: str, row_number: int) -> float:
    try:
        parsed = float(value or "")
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid {label} at data row {row_number}: {value!r}") from error
    if not math.isfinite(parsed):
        raise ValueError(f"Non-finite {label} at data row {row_number}: {value!r}")
    return parsed


def integer_count(value: str | None, label: str, row_number: int) -> int:
    parsed = finite_float(value, label, row_number)
    if not parsed.is_integer() or parsed < 0:
        raise ValueError(f"Expected a non-negative integer for {label} at data row {row_number}: {value!r}")
    return int(parsed)


def candidate_neighborhood(row: dict[str, str]) -> str:
    return row.get("Mahalle_Name_Turkish") or row.get("Mahalle_Name_English") or ""


def optional_value(row: dict[str, str], *names: str) -> str:
    for name in names:
        value = row.get(name)
        if value is not None and value != "":
            return value
    return ""


def write_csv_atomic(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary_path = Path(handle.name)
            writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
            writer.writeheader()
            writer.writerows(rows)
        temporary_path.replace(path)
    except Exception:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
        raise


def main() -> None:
    candidate_fields, candidates = read_csv(CANDIDATE_CSV)
    locker_fields, lockers = read_csv(LOCKER_CSV)
    require_columns(candidate_fields, REQUIRED_CANDIDATE_COLUMNS, CANDIDATE_CSV)
    require_columns(locker_fields, REQUIRED_LOCKER_COLUMNS, LOCKER_CSV)

    if not candidates:
        raise ValueError("Candidate CSV contains no data rows.")
    if not lockers:
        raise ValueError("Existing-locker CSV contains no data rows.")

    candidate_ids = [row["id"] for row in candidates]
    if any(not candidate_id for candidate_id in candidate_ids):
        raise ValueError("Candidate IDs must not be blank.")
    duplicate_ids = sorted(candidate_id for candidate_id, count in Counter(candidate_ids).items() if count > 1)
    if duplicate_ids:
        raise ValueError(f"Candidate IDs must be unique; duplicates: {', '.join(duplicate_ids[:10])}")

    renamed_locker_count = False
    if "locker_count" in candidate_fields and "nearby_locker_count" not in candidate_fields:
        locker_count_index = candidate_fields.index("locker_count")
        candidate_fields[locker_count_index] = "nearby_locker_count"
        for row in candidates:
            row["nearby_locker_count"] = row.pop("locker_count", "")
        renamed_locker_count = True
        column_note = "locker_count alanı nearby_locker_count olarak yeniden adlandırıldı."
    elif "locker_count" in candidate_fields and "nearby_locker_count" in candidate_fields:
        column_note = (
            "locker_count ve nearby_locker_count birlikte bulundu; mevcut nearby_locker_count korundu "
            "ve locker_count değiştirilmedi."
        )
    elif "nearby_locker_count" in candidate_fields:
        column_note = "nearby_locker_count zaten mevcut olduğu için yeniden adlandırma gerekmedi."
    else:
        raise ValueError("Candidate CSV must contain locker_count or nearby_locker_count.")

    if "existing_locker_count" not in candidate_fields:
        nearby_index = candidate_fields.index("nearby_locker_count")
        candidate_fields.insert(nearby_index + 1, "existing_locker_count")

    centers: list[tuple[float, float]] = []
    for row_number, row in enumerate(candidates, start=2):
        left = finite_float(row.get("left"), "candidate left", row_number)
        right = finite_float(row.get("right"), "candidate right", row_number)
        top = finite_float(row.get("top"), "candidate top", row_number)
        bottom = finite_float(row.get("bottom"), "candidate bottom", row_number)
        centers.append(((left + right) / 2.0, (top + bottom) / 2.0))
        row["existing_locker_count"] = 0

    snap_rows: list[dict[str, object]] = []
    snapped_candidate_indexes: list[int] = []
    snap_distances: list[float] = []

    for source_position, locker in enumerate(lockers):
        row_number = source_position + 2
        locker_x = finite_float(locker.get("x_32635"), "locker x_32635", row_number)
        locker_y = finite_float(locker.get("y_32635"), "locker y_32635", row_number)

        nearest_index = min(
            range(len(centers)),
            key=lambda index: (centers[index][0] - locker_x) ** 2 + (centers[index][1] - locker_y) ** 2,
        )
        center_x, center_y = centers[nearest_index]
        distance_m = math.hypot(locker_x - center_x, locker_y - center_y)
        candidate = candidates[nearest_index]
        candidate["existing_locker_count"] = int(candidate["existing_locker_count"]) + 1
        snapped_candidate_indexes.append(nearest_index)
        snap_distances.append(distance_m)

        snap_rows.append(
            {
                "locker_source_index": optional_value(locker, "locker_source_index") or source_position,
                "locker_name": optional_value(locker, "name"),
                "locker_code": optional_value(locker, "code"),
                "locker_source": optional_value(locker, "source_file", "source"),
                "locker_address": optional_value(locker, "address"),
                "source_x_32635": f"{locker_x:.6f}",
                "source_y_32635": f"{locker_y:.6f}",
                "source_lat": optional_value(locker, "lat"),
                "source_lon": optional_value(locker, "lon"),
                "candidate_id": candidate["id"],
                "candidate_center_x_32635": f"{center_x:.6f}",
                "candidate_center_y_32635": f"{center_y:.6f}",
                "candidate_lat": candidate.get("lat", ""),
                "candidate_lon": candidate.get("lon", ""),
                "snap_distance_m": f"{distance_m:.6f}",
                "candidate_neighborhood": candidate_neighborhood(candidate),
            }
        )

    timestamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)
    backup_path = ARCHIVE_DIR / f"candidate_points_before_existing_locker_mapping_{timestamp}.csv"
    if backup_path.exists():
        raise FileExistsError(f"Backup path already exists: {backup_path}")
    shutil.copy2(CANDIDATE_CSV, backup_path)

    write_csv_atomic(CANDIDATE_CSV, candidate_fields, candidates)
    write_csv_atomic(SNAP_AUDIT_CSV, AUDIT_COLUMNS, snap_rows)

    snapped_counts = Counter(snapped_candidate_indexes)
    unique_candidate_count = len(snapped_counts)
    source_locker_count = len(lockers)
    duplicate_snap_count = source_locker_count - unique_candidate_count
    max_existing_count = max(snapped_counts.values(), default=0)
    max_snap_distance = max(snap_distances, default=0.0)
    mean_snap_distance = fmean(snap_distances) if snap_distances else 0.0

    summary = {
        "source_locker_count": source_locker_count,
        "unique_candidate_count": unique_candidate_count,
        "duplicate_snap_count": duplicate_snap_count,
        "max_existing_locker_count_on_single_candidate": max_existing_count,
        "max_snap_distance_m": round(max_snap_distance, 6),
        "mean_snap_distance_m": round(mean_snap_distance, 6),
        "candidate_csv_updated": True,
        "renamed_locker_count_to_nearby_locker_count": renamed_locker_count,
        "source_file": relative_path(LOCKER_CSV),
        "mapping_crs": "EPSG:32635",
    }
    SUMMARY_JSON.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    duplicate_description = (
        f"Evet. Aynı candidate noktasına ek olarak snap edilen locker sayısı: {duplicate_snap_count}."
        if duplicate_snap_count
        else "Hayır. Her fiziksel locker farklı bir candidate noktasına snap edildi."
    )
    report = f"""# Mevcut Locker Mapping Raporu

## Alanların anlamı

- `nearby_locker_count`: Candidate noktasının 300 metre etki/buffer alanındaki locker sayısıdır. Fiziksel locker konumu değildir.
- `existing_locker_count`: Fiziksel mevcut dolabın snap edilerek map edildiği gerçek candidate noktasındaki locker sayısıdır.

## Mapping yöntemi

Mapping, `EPSG:32635` metre koordinatlarıyla yapıldı. Candidate merkezi `(left + right) / 2`, `(top + bottom) / 2` formülüyle hesaplandı ve her fiziksel locker Öklid mesafesine göre en yakın candidate merkezine snap edildi.

## Sonuçlar

- Fiziksel locker sayısı: **{source_locker_count}**
- Snap edilen unique candidate sayısı: **{unique_candidate_count}**
- Duplicate snap: **{duplicate_description}**
- Tek candidate üzerindeki maksimum fiziksel locker sayısı: **{max_existing_count}**
- Maksimum snap mesafesi: **{max_snap_distance:.6f} m**
- Ortalama snap mesafesi: **{mean_snap_distance:.6f} m**
- Kolon işlemi: {column_note}

## Güncellenen ve üretilen dosyalar

- Güncellendi: `{relative_path(CANDIDATE_CSV)}`
- Yedek: `{relative_path(backup_path)}`
- Locker bazlı audit: `{relative_path(SNAP_AUDIT_CSV)}`
- Özet: `{relative_path(SUMMARY_JSON)}`
- Bu rapor: `{relative_path(REPORT_MD)}`
"""
    REPORT_MD.write_text(report, encoding="utf-8")

    nearby_values = [
        integer_count(row.get("nearby_locker_count"), "nearby_locker_count", row_number)
        for row_number, row in enumerate(candidates, start=2)
    ]
    existing_values = [int(row["existing_locker_count"]) for row in candidates]

    print(f"Total candidate rows: {len(candidates)}")
    print(f"Sum of nearby_locker_count: {sum(nearby_values)}")
    print(f"Rows with nearby_locker_count > 0: {sum(value > 0 for value in nearby_values)}")
    print(f"Sum of existing_locker_count: {sum(existing_values)}")
    print(f"Rows with existing_locker_count > 0: {sum(value > 0 for value in existing_values)}")
    print(f"Max existing_locker_count: {max(existing_values, default=0)}")
    print(f"Max snap distance (m): {max_snap_distance:.6f}")
    print(f"Mean snap distance (m): {mean_snap_distance:.6f}")
    print(f"Backup path: {relative_path(backup_path)}")
    print(f"Snap audit path: {relative_path(SNAP_AUDIT_CSV)}")
    print(f"Summary path: {relative_path(SUMMARY_JSON)}")
    print(f"Report path: {relative_path(REPORT_MD)}")


if __name__ == "__main__":
    main()
