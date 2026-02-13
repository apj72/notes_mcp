#!/usr/bin/env bash
# Shared helpers for notes_mcp install/uninstall scripts.
# Sourced by scripts/start_worker.sh, scripts/start_ingress.sh, and install_macos.sh.
# Compatible with bash and zsh.

# Keychain service names (must match install_macos.sh and uninstall_macos.sh)
NOTES_MCP_KEYCHAIN_SERVICE_TOKEN="notes_mcp_token"
NOTES_MCP_KEYCHAIN_SERVICE_GITHUB="notes_mcp_github_token"
NOTES_MCP_KEYCHAIN_SERVICE_GIST_ID="notes_mcp_queue_gist_id"
NOTES_MCP_KEYCHAIN_SERVICE_INGRESS_KEY="notes_mcp_ingress_key"

# --- Logging ---
log_info()  { echo "[notes_mcp] $*"; }
log_ok()    { echo "[notes_mcp] ✓ $*"; }
log_warn()  { echo "[notes_mcp] ⚠ $*" >&2; }
log_err()   { echo "[notes_mcp] Error: $*" >&2; }
log_fatal() { echo "[notes_mcp] Fatal: $*" >&2; exit 1; }

# --- Keychain (macOS security CLI) ---
# Usage: keychain_get <service_name>
# Returns secret value or empty string.
keychain_get() {
    local service="${1:?}"
    security find-generic-password -s "$service" -w 2>/dev/null || true
}

# Usage: keychain_set <service_name> <value>
keychain_set() {
    local service="${1:?}"
    local value="${2:?}"
    local account="notes_mcp"
    security add-generic-password -s "$service" -a "$account" -w "$value" -U 2>/dev/null || \
    security delete-generic-password -s "$service" -a "$account" 2>/dev/null
    security add-generic-password -s "$service" -a "$account" -w "$value" -U
}

# Usage: keychain_delete <service_name>
keychain_delete() {
    local service="${1:?}"
    security delete-generic-password -s "$service" -a "notes_mcp" 2>/dev/null || true
}

# --- Command checks ---
cmd_exists() { command -v "$1" >/dev/null 2>&1; }
require_cmd() {
    if ! cmd_exists "$1"; then
        log_fatal "Required command not found: $1"
    fi
}

# --- macOS / arch ---
is_macos() {
    case "$(uname -s)" in
        Darwin) return 0 ;;
        *)      return 1 ;;
    esac
}

get_arch() {
    uname -m
}

# Homebrew path (Intel vs Apple Silicon)
get_brew_prefix() {
    if [ -d /opt/homebrew ]; then
        echo /opt/homebrew
    else
        echo /usr/local
    fi
}

# --- Xcode Command Line Tools ---
has_xcode_cli() {
    xcode-select -p >/dev/null 2>&1
}

# --- Network (best effort) ---
check_network() {
    if cmd_exists curl; then
        curl -fsS --connect-timeout 3 -o /dev/null https://api.github.com 2>/dev/null && return 0
    fi
    if cmd_exists ping; then
        ping -c 1 -t 2 8.8.8.8 >/dev/null 2>&1 && return 0
    fi
    return 1
}
