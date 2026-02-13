#!/usr/bin/env zsh
# Uninstall notes_mcp launchd services and optionally Keychain entries.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
# shellcheck source=common.sh
source "$REPO_DIR/scripts/common.sh"

LAUNCH_AGENTS="$HOME/Library/LaunchAgents"

log_info "Unloading launchd services..."
for label in com.notes-mcp.worker com.notes-mcp.ingress; do
    if launchctl print "gui/$(id -u)/$label" &>/dev/null; then
        launchctl bootout "gui/$(id -u)/$label" 2>/dev/null || launchctl unload "$LAUNCH_AGENTS/$label.plist" 2>/dev/null || true
        log_ok "Unloaded $label"
    fi
done

# Remove plists we may have installed
for name in com.notes-mcp.worker com.notes-mcp.ingress; do
    if [[ -f "$LAUNCH_AGENTS/$name.plist" ]]; then
        rm -f "$LAUNCH_AGENTS/$name.plist"
        log_ok "Removed $LAUNCH_AGENTS/$name.plist"
    fi
done

# Tailscale serve: best-effort turn off (same port)
if command -v tailscale &>/dev/null; then
    tailscale serve --bg --http=8443 off 2>/dev/null || true
    log_ok "Tailscale serve disabled (best effort)"
fi

echo ""
read -q "confirm?Remove Keychain entries (notes_mcp secrets)? [y/N] "
echo ""
if [[ "$confirm" == [yY] ]]; then
    keychain_delete "$NOTES_MCP_KEYCHAIN_SERVICE_TOKEN"
    keychain_delete "$NOTES_MCP_KEYCHAIN_SERVICE_GITHUB"
    keychain_delete "$NOTES_MCP_KEYCHAIN_SERVICE_GIST_ID"
    keychain_delete "$NOTES_MCP_KEYCHAIN_SERVICE_INGRESS_KEY"
    log_ok "Keychain entries removed"
else
    log_info "Keychain entries left in place."
fi

log_ok "Uninstall complete."
