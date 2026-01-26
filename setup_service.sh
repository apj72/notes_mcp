#!/bin/bash
# Setup script for notes-mcp pull worker as a macOS launchd service

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PLIST_NAME="com.notes-mcp.worker.plist"
LAUNCH_AGENTS_DIR="$HOME/Library/LaunchAgents"
PLIST_SOURCE="$SCRIPT_DIR/$PLIST_NAME"
PLIST_DEST="$LAUNCH_AGENTS_DIR/$PLIST_NAME"

echo "Setting up notes-mcp pull worker as a background service..."
echo ""

# Check if start_worker.sh exists and is executable
if [ ! -f "$SCRIPT_DIR/start_worker.sh" ]; then
    echo "Error: start_worker.sh not found in $SCRIPT_DIR"
    exit 1
fi

chmod +x "$SCRIPT_DIR/start_worker.sh"
echo "✓ Made start_worker.sh executable"

# Create LaunchAgents directory if it doesn't exist
mkdir -p "$LAUNCH_AGENTS_DIR"
echo "✓ Created LaunchAgents directory"

# Copy plist file
cp "$PLIST_SOURCE" "$PLIST_DEST"
echo "✓ Copied plist to $PLIST_DEST"

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
