@echo off
REM Runs everything: tests, evaluation and the dashboard (Windows)

REM 1. make the test data
python data\make_bundles.py || exit /b 1

REM 2. run the tests
python -m pytest tests || exit /b 1

REM 3. run the evaluation
python eval\run_eval.py || exit /b 1
python eval\run_eval.py --split dev || exit /b 1
python eval\run_eval.py --split heldout || exit /b 1

echo All done. Reports are in the reports folder.

REM 4. open the dashboard in the browser (Ctrl+C to stop)
python serve_ui.py