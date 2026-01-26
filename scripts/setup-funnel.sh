#!/bin/bash
# Setup Tailscale Funnel for public ChatGPT access
# Usage: ./scripts/setup-funnel.sh

TAILSCALE_BIN="/Applications/Tailscale.app/Contents/MacOS/tailscale"
PORT="${PORT:-8443}"

if [ ! -f "$TAILSCALE_BIN" ]; then
    echo "Error: Tailscale not found at $TAILSCALE_BIN" >&2
    exit 1
fi

echo "Setting up Tailscale Funnel for public access..."
echo ""

# Source environment from start_worker.sh if it exists
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
if [ -f "$PROJECT_ROOT/start_worker.sh" ]; then
    # Extract and source the NOTES_MCP_INGRESS_KEY line
    INGRESS_KEY_LINE=$(grep "^export NOTES_MCP_INGRESS_KEY=" "$PROJECT_ROOT/start_worker.sh" 2>/dev/null | grep -v "^#" | head -1)
    if [ -n "$INGRESS_KEY_LINE" ]; then
        eval "$INGRESS_KEY_LINE"
    fi
fi

# Check if ingress key is set
if [ -z "$NOTES_MCP_INGRESS_KEY" ]; then
    echo "⚠️  WARNING: NOTES_MCP_INGRESS_KEY is not set!"
    echo ""
    echo "For security, you should set an ingress key before making the service public."
    echo "Generate one with:"
    echo "  export NOTES_MCP_INGRESS_KEY=\"\$(openssl rand -hex 32)\""
    echo ""
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Exiting. Set NOTES_MCP_INGRESS_KEY and try again."
        exit 1
    fi
fi

# Check if local service is running
echo "Checking local service..."
if ! curl -s http://127.0.0.1:$PORT/health > /dev/null 2>&1; then
    echo "⚠️  Warning: Local service not responding on http://127.0.0.1:$PORT"
    echo "   Make sure the ingress service is running: ./start_ingress.sh"
    read -p "Continue anyway? (y/N) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Enable Funnel
echo ""
echo "Enabling Tailscale Funnel..."
# Funnel syntax: tailscale funnel --bg <target>
# Target can be port number or URL
sudo "$TAILSCALE_BIN" funnel --bg http://127.0.0.1:$PORT

if [ $? -eq 0 ]; then
    echo ""
    echo "✓ Funnel enabled!"
    echo ""
    echo "Public URL:"
    PUBLIC_URL=$("$TAILSCALE_BIN" funnel status 2>/dev/null | grep -o 'https://[^ ]*' | head -1)
    if [ -n "$PUBLIC_URL" ]; then
        echo "  $PUBLIC_URL"
        echo ""
        echo "Test it:"
        echo "  curl $PUBLIC_URL/health"
        echo ""
        echo "Use this URL in your ChatGPT Custom GPT action configuration."
        echo ""
        if [ -n "$NOTES_MCP_INGRESS_KEY" ]; then
            echo "Remember: ChatGPT requests must include header:"
            echo "  X-Notes-MCP-Key: $NOTES_MCP_INGRESS_KEY"
        else
            echo "⚠️  Remember to set NOTES_MCP_INGRESS_KEY for security!"
        fi
    else
        echo "  (Run 'tailscale funnel status' to see the URL)"
    fi
else
    echo "✗ Failed to enable Funnel" >&2
    exit 1
fi
