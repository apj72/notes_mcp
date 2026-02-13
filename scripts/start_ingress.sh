#!/usr/bin/env bash
# Start the notes-mcp ingress API and Tailscale serve. Reads secrets from Keychain at runtime.
set -e
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

if [ -d ".venv" ]; then
    # shellcheck source=/dev/null
    . .venv/bin/activate
fi
export PYTHONPATH="${REPO_DIR}/src:${PYTHONPATH:-}"

COMMON="${REPO_DIR}/scripts/common.sh"
if [ -f "$COMMON" ]; then
    # shellcheck source=common.sh
    . "$COMMON"
    [ -z "${GITHUB_TOKEN:-}" ]          && export GITHUB_TOKEN="$(keychain_get "$NOTES_MCP_KEYCHAIN_SERVICE_GITHUB")"
    [ -z "${NOTES_QUEUE_GIST_ID:-}" ]   && export NOTES_QUEUE_GIST_ID="$(keychain_get "$NOTES_MCP_KEYCHAIN_SERVICE_GIST_ID")"
    [ -z "${NOTES_MCP_TOKEN:-}" ]       && export NOTES_MCP_TOKEN="$(keychain_get "$NOTES_MCP_KEYCHAIN_SERVICE_TOKEN")"
    [ -z "${NOTES_MCP_INGRESS_KEY:-}" ] && export NOTES_MCP_INGRESS_KEY="$(keychain_get "$NOTES_MCP_KEYCHAIN_SERVICE_INGRESS_KEY")"
fi
export NOTES_MCP_ALLOWED_FOLDERS="${NOTES_MCP_ALLOWED_FOLDERS:-MCP Inbox,RedHat,Personal}"

# Tailscale serve (optional): expose 8443 over tailnet when logged in
if command -v tailscale >/dev/null 2>&1 && tailscale status >/dev/null 2>&1; then
    tailscale serve --bg --http=8443 http://127.0.0.1:8443 2>/dev/null || true
fi

exec python3 -m uvicorn notes_mcp.ingress:app --host 127.0.0.1 --port 8443 --log-level info
