import os
import sys
from pathlib import Path

# Add the Inner_Speech_Dataset libraries to path to use their excellent event correction logic
project_root = Path(__file__).resolve().parent.parent
lib_path = project_root / "Inner_Speech_Dataset" / "Python_Processing"
sys.path.append(str(lib_path))

import mne
import numpy as np
import pandas as pd

from lib.events_analysis import (
    event_correction,
    check_baseline_tags,
    add_condition_tag,
    standardize_labels,
)
from lib.data_extractions import get_events_from_raw, sub_name

def preprocess_inner_speech_data(data_dir: Path, save_dir: Path):
    """
    Preprocess the entire ds003626 dataset specifically for the Inner Speech condition
    and the 4-word classification task.
    """
    # Processing Variables
    N_Subj_arr = range(1, 11)  # 1 to 10
    N_block_arr = range(1, 4)  # 1 to 3
    
    # Filtering settings
    LOW_CUT = 0.5
    HIGH_CUT = 100
    NOTCH_FREQ = 50
    DS_RATE = 4  # Downsample rate to reduce memory footprint
    
    # Event IDs dict
    event_id = dict(Arriba=31, Abajo=32, Derecha=33, Izquierda=34)
    target_tags = [31, 32, 33, 34]
    
    # Lists to collect all epochs
    all_X = []
    all_y_words = []
    all_y_conditions = []
    all_subject_ids = []
    
    for n_s in N_Subj_arr:
        # Handle subject 3 ad-hoc modifications (session 2 was actually run with only 3 words due to time or error, etc.)
        # but to keep the script robust against those errors, we'll try/except the files
        num_s = sub_name(n_s)
        print(f"\nProcessing Subject: {num_s}")
        
        for n_b in N_block_arr:
            try:
                bdf_path = data_dir / f"{num_s}/ses-0{n_b}/eeg/{num_s}_ses-0{n_b}_task-innerspeech_eeg.bdf"
                if not bdf_path.exists():
                    print(f"Skipping {num_s} Session {n_b}: File not found.")
                    continue
                
                print(f"  Loading Session: {n_b} ...")
                # 1. Load data
                rawdata = mne.io.read_raw_bdf(input_fname=bdf_path, preload=True, verbose="WARNING")
                
                # 2. Re-reference to EXG1 and EXG2 (mastoids)
                rawdata.set_eeg_reference(ref_channels=["EXG1", "EXG2"], verbose="WARNING")
                
                # 3. Filtering
                print(f"    Applying Notch ({NOTCH_FREQ}Hz) and Bandpass ({LOW_CUT}-{HIGH_CUT}Hz) filters...")
                rawdata.notch_filter(freqs=NOTCH_FREQ, verbose="WARNING")
                rawdata.filter(LOW_CUT, HIGH_CUT, verbose="WARNING")
                
                # 4. Extract & Correct Events
                events = get_events_from_raw(rawdata, n_s, n_b)
                events = check_baseline_tags(events)
                events = event_correction(events=events)
                
                # Add condition tag (0: Pron, 1: Inner, 2: Vis)
                events = add_condition_tag(events)
                
                # Standardize labels (31->0, 32->1, 33->2, 34->3)
                events = finalize_labels(events)
                
                # 5. Filter Events for the 4 target words across ALL conditions
                # We want codes 0, 1, 2, 3 (already standardized by finalize_labels)
                target_events_df = events[events['Code'].isin([0, 1, 2, 3])].copy()
                
                if len(target_events_df) == 0:
                    print(f"    No target speech events found for {num_s} ses-0{n_b}. Skipping.")
                    continue
                
                target_event_array = target_events_df[['Time', 'Duration', 'Code']].astype(int).to_numpy()
                target_words_y = target_events_df['Code'].astype(int).to_numpy()
                target_conditions_y = target_events_df['condition'].astype(int).to_numpy()
                
                # Create an array of the subject ID for every single trial extracted here
                subject_id_array = np.full(len(target_events_df), n_s, dtype=int)
                
                # 6. Epoching
                # Select only the 128 EEG channels
                picks_eeg = mne.pick_types(rawdata.info, eeg=True, exclude=["EXG1", "EXG2", "EXG3", "EXG4", "EXG5", "EXG6", "EXG7", "EXG8"], stim=False)
                
                # Time window relative to the start of the stimulus
                tmin = -0.5
                tmax = 4.0
                
                print(f"    Extracting {len(target_event_array)} epochs for All Target Words...")
                epochs = mne.Epochs(
                    rawdata, 
                    target_event_array, 
                    tmin=tmin, 
                    tmax=tmax, 
                    picks=picks_eeg,
                    preload=True,
                    detrend=0,
                    decim=DS_RATE,
                    baseline=None,
                    verbose="WARNING"
                )
                
                # Append to our total lists
                all_X.append(epochs.get_data())
                all_y_words.append(target_words_y)
                all_y_conditions.append(target_conditions_y)
                all_subject_ids.append(subject_id_array)
                
                # Memory management
                del rawdata
                del epochs
                
            except Exception as e:
                print(f"  Error processing {num_s} ses-0{n_b}: {e}")
                
    # Stack all subjects
    if all_X:
        print("\nStacking arrays across all subjects and sessions...")
        X_stacked = np.vstack(all_X)
        y_words_stacked = np.concatenate(all_y_words)
        y_conditions_stacked = np.concatenate(all_y_conditions)
        subject_ids_stacked = np.concatenate(all_subject_ids)
        
        print(f"Final Data Shapes:\n  X: {X_stacked.shape} (Trials, Channels, TimeSteps)")
        print(f"  y_words: {y_words_stacked.shape} (Trials,)")
        print(f"  y_conditions: {y_conditions_stacked.shape} (Trials,)")
        print(f"  subject_ids: {subject_ids_stacked.shape} (Trials,)")
        
        # Save to disk
        os.makedirs(save_dir, exist_ok=True)
        np.save(save_dir / "X.npy", X_stacked)
        np.save(save_dir / "y_words.npy", y_words_stacked)
        np.save(save_dir / "y_conditions.npy", y_conditions_stacked)
        np.save(save_dir / "subject_ids.npy", subject_ids_stacked)
        
        print(f"Data saved to {save_dir}/ (X.npy, y_words.npy, y_conditions.npy, subject_ids.npy)")
    else:
        print("No speech data was successfully extracted.")


def finalize_labels(events: pd.DataFrame) -> pd.DataFrame:
    """
    Standardizes label codes mapping.
    MNE needs the 3rd column "Code" strictly as the event ID.
    During condition filtering, we map the 4 words to class indices [0, 1, 2, 3].
    """
    code_mapping = {
        31: 0,  # "Arriba" / "Up"
        32: 1,  # "Abajo" / "Down"
        33: 2,  # "Derecha" / "Right"
        34: 3,  # "Izquierda" / "Left"
    }
    
    # We add a 'Duration' column if missing because mne expects (time, duration, code)
    if 'Duration' not in events.columns:
        if 'Trigger' in events.columns:
             events.rename(columns={'Trigger': 'Duration'}, inplace=True)
             events['Duration'] = 0
        else:
             events.insert(1, 'Duration', 0)
        
    events["Code"] = events["Code"].replace(code_mapping)
    return events


if __name__ == "__main__":
    # Define paths
    dataset_dir = project_root / "ds003626"
    processed_dir = project_root / "Neuroscience-Hackathon-Imperial" / "processed_data"
    
    if not dataset_dir.exists():
         print(f"Error: Dataset not found at {dataset_dir}")
         sys.exit(1)
         
    preprocess_inner_speech_data(dataset_dir, processed_dir)
