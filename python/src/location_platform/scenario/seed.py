"""Generate a default current-network scenario from V0 `existing_locker_count` data.

This is the one place in ``location_platform`` that is *supposed* to read
``existing_locker_count`` directly from the candidate CSV — it is the V0
seed generator itself. ``nearby_locker_count`` and legacy ``locker_count``
are never read here or anywhere else in this module.

Does not own:

- scenario schema validation (``location_platform.scenario.validation``) —
  this module does not self-check its own output against the schema; a
  generated scenario should still be validated separately, exactly as today.
- optimizer-input derivation (``location_platform.scenario.optimizer_inputs``,
  later batch)
- CLI parsing, printing, or exit codes (the thin wrapper script)
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from location_platform.common.parsing import parse_float, parse_int
from location_platform.common.paths import display_path
from location_platform.data.candidates import load_candidate_rows

REQUIRED_COLUMNS = ("id", "lat", "lon", "existing_locker_count")
NEIGHBORHOOD_COLUMNS = ("Mahalle_Name_Turkish", "Mahalle_Name_English")


def load_existing_facility_seed_rows(candidate_csv: Path) -> list[dict[str, Any]]:
    """Load candidate rows and select the `existing_locker_count > 0` seed subset.

    Returns rows sorted by candidate ID ascending. Never reads
    ``nearby_locker_count`` or legacy ``locker_count``. Raises
    ``FileNotFoundError``/``ValueError`` (missing columns, invalid values,
    or no qualifying rows) exactly as the previous script-only
    implementation did.
    """
    rows = load_candidate_rows(candidate_csv, required_columns=REQUIRED_COLUMNS)

    selected_rows: list[dict[str, Any]] = []
    for row_number, row in enumerate(rows, start=2):
        candidate_id = parse_int(row["id"], f"Row {row_number}: `id`")
        lat = parse_float(row["lat"], f"Row {row_number}: `lat`")
        lon = parse_float(row["lon"], f"Row {row_number}: `lon`")
        existing_locker_count = parse_int(
            row["existing_locker_count"], f"Row {row_number}: `existing_locker_count`"
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


def build_facility_from_seed_row(index: int, row: dict[str, Any]) -> dict[str, Any]:
    """Build one `existing`-kind V1 scenario facility dict from a seed row."""
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


def build_current_network_scenario(candidate_csv: Path, facility_rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Build the full V1 current-network scenario dict from seed rows."""
    facilities = [
        build_facility_from_seed_row(index, row)
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


def generate_current_network_scenario(candidate_csv: Path) -> dict[str, Any]:
    """Load seed rows and build the current-network scenario in one call."""
    facility_rows = load_existing_facility_seed_rows(candidate_csv)
    return build_current_network_scenario(candidate_csv, facility_rows)


def write_scenario_json(output_path: Path, scenario: dict[str, Any]) -> None:
    """Write a scenario dict to disk with a trailing newline, creating parent dirs."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(scenario, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
