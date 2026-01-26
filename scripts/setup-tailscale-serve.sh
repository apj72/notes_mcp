#!/bin/bash
# Setup Tailscale serve for ingress API
# Usage: ./scripts/setup-tailscale-serve.sh

TAILSCALE_BIN="/Applications/Tailscale.app/Contents/MacOS/tailscale"
PORT="${PORT:-8443}"

if [ ! -f "$TAILSCALE_BIN" ]; then
    echo "Error: Tailscale not found at $TAILSCALE_BIN" >&2
    echo "Please install Tailscale or update the path in this script" >&2
    exit 1
fi

echo "Setting up Tailscale serve for ingress API..."
echo ""

# Check if already configured
if sudo "$TAILSCALE_BIN" serve status 2>/dev/null | grep -q "http=8443"; then
    echo "Tailscale serve is already configured for port 8443"
    echo "To reset: sudo $TAILSCALE_BIN serve reset"
    exit 0
fi

# Configure serve
echo "Configuring Tailscale serve..."
sudo "$TAILSCALE_BIN" serve --bg --http=$PORT http://127.0.0.1:$PORT

if [ $? -eq 0 ]; then
    echo "✓ Tailscale serve configured successfully"
    echo ""
    echo "Your ingress API is now accessible at:"
    echo "  http://taila02178.ts.net:$PORT"
    echo ""
    echo "Test it:"
    echo "  curl http://taila02178.ts.net:$PORT/health"
else
    echo "✗ Failed to configure Tailscale serve" >&2
    exit 1
fi
