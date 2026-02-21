import matplotlib.pyplot as plt
import numpy as np
import os

def plot_eeg_samples(data_dir="processed_data", num_samples=5, channel_to_plot=0):
    """
    Plots a few random samples of the cropped 2.5s EEG action interval.
    """
    x_path = os.path.join(data_dir, "X_inner.npy")
    y_path = os.path.join(data_dir, "y_inner.npy")
    
    if not os.path.exists(x_path):
        print(f"Error: Could not find {x_path}")
        return
        
    print(f"Loading data from {data_dir}...")
    X = np.load(x_path)
    y = np.load(y_path)
    
    # 1. Z-Score Normalize (Same as training)
    mean = np.mean(X, axis=2, keepdims=True)
    std = np.std(X, axis=2, keepdims=True)
    X = (X - mean) / (std + 1e-8)
    
    # 2. Crop to Action Interval (Same as training)
    start_idx = 384
    end_idx = 1024 
    X_cropped = X[:, :, start_idx:end_idx]
    
    # Label Mapping
    labels_map = {0: "Up", 1: "Down", 2: "Right", 3: "Left"}
    
    # Select random indices
    np.random.seed(42) # For reproducibility
    random_indices = np.random.choice(X_cropped.shape[0], num_samples, replace=False)
    
    # Time axis (640 samples at 256Hz = 2.5 seconds)
    # The action interval starts at exactly 1.0s and ends at 3.5s
    time = np.linspace(1.0, 3.5, X_cropped.shape[2]) 
    
    # Plot setup
    fig, axes = plt.subplots(num_samples, 1, figsize=(10, 2 * num_samples), sharex=True)
    fig.suptitle(f"EEG Signal Visualization (Channel {channel_to_plot})\nAction Interval: 1.0s to 3.5s", fontsize=16)
    
    for i, idx in enumerate(random_indices):
        signal = X_cropped[idx, channel_to_plot, :]
        label = labels_map[y[idx]]
        
        axes[i].plot(time, signal, color='b', linewidth=1)
        axes[i].set_title(f"Trial Index: {idx} | Class: {label}", fontsize=12)
        axes[i].set_ylabel("Amplitude (Z-score)")
        axes[i].grid(True, alpha=0.3)
        
    axes[-1].set_xlabel("Time (seconds)")
    plt.tight_layout()
    
    save_path = "eeg_visualization.png"
    plt.savefig(save_path, dpi=300)
    print(f"Plot successfully saved to {save_path}")

if __name__ == "__main__":
    plot_eeg_samples()
