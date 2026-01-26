#!/bin/bash
# Start the Notes MCP Ingress API service
# This script is called by launchd

# Get the directory of this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Source environment script if provided
if [ -n "$ENV_SCRIPT_PATH" ] && [ -f "$ENV_SCRIPT_PATH" ]; then
    source "$ENV_SCRIPT_PATH"
fi

# Also try to source start_worker.sh for environment variables
if [ -f "$PROJECT_ROOT/start_worker.sh" ]; then
    # Use a more robust method to source environment variables
    # Create a temp file to avoid process substitution issues in launchd
    TEMP_ENV=$(mktemp)
    grep "^export" "$PROJECT_ROOT/start_worker.sh" | sed 's/^export //' > "$TEMP_ENV"
    source "$TEMP_ENV"
    rm -f "$TEMP_ENV"
fi

# Activate virtual environment if it exists
if [ -d "$PROJECT_ROOT/venv" ]; then
    source "$PROJECT_ROOT/venv/bin/activate"
fi

# Set PYTHONPATH
export PYTHONPATH="$PROJECT_ROOT/src:$PYTHONPATH"

# Start uvicorn
exec python3 -m uvicorn notes_mcp.ingress:app \
    --host 127.0.0.1 \
    --port 8443 \
    --log-level info
