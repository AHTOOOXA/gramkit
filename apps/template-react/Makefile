.PHONY: up down restart status logs logs-webhook logs-bot logs-worker
.PHONY: shell-webhook shell-bot shell-worker
.PHONY: test test-backend migration upgrade downgrade schema lint typecheck

# ============================================================================
# Docker Commands (Backend Only - Frontend runs locally)
# ============================================================================

up:
	docker compose -f docker-compose.local.yml up -d --build --remove-orphans

down:
	docker compose -f docker-compose.local.yml down

up-frontend:
	cd frontend && pnpm dev

restart:
	docker compose -f docker-compose.local.yml restart

status:
	docker compose -f docker-compose.local.yml ps

# ============================================================================
# Logs
# ============================================================================

logs:
	docker compose -f docker-compose.local.yml logs -f

logs-webhook:
	docker compose -f docker-compose.local.yml logs -f webhook

logs-bot:
	docker compose -f docker-compose.local.yml logs -f bot

logs-worker:
	docker compose -f docker-compose.local.yml logs -f worker

# ============================================================================
# Shell Access
# ============================================================================

shell-webhook:
	docker exec -it template-react-webhook bash

shell-bot:
	docker exec -it template-react-bot bash

shell-worker:
	docker exec -it template-react-worker bash

# ============================================================================
# Backend Commands
# ============================================================================

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

test-backend:
	docker exec template-react-webhook pytest src/app/tests/ -v

test-file:
	@if [ -z "$(file)" ]; then \
		echo "Usage: make test-file file=<path_to_test_file>"; \
		echo "Example: make test-file file=src/app/tests/contracts/api/test_demo.py"; \
		exit 1; \
	fi
	@echo "==> Running tests in $(file)..."
	@cd backend && ENV_FILE=.env.test uv run pytest $(file) -v

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

migration:
	@if [ -z "$(msg)" ]; then \
		echo "Error: msg is required. Usage: make migration msg='description'"; \
		exit 1; \
	fi
	docker exec template-react-webhook alembic revision --autogenerate -m "$(msg)"

upgrade:
	docker exec template-react-webhook alembic upgrade head

downgrade:
	docker exec template-react-webhook alembic downgrade -1

# ============================================================================
# Frontend Commands (Run locally in apps/template-react/frontend)
# ============================================================================

schema:
	cd frontend && pnpm generate

# ============================================================================
# Database Commands
# ============================================================================

db-shell:
	docker exec -it template-react-db psql -U postgres -d template_react

db-reset:
	docker compose -f docker-compose.local.yml down -v
	docker compose -f docker-compose.local.yml up -d db redis
	sleep 5
	$(MAKE) upgrade

# ============================================================================
# Script Execution
# ============================================================================

script:
	@if [ -z "$(name)" ]; then \
		echo "Usage: make script name=<script_name> [args='<arguments>']"; \
		echo "Example: make script name=demo_user_stats"; \
		echo "Run 'make script-list' to see available scripts"; \
		exit 1; \
	fi
	@echo "Running script: $(name) $(args)"
	@docker exec template-react-webhook bash -c "cd /workspace/apps/template-react/backend && python -m app.scripts $(name) $(args)"

script-list:
	@echo "Available scripts:"
	@echo ""
	@echo "App-specific:"
	@docker exec template-react-webhook bash -c "cd /workspace/apps/template-react/backend/src/app/scripts && ls -1 *.py 2>/dev/null | grep -v '__init__' | grep -v '__main__' | sed 's/\.py$$//' | sed 's/^/  - /' || echo '  (none)'"
	@echo ""
	@echo "Common (available to all apps):"
	@docker exec template-react-webhook bash -c "cd /workspace/core/backend/src/core/scripts/common && ls -1 *.py 2>/dev/null | grep -v '__init__' | sed 's/\.py$$//' | sed 's/^/  - /'"
	@echo ""
	@echo "Usage: make script name=<script_name> [args='<arguments>']"

# Fix frontend dependencies (reinstall node_modules)
fix:
	@echo "Reinstalling frontend dependencies..."
	cd frontend && rm -rf node_modules && pnpm install
	@echo "✓ Frontend dependencies reinstalled"
