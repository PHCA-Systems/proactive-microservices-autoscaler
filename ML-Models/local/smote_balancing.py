"""
SMOTE balancing module for handling class imbalance
"""

from imblearn.over_sampling import SMOTE
from config import SMOTE_SAMPLING_STRATEGY, SMOTE_RANDOM_STATE


def apply_smote(X_train, y_train):
    """
    Apply SMOTE to training data only to balance classes.
    
    CRITICAL: Test set must remain untouched to provide unbiased performance
    estimates for thesis validity. SMOTE on test data would artificially 
    inflate metrics.
    
    Args:
        X_train: Training features
        y_train: Training target
        
    Returns:
        tuple: (X_train_smote, y_train_smote) balanced training data
    """
    print("\n" + "=" * 80)
    print("SMOTE CLASS BALANCING")
    print("=" * 80)
    
    # Calculate scale_pos_weight for XGBoost (before SMOTE)
    neg_count = (y_train == 0).sum()
    pos_count = (y_train == 1).sum()
    scale_pos_weight = neg_count / pos_count
    print(f"\nScale_pos_weight for XGBoost: {scale_pos_weight:.2f}")
    
    # Apply SMOTE
    smote = SMOTE(random_state=SMOTE_RANDOM_STATE, sampling_strategy=SMOTE_SAMPLING_STRATEGY)
    X_train_smote, y_train_smote = smote.fit_resample(X_train, y_train)
    
    print(f"\nAfter SMOTE training set class distribution:")
    print(f"  Class 0 (no violation): {(y_train_smote == 0).sum()} ({(y_train_smote == 0).sum() / len(y_train_smote) * 100:.1f}%)")
    print(f"  Class 1 (violation):    {(y_train_smote == 1).sum()} ({(y_train_smote == 1).sum() / len(y_train_smote) * 100:.1f}%)")
    print(f"Training set size after SMOTE: {X_train_smote.shape[0]} samples")
    
    return X_train_smote, y_train_smote, scale_pos_weight
