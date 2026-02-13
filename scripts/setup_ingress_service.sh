#!/usr/bin/env bash
# Setup notes-mcp ingress (Tailscale serve + uvicorn) as a macOS launchd service.
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# When in scripts/, repo is parent
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
INSTALL_DIR="${1:-$REPO_DIR}"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_DEST="$LAUNCH_AGENTS_DIR/com.notes-mcp.ingress.plist"

echo "Setting up notes-mcp ingress as a background service..."
echo ""

if [ ! -f "$REPO_DIR/scripts/start_ingress.sh" ]; then
    echo "Error: scripts/start_ingress.sh not found"
    exit 1
fi
chmod +x "$REPO_DIR/scripts/start_ingress.sh"

TEMPLATE="$REPO_DIR/com.notes-mcp.ingress.plist.template"
if [ -f "$TEMPLATE" ]; then
    sed "s|__INSTALL_DIR__|$INSTALL_DIR|g" "$TEMPLATE" > "$PLIST_DEST"
else
    echo "Error: $TEMPLATE not found"
    exit 1
fi

mkdir -p "$LAUNCH_AGENTS_DIR"
launchctl bootout "gui/$(id -u)/com.notes-mcp.ingress" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_DEST" 2>/dev/null || launchctl load "$PLIST_DEST"
echo "✓ Ingress service loaded. Tailscale serve is started by start_ingress.sh at run time."
