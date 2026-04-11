@echo off
echo ================================================================================
echo RETRAINING ALL 3 MODELS WITH ONE-HOT ENCODED SERVICE FEATURE
echo ================================================================================
echo.
echo Dataset: GKE Mixed 4-hour
echo Models: XGBoost, Random Forest, Logistic Regression
echo Feature Engineering: One-hot encoding of service feature
echo.
echo ================================================================================
echo.

cd /d "%~dp0"

python train_with_onehot_service.py

echo.
echo ================================================================================
echo TRAINING COMPLETE
echo ================================================================================
echo.
echo Check the following outputs:
echo   - models_mixed_onehot/ folder for trained models
echo   - results_mixed_onehot.json for evaluation metrics
echo   - feature_importance_*_mixed_onehot.png for feature importance plots
echo.
pause
