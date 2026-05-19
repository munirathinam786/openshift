.PHONY: install dev test lint fmt docs serve build clean

install:
	python3 -m pip install -e .

dev:
	python3 -m pip install -e .[dev]

test:
	python3 -m pytest -v

lint:
	python3 -m ruff check src/ tests/

fmt:
	python3 -m ruff format src/ tests/

docs:
	mkdocs build

serve:
	mkdocs serve

build:
	bash ./scripts/podman-compose.sh -f compose.yaml up -d --build

down:
	bash ./scripts/podman-compose.sh -f compose.yaml down

refresh:
	bash ./scripts/podman-dev-refresh.sh

clean:
	rm -rf site/ dist/ *.egg-info .pytest_cache __pycache__
