import csv
import json
import os
from pathlib import Path

# Paths
SCRIPTS_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", SCRIPTS_DIR.parents[2])).resolve()
UI_ROOT = Path(os.environ.get("UI_ROOT", SCRIPTS_DIR.parents[1])).resolve()


def resolve_project_path(value):
    path = Path(value)
    if path.is_absolute():
        return path.resolve()
    return (PROJECT_ROOT / path).resolve()


CANDIDATE_CSV = resolve_project_path(os.environ.get("GA_CANDIDATE_CSV", "data/candidate_points.csv"))
OUTPUT_DIR = resolve_project_path(os.environ.get("GA_OUTPUT_DIR", "output"))
UI_MOCK_DIR = resolve_project_path(
    os.environ.get("UI_MOCK_DIR", "parcel-locker-ui/public/mock")
)
FINAL_ARCHIVE_CSV = OUTPUT_DIR / "final_archive.csv"

CANDIDATE_JSON_DST = UI_MOCK_DIR / "candidate-points.json"
GA_RESULTS_JSON_DST = UI_MOCK_DIR / "ga-results.json"

def process_candidates():
    candidates = {}
    rows_for_json = []
    
    with CANDIDATE_CSV.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            # Clean keys (handle BOM and spaces)
            row = {k.strip().lstrip("\ufeff"): v for k, v in row.items()}
            
            c_id = str(row["id"])
            lat = float(row["lat"])
            lng = float(row["lon"])
            neighborhood = row.get("Mahalle_Name_Turkish", row.get("Mahalle_Name_English", ""))
            
            candidate_data = {
                "id": c_id,
                "lat": lat,
                "lng": lng,
                "neighborhood": neighborhood,
                "population": int(float(row.get("population_candidate") or 0)),
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
            }
            
            candidates[c_id] = candidate_data
            rows_for_json.append(candidate_data)
            
    CANDIDATE_JSON_DST.parent.mkdir(parents=True, exist_ok=True)
    with CANDIDATE_JSON_DST.open("w", encoding="utf-8") as f:
        json.dump(rows_for_json, f, ensure_ascii=False, indent=2)
        
    print(f"Processed {len(rows_for_json)} candidate points.")
    return candidates

def is_non_dominated(current_metrics, all_results):
    """
    Returns True if current_metrics is not dominated by any solution in all_results.
    Assumes minimization for both accessibility (f1) and equity (f2).
    """
    f1_i = current_metrics["accessibility"]
    f2_i = current_metrics["equity"]
    
    for other in all_results:
        f1_j = other["metrics"]["accessibility"]
        f2_j = other["metrics"]["equity"]
        
        # j dominates i if (f1_j <= f1_i and f2_j <= f2_i) and (f1_j < f1_i or f2_j < f2_i)
        if (f1_j <= f1_i and f2_j <= f2_i) and (f1_j < f1_i or f2_j < f2_i):
            return False
    return True

def process_ga_results(candidates_map):
    raw_results = []
    
    if not FINAL_ARCHIVE_CSV.exists():
        print(f"Warning: {FINAL_ARCHIVE_CSV} not found. Skipping GA results.")
        return

    with FINAL_ARCHIVE_CSV.open("r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            row = {k.strip().lstrip("\ufeff"): v for k, v in row.items()}
            
            archive_index = int(row["archive_index"])
            chromosome = row["chromosome"].split("|")
            
            lockers = []
            for c_id in chromosome:
                if c_id in candidates_map:
                    c = candidates_map[c_id]
                    lockers.append({
                        "id": c["id"],
                        "lat": c["lat"],
                        "lng": c["lng"],
                        "neighborhood": c["neighborhood"],
                        "score": 0,
                        "source": "elite"
                    })

            raw_results.append({
                "id": archive_index,
                "lockers": lockers,
                "metrics": {
                    "accessibility": float(row["f1"]),
                    "equity": float(row["f2"]),
                    "fitness": float(row.get("total_fitness", 0)),
                    "norm_f1": float(row.get("norm_f1", 0)),
                    "norm_f2": float(row.get("norm_f2", 0))
                }
            })

    # Calculate actual Pareto status
    for res in raw_results:
        res["isPareto"] = is_non_dominated(res["metrics"], raw_results)
    
    # Identify best solutions among Pareto front
    pareto_solutions = [r for r in raw_results if r["isPareto"]]
    if pareto_solutions:
        best_f1 = min(pareto_solutions, key=lambda x: x["metrics"]["accessibility"])
        best_f2 = min(pareto_solutions, key=lambda x: x["metrics"]["equity"])
        
        for res in raw_results:
            res["isBestF1"] = (res["id"] == best_f1["id"])
            res["isBestF2"] = (res["id"] == best_f2["id"])
    else:
        for res in raw_results:
            res["isBestF1"] = False
            res["isBestF2"] = False
            
    GA_RESULTS_JSON_DST.parent.mkdir(parents=True, exist_ok=True)
    with GA_RESULTS_JSON_DST.open("w", encoding="utf-8") as f:
        json.dump(raw_results, f, ensure_ascii=False, indent=2)
        
    pareto_count = len(pareto_solutions)
    print(f"Processed {len(raw_results)} archive solutions. Found {pareto_count} Pareto optimal solutions.")

if __name__ == "__main__":
    candidates = process_candidates()
    process_ga_results(candidates)
