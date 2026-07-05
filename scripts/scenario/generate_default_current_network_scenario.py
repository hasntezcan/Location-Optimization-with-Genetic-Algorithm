"""Generate the default Kadikoy current-network scenario from V0 data."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any


DEFAULT_CANDIDATE_CSV = Path("data/candidate_points.csv")
DEFAULT_OUTPUT = Path("data/scenarios/kadikoy_parcel_locker_current_network.json")
REQUIRED_COLUMNS = ("id", "lat", "lon", "existing_locker_count")
NEIGHBORHOOD_COLUMNS = ("Mahalle_Name_Turkish", "Mahalle_Name_English")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a V1 current-network scenario JSON from "
            "data/candidate_points.csv existing_locker_count values."
        )
    )
    parser.add_argument(
        "--candidate-csv",
        default=str(DEFAULT_CANDIDATE_CSV),
        help="Candidate CSV to read. Defaults to data/candidate_points.csv.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT),
        help=(
            "Scenario JSON output path. Defaults to "
            "data/scenarios/kadikoy_parcel_locker_current_network.json."
        ),
    )
    return parser.parse_args()


def display_path(path: Path) -> str:
    return path.as_posix()


def parse_int(value: str, field: str, row_number: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Row {row_number}: `{field}` must be an integer, got {value!r}.") from exc


def parse_float(value: str, field: str, row_number: int) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Row {row_number}: `{field}` must be a float, got {value!r}.") from exc


def load_existing_facility_rows(candidate_csv: Path) -> list[dict[str, Any]]:
    if not candidate_csv.exists():
        raise FileNotFoundError(f"Candidate CSV does not exist: {display_path(candidate_csv)}")

    with candidate_csv.open("r", encoding="utf-8", newline="") as csv_file:
        reader = csv.DictReader(csv_file)
        fieldnames = reader.fieldnames or []
        missing_columns = [column for column in REQUIRED_COLUMNS if column not in fieldnames]
        if missing_columns:
            missing = ", ".join(missing_columns)
            raise ValueError(f"Candidate CSV is missing required columns: {missing}")

        selected_rows: list[dict[str, Any]] = []
        for row_number, row in enumerate(reader, start=2):
            candidate_id = parse_int(row["id"], "id", row_number)
            lat = parse_float(row["lat"], "lat", row_number)
            lon = parse_float(row["lon"], "lon", row_number)
            existing_locker_count = parse_int(
                row["existing_locker_count"],
                "existing_locker_count",
                row_number,
            )

            if existing_locker_count > 0:
                selected_rows.append(
                    {
                        "candidateId": candidate_id,
                        "lat": lat,
                        "lon": lon,
                        "physicalCount": existing_locker_count,
                        "neighborhoodTurkish": row.get("Mahalle_Name_Turkish", ""),
                        "neighborhoodEnglish": row.get("Mahalle_Name_English", ""),
                    }
                )

    if not selected_rows:
        raise ValueError("No rows found with existing_locker_count > 0.")

    selected_rows.sort(key=lambda item: item["candidateId"])
    return selected_rows


def build_facility(index: int, row: dict[str, Any]) -> dict[str, Any]:
    facility_number = f"{index:04d}"
    metadata: dict[str, Any] = {
        "physicalCount": row["physicalCount"],
        "sourceColumn": "existing_locker_count",
    }

    if row.get("neighborhoodTurkish"):
        metadata["neighborhoodTurkish"] = row["neighborhoodTurkish"]
    if row.get("neighborhoodEnglish"):
        metadata["neighborhoodEnglish"] = row["neighborhoodEnglish"]

    return {
        "id": f"existing-{facility_number}",
        "kind": "existing",
        "status": "enabled",
        "facilityType": "parcel_locker",
        "label": f"Existing parcel locker {facility_number}",
        "source": "seed_from_v0_data",
        "coordinates": {
            "lat": row["lat"],
            "lon": row["lon"],
            "crs": "EPSG:4326",
        },
        "snap": {
            "candidateId": row["candidateId"],
            "snapDistanceMeters": 0,
            "snapMethod": "seed_from_existing_locker_count",
            "snapStatus": "snapped",
        },
        "metadata": metadata,
    }


def build_scenario(candidate_csv: Path, facility_rows: list[dict[str, Any]]) -> dict[str, Any]:
    facilities = [
        build_facility(index, row)
        for index, row in enumerate(facility_rows, start=1)
    ]
    physical_facility_count = sum(row["physicalCount"] for row in facility_rows)

    return {
        "schemaVersion": "v1",
        "scenarioId": "kadikoy-parcel-locker-current-network",
        "name": "Kadikoy Parcel Locker Current Network",
        "description": "Default current-network scenario seeded from V0 existing_locker_count.",
        "useCase": "parcel_locker",
        "grid": {
            "candidateSource": display_path(candidate_csv),
            "distanceMatrixSource": "data/kadikoy_distance_meters_nxn.npy",
            "candidateIdOrder": "ascending",
            "crs": {
                "display": "EPSG:4326",
                "metric": "EPSG:32635",
            },
        },
        "settings": {
            "runType": "current_network",
            "includeExistingFacilities": True,
            "targetNewFacilityCount": 0,
            "targetTotalFacilityCount": None,
            "objectiveBundle": "parcel_locker_current_baseline",
        },
        "facilities": facilities,
        "constraints": {
            "lockedCandidateIds": [],
            "disabledCandidateIds": [],
        },
        "benchmark": {
            "demandType": "proxy",
            "coverageThresholdMeters": 500,
        },
        "metadata": {
            "createdBy": "script",
            "source": "existing_locker_count",
            "sourceCandidateCsv": display_path(candidate_csv),
            "effectiveFacilityLocationCount": len(facilities),
            "physicalFacilityCount": physical_facility_count,
            "notes": [
                "One scenario facility is created per candidate with existing_locker_count > 0.",
                "physicalCount preserves cases where multiple physical facilities map to one candidate.",
                "nearby_locker_count is not used.",
            ],
        },
    }


def write_scenario(output_path: Path, scenario: dict[str, Any]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(scenario, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def main() -> None:
    args = parse_args()
    candidate_csv = Path(args.candidate_csv)
    output_path = Path(args.output)

    facility_rows = load_existing_facility_rows(candidate_csv)
    scenario = build_scenario(candidate_csv, facility_rows)
    write_scenario(output_path, scenario)

    print("Generated default current-network scenario:")
    print(f"  output: {display_path(output_path)}")
    print(f"  effective facility locations: {scenario['metadata']['effectiveFacilityLocationCount']}")
    print(f"  physical facilities: {scenario['metadata']['physicalFacilityCount']}")
    print(f"  source: {display_path(candidate_csv)}")


if __name__ == "__main__":
    main()
