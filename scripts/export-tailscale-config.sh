#!/bin/bash
# Export current Tailscale serve configuration
# Usage: ./scripts/export-tailscale-config.sh

TAILSCALE_BIN="/Applications/Tailscale.app/Contents/MacOS/tailscale"

if [ ! -f "$TAILSCALE_BIN" ]; then
    echo "Error: Tailscale not found at $TAILSCALE_BIN" >&2
    exit 1
fi

echo "Current Tailscale serve configuration:"
echo "======================================"
echo ""

# Get current config
sudo "$TAILSCALE_BIN" serve get-config 2>/dev/null || {
    echo "Note: No serve config found (or error getting config)"
    echo ""
    echo "Current serve status:"
    sudo "$TAILSCALE_BIN" serve status
}

echo ""
echo ""
echo "To configure via admin console, use this JSON:"
echo "=============================================="
cat << 'EOF'
{
  "TCP": {
    "8443": {
      "HTTPS": false,
      "Handlers": {
        "HTTP": "http://127.0.0.1:8443"
      }
    }
  }
}
EOF
