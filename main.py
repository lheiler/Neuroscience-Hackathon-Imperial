import os
import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedKFold
from sklearn.metrics import accuracy_score
import mrmr
from model import get_ensemble_model

def load_classical_data(data_dir):
    """
    Loads the flattened ~24,000 feature array from `feature_extraction.py`
    and filters for Inner Speech (Condition 1).
    """
    X_features = np.load(os.path.join(data_dir, "X_features.npy"))
    y_words = np.load(os.path.join(data_dir, "y_words.npy"))
    y_conds = np.load(os.path.join(data_dir, "y_conditions.npy"))
    sub_ids = np.load(os.path.join(data_dir, "subject_ids.npy"))
    
    # Filter Inner Speech
    mask = (y_conds == 1)
    return X_features[mask], y_words[mask], sub_ids[mask]


def run_subject_specific_evaluation(subject_id, X, y):
    """
    1. Selects only data for `subject_id`
    2. Performs 10-Fold CV
    3. Calculates top 590 features using MRMR *inside* each fold to strictly 
       prevent data leakage from the validation set into the feature selection.
    """
    print(f"\n======================================")
    print(f"|  SUBJECT {subject_id:02d} | 10-Fold Ensemble CV  |")
    print(f"======================================")
    
    # Isolate the subject
    sub_mask = (X == X) # Placeholder, we pass already masked data
    
    # mRMR config
    K_FEATURES = 590
    
    # 10-Fold CV Configuration (Stratified to maintain class balance)
    skf = StratifiedKFold(n_splits=10, shuffle=True, random_state=42)
    fold_accuracies = []
    
    from sklearn.preprocessing import StandardScaler
    
    for fold, (train_idx, val_idx) in enumerate(skf.split(X, y)):
        X_train, y_train = X[train_idx], y[train_idx]
        X_val, y_val = X[val_idx], y[val_idx]
        
        # 0. Scale Features strictly on the training set to prevent leakage
        scaler = StandardScaler()
        X_train_scaled = scaler.fit_transform(X_train)
        X_val_scaled = scaler.transform(X_val)
        
        # 1. mRMR Selection (Selecting Top K strictly from the training set)
        print(f"  [Fold {fold+1}] Running mRMR (Selecting Top {K_FEATURES} from {X_train.shape[1]})...")
        df_train = pd.DataFrame(X_train_scaled)
        y_train_series = pd.Series(y_train)
        
        selected_features = mrmr.mrmr_classif(X=df_train, y=y_train_series, K=K_FEATURES, show_progress=False)
        
        # Apply the discovered feature indices to both train and val sets
        X_train_reduced = X_train_scaled[:, selected_features]
        X_val_reduced = X_val_scaled[:, selected_features]
        
        # --- ENSEMBLE CLASSIFICATION ---
        model = get_ensemble_model()
        model.fit(X_train_reduced, y_train)
        
        # Validate
        preds = model.predict(X_val_reduced)
        acc = accuracy_score(y_val, preds) * 100.0
        
        print(f"  [Fold {fold+1}] Accuracy: {acc:.2f}%")
        fold_accuracies.append(acc)
        
    avg_acc = np.mean(fold_accuracies)
    print(f"\n>> Final 10-Fold CV Accuracy for Subject {subject_id}: {avg_acc:.2f}%\n")


if __name__ == "__main__":
    data_dir = "processed_data"
    print("Loading Massive TSFEL Feature Matrix...")
    X_all, y_all, sub_ids_all = load_classical_data(data_dir)
    
    # Get unique valid subjects (typically 2, 3, 5, 6)
    valid_subjects = np.unique(sub_ids_all)
    
    # Execute evaluating loop completely independently for each subject
    for sub in valid_subjects:
        mask = (sub_ids_all == sub)
        run_subject_specific_evaluation(
            subject_id=sub, 
            X=X_all[mask], 
            y=y_all[mask]
        )
