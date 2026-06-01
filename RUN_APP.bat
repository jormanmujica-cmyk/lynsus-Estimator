@echo off
echo.
echo  ============================================
echo   DRIVEWAY ESTIMATOR PRO - Lynsus
echo  ============================================
echo.

:: Install dependencies if needed
pip install -r requirements.txt --quiet

echo  Starting app... opening browser automatically.
echo  To stop: press Ctrl+C in this window
echo.

streamlit run driveway.py --server.port 8501

pause
