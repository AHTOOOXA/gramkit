#!/bin/bash
#
# Check Template Backend Synchronization
#
# This script verifies that template and template-react backends are in sync.
# It reports differences and validates app-specific configuration.
#
# Usage:
#   ./scripts/check-template-sync.sh           # Full check
#   ./scripts/check-template-sync.sh --verbose # Show file-by-file comparison
#   ./scripts/check-template-sync.sh --quick   # Quick check (Python only)
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Paths
TEMPLATE_BACKEND="$PROJECT_ROOT/apps/template-vue/backend"
TEMPLATE_REACT_BACKEND="$PROJECT_ROOT/apps/template-react/backend"

# Parse arguments
VERBOSE=false
QUICK=false

for arg in "$@"; do
    case $arg in
        --verbose|-v)
            VERBOSE=true
            shift
            ;;
        --quick|-q)
            QUICK=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--verbose] [--quick]"
            echo ""
            echo "Options:"
            echo "  --verbose    Show detailed file-by-file comparison"
            echo "  --quick      Quick check (Python files only)"
            echo "  --help       Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $arg${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Validation
if [[ ! -d "$TEMPLATE_BACKEND" ]]; then
    echo -e "${RED}Error: Template backend not found: $TEMPLATE_BACKEND${NC}"
    exit 1
fi

if [[ ! -d "$TEMPLATE_REACT_BACKEND" ]]; then
    echo -e "${RED}Error: Template-React backend not found: $TEMPLATE_REACT_BACKEND${NC}"
    exit 1
fi

# Header
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Template Backend Sync Verification                     ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Counters
total_checked=0
identical_files=0
different_files=0
missing_files=0
unexpected_diffs=0

# Expected differences (stored as simple variables)
EXPECTED_DIFF_DOCKERFILE="App name and paths (GOOD)"
EXPECTED_DIFF_PYPROJECT="Package name only (GOOD)"

# Files to check
PYTHON_FILES=(
    "src/app/__init__.py"
    "src/app/config.py"
    "src/app/exceptions.py"
    "src/app/domain/__init__.py"
    "src/app/domain/products.py"
    "src/app/infrastructure/__init__.py"
    "src/app/infrastructure/database/__init__.py"
    "src/app/infrastructure/database/setup.py"
    "src/app/infrastructure/database/models/__init__.py"
    "src/app/infrastructure/database/models/balance.py"
    "src/app/infrastructure/database/repo/__init__.py"
    "src/app/infrastructure/database/repo/balance.py"
    "src/app/infrastructure/database/repo/requests.py"
    "src/app/schemas/__init__.py"
    "src/app/scripts/__init__.py"
    "src/app/scripts/demo_user_stats.py"
    "src/app/services/__init__.py"
    "src/app/services/base.py"
    "src/app/services/balance.py"
    "src/app/services/requests.py"
    "src/app/services/statistics.py"
    "src/app/services/notifications/__init__.py"
    "src/app/services/notifications/service.py"
    "src/app/services/notifications/templates.py"
    "src/app/tgbot/__init__.py"
    "src/app/tgbot/bot.py"
    "src/app/tgbot/handlers/__init__.py"
    "src/app/tgbot/handlers/admin.py"
    "src/app/tgbot/handlers/start.py"
    "src/app/tgbot/keyboards/keyboards.py"
    "src/app/tgbot/keyboards/notification_keyboards.py"
    "src/app/webhook/__init__.py"
    "src/app/webhook/app.py"
    "src/app/webhook/auth.py"
    "src/app/webhook/dependencies/arq.py"
    "src/app/webhook/dependencies/bot.py"
    "src/app/webhook/dependencies/database.py"
    "src/app/webhook/dependencies/rabbit.py"
    "src/app/webhook/dependencies/redis.py"
    "src/app/webhook/dependencies/service.py"
    "src/app/webhook/middlewares/__init__.py"
    "src/app/webhook/routers/__init__.py"
    "src/app/webhook/routers/admin.py"
    "src/app/webhook/routers/base.py"
    "src/app/webhook/admin/__init__.py"
    "src/app/webhook/admin/users.py"
    "src/app/worker/__init__.py"
    "src/app/worker/worker.py"
    "src/app/worker/jobs.py"
    "src/worker_entry.py"
)

CONFIG_FILES=(
    "Dockerfile"
    "pyproject.toml"
)

# Check Python files
echo -e "${CYAN}Checking Python files...${NC}"
echo ""

declare -a python_diffs=()
declare -a python_missing=()

for file in "${PYTHON_FILES[@]}"; do
    template_file="$TEMPLATE_BACKEND/$file"
    react_file="$TEMPLATE_REACT_BACKEND/$file"

    ((total_checked++))

    if [[ ! -f "$template_file" ]]; then
        if [[ "$VERBOSE" = true ]]; then
            echo -e "  ${YELLOW}SKIP${NC} $file (not in template)"
        fi
        continue
    fi

    if [[ ! -f "$react_file" ]]; then
        python_missing+=("$file")
        ((missing_files++))
        if [[ "$VERBOSE" = true ]]; then
            echo -e "  ${RED}MISS${NC} $file"
        fi
        continue
    fi

    if cmp -s "$template_file" "$react_file"; then
        ((identical_files++))
        if [[ "$VERBOSE" = true ]]; then
            echo -e "  ${GREEN}✓${NC} $file"
        fi
    else
        python_diffs+=("$file")
        ((different_files++))
        ((unexpected_diffs++))
        if [[ "$VERBOSE" = true ]]; then
            echo -e "  ${RED}✗${NC} $file"
        fi
    fi
done

# Check config files (should be different)
if [[ "$QUICK" != true ]]; then
    echo ""
    echo -e "${CYAN}Checking configuration files...${NC}"
    echo ""

    for file in "${CONFIG_FILES[@]}"; do
        template_file="$TEMPLATE_BACKEND/$file"
        react_file="$TEMPLATE_REACT_BACKEND/$file"

        ((total_checked++))

        if [[ ! -f "$template_file" ]] || [[ ! -f "$react_file" ]]; then
            if [[ "$VERBOSE" = true ]]; then
                echo -e "  ${YELLOW}SKIP${NC} $file (missing)"
            fi
            continue
        fi

        if cmp -s "$template_file" "$react_file"; then
            echo -e "  ${RED}WARN${NC} $file - SHOULD be different but is identical!"
            ((unexpected_diffs++))
        else
            # Validate that ONLY expected lines differ
            case "$file" in
                "Dockerfile")
                    # Check Dockerfile - template has single-stage, template-react has multi-stage
                    # This is a known architectural difference (acceptable)
                    # Just verify both files exist and differ (don't validate structure)

                    # Count lines that differ after normalizing app names
                    diff_count=$(diff \
                        <(sed 's/tarot/APP/g; s/template/APP/g' "$template_file") \
                        <(sed 's/template-react/APP/g' "$react_file") \
                        2>&1 | grep -E "^[<>]" | wc -l | tr -d ' ')

                    # Template-react has multi-stage build, so expect structural differences
                    # Just verify they're not identical
                    if [[ "$diff_count" -gt "0" ]]; then
                        if [[ "$VERBOSE" = true ]]; then
                            echo -e "  ${GREEN}✓${NC} $file - Different (template: single-stage, template-react: multi-stage)"
                        else
                            echo -e "  ${GREEN}✓${NC} $file - Different (GOOD - known architectural difference)"
                        fi
                    else
                        echo -e "  ${YELLOW}⚠${NC} $file - Files are identical (should differ)"
                        ((unexpected_diffs++))
                    fi
                    ;;
                "pyproject.toml")
                    # Check pyproject.toml - should only differ in package name
                    diff_lines=$(diff "$template_file" "$react_file" | grep '^[<>]' | wc -l | tr -d ' ')

                    # Should only have 2 lines different (the 'name =' line)
                    if [[ "$diff_lines" -eq "2" ]]; then
                        # Verify it's the name field
                        name_diff=$(diff "$template_file" "$react_file" | grep 'name = ' || echo "")
                        if [[ -n "$name_diff" ]]; then
                            echo -e "  ${GREEN}✓${NC} $file - Only package name differs (GOOD)"
                        else
                            echo -e "  ${YELLOW}⚠${NC} $file - Has unexpected differences!"
                            ((unexpected_diffs++))
                        fi
                    else
                        echo -e "  ${YELLOW}⚠${NC} $file - Has $diff_lines differing lines (expected 2)"
                        if [[ "$VERBOSE" = true ]]; then
                            diff "$template_file" "$react_file" | grep '^[<>]' | head -10 | sed 's/^/      /'
                        fi
                        ((unexpected_diffs++))
                    fi
                    ;;
            esac
        fi
    done
fi

# Summary
echo ""
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║                         Summary                                ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "Total files checked:    $total_checked"
echo "Identical:              $identical_files"
echo "Different (unexpected): $different_files"
echo "Missing:                $missing_files"
echo ""

# Show problems
has_issues=false

if [[ $different_files -gt 0 ]]; then
    has_issues=true
    echo -e "${RED}⚠ Python files that differ (should be identical):${NC}"
    for file in "${python_diffs[@]}"; do
        echo "  • $file"
        if [[ "$VERBOSE" = true ]]; then
            echo -e "${YELLOW}    Diff preview:${NC}"
            diff -u "$TEMPLATE_BACKEND/$file" "$TEMPLATE_REACT_BACKEND/$file" | head -20 | sed 's/^/    /'
            echo ""
        fi
    done
    echo ""
    echo -e "${YELLOW}To fix:${NC} ./scripts/sync-template-backends.sh"
    echo ""
fi

if [[ $missing_files -gt 0 ]]; then
    has_issues=true
    echo -e "${RED}⚠ Missing files in template-react:${NC}"
    for file in "${python_missing[@]}"; do
        echo "  • $file"
    done
    echo ""
    echo -e "${YELLOW}To fix:${NC} ./scripts/sync-template-backends.sh"
    echo ""
fi

# Port allocation check
if [[ "$QUICK" != true ]]; then
    echo -e "${CYAN}Checking port allocation...${NC}"
    echo ""

    template_env="$PROJECT_ROOT/apps/template-vue/.env"
    react_env="$PROJECT_ROOT/apps/template-react/.env"

    if [[ -f "$template_env" ]] && [[ -f "$react_env" ]]; then
        # Extract ports
        t_webhook=$(grep "8002:8000" "$PROJECT_ROOT/apps/template-vue/docker-compose.local.yml" || echo "")
        r_webhook=$(grep "8003:8000" "$PROJECT_ROOT/apps/template-react/docker-compose.local.yml" || echo "")

        t_redis=$(grep "REDIS_PORT=" "$template_env" | cut -d'=' -f2)
        r_redis=$(grep "REDIS_PORT=" "$react_env" | cut -d'=' -f2)

        # Validate pattern (template-react should be template + 1)
        port_issues=false

        if [[ -z "$r_webhook" ]]; then
            echo -e "  ${RED}✗${NC} Webhook port should be 8003 (template: 8002)"
            port_issues=true
            has_issues=true
        else
            echo -e "  ${GREEN}✓${NC} Webhook port: 8003 (template: 8002)"
        fi

        if [[ "$r_redis" != "6391" ]]; then
            echo -e "  ${RED}✗${NC} Redis port should be 6391 (template: 6390, got: $r_redis)"
            port_issues=true
            has_issues=true
        else
            echo -e "  ${GREEN}✓${NC} Redis port: 6391 (template: 6390)"
        fi

        echo ""
    fi
fi

# Docker-compose check
if [[ "$QUICK" != true ]]; then
    echo -e "${CYAN}Checking docker-compose bot/worker commands...${NC}"
    echo ""

    template_dc="$PROJECT_ROOT/apps/template-vue/docker-compose.local.yml"
    react_dc="$PROJECT_ROOT/apps/template-react/docker-compose.local.yml"

    # Check if both use hot_reload.py
    if grep -q "hot_reload.py" "$template_dc" && grep -q "hot_reload.py" "$react_dc"; then
        echo -e "  ${GREEN}✓${NC} Both use hot_reload.py for bot/worker"
    else
        echo -e "  ${RED}✗${NC} Bot/worker should use hot_reload.py"
        has_issues=true
    fi

    # Check if react uses correct paths
    if grep -q "template-react" "$react_dc"; then
        echo -e "  ${GREEN}✓${NC} Template-react paths are correct"
    else
        echo -e "  ${RED}✗${NC} Docker-compose should use template-react paths"
        has_issues=true
    fi

    echo ""
fi

# Final result
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
if [[ "$has_issues" = false ]]; then
    echo -e "${BLUE}║${GREEN}                    ✓ All Checks Passed!                       ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${GREEN}Template and template-react backends are in sync.${NC}"
    exit 0
else
    echo -e "${BLUE}║${RED}                    ⚠ Issues Found!                            ${BLUE}║${NC}"
    echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
    echo ""
    echo -e "${YELLOW}Run './scripts/sync-template-backends.sh' to fix sync issues.${NC}"
    exit 1
fi
