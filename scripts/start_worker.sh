#!/usr/bin/env bash
# Start the notes-mcp pull worker. Reads secrets from macOS Keychain at runtime.
# Env vars override Keychain (so you can still use export in shell).
set -e
REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO_DIR"

if [ -d ".venv" ]; then
    # shellcheck source=/dev/null
    . .venv/bin/activate
fi
export PYTHONPATH="${REPO_DIR}/src:${PYTHONPATH:-}"

# Load helpers and Keychain (same script works when sourced from launchd)
COMMON="${REPO_DIR}/scripts/common.sh"
if [ -f "$COMMON" ]; then
    # shellcheck source=common.sh
    . "$COMMON"
    [ -z "${GITHUB_TOKEN:-}" ]          && export GITHUB_TOKEN="$(keychain_get "$NOTES_MCP_KEYCHAIN_SERVICE_GITHUB")"
    [ -z "${NOTES_QUEUE_GIST_ID:-}" ]   && export NOTES_QUEUE_GIST_ID="$(keychain_get "$NOTES_MCP_KEYCHAIN_SERVICE_GIST_ID")"
    [ -z "${NOTES_MCP_TOKEN:-}" ]      && export NOTES_MCP_TOKEN="$(keychain_get "$NOTES_MCP_KEYCHAIN_SERVICE_TOKEN")"
    [ -z "${NOTES_MCP_INGRESS_KEY:-}" ] && export NOTES_MCP_INGRESS_KEY="$(keychain_get "$NOTES_MCP_KEYCHAIN_SERVICE_INGRESS_KEY")"
fi

# Optional: allowed folders (no secret)
export NOTES_MCP_ALLOWED_FOLDERS="${NOTES_MCP_ALLOWED_FOLDERS:-MCP Inbox,RedHat,Personal}"

exec python3 -m notes_mcp.pull_worker
