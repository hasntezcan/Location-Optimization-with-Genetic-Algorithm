GA Input Artifacts Guide
========================

Generated: 2026-04-07 15:27:17
Source CSV: candidate_points.csv
Candidate order: sorted by id ascending

What this script generates
--------------------------

1) Distance matrix (meters): kadikoy_distance_meters_nxn.npy
   - Stores: dist[i, j] = distance between candidate idx i and idx j (meters).
   - Why: fast fitness calculations (coverage / overlap / dispersion).

2) Candidate ID list (same order): kadikoy_candidate_ids_sorted.npy
   - Stores: ids[idx] = stable candidate ID.
   - Why: map GA internal indices back to stable IDs.

3) Index map (human-readable): kadikoy_index_map.csv
   - Columns: idx, id, lon, lat
   - Why: pin GA results on the map and debug easily.

Demand (important)
------------------

- This script does NOT export demand.
- Use demand directly from the candidate CSV (e.g., weighted_population).

How to use in GA (quick)
------------------------

Python example:

    import numpy as np, pandas as pd
    dist = np.load('kadikoy_distance_meters_nxn.npy')
    ids  = np.load('kadikoy_candidate_ids_sorted.npy')
    idx_map = pd.read_csv('kadikoy_index_map.csv')  # optional for lon/lat

    # If GA returns idx list:
    # chosen_ids = ids[idx_list]
    # chosen_coords = idx_map[idx_map['idx'].isin(idx_list)][['lon','lat']]

Forbidden filtering
-------------------

Applied: none (assumes your CSV is already clean).

Sanity
------

N candidates: 2717
Distance matrix size: ~28.2 MB (float32)
If memory becomes a problem later: switch to k-NN / sparse distances.
