#!/bin/bash
#
# Sync Template Backend to Template-React Backend
#
# This script syncs all Python backend code from template to template-react,
# preserving app-specific configuration files.
#
# Usage:
#   ./scripts/sync-template-backends.sh           # Sync with confirmation
#   ./scripts/sync-template-backends.sh --dry-run # Preview changes
#   ./scripts/sync-template-backends.sh --force   # Skip confirmation
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Source and destination
SOURCE_DIR="$PROJECT_ROOT/apps/template-vue/backend"
DEST_DIR="$PROJECT_ROOT/apps/template-react/backend"

# Parse arguments
DRY_RUN=false
FORCE=false

for arg in "$@"; do
    case $arg in
        --dry-run)
            DRY_RUN=true
            shift
            ;;
        --force)
            FORCE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--dry-run] [--force]"
            echo ""
            echo "Options:"
            echo "  --dry-run    Preview changes without applying them"
            echo "  --force      Skip confirmation prompt"
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
if [[ ! -d "$SOURCE_DIR" ]]; then
    echo -e "${RED}Error: Source directory not found: $SOURCE_DIR${NC}"
    exit 1
fi

if [[ ! -d "$DEST_DIR" ]]; then
    echo -e "${RED}Error: Destination directory not found: $DEST_DIR${NC}"
    exit 1
fi

# Header
echo -e "${BLUE}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║         Template Backend Synchronization Script               ║${NC}"
echo -e "${BLUE}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo -e "${YELLOW}Source:${NC}      $SOURCE_DIR"
echo -e "${YELLOW}Destination:${NC} $DEST_DIR"
echo -e "${YELLOW}Mode:${NC}        $([ "$DRY_RUN" = true ] && echo "DRY RUN (preview only)" || echo "LIVE (will modify files)")"
echo ""

# Files and directories to sync (relative to backend/)
SYNC_PATHS=(
    "src/app/__init__.py"
    "src/app/config.py"
    "src/app/exceptions.py"
    "src/app/domain/"
    "src/app/infrastructure/"
    "src/app/schemas/"
    "src/app/scripts/"
    "src/app/services/"
    "src/app/tgbot/"
    "src/app/webhook/"
    "src/app/worker/"
    "src/worker_entry.py"
)

# Files to NEVER sync (app-specific)
EXCLUDE_PATTERNS=(
    "Dockerfile"
    "pyproject.toml"
    "docker-compose*.yml"
    ".env*"
    "migrations/"
    ".venv/"
    "__pycache__/"
    "*.pyc"
    ".pytest_cache/"
    ".ruff_cache/"
    ".import_linter_cache/"
    "*.egg-info/"
)

# Function to check if path should be excluded
should_exclude() {
    local path="$1"
    for pattern in "${EXCLUDE_PATTERNS[@]}"; do
        if [[ "$path" == *"$pattern"* ]]; then
            return 0 # true - should exclude
        fi
    done
    return 1 # false - should not exclude
}

# Count files to sync
total_files=0
changed_files=0
identical_files=0
new_files=0

echo -e "${BLUE}Analyzing files...${NC}"
echo ""

# Collect files to sync
declare -a files_to_sync=()
declare -a files_changed=()
declare -a files_new=()

for path in "${SYNC_PATHS[@]}"; do
    source_path="$SOURCE_DIR/$path"

    if [[ -f "$source_path" ]]; then
        # Single file
        if ! should_exclude "$path"; then
            dest_path="$DEST_DIR/$path"
            files_to_sync+=("$path")
            ((total_files++))

            if [[ ! -f "$dest_path" ]]; then
                files_new+=("$path")
                ((new_files++))
            elif ! cmp -s "$source_path" "$dest_path"; then
                files_changed+=("$path")
                ((changed_files++))
            else
                ((identical_files++))
            fi
        fi
    elif [[ -d "$source_path" ]]; then
        # Directory - find all files recursively
        while IFS= read -r -d '' file; do
            rel_path="${file#$SOURCE_DIR/}"

            if ! should_exclude "$rel_path"; then
                dest_file="$DEST_DIR/$rel_path"
                files_to_sync+=("$rel_path")
                ((total_files++))

                if [[ ! -f "$dest_file" ]]; then
                    files_new+=("$rel_path")
                    ((new_files++))
                elif ! cmp -s "$file" "$dest_file"; then
                    files_changed+=("$rel_path")
                    ((changed_files++))
                else
                    ((identical_files++))
                fi
            fi
        done < <(find "$source_path" -type f -print0)
    fi
done

# Summary
echo -e "${GREEN}Summary:${NC}"
echo "  Total files:     $total_files"
echo "  Identical:       $identical_files"
echo "  Changed:         $changed_files"
echo "  New:             $new_files"
echo ""

# Show changes
if [[ $changed_files -gt 0 ]]; then
    echo -e "${YELLOW}Changed files:${NC}"
    for file in "${files_changed[@]}"; do
        echo "  • $file"
    done
    echo ""
fi

if [[ $new_files -gt 0 ]]; then
    echo -e "${GREEN}New files:${NC}"
    for file in "${files_new[@]}"; do
        echo "  • $file"
    done
    echo ""
fi

# Exit if dry run
if [[ "$DRY_RUN" = true ]]; then
    echo -e "${BLUE}Dry run complete. No files were modified.${NC}"
    exit 0
fi

# Exit if nothing to sync
if [[ $changed_files -eq 0 && $new_files -eq 0 ]]; then
    echo -e "${GREEN}✓ All files are already in sync!${NC}"
    exit 0
fi

# Confirmation
if [[ "$FORCE" != true ]]; then
    echo -e "${YELLOW}This will modify $((changed_files + new_files)) files in template-react.${NC}"
    read -p "Continue? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo -e "${RED}Aborted.${NC}"
        exit 1
    fi
fi

# Perform sync
echo -e "${BLUE}Syncing files...${NC}"
echo ""

synced_count=0
error_count=0

for path in "${files_to_sync[@]}"; do
    source_file="$SOURCE_DIR/$path"
    dest_file="$DEST_DIR/$path"

    # Skip if identical
    if [[ -f "$dest_file" ]] && cmp -s "$source_file" "$dest_file"; then
        continue
    fi

    # Create parent directory if needed
    dest_dir="$(dirname "$dest_file")"
    if [[ ! -d "$dest_dir" ]]; then
        mkdir -p "$dest_dir"
    fi

    # Copy file
    if cp "$source_file" "$dest_file"; then
        echo -e "  ${GREEN}✓${NC} $path"
        ((synced_count++))
    else
        echo -e "  ${RED}✗${NC} $path"
        ((error_count++))
    fi
done

echo ""
echo -e "${GREEN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║                    Sync Complete!                              ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "  Files synced: $synced_count"
echo "  Errors:       $error_count"
echo ""

if [[ $error_count -eq 0 ]]; then
    echo -e "${YELLOW}Next steps:${NC}"
    echo "  1. Run diff check:  ./scripts/check-template-sync.sh"
    echo "  2. Run tests:       cd apps/template-react/backend && make test"
    echo "  3. Start services:  cd apps/template-react && docker-compose -f docker-compose.local.yml up -d"
    echo ""
    echo -e "${GREEN}✓ Sync successful!${NC}"
    exit 0
else
    echo -e "${RED}⚠ Sync completed with errors. Please review the output above.${NC}"
    exit 1
fi
