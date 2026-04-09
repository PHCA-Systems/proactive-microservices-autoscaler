"""
Configuration file for SLA violation prediction pipeline
"""

# Service label encoding (fixed mapping for deterministic inference)
SERVICE_MAPPING = {
    'catalogue': 0,
    'carts': 1,
    'front-end': 2,
    'orders': 3,
    'payment': 4,
    'shipping': 5,
    'user': 6
}

# Data paths
DATA_PATH = 'mixed_4hour_metrics.csv'

# Model output directories
MODEL_DIR_XGB = 'models/xgboost'
MODEL_DIR_RF = 'models/random_forest'
MODEL_DIR_LR = 'models/logistic_regression'

# Model file paths
MODEL_XGB_PATH = f'{MODEL_DIR_XGB}/model.joblib'
MODEL_RF_PATH = f'{MODEL_DIR_RF}/model.joblib'
MODEL_LR_PATH = f'{MODEL_DIR_LR}/model.joblib'

# Parameter file paths
PARAMS_XGB_PATH = f'{MODEL_DIR_XGB}/parameters.json'
PARAMS_RF_PATH = f'{MODEL_DIR_RF}/parameters.json'
PARAMS_LR_PATH = f'{MODEL_DIR_LR}/parameters.json'

# Metrics file paths
METRICS_XGB_PATH = f'{MODEL_DIR_XGB}/metrics.json'
METRICS_RF_PATH = f'{MODEL_DIR_RF}/metrics.json'
METRICS_LR_PATH = f'{MODEL_DIR_LR}/metrics.json'

# Train/test split parameters
TEST_SIZE = 0.2
RANDOM_STATE = 42

# SMOTE parameters
SMOTE_SAMPLING_STRATEGY = 1.0  # 50/50 balance
SMOTE_RANDOM_STATE = 42

# Model hyperparameters
XGB_PARAMS = {
    'n_estimators': 200,
    'max_depth': 6,
    'learning_rate': 0.1,
    'use_label_encoder': False,
    'eval_metric': 'logloss',
    'random_state': 42
}

RF_PARAMS = {
    'n_estimators': 200,
    'max_depth': 8,
    'class_weight': 'balanced',
    'random_state': 42
}

LR_PARAMS = {
    'class_weight': 'balanced',
    'max_iter': 1000,
    'random_state': 42
}

# Feature importance plot settings
PLOT_DPI = 300
PLOT_FIGSIZE = (10, 6)
