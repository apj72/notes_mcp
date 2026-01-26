#!/bin/bash
# Get your Tailscale hostname
# Usage: ./scripts/get-tailscale-hostname.sh

TAILSCALE_BIN="/Applications/Tailscale.app/Contents/MacOS/tailscale"

if [ ! -f "$TAILSCALE_BIN" ]; then
    echo "Error: Tailscale not found at $TAILSCALE_BIN" >&2
    exit 1
fi

echo "Your Tailscale hostname:"
"$TAILSCALE_BIN" status --json 2>/dev/null | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    dns_name = data.get('Self', {}).get('DNSName', '')
    if dns_name:
        print(dns_name)
    else:
        print('Hostname not found. Check Tailscale admin console.')
        sys.exit(1)
except Exception as e:
    print(f'Error: {e}', file=sys.stderr)
    sys.exit(1)
" 2>/dev/null

if [ $? -ne 0 ]; then
    echo ""
    echo "Alternative: Check your Tailscale admin console at:"
    echo "  https://login.tailscale.com/admin/machines"
    echo ""
    echo "Or use the IP address directly:"
    "$TAILSCALE_BIN" status | head -1 | awk '{print "  http://" $1 ":8443"}'
fi
