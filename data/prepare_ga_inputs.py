#!/usr/bin/env python3
import argparse
from datetime import datetime

import numpy as np
import pandas as pd

EARTH_RADIUS_M = 6371000.0  # meters


def haversine_block(lat_rad, lon_rad, start, end):
    lat1 = lat_rad[start:end][:, None]
    lon1 = lon_rad[start:end][:, None]
    lat2 = lat_rad[None, :]
    lon2 = lon_rad[None, :]

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = np.sin(dlat / 2.0) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin(dlon / 2.0) ** 2
    c = 2.0 * np.arctan2(np.sqrt(a), np.sqrt(1.0 - a))
    return (EARTH_RADIUS_M * c).astype(np.float32)


def main():
    parser = argparse.ArgumentParser(description="Build NxN distance matrix (meters) from candidate lon/lat.")
    parser.add_argument("--input_csv", required=True, help="Candidate CSV exported from QGIS.")
    parser.add_argument("--out_prefix", required=True, help="Prefix for output artifacts.")
    parser.add_argument("--id_col", default="id", help="Unique candidate id column.")
    parser.add_argument("--lon_col", default="lon", help="Longitude column (EPSG:4326).")
    parser.add_argument("--lat_col", default="lat", help="Latitude column (EPSG:4326).")
    parser.add_argument("--filter_forbidden", action="store_true",
                        help="If set, keep only rows with is_forbidden == 0 (requires column).")
    parser.add_argument("--block_size", type=int, default=256, help="Block size for matrix computation.")
    args = parser.parse_args()

    df = pd.read_csv(args.input_csv)

    # validate required columns
    required = [args.id_col, args.lon_col, args.lat_col]
    missing = [c for c in required if c not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}\nFound: {list(df.columns)}")

    # optional forbidden filtering (just in case)
    if args.filter_forbidden:
        if "is_forbidden" in df.columns:
            df = df[df["is_forbidden"] == 0].copy()
        else:
            raise ValueError("--filter_forbidden used but 'is_forbidden' column not found in CSV.")

    # NA checks
    if df[args.id_col].isna().any():
        raise ValueError("Found NA in id column.")
    if df[[args.lon_col, args.lat_col]].isna().any().any():
        raise ValueError("Found NA in lon/lat columns.")

    # unique IDs
    if not df[args.id_col].is_unique:
        dup = df[df[args.id_col].duplicated(keep=False)][args.id_col].astype(str).unique()[:20]
        raise ValueError(f"ID column is not unique. Example duplicates: {dup}")

    # deterministic ordering by id (stable)
    df = df.sort_values(by=args.id_col, kind="mergesort").reset_index(drop=True)

    ids = df[args.id_col].to_numpy()
    lon = df[args.lon_col].astype(float).to_numpy()
    lat = df[args.lat_col].astype(float).to_numpy()

    lon_rad = np.radians(lon).astype(np.float64)
    lat_rad = np.radians(lat).astype(np.float64)

    n = len(df)
    dist = np.empty((n, n), dtype=np.float32)

    bs = max(1, args.block_size)
    for start in range(0, n, bs):
        end = min(n, start + bs)
        dist[start:end, :] = haversine_block(lat_rad, lon_rad, start, end)

    prefix = args.out_prefix

    # clearer naming
    out_dist = f"{prefix}_distance_meters_nxn.npy"
    out_ids = f"{prefix}_candidate_ids_sorted.npy"
    out_index = f"{prefix}_index_map.csv"
    out_info = f"{prefix}_ARTIFACTS_GUIDE.md"

    # save artifacts
    np.save(out_dist, dist)
    np.save(out_ids, ids)

    idx_df = pd.DataFrame(
        {"idx": np.arange(n, dtype=np.int32), "id": ids, "lon": lon, "lat": lat}
    )
    idx_df.to_csv(out_index, index=False)

    # write guide (Markdown, minimal stars)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    size_mb = dist.nbytes / (1024 * 1024)

    with open(out_info, "w", encoding="utf-8") as f:
        f.write("GA Input Artifacts Guide\n")
        f.write("========================\n\n")
        f.write(f"Generated: {now}\n")
        f.write(f"Source CSV: {args.input_csv}\n")
        f.write(f"Candidate order: sorted by {args.id_col} ascending\n\n")

        f.write("What this script generates\n")
        f.write("--------------------------\n\n")

        f.write(f"1) Distance matrix (meters): {out_dist}\n")
        f.write("   - Stores: dist[i, j] = distance between candidate idx i and idx j (meters).\n")
        f.write("   - Why: fast fitness calculations (coverage / overlap / dispersion).\n\n")

        f.write(f"2) Candidate ID list (same order): {out_ids}\n")
        f.write("   - Stores: ids[idx] = stable candidate ID.\n")
        f.write("   - Why: map GA internal indices back to stable IDs.\n\n")

        f.write(f"3) Index map (human-readable): {out_index}\n")
        f.write("   - Columns: idx, id, lon, lat\n")
        f.write("   - Why: pin GA results on the map and debug easily.\n\n")

        f.write("Demand (important)\n")
        f.write("------------------\n\n")
        f.write("- This script does NOT export demand.\n")
        f.write("- Use demand directly from the candidate CSV (e.g., weighted_population).\n\n")

        f.write("How to use in GA (quick)\n")
        f.write("------------------------\n\n")
        f.write("Python example:\n\n")
        f.write("    import numpy as np, pandas as pd\n")
        f.write(f"    dist = np.load('{out_dist}')\n")
        f.write(f"    ids  = np.load('{out_ids}')\n")
        f.write(f"    idx_map = pd.read_csv('{out_index}')  # optional for lon/lat\n\n")
        f.write("    # If GA returns idx list:\n")
        f.write("    # chosen_ids = ids[idx_list]\n")
        f.write("    # chosen_coords = idx_map[idx_map['idx'].isin(idx_list)][['lon','lat']]\n\n")

        f.write("Forbidden filtering\n")
        f.write("-------------------\n\n")
        if args.filter_forbidden:
            f.write("Applied: kept only rows where is_forbidden == 0.\n\n")
        else:
            f.write("Applied: none (assumes your CSV is already clean).\n\n")

        f.write("Sanity\n")
        f.write("------\n\n")
        f.write(f"N candidates: {n}\n")
        f.write(f"Distance matrix size: ~{size_mb:.1f} MB (float32)\n")
        f.write("If memory becomes a problem later: switch to k-NN / sparse distances.\n")

    print("DONE")
    print(f"Index map : {out_index}")
    print(f"IDs      : {out_ids}")
    print(f"Dist NxN : {out_dist} (meters, float32)")
    print(f"Info     : {out_info}")


if __name__ == "__main__":
    main()