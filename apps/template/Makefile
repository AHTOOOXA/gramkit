.PHONY: up up-frontend down build rebuild logs logs-service shell-webhook shell-bot migration upgrade downgrade test test-snapshots test-snapshots-update test-file lint typecheck schema status clean clean-build script script-list frontend-dev frontend-build up-prod down-prod up-dev down-dev up-local down-local bump-patch bump-minor bump-major fix

# Docker Compose commands (relative to apps/template/)
# Default: Local development
up: up-local
down: down-local

# Local development (hot reload)
up-local:
	docker compose -f docker-compose.local.yml up -d --build --remove-orphans

up-frontend:
	cd frontend && pnpm dev

down-local:
	docker compose -f docker-compose.local.yml down

# Production
up-prod:
	docker compose -f docker-compose.yml up -d --build --remove-orphans

down-prod:
	docker compose -f docker-compose.yml down

# Dev (production-like, but separate containers)
up-dev:
	docker compose -f docker-compose.dev.yml up -d --build --remove-orphans

down-dev:
	docker compose -f docker-compose.dev.yml down

build:
	docker compose -f docker-compose.local.yml build --no-cache

rebuild: down build up

logs:
	docker compose -f docker-compose.local.yml logs

# Show logs for specific service with optional tail length
# Usage: make logs-service service=webhook tail=50
logs-service:
	@if [ -z "$(service)" ]; then \
		echo "Usage: make logs-service service=<service_name> [tail=<number>]"; \
		echo "Available services: webhook, bot, worker, app, pg_database, redis_cache"; \
		exit 1; \
	fi; \
	if [ -n "$(tail)" ]; then \
		docker compose -f docker-compose.local.yml logs --tail=$(tail) $(service); \
	else \
		docker compose -f docker-compose.local.yml logs --tail=50 $(service); \
	fi

status:
	docker compose -f docker-compose.local.yml ps

# Shell access
shell-webhook:
	docker exec -it template-webhook /bin/bash

shell-bot:
	docker exec -it template-bot /bin/bash

# Alembic migrations
migration:
	@if [ -z "$(msg)" ]; then \
		read -p "Enter migration message: " msg; \
		docker exec template-webhook alembic revision --autogenerate -m "$$msg"; \
	else \
		docker exec template-webhook alembic revision --autogenerate -m "$(msg)"; \
	fi

upgrade:
	docker exec template-webhook alembic upgrade head

downgrade:
	docker exec template-webhook alembic downgrade -1

# Backend: Linting & Formatting
lint:
	@echo "==> Running backend linting (ruff)..."
	@cd backend && ENV_FILE=.env.test uv run ruff check --fix src/
	@echo "==> Running backend formatting (ruff)..."
	@cd backend && ENV_FILE=.env.test uv run ruff format src/
	@echo "==> Checking architecture boundaries (import-linter)..."
	@cd backend/src && ENV_FILE=../.env.test uv run lint-imports --config ../.importlinter
	@echo "==> Running frontend linting + formatting (ESLint)..."
	@cd frontend && pnpm lint:fix
	@echo "==> Running TypeScript type checking..."
	@cd frontend && pnpm typecheck
	@echo "==> ✓ All checks passed!"

# Backend: Type checking
typecheck:
	@echo "==> Running type checking (pyright)..."
	@cd backend && uvx pyright src/

# Backend: Testing (config in pyproject.toml)
test:
	@echo "==> Running all tests (core + app)..."
	@cd backend && ENV_FILE=.env.test uv run pytest
	@echo ""
	@echo "💡 Tip: Use pytest directly for advanced options:"
	@echo "   cd backend && ENV_FILE=.env.test uv run pytest -m contract    # Run contract tests only"
	@echo "   cd backend && ENV_FILE=.env.test uv run pytest -n0            # Run without parallelization"
	@echo "   cd backend && ENV_FILE=.env.test uv run pytest --cov=app      # Run with coverage"

test-quick:
	@echo "==> Running incremental tests (testmon + parallel)..."
	@cd backend && ENV_FILE=.env.test uv run pytest --testmon -n 2 --tb=short

test-snapshots:
	@echo "==> Running tests in SEQUENTIAL mode for snapshot validation..."
	@cd backend && ENV_FILE=.env.test uv run pytest src/app/tests/ -v -n0 --ignore=src/app/tests/_archived

test-snapshots-update:
	@echo "==> Updating snapshots (sequential mode)..."
	@cd backend && ENV_FILE=.env.test uv run pytest src/app/tests/ -v -n0 --inline-snapshot=fix --ignore=src/app/tests/_archived

test-file:
	@if [ -z "$(file)" ]; then \
		echo "Usage: make test-file file=<path_to_test_file>"; \
		echo "Example: make test-file file=src/app/tests/contracts/api/test_setup.py"; \
		exit 1; \
	fi
	@echo "==> Running tests in $(file)..."
	@cd backend && ENV_FILE=.env.test uv run pytest $(file) -v

# Frontend: Commands
frontend-dev:
	cd frontend && pnpm dev

frontend-build:
	cd frontend && pnpm build

schema:
	cd frontend && pnpm generate

# Version bumping
bump-patch:
	python3 bump_version.py patch

bump-minor:
	python3 bump_version.py minor

bump-major:
	python3 bump_version.py major

# Docker cleanup
clean:
	docker system prune -f

clean-build: down
	docker builder prune -af
	docker compose -f docker-compose.local.yml build --no-cache
	docker compose -f docker-compose.local.yml up -d

# Script execution
script:
	@if [ -z "$(name)" ]; then \
		echo "Usage: make script name=<script_name> [args='<arguments>']"; \
		echo "Example: make script name=demo_user_stats"; \
		echo "Run 'make script-list' to see available scripts"; \
		exit 1; \
	fi
	@echo "Running script: $(name) $(args)"
	@docker exec template-webhook bash -c "cd /workspace/apps/template/backend && python -m app.scripts $(name) $(args)"

script-list:
	@echo "Available scripts:"
	@echo ""
	@echo "App-specific:"
	@docker exec template-webhook bash -c "cd /workspace/apps/template/backend/src/app/scripts && ls -1 *.py 2>/dev/null | grep -v '__init__' | grep -v '__main__' | sed 's/\.py$$//' | sed 's/^/  - /' || echo '  (none)'"
	@echo ""
	@echo "Common (available to all apps):"
	@docker exec template-webhook bash -c "cd /workspace/core/backend/src/core/scripts/common && ls -1 *.py 2>/dev/null | grep -v '__init__' | sed 's/\.py$$//' | sed 's/^/  - /'"
	@echo ""
	@echo "Usage: make script name=<script_name> [args='<arguments>']"

# Fix frontend dependencies (reinstall node_modules)
fix:
	@echo "Reinstalling frontend dependencies..."
	cd frontend && rm -rf node_modules && pnpm install
	@echo "✓ Frontend dependencies reinstalled"
