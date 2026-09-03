.PHONY: install build test test-all lint verify score generate e2e clean help

PY ?= python3
PYTEST ?= $(PY) -m pytest

help:
	@echo "Targets:"
	@echo "  install    Install Python package in editable mode"
	@echo "  build      Build Rust binaries in release mode"
	@echo "  test       Run unit tests (no network)"
	@echo "  test-all   Run unit + live integration tests (KAQG_LIVE=1)"
	@echo "  lint       Run ruff + mypy"
	@echo "  verify     Run Neo4j connection verification"
	@echo "  score      Run centrality scoring against Neo4j"
	@echo "  generate   Generate MCQ bank (usage: make generate DIFF=hard N=5)"
	@echo "  e2e        End-to-end pipeline (PDF + score + generate)"
	@echo "  clean      Remove build artifacts"

install:
	$(PY) -m pip install -e ".[dev]"

build:
	cd rust_kg_engine && cargo build --release

test:
	PYTHONPATH=src $(PYTEST) tests/unit -q

test-all:
	PYTHONPATH=src KAQG_LIVE=1 $(PYTEST) tests -q

lint:
	$(PY) -m ruff check src tests
	$(PY) -m mypy src

verify:
	$(PY) -m kaqg verify

score:
	$(PY) -m kaqg score

generate:
	$(PY) -m kaqg generate --difficulty $(DIFF) --count $(or $(N),5) --output $(or $(OUT),$(DIFF).json)

e2e:
	$(PY) -m kaqg e2e $(PDF) --difficulty $(DIFF) --count $(or $(N),3) --output $(or $(OUT),e2e_questions.json)

clean:
	rm -rf rust_kg_engine/target build dist src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} +