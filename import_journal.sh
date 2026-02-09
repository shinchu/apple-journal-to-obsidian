#!/bin/bash
# Apple Journal → Obsidian daily note integration
# Preview with dry-run → confirm → execute

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_SCRIPT="$SCRIPT_DIR/import_journal.py"

usage() {
    echo "Usage: $0 <source-directory> [--vault <vault-path>]"
    echo ""
    echo "You can also set the vault path via the JOURNAL_OBSIDIAN_VAULT environment variable."
    exit 1
}

# Parse arguments
SOURCE_DIR=""
VAULT_ARGS=()

while [[ $# -gt 0 ]]; do
    case "$1" in
        --vault)
            VAULT_ARGS=("--vault" "${2:?--vault requires a path}")
            shift 2
            ;;
        -h|--help)
            usage
            ;;
        *)
            if [[ -z "$SOURCE_DIR" ]]; then
                SOURCE_DIR="$1"
            else
                echo "Error: unknown argument: $1" >&2
                usage
            fi
            shift
            ;;
    esac
done

if [[ -z "$SOURCE_DIR" ]]; then
    echo "Error: source directory is required" >&2
    usage
fi

echo "=== Apple Journal → Obsidian Import ==="
echo ""

# Step 1: dry-run
echo "--- Preview (dry-run) ---"
python3 "$PYTHON_SCRIPT" --source "$SOURCE_DIR" "${VAULT_ARGS[@]+"${VAULT_ARGS[@]}"}" --dry-run
echo ""

# Step 2: Confirm
read -rp "Proceed? (y/N): " answer
if [[ "$answer" != "y" && "$answer" != "Y" ]]; then
    echo "Cancelled."
    exit 0
fi

# Step 3: Execute
echo ""
echo "--- Executing ---"
python3 "$PYTHON_SCRIPT" --source "$SOURCE_DIR" "${VAULT_ARGS[@]+"${VAULT_ARGS[@]}"}"
echo ""
echo "Done!"
