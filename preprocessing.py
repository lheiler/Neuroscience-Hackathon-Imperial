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
    Preprocess the ds003626 dataset specifically to replicate the Spectro-Temporal Transformer
    reaching 82.4% accuracy. Uses strict filtering and artifact rejection.
    """
    # Processing Variables: Study uses Sub 02, 03, 05, 06. Excludes 04.
    N_Subj_arr = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]    
    N_block_arr = range(1, 4)
    
    # 1. FIR Bandpass (1.0 - 100 Hz) and Notch (50 Hz)
    LOW_CUT = 1.0
    HIGH_CUT = 100.0
    NOTCH_FREQ = 50.0
    DS_RATE = 1 
    
    event_id = dict(Arriba=31, Abajo=32, Derecha=33, Izquierda=34)
    
    all_X = []
    all_y_words = []
    all_y_conditions = []
    all_subject_ids = []
    all_trial_ids = [] # Grouping factor for CV
    
    global_trial_counter = 0
    
    for n_s in N_Subj_arr:
        num_s = sub_name(n_s)
        print(f"\nProcessing Subject: {num_s}")
        
        for n_b in N_block_arr:
            try:
                # ... (BDF reading/filtering remains same)
                bdf_path = data_dir / f"{num_s}/ses-0{n_b}/eeg/{num_s}_ses-0{n_b}_task-innerspeech_eeg.bdf"
                if not bdf_path.exists():
                    continue
                
                print(f"  Loading Session: {n_b} ...")
                rawdata = mne.io.read_raw_bdf(input_fname=bdf_path, preload=True, verbose="WARNING")
                rawdata.set_eeg_reference(ref_channels='average', verbose="WARNING")
                
                # 1. Causal FIR Filtering (Minimum phase for zero-latency simulation)
                rawdata.notch_filter(freqs=NOTCH_FREQ, verbose="WARNING", fir_design='firwin', phase='minimum')
                rawdata.filter(LOW_CUT, HIGH_CUT, verbose="WARNING", fir_design='firwin', phase='minimum')
                
                # Extract Events FIRST
                print("    Extracting Events...")
                events = get_events_from_raw(rawdata, n_s, n_b)
                events = check_baseline_tags(events)
                events = event_correction(events=events)
                
                events = add_condition_tag(events)
                events = finalize_labels(events)
                
                # Filter for Word Classes
                target_events_df = events[events['Code'].isin([0, 1, 2, 3])].copy()
                if len(target_events_df) == 0:
                    continue
                
                target_event_array = target_events_df[['Time', 'Duration', 'Code']].astype(int).to_numpy()
                target_words_y = target_events_df['Code'].astype(int).to_numpy()
                target_conditions_y = target_events_df['condition'].astype(int).to_numpy()
                subject_id_array = np.full(len(target_events_df), n_s, dtype=int)
                
                # Resample
                rawdata, target_event_array = rawdata.resample(256.0, events=target_event_array, verbose="WARNING")
                
                picks_eeg = mne.pick_types(rawdata.info, eeg=True, exclude=["EXG1", "EXG2", "EXG3", "EXG4", "EXG5", "EXG6", "EXG7", "EXG8"], stim=False)
                
                # Epoching
                print(f"    Extracting epochs [0.5, 3.0]s (Action-Aligned)...")
                epochs = mne.Epochs(
                    rawdata, 
                    target_event_array, 
                    tmin=0.5, 
                    tmax=3.0, 
                    picks=picks_eeg,
                    preload=True,
                    baseline=None,
                    verbose="WARNING"
                )
                
                data = epochs.get_data() # (n_epochs, n_channels, n_times)
                ptp = np.ptp(data, axis=-1)
                flat_mask = np.any(ptp < 1e-6, axis=1)
                
                if np.any(flat_mask):
                    epochs.drop(flat_mask, reason="FLAT")
                    data = epochs.get_data()
                    ptp = np.ptp(data, axis=-1)
                    
                # VMD ARTIFACT REMOVAL (DISABLED for Phase 10 to preserve signal fidelity)
                # We skip the VMD cleaning as Riemannian covariance is robust to stochastic noise
                # but VMD (IMF0 removal) was likely deleting discriminative intent.
                epochs._data = data

                # 6. SAVE FULL 2.5s TRIALS (No Augmentation)
                n_epochs = data.shape[0]
                # Enforce Session-Level Grouping: Use SubjectID + BlockID as the group index
                session_group_id = int(f"{n_s}{n_b}")
                current_session_ids = np.full(n_epochs, session_group_id, dtype=int)
                
                # Labels for remaining synchronized epochs
                kept_indices = [i for i, log in enumerate(epochs.drop_log) if not log]
                
                all_X.append(data)
                all_y_words.append(target_words_y[kept_indices])
                all_y_conditions.append(target_conditions_y[kept_indices])
                all_subject_ids.append(subject_id_array[kept_indices])
                all_trial_ids.append(current_session_ids)
                
                del rawdata
                del epochs
                
            except Exception as e:
                print(f"  Error: {e}")
                
    if all_X:
        X_stacked = np.vstack(all_X)
        y_words_stacked = np.concatenate(all_y_words)
        y_conditions_stacked = np.concatenate(all_y_conditions)
        subject_ids_stacked = np.concatenate(all_subject_ids)
        trial_ids_stacked = np.concatenate(all_trial_ids)
        
        print(f"\nFinal Preprocessed Snapshot (Shape): {X_stacked.shape}")
        
        os.makedirs(save_dir, exist_ok=True)
        np.save(save_dir / "X.npy", X_stacked)
        np.save(save_dir / "y_words.npy", y_words_stacked)
        np.save(save_dir / "y_conditions.npy", y_conditions_stacked)
        np.save(save_dir / "subject_ids.npy", subject_ids_stacked)
        np.save(save_dir / "trial_ids.npy", trial_ids_stacked)
        
        print(f"Data saved to {save_dir}/ (X.npy, y_words, etc., trial_ids.npy)")
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
