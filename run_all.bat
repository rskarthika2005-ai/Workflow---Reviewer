@echo off
REM Windows version of "make all": offline tests + eval, CPU only.
python data\make_bundles.py || exit /b 1
python -m pytest tests || exit /b 1
python eval\run_eval.py || exit /b 1
python eval\run_eval.py --split dev || exit /b 1
python eval\run_eval.py --split heldout || exit /b 1
echo All done. Reports are in the reports folder.