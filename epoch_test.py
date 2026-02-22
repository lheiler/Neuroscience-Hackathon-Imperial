import numpy as np
import pandas as pd
import os
import glob
from epoch_splitter import split_epochs


def get_latest_csv(directory):
    files = glob.glob(os.path.join(directory, "*.csv"))
    return max(files, key=os.path.getctime)

script_dir = os.path.dirname(os.path.abspath(__file__))
recordings_dir = os.path.join(script_dir, "gPype_Example/UnicornHybridBlackExample/recordings")
csv_path = get_latest_csv(recordings_dir)

epochs = split_epochs(csv_path)

if __name__ == "__main__":
    del epochs[0]
    epochs.pop()
    for ep in epochs:
        print(ep['direction'], ep['eeg'].shape)