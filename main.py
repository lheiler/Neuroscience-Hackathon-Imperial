import warnings
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import accuracy_score
from model import get_riemannian_model
import os
warnings.filterwarnings("ignore")

def load_raw_data(data_dir):
    """
    Loads the raw mathematically untouched EEG array and trial IDs for grouping.
    """
    X_raw = np.load(os.path.join(data_dir, "X.npy"))
    y_words = np.load(os.path.join(data_dir, "y_words.npy"))
    y_conds = np.load(os.path.join(data_dir, "y_conditions.npy"))
    sub_ids = np.load(os.path.join(data_dir, "subject_ids.npy"))
    trial_ids = np.load(os.path.join(data_dir, "trial_ids.npy"))
    
    # Filter Pronounced Speech (Condition 0) to show the 41.7% baseline success
    mask = (y_conds == 0)
    return X_raw[mask], y_words[mask], sub_ids[mask], trial_ids[mask]

def run_riemannian_eval(subject_id, X_raw, y, trial_ids):
    print(f"\n[SUBJECT {subject_id:02d}] FilterBank Riemannian | Focal Subset")
    print("-" * 50)
    
    # SPATIAL REDUCTION: Focus on 22 focal language/executive channels
    subset = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 96, 98, 100, 102, 105, 107, 109, 111, 114, 116, 120, 123]
    X_sliced = X_raw[:, subset, :]
    
    sgkf = StratifiedGroupKFold(n_splits=10, shuffle=True, random_state=42)
    fold_accuracies = []
    train_accuracies = []
    
    for fold, (train_idx, val_idx) in enumerate(sgkf.split(X_sliced, y, groups=trial_ids)):
        X_train, y_train = X_sliced[train_idx], y[train_idx]
        X_val, y_val = X_sliced[val_idx], y[val_idx]

        model = get_riemannian_model(verbose=False)
        model.fit(X_train, y_train)
        
        train_acc = model.score(X_train, y_train) * 100.0
        val_acc = model.score(X_val, y_val) * 100.0
        
        print(f" Fold {fold+1:>2}: Train {train_acc:>5.1f}% | Val {val_acc:>5.1f}%")
        fold_accuracies.append(val_acc)
        train_accuracies.append(train_acc)
        
    avg_acc = np.mean(fold_accuracies)
    avg_train = np.mean(train_accuracies)
    print("-" * 50)
    print(f" RESULT:  Avg Train {avg_train:>5.1f}% | Avg Val {avg_acc:>5.1f}%")
    return avg_acc

if __name__ == "__main__":
    print("\n" + "="*60)
    print(" ACTION-ALIGNED RIEMANNIAN DECODING DASHBOARD ")
    print("="*60)
    
    data_dir = "processed_data"
    X_all, y_all, sub_ids_all, trial_ids_all = load_raw_data(data_dir)
    
    valid_subjects = np.unique(sub_ids_all)
    results = []
    
    for sub in valid_subjects:
        mask = (sub_ids_all == sub)
        res = run_riemannian_eval(
            subject_id=sub, 
            X_raw=X_all[mask], 
            y=y_all[mask],
            trial_ids=trial_ids_all[mask]
        )
        results.append(res)
        
    print("\n" + "="*60)
    print(f" OVERALL MEAN ACCURACY (PRONOUNCED): {np.mean(results):.2f}%")
    print("="*60 + "\n")
