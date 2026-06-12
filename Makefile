.DEFAULT_GOAL := help
.PHONY: help install backend frontend dev test lint build up up-ollama down logs

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
	  awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'

install: ## Install backend (venv) + frontend deps for local dev
	python3 -m venv .venv && . .venv/bin/activate && \
	  pip install -r backend/requirements-dev.txt
	cd frontend && npm install

backend: ## Run the API with autoreload on :8000 (needs `make install`)
	. .venv/bin/activate && cd backend && \
	  DATA_DIR=../data uvicorn app.main:app --reload --port 8000

frontend: ## Run the Vite dev server on :5173 (proxies /api to :8000)
	cd frontend && npm run dev

test: ## Run backend tests
	. .venv/bin/activate && cd backend && pytest -q

lint: ## Lint the backend
	. .venv/bin/activate && cd backend && ruff check .

build: ## Build the production Docker image
	docker build -t caption-generation:latest .

up: ## Start Caption Generation (app only) in the background
	docker compose up -d --build

up-ollama: ## Start Caption Generation together with a bundled Ollama LLM
	docker compose --profile ollama up -d --build

down: ## Stop everything
	docker compose down

logs: ## Tail the app logs
	docker compose logs -f app
