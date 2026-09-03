.PHONY: build test score generate clean help

help:
	@echo "Targets:"
	@echo "  build     Build the Rust binaries in release mode"
	@echo "  test      Run offline smoke tests + benchmark"
	@echo "  score     Run Phase 4 centrality scoring against Neo4j"
	@echo "  generate  Run Phase 5 MCQ generation (usage: make generate DIFF=hard N=5)"
	@echo "  clean     Remove build artifacts"

build:
	cd rust_kg_engine && cargo build --release

test:
	python3 tests/test_smoke.py
	python3 tests/benchmark.py

score:
	python3 main.py --score

generate:
	python3 main.py --generate-qg --difficulty $(DIFF) --count $(or $(N),5) --output $(or $(OUT),$(DIFF).json)

clean:
	rm -rf rust_kg_engine/target
	find . -type d -name __pycache__ -exec rm -rf {} +