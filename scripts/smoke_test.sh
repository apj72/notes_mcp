#!/bin/bash
# Minimal smoke test for notes-mcp pull worker
# Tests: sign_job -> enqueue_job -> worker processes -> note created

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"

cd "$PROJECT_DIR"

# Check environment
if [ -z "$NOTES_MCP_TOKEN" ]; then
    echo "Error: NOTES_MCP_TOKEN not set"
    exit 1
fi

if [ -z "$NOTES_QUEUE_GIST_ID" ]; then
    echo "Error: NOTES_QUEUE_GIST_ID not set"
    exit 1
fi

if [ -z "$GITHUB_TOKEN" ]; then
    echo "Error: GITHUB_TOKEN not set"
    exit 1
fi

# Activate venv if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Set PYTHONPATH
export PYTHONPATH="src:$PYTHONPATH"

echo "Smoke Test: Notes MCP Pull Worker"
echo "=================================="
echo ""

# Generate a unique test note title
TEST_TITLE="Smoke Test $(date +%s)"
TEST_BODY="This is an automated smoke test. If you see this note, the system is working!"

echo "Step 1: Generating signed job..."
JOB_LINE=$(python3 -m notes_mcp.sign_job \
    --title "$TEST_TITLE" \
    --body "$TEST_BODY" \
    --folder "MCP Inbox")

if [ -z "$JOB_LINE" ]; then
    echo "Error: Failed to generate job"
    exit 1
fi

echo "✓ Job generated"
echo ""

echo "Step 2: Enqueuing job..."
if echo "$JOB_LINE" | python3 -m notes_mcp.enqueue_job; then
    echo "✓ Job enqueued"
else
    echo "Error: Failed to enqueue job"
    exit 1
fi

echo ""
echo "Step 3: Waiting for processing..."
echo "  (Worker should process within 15-30 seconds)"
echo ""
echo "To verify:"
echo "  1. Check Apple Notes for: '$TEST_TITLE'"
echo "  2. Check your Gist's results.jsonl for the result"
echo ""
echo "Smoke test job enqueued successfully!"
echo "Note: This test only verifies enqueueing works."
echo "      Full test requires the worker to be running."
