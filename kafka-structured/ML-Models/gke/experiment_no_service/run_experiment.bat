@echo off
echo ================================================================================
echo EXPERIMENT: Training Models Without Service Feature
echo ================================================================================
echo.
echo This experiment will train all 3 models on all 3 datasets without the service feature.
echo.
echo Requirements:
echo - pandas, numpy, scikit-learn, imbalanced-learn, xgboost, matplotlib, joblib
echo.
echo If you get ModuleNotFoundError, install requirements:
echo   pip install pandas numpy scikit-learn imbalanced-learn xgboost matplotlib joblib
echo.
echo ================================================================================
echo.

python train_no_service.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ================================================================================
    echo EXPERIMENT COMPLETE!
    echo ================================================================================
    echo.
    echo Next steps:
    echo 1. Check results_no_service.json for metrics
    echo 2. View feature importance plots (*.png files)
    echo 3. Run: python compare_with_without_service.py
    echo.
) else (
    echo.
    echo ================================================================================
    echo ERROR: Training failed
    echo ================================================================================
    echo.
    echo Please ensure all required packages are installed:
    echo   pip install pandas numpy scikit-learn imbalanced-learn xgboost matplotlib joblib
    echo.
)

pause
