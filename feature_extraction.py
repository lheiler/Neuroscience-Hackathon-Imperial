import os
import numpy as np
import tsfel
import pandas as pd
from tqdm import tqdm

    
import concurrent.futures

import pywt

def compute_dwt_features(channel_data, wavelet='db4'):
    # Dynamically find safe level to prevent boundary warnings
    safe_level = pywt.dwt_max_level(len(channel_data), wavelet)
    coeffs = pywt.wavedec(channel_data, wavelet, level=safe_level)
    
    features = []
    for c in coeffs:
        energy = np.sum(np.square(c))
        std_dev = np.std(c)
        wav_len = np.sum(np.abs(np.diff(c)))
        mav = np.mean(np.abs(c))
        rms = np.sqrt(np.mean(np.square(c)))
        features.extend([energy, std_dev, wav_len, mav, rms])
    return features

def process_trial(args):
    import warnings
    i, trial_data = args
    cfg = tsfel.get_features_by_domain()
    
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        
        # --- 1. TSFEL Extraction ---
        trial_df = pd.DataFrame(trial_data.T)
        # 1. FIX: Set fs=256 to match the downsampled data
        trial_features = tsfel.time_series_features_extractor(cfg, trial_df, fs=256, verbose=0)
        tsfel_array = trial_features.values[0]
        
        # --- 2. DWT Extraction ---
        # 2. FIX: Actually extract the DWT features for all 128 channels
        dwt_features = []
        for ch_idx in range(trial_data.shape[0]):
            ch_data = trial_data[ch_idx, :]
            dwt_features.extend(compute_dwt_features(ch_data, wavelet='db4'))
            
        # Combine both feature sets into one massive array for MRMR
        final_features = np.concatenate([tsfel_array, dwt_features])
        
    return i, final_features

def extract_tsfel_features(X_raw):
    n_trials, n_channels, n_points = X_raw.shape
    
    print(f"Starting TSFEL Feature Extraction on {n_trials} trials using Multiprocessing...")
    
    # Pack arguments
    tasks = [(i, X_raw[i]) for i in range(n_trials)]
    results = []
    
    # Run in parallel
    with concurrent.futures.ProcessPoolExecutor() as executor:
        # Map tasks and wrap with tqdm for progress bar
        for res in tqdm(executor.map(process_trial, tasks), total=n_trials, desc="Extracting Trials"):
            results.append(res)
            
    # Sort results by the original index 'i' to ensure strict label alignment
    results.sort(key=lambda x: x[0])
    
    # Extract just the feature arrays
    all_features = [res[1] for res in results]
    
    X_features = np.vstack(all_features)
    print(f"\nCompleted Extraction. New Feature Matrix Shape: {X_features.shape}")
    
    return X_features


if __name__ == "__main__":
    data_dir = "processed_data"
    raw_path = os.path.join(data_dir, "X.npy")
    
    print("Loading VMD-cleaned raw EEG dataset...")
    X_raw = np.load(raw_path)
    
    print(f"Loaded Raw Dataset: {X_raw.shape} (Trials, Channels, Timepoints)")
    
    # Extract
    X_features = extract_tsfel_features(X_raw)
    
    # Save the massive Feature Matrix
    save_path = os.path.join(data_dir, "X_features.npy")
    np.save(save_path, X_features)
    print(f"Feature matrix saved successfully to {save_path}!")
