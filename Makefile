.PHONY: help setup pipeline refresh api dev build synthetic clean check

help:
	@echo "Canary — targets:"
	@echo "  make setup       install Python + frontend deps"
	@echo "  make pipeline    run the full pipeline (uses caches)"
	@echo "  make refresh     re-pull raw data and run the pipeline"
	@echo "  make api         start the FastAPI backend on :8000"
	@echo "  make dev         start the Vite dashboard on :5173"
	@echo "  make build       build the static dashboard"
	@echo "  make synthetic   generate synthetic 311 data for offline testing"
	@echo "  make check       run pipeline end-to-end + build frontend"
	@echo "  make clean       remove generated data/outputs"

setup:
	uv sync --extra embeddings
	cd frontend && npm install

pipeline:
	uv run canary

refresh:
	uv run canary --refresh

api:
	uv run uvicorn api.main:app --port 8000 --reload

dev:
	cd frontend && npm run dev

build:
	cd frontend && npm run build

synthetic:
	uv run python scripts/make_synthetic_311.py

check:
	uv run canary --refresh
	cd frontend && npm run build
	@echo "OK — pipeline ran and frontend built."

clean:
	rm -rf data/raw/* data/processed/* cache/* outputs/*
	@touch data/raw/.gitkeep data/processed/.gitkeep cache/.gitkeep outputs/.gitkeep
