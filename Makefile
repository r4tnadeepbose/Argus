.PHONY: help run test lint format install-dev clean clean-data

help:
	@echo "Targets:"
	@echo "  run         Start the GUI (python recon_gui.py)"
	@echo "  test        Run the pytest suite"
	@echo "  lint        Run ruff"
	@echo "  format      Format with ruff"
	@echo "  install-dev Install development dependencies"
	@echo "  clean       Remove build and cache artifacts"
	@echo "  clean-data  Remove runs/ and resume.cfg (destructive)"

run:
	python recon_gui.py

test:
	python -m pytest

lint:
	ruff check .

format:
	ruff format .

install-dev:
	python -m pip install -r requirements-dev.txt

clean:
	find . -type d -name __pycache__ -prune -exec rm -rf {} +
	rm -rf .pytest_cache .ruff_cache build dist *.egg-info

clean-data:
	rm -rf runs resume.cfg
