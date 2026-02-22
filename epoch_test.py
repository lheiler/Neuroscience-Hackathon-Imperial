import numpy as np
import pandas as pd
import os
import glob
from epoch_splitter import split_epochs

import numpy as np
from scipy.signal import resample

DIRECTION_MAP_INV = {'up': 0, 'down': 1, 'right': 2, 'left': 3}

# Match the dataset label mapping:
# 0=Up(Arriba), 1=Down(Abajo), 2=Right(Derecha), 3=Left(Izquierda)

SOURCE_SFREQ = 250   # Unicorn hardware rate
TARGET_SFREQ = 256   # model was trained at this rate
TARGET_SAMPLES = 641 # samples in a 0.5–3.0s window at 256Hz


def prepare_for_model(epochs: list) -> tuple:
    """
    Takes output of split_epochs() and returns (X, y) ready for the model.
    X shape: (n_epochs, n_channels, n_times)
    y shape: (n_epochs,)
    """
    X_list = []
    y_list = []

    for ep in epochs:
        eeg = ep['eeg']          # (8, n_samples) at 250Hz
        if eeg.shape[1] < TARGET_SAMPLES:
            print(f"Skipping short epoch: {ep['direction']} ({eeg.shape[1]} samples)")
        else:
            label = DIRECTION_MAP_INV[ep['direction']]

            # 1. Resample from 250Hz → 256Hz
            n_samples_resampled = int(eeg.shape[1] * TARGET_SFREQ / SOURCE_SFREQ)
            eeg_resampled = resample(eeg, n_samples_resampled, axis=1)

            # 2. Trim or pad to exactly TARGET_SAMPLES
            if eeg_resampled.shape[1] >= TARGET_SAMPLES:
                eeg_resampled = eeg_resampled[:, :TARGET_SAMPLES]
            else:
                # Pad with zeros if epoch is too short
                pad = TARGET_SAMPLES - eeg_resampled.shape[1]
                eeg_resampled = np.pad(eeg_resampled, ((0, 0), (0, pad)))

            X_list.append(eeg_resampled)
            y_list.append(label)

    X = np.stack(X_list, axis=0)   # (n_epochs, 8, 641)
    y = np.array(y_list)            # (n_epochs,)

    return X, y

def get_latest_csv(directory):
    files = glob.glob(os.path.join(directory, "*.csv"))
    return max(files, key=os.path.getctime)

script_dir = os.path.dirname(os.path.abspath(__file__))
recordings_dir = os.path.join(script_dir, "gPype_Example/UnicornHybridBlackExample/recordings")
csv_path = get_latest_csv(recordings_dir)

epochs = split_epochs(csv_path)

if __name__ == "__main__":
    epochs = split_epochs(csv_path)
    X, y = prepare_for_model(epochs)

    print(X.shape)  # (n_epochs, 8, 641)
    print(y)        # [0, 2, 3, 1, ...]