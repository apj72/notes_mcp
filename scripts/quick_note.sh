#!/bin/bash
# Quick note creation script
# Usage: ./scripts/quick_note.sh "Title" "Body" ["Folder"]
# ChatGPT can suggest this as an alternative to curl

cd "$(dirname "$0")/.."

# Source environment
if [ -f "start_worker.sh" ]; then
    source <(grep "^export" start_worker.sh | sed 's/export //')
fi

TITLE="$1"
BODY="$2"
FOLDER="${3:-MCP Inbox}"

if [ -z "$TITLE" ] || [ -z "$BODY" ]; then
    echo "Usage: $0 \"Title\" \"Body\" [\"Folder\"]" >&2
    exit 1
fi

if [ -z "$NOTES_MCP_INGRESS_KEY" ]; then
    echo "Error: NOTES_MCP_INGRESS_KEY not set" >&2
    echo "Set it with: export NOTES_MCP_INGRESS_KEY=\"your-key\"" >&2
    exit 1
fi

# Get Funnel URL (or use default)
FUNNEL_URL="${NOTES_MCP_FUNNEL_URL:-https://notes-mcp-ingress.taila02178.ts.net}"

curl -X POST "$FUNNEL_URL/notes" \
  -H "Content-Type: application/json" \
  -H "X-Notes-MCP-Key: $NOTES_MCP_INGRESS_KEY" \
  -d "{\"title\": \"$TITLE\", \"body\": \"$BODY\", \"folder\": \"$FOLDER\"}" \
  | python3 -m json.tool 2>/dev/null || cat

echo ""
