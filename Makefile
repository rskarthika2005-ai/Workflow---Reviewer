PYTHON ?= python

.PHONY: all test eval data

all: data test eval

data:
	$(PYTHON) data/make_bundles.py

test:
	$(PYTHON) -m pytest tests

eval:
	$(PYTHON) eval/run_eval.py
	$(PYTHON) eval/run_eval.py --split dev
	$(PYTHON) eval/run_eval.py --split heldout