.PHONY: help venv install run clean

help:
	@echo "Available targets:"
	@echo "  venv     - Create a Python virtual environment"
	@echo "  install  - Install dependencies into the venv"
	@echo "  run      - Run the FastAPI app with uvicorn"
	@echo "  clean    - Remove venv and __pycache__"

venv:
	python3 -m venv venv

install: venv
	. venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

run:
	. venv/bin/activate && uvicorn main:app --reload

clean:
	rm -rf venv __pycache__ .pytest_cache *.pyc *.pyo