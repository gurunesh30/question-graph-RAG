.PHONY: build test test-all score generate e2e clean help

help:
	@echo "Targets:"
	@echo "  build     Build the Rust binaries in release mode"
	@echo "  test      Run offline smoke tests + benchmark"
	@echo "  test-all  Run smoke + benchmark + Neo4j connection verification"
	@echo "  score     Run Phase 4 centrality scoring against Neo4j"
	@echo "  generate  Run Phase 5 MCQ generation (usage: make generate DIFF=hard N=5)"
	@echo "  e2e       End-to-end pipeline verification (live or offline fallback)"
	@echo "  clean     Remove build artifacts"

build:
	cd rust_kg_engine && cargo build --release

test:
	python3 tests/test_smoke.py
	python3 tests/benchmark.py

test-all: test
	python3 tests/verify_neo4j.py || true

score:
	python3 main.py --score

generate:
	python3 main.py --generate-qg --difficulty $(DIFF) --count $(or $(N),5) --output $(or $(OUT),$(DIFF).json)

e2e:
	python3 tests/e2e_pipeline.py --difficulty $(DIFF) --count $(or $(N),3) --output $(or $(OUT),e2e_questions.json)

clean:
	rm -rf rust_kg_engine/target
	find . -type d -name __pycache__ -exec rm -rf {} +