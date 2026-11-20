.PHONY: test serve compare

test:
	python3 -m unittest discover -s tests

serve:
	python3 -m src.server

compare:
	python3 -m experiments.strategy_comparison
