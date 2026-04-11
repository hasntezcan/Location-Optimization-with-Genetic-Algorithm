import pandas as pd
import numpy as np
import os

# --- CONFIGURATION ---
INPUT_FILE = "data/candidate_points.csv"
# Çıktı dosyasını giriş dosyasıyla aynı yaptık, böylece üzerine yazar.
OUTPUT_FILE = "data/candidate_points.csv" 
POI_PREFIX = "poi_"

# CSV'deki gerçek nüfus kolonu ismi
BASE_DEMAND_COL = "population_candidate" 

def get_lambda_value():
    """Prompts the user to input a Lambda value via terminal with explanation."""
    print("\n" + "="*55)
    print("LAMBDA (\u03BB) PARAMETER CONFIGURATION")
    print("="*55)
    print("Lambda (\u03BB) controls how much the POI Score (urban attractiveness)")
    print("influences the final demand. It acts as a multiplier on the base demand.")
    print("  - 0.0 : No POI influence (Demand = Population only)")
    print("  - 0.5 : Moderate POI influence (Balanced)")
    print("  - 1.0 : High POI influence (Aggressive)")
    print("Suggested range: 0.0 to 1.0")
    print("-" * 55)
    
    while True:
        user_input = input("\nPlease enter the Lambda value you want to use (e.g., 0.5): ")
        try:
            # Virgülü noktaya çevirerek hata payını azaltıyoruz
            lambda_val = float(user_input.replace(',', '.'))
            if lambda_val < 0:
                print("Warning: Lambda value cannot be negative. Please try again.")
                continue
            return lambda_val
        except ValueError:
            print("Error: Invalid input. Please enter a valid number (e.g., 0.5).")

def calculate_ewm_weights(df, poi_cols):
    """Calculates objective weights using the Entropy Weight Method (EWM)."""
    poi_data = df[poi_cols].fillna(0)
    n = len(poi_data)
    
    # Logarithmic Transformation & Min-Max Normalization
    log_x = np.log1p(poi_data)
    min_vals = log_x.min()
    max_vals = log_x.max()
    ranges = max_vals - min_vals
    ranges[ranges == 0] = 1.0 
    
    norm_x = (log_x - min_vals) / ranges
    
    # Entropy Calculation
    col_sums = norm_x.sum()
    p = norm_x.divide(col_sums.replace(0, 1)) 
    ln_p = np.log(p.replace(0, 1))
    
    k = 1.0 / np.log(n)
    entropy = -k * (p * ln_p).sum()
    
    # Weight Calculation
    divergence = 1 - entropy
    divergence[col_sums == 0] = 0
    weights = divergence / divergence.sum()
    
    return weights, norm_x

def main():
    print(f"Loading data from {INPUT_FILE}...")
    try:
        df = pd.read_csv(INPUT_FILE)
    except FileNotFoundError:
        print(f"ERROR: {INPUT_FILE} not found. Please check your current directory.")
        return

    # 1. Lambda değerini sor
    lambda_val = get_lambda_value()

    # 2. POI kolonlarını belirle
    poi_cols = [col for col in df.columns if col.startswith(POI_PREFIX)]
    if not poi_cols:
        print(f"ERROR: No columns with prefix '{POI_PREFIX}' found.")
        return

    # 3. EWM Ağırlıklarını hesapla
    print("\nCalculating Entropy Weights...")
    weights, norm_x = calculate_ewm_weights(df, poi_cols)

    # 4. POI Skoru oluştur (poi_score)
    print("Generating 'poi_score' column...")
    df['poi_score'] = (norm_x * weights).sum(axis=1)

    # 5. Nihai talebi hesapla (demand_final)
    if BASE_DEMAND_COL not in df.columns:
        print(f"ERROR: Base demand column '{BASE_DEMAND_COL}' not found in CSV.")
        return

    print(f"Updating 'demand_final' column (Lambda = {lambda_val})...")
    df['demand_final'] = df[BASE_DEMAND_COL] * (1 + (lambda_val * df['poi_score']))

    # Özet istatistikler
    print("\n--- Summary Statistics ---")
    print(f"Lambda Parameter:   {lambda_val}")
    print(f"Base Demand (Mean): {df[BASE_DEMAND_COL].mean():.2f}")
    print(f"POI Score (Mean):   {df['poi_score'].mean():.4f}")
    print(f"Final Demand (Mean):{df['demand_final'].mean():.2f}")

    # 6. Dosyanın üzerine yaz (Overwrite)
    df.to_csv(OUTPUT_FILE, index=False)
    print(f"\nSUCCESS: Original file {OUTPUT_FILE} has been updated with enriched data.")

if __name__ == "__main__":
    main()