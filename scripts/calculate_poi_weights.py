import pandas as pd
import numpy as np

def calculate_poi_weights(csv_path, poi_prefix='poi_'):
    """
    Calculates objective weights of POI categories from the candidate points CSV file
    using the Entropy Weight Method (EWM).
    
    Parameters:
    - csv_path: Path to the candidate_points.csv file
    - poi_prefix: Prefix used to identify POI columns
    
    Returns:
    - A dictionary containing the calculated weights for each POI category
    """
    # 1. Load data and filter POI columns
    df = pd.read_csv(csv_path)
    poi_cols = [col for col in df.columns if col.startswith(poi_prefix)]
    
    if not poi_cols:
        raise ValueError(f"No columns found starting with prefix '{poi_prefix}'. Please check the data.")
        
    # Extract only POI data and fill possible NaN values with 0
    poi_data = df[poi_cols].fillna(0)
    n = len(poi_data)
    
    # 2. Logarithmic Transformation and Min-Max Normalization
    # Use log1p (log(1+x)) to smooth out spiky (rare but heavily clustered) data
    log_x = np.log1p(poi_data)
    
    min_vals = log_x.min()
    max_vals = log_x.max()
    ranges = max_vals - min_vals
    ranges[ranges == 0] = 1.0  # Prevent division by zero for columns where all values are identical
    
    norm_x = (log_x - min_vals) / ranges
    
    # 3. Entropy Weight Method (EWM) Calculation
    # P_ij: Proportion of the normalized value within its own column
    col_sums = norm_x.sum()
    p = norm_x.divide(col_sums.replace(0, 1)) 
    
    # ln(P_ij): Logarithmic value (replacing 0s with 1s to avoid log(0) errors)
    ln_p = np.log(p.replace(0, 1))
    
    # E_j: Entropy value of each column
    k = 1.0 / np.log(n)
    entropy = -k * (p * ln_p).sum()
    
    # D_j: Divergence (Information Discriminability) -> D_j = 1 - E_j
    divergence = 1 - entropy
    divergence[col_sums == 0] = 0  # Columns containing absolutely no data should have a weight of 0
    
    # W_j: Final Weights (Ratio of divergence values to their total sum)
    weights = divergence / divergence.sum()
    
    # Convert the result to a readable dictionary and return
    weight_dict = weights.to_dict()
    
    return weight_dict

if __name__ == "__main__":
    # Test block
    INPUT_CSV = "data/candidate_points.csv"
    
    try:
        print("Calculating POI weights...\n")
        weights = calculate_poi_weights(INPUT_CSV)
        
        # Sort results in descending order and print
        sorted_weights = sorted(weights.items(), key=lambda item: item[1], reverse=True)
        
        for poi, weight in sorted_weights:
            print(f"{poi:<20}: {weight:.4f} ({weight*100:.2f}%)")
            
    except Exception as e:
        print(f"An error occurred: {e}")