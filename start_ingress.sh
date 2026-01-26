#!/bin/bash
# Start the notes-mcp ingress API service
# This service provides an HTTP API for creating notes via Tailscale

cd "$(dirname "$0")"

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set PYTHONPATH
export PYTHONPATH="src:$PYTHONPATH"

# ============================================
# EDIT THESE VALUES WITH YOUR ACTUAL TOKENS
# ============================================
# Source environment variables from start_worker.sh if it exists
if [ -f "start_worker.sh" ]; then
    source <(grep "^export" start_worker.sh | sed 's/export //')
fi

# Optional: Set ingress key for additional security
# export NOTES_MCP_INGRESS_KEY="your-secret-key-here"

# Optional: Require confirmation for all notes
# export NOTES_MCP_REQUIRE_CONFIRM="true"

echo "Starting Notes MCP Ingress API on http://127.0.0.1:8443"
echo "Expose via Tailscale: sudo /Applications/Tailscale.app/Contents/MacOS/tailscale serve --bg --http=8443 http://127.0.0.1:8443"
echo ""

# Start uvicorn
exec python3 -m uvicorn notes_mcp.ingress:app \
    --host 127.0.0.1 \
    --port 8443 \
    --log-level info
