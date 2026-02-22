from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import StackingClassifier

def get_ensemble_model():
    """
    Constructs the Classical ML Ensemble specified by the paper to replace the
    failed PyTorch Deep Learning approaches.
    
    Architecture:
    Exactly 5 Logistic Regression (LR) estimators stacked together.
    """
    estimators = [
        ('lr1', LogisticRegression(penalty='l1', solver='saga', C=0.5, max_iter=1000, random_state=42)),
        ('lr2', LogisticRegression(penalty='l1', solver='saga', C=1.0, max_iter=1000, random_state=43)),
        ('lr3', LogisticRegression(penalty='l1', solver='saga', C=1.5, max_iter=1000, random_state=44)),
        ('lr4', LogisticRegression(penalty='l1', solver='saga', C=2.0, max_iter=1000, random_state=45, class_weight='balanced')),
        ('lr5', LogisticRegression(penalty='l1', solver='saga', C=0.1, max_iter=1000, random_state=46))
    ]
    
    # Stacking learns how to optimally weight the 5 base LR models
    ensemble = StackingClassifier(
        estimators=estimators, 
        final_estimator=LogisticRegression(penalty='l2', C=0.5, max_iter=1000),
        n_jobs=-1
    )
    
    return ensemble

