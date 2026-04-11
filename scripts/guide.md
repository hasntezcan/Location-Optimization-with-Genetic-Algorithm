# Scripts Guide: Data Pipeline

This folder contains Python scripts to process urban data before running the Java optimization.

## 📂 Data Flow
1. **Input:** `data/candidate_points.csv` (Raw population & POI data)
2. **Output:** `data/candidate_points_enriched.csv` (Processed data with final demand scores)

---

## 🐍 Script Functions

### 1. `prepare_demand.py` (Main Pipeline)
Calculates the final importance (demand) for each candidate location.
- **POI Weighting:** Uses the **Entropy Weight Method (EWM)** to objectively decide which POIs (University, Transport, etc.) are more important based on their distribution.
- **Interactive λ (Lambda):** Prompts the user to set the POI influence (0.0 to 1.0).
- **Output Columns:** Adds `poi_score` and `demand_final` to the new CSV.

### 2. `calculate_poi_weights.py` (Analysis)
Shows the percentage importance of each POI category. Used to verify the EWM results.

---

## 🧮 Calculation Logic

The final demand used by the Genetic Algorithm is calculated as:
**`demand_final = population_candidate * (1 + lambda * poi_score)`**

- **Lambda = 0.5 (Balanced):** Recommended for general scenarios.
- **Lambda = 1.0 (Aggressive):** High priority for urban activity hubs.

---

## 🚀 Usage
Run the pipeline from the project root:
```bash
python3 scripts/prepare_demand.py