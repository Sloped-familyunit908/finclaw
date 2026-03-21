.PHONY: install test lint run

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v

lint:
	ruff check .

run:
	python scripts/main.py
