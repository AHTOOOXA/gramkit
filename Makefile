.PHONY: up down build rebuild logs logs-service logs-frontend restart-frontend shell-webhook shell-bot migration upgrade downgrade clean clean-build bump-patch bump-minor bump-major release test test-snapshots test-snapshots-update test-file lint schema status script script-list up-shared down-shared restart-shared reload-nginx status-all all-up all-down sync sync-env

# Directory for frontend logs
FRONTEND_RUN_DIR := .run

# Frontend ports by app (must match package.json dev scripts)
PORT_template := 5174
PORT_template-react := 3001

# Kill process on a given port (usage: $(call kill_port,3001))
define kill_port
	@lsof -ti:$(1) | xargs kill -9 2>/dev/null || true
endef

# No default app - must be explicitly specified
APP_DIR = apps/$(APP)

define check_app
	@if [ ! -d "$(APP_DIR)" ]; then \
		echo "Error: App '$(APP)' not found at $(APP_DIR)"; \
		echo "Available apps:"; \
		ls -d apps/*/ 2>/dev/null | xargs -I {} basename {} | sed 's/^/  - /'; \
		exit 1; \
	fi; \
	if [ ! -f "$(APP_DIR)/Makefile" ]; then \
		echo "Error: $(APP_DIR)/Makefile not found"; \
		echo "Each app must have its own Makefile"; \
		exit 1; \
	fi
endef

# Docker Compose commands (backend only - frontends run locally)
up:
	@if [ -z "$(APP)" ]; then \
		echo "Select app:"; \
		i=1; \
		for app_dir in apps/*/; do \
			app=$$(basename $$app_dir); \
			case $$app in \
				template-react) color="\033[1;36m" ;; \
				template) color="\033[1;32m" ;; \
				*) color="\033[0m" ;; \
			esac; \
			echo "$$i. $${color}$$app\033[0m"; \
			i=$$((i + 1)); \
		done; \
		echo "$$i. \033[1;33mall\033[0m"; \
		printf "Choice (q=quit): "; \
		read choice; \
		if [ "$$choice" = "q" ] || [ "$$choice" = "Q" ]; then \
			exit 1; \
		fi; \
		if [ "$$choice" = "$$i" ]; then \
			echo "→ make up APP=all"; \
			exec $(MAKE) up APP=all; \
		fi; \
		selected_app=$$(ls -d apps/*/ 2>/dev/null | xargs -I {} basename {} | sed -n "$${choice}p"); \
		if [ -z "$$selected_app" ]; then \
			echo "Invalid choice"; \
			exit 1; \
		fi; \
		echo "→ make up APP=$$selected_app"; \
		exec $(MAKE) up APP=$$selected_app; \
	elif [ "$(APP)" = "all" ]; then \
		echo "=========================================="; \
		echo "Starting Complete System (Backend)"; \
		echo "=========================================="; \
		echo ""; \
		echo "[1/4] Starting shared infrastructure..."; \
		$(MAKE) up-shared; \
		echo ""; \
		echo "[2/4] Waiting for network..."; \
		sleep 2; \
		echo ""; \
		echo "[3/4] Starting all app backends..."; \
		for app in apps/*/; do \
			app_name=$$(basename $$app); \
			if [ -f "apps/$$app_name/Makefile" ]; then \
				echo "  ==> Starting $$app_name backend..."; \
				cd apps/$$app_name && $(MAKE) up && cd ../..; \
			fi; \
		done; \
		echo ""; \
		echo "[4/4] Reloading nginx..."; \
		docker exec nginx nginx -s reload 2>/dev/null && echo "✓ Nginx reloaded" || echo "⚠ Nginx reload failed"; \
		echo ""; \
		echo "=========================================="; \
		echo "Backend ready! Start frontends locally:"; \
		echo "=========================================="; \
		echo "  cd apps/template/frontend && pnpm dev"; \
		echo "  cd apps/template-react/frontend && pnpm dev"; \
		echo "=========================================="; \
	else \
		if [ ! -d "apps/$(APP)" ]; then \
			echo "Error: App '$(APP)' not found"; \
			exit 1; \
		fi; \
		if [ ! -f "apps/$(APP)/Makefile" ]; then \
			echo "Error: apps/$(APP)/Makefile not found"; \
			exit 1; \
		fi; \
		echo "Starting $(APP) backend..."; \
		cd apps/$(APP) && $(MAKE) up; \
		echo "Reloading nginx..."; \
		docker exec nginx nginx -s reload 2>/dev/null && echo "✓ Nginx reloaded" || echo "ℹ Nginx not running (run 'make up-shared' first)"; \
		echo ""; \
		echo "Starting $(APP) frontend..."; \
		mkdir -p $(CURDIR)/$(FRONTEND_RUN_DIR); \
		PORT=$(PORT_$(APP)); \
		if [ -z "$$PORT" ]; then \
			echo "✗ Unknown app port for $(APP)"; \
			exit 1; \
		fi; \
		echo "Checking port $$PORT..."; \
		PID=$$(lsof -ti:$$PORT 2>/dev/null); \
		if [ -n "$$PID" ]; then \
			echo "  Killing process $$PID on port $$PORT..."; \
			kill -9 $$PID 2>/dev/null || true; \
			sleep 0.5; \
			PID=$$(lsof -ti:$$PORT 2>/dev/null); \
			if [ -n "$$PID" ]; then \
				echo "  Retrying kill for $$PID..."; \
				kill -9 $$PID 2>/dev/null || true; \
				sleep 1; \
			fi; \
		fi; \
		PID=$$(lsof -ti:$$PORT 2>/dev/null); \
		if [ -n "$$PID" ]; then \
			echo "✗ Port $$PORT still in use by PID $$PID. Kill it manually: kill -9 $$PID"; \
			exit 1; \
		fi; \
		echo "  ✓ Port $$PORT is free"; \
		ln -sf ../.env $(CURDIR)/apps/$(APP)/frontend/.env 2>/dev/null || true; \
		cd $(CURDIR)/apps/$(APP)/frontend && pnpm dev > $(CURDIR)/$(FRONTEND_RUN_DIR)/$(APP)-frontend.log 2>&1 & \
		echo "  Stop: make down APP=$(APP)"; \
		echo "  Ctrl+C to detach (frontend keeps running)"; \
		echo ""; \
		sleep 1; \
		tail -f $(CURDIR)/$(FRONTEND_RUN_DIR)/$(APP)-frontend.log; \
	fi

down:
	@if [ "$(APP)" = "all" ]; then \
		echo "=========================================="; \
		echo "Stopping Complete System"; \
		echo "=========================================="; \
		echo ""; \
		echo "[1/3] Stopping all frontends..."; \
		for port in 5173 5174 3001 3002; do \
			lsof -ti:$$port | xargs kill -9 2>/dev/null || true; \
		done; \
		echo "  ✓ All frontend ports cleared"; \
		echo ""; \
		echo "[2/3] Stopping all backends..."; \
		for app in apps/*/; do \
			app_name=$$(basename $$app); \
			if [ -f "apps/$$app_name/Makefile" ]; then \
				echo "  ==> Stopping $$app_name..."; \
				cd apps/$$app_name && $(MAKE) down && cd ../..; \
			fi; \
		done; \
		echo ""; \
		echo "[3/3] Stopping shared infrastructure..."; \
		$(MAKE) down-shared; \
		echo ""; \
		echo "✓ Complete system stopped"; \
	else \
		if [ ! -d "$(APP_DIR)" ]; then \
			echo "Error: App '$(APP)' not found at $(APP_DIR)"; \
			exit 1; \
		fi; \
		echo "Stopping $(APP) frontend..."; \
		PORT=$(PORT_$(APP)); \
		if [ -n "$$PORT" ]; then \
			lsof -ti:$$PORT | xargs kill -9 2>/dev/null && echo "✓ Frontend stopped (port $$PORT)" || echo "ℹ Frontend was not running"; \
		fi; \
		echo "Stopping $(APP) backend..."; \
		cd $(APP_DIR) && $(MAKE) down; \
	fi

build:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) build

rebuild:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) rebuild

logs:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) logs

logs-frontend:
	$(check_app)
	@if [ -f "$(CURDIR)/$(FRONTEND_RUN_DIR)/$(APP)-frontend.log" ]; then \
		tail -f $(CURDIR)/$(FRONTEND_RUN_DIR)/$(APP)-frontend.log; \
	else \
		echo "No frontend logs found for $(APP)"; \
		echo "Start the app first: make up APP=$(APP)"; \
	fi

restart-frontend:
	$(check_app)
	@PORT=$(PORT_$(APP)); \
	if [ -z "$$PORT" ]; then \
		echo "✗ Unknown app port for $(APP)"; \
		exit 1; \
	fi; \
	echo "Restarting $(APP) frontend..."; \
	lsof -ti:$$PORT | xargs kill -9 2>/dev/null || true; \
	sleep 0.5; \
	mkdir -p $(CURDIR)/$(FRONTEND_RUN_DIR); \
	ln -sf ../.env $(CURDIR)/apps/$(APP)/frontend/.env 2>/dev/null || true; \
	cd $(CURDIR)/apps/$(APP)/frontend && pnpm dev > $(CURDIR)/$(FRONTEND_RUN_DIR)/$(APP)-frontend.log 2>&1 & \
	sleep 2; \
	if lsof -ti:$$PORT > /dev/null 2>&1; then \
		echo "✓ Frontend restarted on port $$PORT"; \
	else \
		echo "✗ Frontend failed to start. Check logs:"; \
		tail -20 $(CURDIR)/$(FRONTEND_RUN_DIR)/$(APP)-frontend.log; \
	fi

logs-service:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) logs-service service=$(service) tail=$(tail)

status:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) status

# Shared Infrastructure
up-shared:
	@echo "Starting shared infrastructure (nginx + cloudflare tunnel)..."
	@docker compose -f docker-compose.shared.yml up -d
	@echo ""
	@echo "✓ Shared infrastructure started!"
	@echo "  Gateway: http://localhost:8080/health"
	@echo "  Landing: http://localhost:8080/"

down-shared:
	@echo "Stopping shared infrastructure..."
	@docker compose -f docker-compose.shared.yml down
	@echo "✓ Shared infrastructure stopped"

restart-shared: down-shared up-shared

reload-nginx:
	@echo "Reloading nginx configuration..."
	@docker exec nginx nginx -s reload 2>/dev/null && echo "✓ Nginx reloaded successfully" || echo "✗ Error: Nginx not running (start it with 'make up-shared')"

logs-shared:
	@docker compose -f docker-compose.shared.yml logs -f

status-shared:
	@echo "=== Shared Infrastructure ==="
	@docker compose -f docker-compose.shared.yml ps

status-all:
	@echo "=========================================="
	@echo "System Status"
	@echo "=========================================="
	@echo ""
	@echo "=== Shared Infrastructure ==="
	@docker compose -f docker-compose.shared.yml ps 2>/dev/null || echo "  (not running)"
	@echo ""
	@for app in apps/*/; do \
		app_name=$$(basename $$app); \
		if [ -f "apps/$$app_name/docker-compose.local.yml" ]; then \
			echo "=== $$app_name Backend ==="; \
			cd apps/$$app_name && docker compose -f docker-compose.local.yml ps 2>/dev/null || echo "  (not running)"; \
			cd ../..; \
			echo ""; \
		fi; \
	done
	@echo "=========================================="
	@echo "Frontends (run locally):"
	@echo "  template:       cd apps/template/frontend && pnpm dev       → :5174"
	@echo "  template-react: cd apps/template-react/frontend && pnpm dev → :3001"
	@echo ""
	@echo "Access Points (via nginx):"
	@echo "  Gateway:        https://local.gramkit.dev/"
	@echo "  Template:       https://local.gramkit.dev/template/"
	@echo "  Template React: https://local.gramkit.dev/template-react/"
	@echo "=========================================="

# Shell access
shell-webhook:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) shell-webhook

shell-bot:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) shell-bot

# Database migrations
migration:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) migration msg="$(msg)"

upgrade:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) upgrade

downgrade:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) downgrade

# Linting & Testing
lint:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) lint

typecheck:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) typecheck

test:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) test

test-quick:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) test-quick

test-snapshots:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) test-snapshots

test-snapshots-update:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) test-snapshots-update

test-file:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) test-file file=$(file)

# Frontend schema generation (runs locally)
schema:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) schema

# Scripts
script:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) script name=$(name) args='$(args)'

script-list:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) script-list

# Docker cleanup
clean:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) clean

clean-build:
	$(check_app)
	@cd $(APP_DIR) && $(MAKE) clean-build

# Multi-app operations (aliases for backward compatibility)
all-up:
	@$(MAKE) up APP=all

all-down:
	@$(MAKE) down APP=all

all-test:
	@echo "Testing all apps..."
	@for app in apps/*/; do \
		app_name=$$(basename $$app); \
		if [ -f "apps/$$app_name/Makefile" ]; then \
			echo "==> Testing $$app_name..."; \
			cd apps/$$app_name && $(MAKE) test && cd ../..; \
		fi; \
	done

all-lint:
	@echo "Linting all apps..."
	@for app in apps/*/; do \
		app_name=$$(basename $$app); \
		if [ -f "apps/$$app_name/Makefile" ]; then \
			echo "==> Linting $$app_name..."; \
			cd apps/$$app_name && $(MAKE) lint && cd ../..; \
		fi; \
	done

# Version bumping (per-app)
bump-patch:
	$(check_app)
	@echo "Bumping patch version for $(APP)..."
	@cd $(APP_DIR) && $(MAKE) bump-patch

bump-minor:
	$(check_app)
	@echo "Bumping minor version for $(APP)..."
	@cd $(APP_DIR) && $(MAKE) bump-minor

bump-major:
	$(check_app)
	@echo "Bumping major version for $(APP)..."
	@cd $(APP_DIR) && $(MAKE) bump-major

# Release workflow (per-app)
release:
	$(check_app)
	@echo "Starting release process for $(APP)..."
	@CURRENT_BRANCH=$$(git branch --show-current); \
	if [ "$$CURRENT_BRANCH" != "dev" ]; then \
		echo "Error: Must be on dev branch for release. Current branch: $$CURRENT_BRANCH"; \
		exit 1; \
	fi; \
	read -p "Do you want to bump the version? (y/n): " bump; \
	if [ "$$bump" = "y" ] || [ "$$bump" = "Y" ]; then \
		echo "Select version bump type:"; \
		echo "  1) patch (x.x.X)"; \
		echo "  2) minor (x.X.0)"; \
		echo "  3) major (X.0.0)"; \
		read -p "Enter choice (1-3): " choice; \
		case $$choice in \
			1) BUMP_TYPE=patch ;; \
			2) BUMP_TYPE=minor ;; \
			3) BUMP_TYPE=major ;; \
			*) echo "Invalid choice. Aborting."; exit 1 ;; \
		esac; \
		echo "Bumping $(APP) version ($$BUMP_TYPE)..."; \
		cd $(APP_DIR) && python3 bump_version.py $$BUMP_TYPE; \
		VERSION=$$(python3 -c "import json; print(json.load(open('$(APP_DIR)/frontend/package.json'))['version'])"); \
		echo "New $(APP) version: $$VERSION"; \
		echo "Committing version bump..."; \
		git add .; \
		git commit -m "chore($(APP)): bump version to $$VERSION"; \
	else \
		VERSION="current"; \
	fi; \
	echo "Switching to main branch..."; \
	git checkout main; \
	echo "Merging dev into main..."; \
	git merge dev --no-edit; \
	if [ "$$VERSION" != "current" ]; then \
		echo "Creating git tag $(APP)-v$$VERSION..."; \
		git tag -a "$(APP)-v$$VERSION" -m "Release $(APP) v$$VERSION"; \
	fi; \
	echo "Pushing main to origin..."; \
	git push origin main; \
	if [ "$$VERSION" != "current" ]; then \
		echo "Pushing tag $(APP)-v$$VERSION..."; \
		git push origin "$(APP)-v$$VERSION"; \
	fi; \
	echo "Switching back to dev..."; \
	git checkout dev; \
	if [ "$$VERSION" != "current" ]; then \
		echo "✓ Release $(APP) v$$VERSION completed successfully!"; \
	else \
		echo "✓ Release $(APP) completed successfully!"; \
	fi

# Help command
help:
	@echo "=========================================="
	@echo "Monorepo Makefile - Multi-App Management"
	@echo "=========================================="
	@echo ""
	@echo "⚡ Frontends run LOCALLY (native Turbopack)"
	@echo "🐳 Backends run in Docker containers"
	@echo ""
	@echo "Available apps:"
	@ls -d apps/*/ 2>/dev/null | xargs -I {} basename {} | sed 's/^/  - /'
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Quick Start:"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  make up-shared                 # Start nginx (once)"
	@echo "  make up APP=template-react     # Start backend + frontend"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "App Commands (APP=<name>):"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  make up APP=<name>           - Start backend + frontend"
	@echo "  make down APP=<name>         - Stop backend + frontend"
	@echo "  make logs APP=<name>         - View backend logs"
	@echo "  make logs-frontend APP=<name> - View frontend logs"
	@echo "  make test APP=<name>         - Run backend tests"
	@echo "  make migration msg='...'     - Create migration"
	@echo "  make upgrade APP=<name>      - Apply migrations"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Shared Infrastructure:"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  make up-shared               - Start nginx + tunnel"
	@echo "  make down-shared             - Stop shared infra"
	@echo "  make reload-nginx            - Reload nginx config"
	@echo "  make status-all              - Show system status"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Frontend Ports:"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  template:       5174 (Vite)"
	@echo "  template-react: 3001 (Next.js)"
	@echo ""
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "Access Points:"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  https://local.gramkit.dev/template/"
	@echo "  https://local.gramkit.dev/template-react/"
	@echo "=========================================="
