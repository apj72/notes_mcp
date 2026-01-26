#!/bin/bash
# Install the ingress service launchd plist
# Usage: ./scripts/install-ingress-service.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PLIST_SOURCE="$PROJECT_ROOT/docs/launchd/com.notes-mcp-ingress.plist"
PLIST_DEST="$HOME/Library/LaunchAgents/com.notes-mcp-ingress.plist"

echo "Installing Notes MCP Ingress service..."

# Check if plist exists
if [ ! -f "$PLIST_SOURCE" ]; then
    echo "Error: Source plist not found: $PLIST_SOURCE" >&2
    exit 1
fi

# Copy plist
echo "Copying plist to LaunchAgents..."
cp "$PLIST_SOURCE" "$PLIST_DEST"

# Update paths in plist (replace /Users/ajoyce with actual user home)
USER_HOME="$HOME"
sed -i '' "s|/Users/ajoyce|$USER_HOME|g" "$PLIST_DEST"

echo "Plist installed at: $PLIST_DEST"
echo ""
echo "Please review and edit the plist if needed:"
echo "  nano $PLIST_DEST"
echo ""
echo "Then load the service:"
echo "  launchctl bootstrap gui/\$(id -u) $PLIST_DEST"
echo ""
echo "Or for older macOS:"
echo "  launchctl load $PLIST_DEST"
echo ""
echo "Check status:"
echo "  launchctl list | grep notes-mcp-ingress"
