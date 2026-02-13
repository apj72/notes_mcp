#!/bin/bash
# Setup script for notes-mcp pull worker as a macOS launchd service.
# Usage: ./setup_service.sh [INSTALL_DIR]  (default: repo root)

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# When setup_service.sh is in repo root, SCRIPT_DIR is the repo
REPO_DIR="${SCRIPT_DIR}"
INSTALL_DIR="${1:-$REPO_DIR}"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_DEST="$LAUNCH_AGENTS_DIR/com.notes-mcp.worker.plist"

echo "Setting up notes-mcp pull worker as a background service..."
echo ""

# Prefer scripts/start_worker.sh (Keychain-based); fallback to repo root start_worker.sh
START_SCRIPT="$REPO_DIR/scripts/start_worker.sh"
if [ ! -f "$START_SCRIPT" ]; then
    START_SCRIPT="$REPO_DIR/start_worker.sh"
fi
if [ ! -f "$START_SCRIPT" ]; then
    echo "Error: start_worker.sh not found in $REPO_DIR or $REPO_DIR/scripts"
    exit 1
fi

chmod +x "$START_SCRIPT"
echo "✓ Made start_worker.sh executable"

mkdir -p "$LAUNCH_AGENTS_DIR"
TEMPLATE="$REPO_DIR/com.notes-mcp.worker.plist.template"
if [ -f "$TEMPLATE" ]; then
    sed "s|__INSTALL_DIR__|$INSTALL_DIR|g" "$TEMPLATE" > "$PLIST_DEST"
    echo "✓ Installed plist to $PLIST_DEST"
else
    # Legacy: copy plist if it exists (no template)
    if [ -f "$REPO_DIR/com.notes-mcp.worker.plist" ]; then
        cp "$REPO_DIR/com.notes-mcp.worker.plist" "$PLIST_DEST"
        echo "✓ Copied plist to $PLIST_DEST"
    else
        echo "Error: neither $TEMPLATE nor com.notes-mcp.worker.plist found"
        exit 1
    fi
fi

# Unload if already loaded (try both old and new methods)
if launchctl list | grep -q "com.notes-mcp.worker"; then
    echo "Unloading existing service..."
    # Try new method first (macOS 13+)
    launchctl bootout gui/$(id -u)/com.notes-mcp.worker 2>/dev/null || \
    # Fall back to old method
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# Load the service (use bootstrap for newer macOS)
echo "Loading service..."
# Try new method first (macOS 13+)
if launchctl bootstrap gui/$(id -u) "$PLIST_DEST" 2>/dev/null; then
    echo "✓ Service loaded (using bootstrap)"
    # Start it immediately
    launchctl kickstart -k gui/$(id -u)/com.notes-mcp.worker 2>/dev/null || true
else
    # Fall back to old method (older macOS)
    launchctl load "$PLIST_DEST"
    echo "✓ Service loaded (using load)"
fi

echo ""
echo "Service setup complete!"
echo ""
echo "To check status:"
echo "  launchctl list | grep notes-mcp"
echo ""
echo "To view logs:"
echo "  tail -f /tmp/notes-mcp-worker.out"
echo "  tail -f /tmp/notes-mcp-worker.err"
echo ""
echo "To stop the service:"
echo "  launchctl bootout gui/\$(id -u)/com.notes-mcp.worker  # macOS 13+"
echo "  # or: launchctl stop com.notes-mcp.worker  # older macOS"
echo ""
echo "To start the service:"
echo "  launchctl kickstart -k gui/\$(id -u)/com.notes-mcp.worker  # macOS 13+"
echo "  # or: launchctl start com.notes-mcp.worker  # older macOS"
echo ""
echo "To unload (disable) the service:"
echo "  launchctl bootout gui/\$(id -u)/com.notes-mcp.worker  # macOS 13+"
echo "  # or: launchctl unload $PLIST_DEST  # older macOS"
echo ""
