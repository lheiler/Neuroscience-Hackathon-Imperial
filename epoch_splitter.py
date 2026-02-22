import pandas as pd
import numpy as np

DIRECTION_MAP = {1: 'up', 2: 'down', 3: 'left', 4: 'right'}
EEG_COLS = list(range(1, 9))   # columns 1–8 (Ch01–Ch08)
TRIG_COL = 9                    # column 9 (Ch09)

def split_epochs(csv_path):
    df = pd.read_csv(csv_path, header=0)  # has header row
    
    trig = df.iloc[:, TRIG_COL].values
    eeg  = df.iloc[:, EEG_COLS].values

    # Find indices where a direction trigger fires
    trigger_idxs = [i for i, v in enumerate(trig) if v in DIRECTION_MAP]

    epochs = []
    for j, start_idx in enumerate(trigger_idxs):
        direction = DIRECTION_MAP[trig[start_idx]]
        
        # Epoch runs from this trigger to just before the next one
        if j + 1 < len(trigger_idxs):
            end_idx = trigger_idxs[j + 1]
        else:
            end_idx = len(trig)  # last epoch goes to end of file

        epoch = eeg[start_idx:end_idx].T  # → (8, n_samples)
        epochs.append({'direction': direction, 'eeg': epoch})

    return epochs