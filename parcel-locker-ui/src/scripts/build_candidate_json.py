import csv
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

src = PROJECT_ROOT / "public" / "mock" / "candidate_points.csv"
dst = PROJECT_ROOT / "public" / "mock" / "candidate-points.json"
dst.parent.mkdir(parents=True, exist_ok=True)

rows = []

with src.open("r", encoding="utf-8-sig", newline="") as f:
    reader = csv.DictReader(f)

    if reader.fieldnames is None:
        raise ValueError("CSV header could not be read.")

    normalized_fieldnames = [fn.strip().lstrip("\ufeff") if fn else "" for fn in reader.fieldnames]
    reader.fieldnames = normalized_fieldnames

    for raw_row in reader:
        row = {
            (key.strip().lstrip("\ufeff") if key else ""): (value.strip() if isinstance(value, str) else value)
            for key, value in raw_row.items()
        }

        neighborhood = (
            row.get("name")
            or row.get("neighborhood")
            or row.get("MAH_JOIN")
            or ""
        ).strip()

        rows.append({
            "id": str(row["id"]),
            "lat": float(row["lat"]),
            "lng": float(row["lon"]),
            "neighborhood": neighborhood,
            "population": int(float(row.get("pop_2024") or 0)),
            "poiAtm": int(float(row.get("poi_atm") or 0)),
            "poiBank": int(float(row.get("poi_bank") or 0)),
            "poiHospital": int(float(row.get("poi_hospital") or 0)),
            "poiSchool": int(float(row.get("poi_school") or 0)),
            "poiUniversity": int(float(row.get("poi_university") or 0)),
            "poiPostOffice": int(float(row.get("poi_post_office") or 0)),
            "poiTransport": int(float(row.get("poi_transport") or 0)),
            "poiBusStop": int(float(row.get("poi_bus_stop") or 0)),
            "isForbidden": str(row.get("is_forbidden", "")).strip() == "1",
            "lockerCount": int(float(row.get("locker_count") or 0)),
        })

dst.write_text(json.dumps(rows, ensure_ascii=False), encoding="utf-8")
print(f"Wrote {len(rows)} rows to {dst}")