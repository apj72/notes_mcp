#!/bin/bash
# Clear the results.jsonl file in the Gist
# Usage: ./scripts/clear_results.sh

cd "$(dirname "$0")/.."

# Source environment
if [ -f "start_worker.sh" ]; then
    source <(grep "^export" start_worker.sh | sed 's/export //')
fi

# Check required environment variables
if [ -z "$NOTES_QUEUE_GIST_ID" ]; then
    echo "Error: NOTES_QUEUE_GIST_ID not set" >&2
    exit 1
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN not set" >&2
    exit 1
fi

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set PYTHONPATH
export PYTHONPATH="src:$PYTHONPATH"

# Get results filename
RESULTS_FILENAME="${NOTES_RESULTS_FILENAME:-results.jsonl}"

echo "Clearing $RESULTS_FILENAME in Gist $NOTES_QUEUE_GIST_ID..."
echo ""

# Use Python to clear the file
python3 << EOF
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from notes_mcp.pull_worker import fetch_gist_files, update_gist_file

gist_id = os.environ.get("NOTES_QUEUE_GIST_ID")
results_filename = os.environ.get("NOTES_RESULTS_FILENAME", "results.jsonl")

if not gist_id:
    print("Error: NOTES_QUEUE_GIST_ID not set", file=sys.stderr)
    sys.exit(1)

try:
    # Fetch current files to get SHA
    files = fetch_gist_files(gist_id)
    
    if results_filename not in files:
        print(f"Warning: {results_filename} not found in Gist")
        print("Nothing to clear.")
        sys.exit(0)
    
    # Get current SHA
    current_sha = files[results_filename]["sha"]
    
    # Clear the file (replace with empty content or just a comment)
    new_content = f"# Notes MCP Job Results\n# This file is automatically maintained by the pull worker.\n# DO NOT manually edit this file.\n"
    
    # Update the file
    success = update_gist_file(gist_id, results_filename, new_content, current_sha)
    
    if success:
        print(f"✓ Successfully cleared {results_filename}")
    else:
        print(f"✗ Failed to clear {results_filename} (concurrent modification, try again)", file=sys.stderr)
        sys.exit(1)
        
except Exception as e:
    print(f"Error: {e}", file=sys.stderr)
    sys.exit(1)
EOF
