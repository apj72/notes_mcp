#!/usr/bin/env zsh
# One-command bootstrap installer for notes_mcp on macOS.
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/apj72/notes_mcp/main/scripts/install_macos.sh | zsh
#   zsh scripts/install_macos.sh [--install-dir DIR] [--force] [--skip-tailscale] [--skip-brew] [--non-interactive]
set -euo pipefail

# Parse args (will re-parse after re-exec when run from repo)
INSTALL_DIR="${INSTALL_DIR:-$HOME/notes_mcp}"
FORCE=false
SKIP_TAILSCALE=false
SKIP_BREW=false
NON_INTERACTIVE=false

# When run via curl-pipe we're not in a git repo; clone and re-exec with same args
RUN_FROM_REPO=false
SCRIPT_DIR="$(cd "$(dirname "$0")" 2>/dev/null && pwd)"
if [[ -n "$SCRIPT_DIR" && -f "$SCRIPT_DIR/common.sh" ]]; then
    REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
    if [[ -d "$REPO_DIR/.git" ]]; then
        RUN_FROM_REPO=true
    fi
fi

if [[ "$RUN_FROM_REPO" != true ]]; then
    # Bootstrap: only parse --install-dir and --help for initial clone
    for arg in "$@"; do
        if [[ "$arg" == --help ]]; then
            echo "Usage: $0 [OPTIONS]"
            echo "  --install-dir <path>   Install directory (default: ~/notes_mcp)"
            echo "  --force                Overwrite Keychain entries and reinstall"
            echo "  --skip-tailscale       Skip Tailscale install and serve config"
            echo "  --skip-brew            Assume Homebrew and deps are installed"
            echo "  --non-interactive      Fail if required values missing (no prompts)"
            echo "  --help                 Show this help"
            exit 0
        fi
        if [[ "$arg" == --install-dir ]]; then
            INSTALL_DIR_NEXT=true
        elif [[ "${INSTALL_DIR_NEXT:-false}" == true ]]; then
            INSTALL_DIR="$arg"
            INSTALL_DIR_NEXT=false
        fi
    done
    echo "[notes_mcp] Running from curl pipe or non-repo; will clone to $INSTALL_DIR and re-run."
    if ! xcode-select -p &>/dev/null; then
        echo "Xcode Command Line Tools are required. Install with: xcode-select --install"
        exit 1
    fi
    if [[ ! -d "$INSTALL_DIR" ]]; then
        git clone https://github.com/apj72/notes_mcp.git "$INSTALL_DIR"
    else
        (cd "$INSTALL_DIR" && git pull --rebase origin main || true)
    fi
    exec zsh "$INSTALL_DIR/scripts/install_macos.sh" "$@"
fi

# From repo: parse all options
while [[ $# -gt 0 ]]; do
    case "$1" in
        --install-dir) INSTALL_DIR="$2"; shift 2 ;;
        --force) FORCE=true; shift ;;
        --skip-tailscale) SKIP_TAILSCALE=true; shift ;;
        --skip-brew) SKIP_BREW=true; shift ;;
        --non-interactive) NON_INTERACTIVE=true; shift ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "  --install-dir <path>   Install directory (default: ~/notes_mcp)"
            echo "  --force                Overwrite Keychain entries and reinstall"
            echo "  --skip-tailscale       Skip Tailscale install and serve config"
            echo "  --skip-brew            Assume Homebrew and deps are installed"
            echo "  --non-interactive      Fail if required values missing (no prompts)"
            echo "  --help                 Show this help"
            exit 0
            ;;
        *) shift ;;  # ignore unknown when re-exec from clone
    esac
done

# From here we run from the repo
REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_DIR"
# shellcheck source=common.sh
source "$REPO_DIR/scripts/common.sh"

# --- Pre-flight ---
log_info "Pre-flight checks..."
if ! is_macos; then
    log_fatal "This installer is for macOS only."
fi
if ! has_xcode_cli; then
    log_err "Xcode Command Line Tools not found."
    echo "Run: xcode-select --install"
    echo "Then re-run this installer."
    exit 1
fi
log_ok "Xcode Command Line Tools found"
if ! check_network; then
    log_warn "Network check failed; continuing anyway."
else
    log_ok "Network reachable"
fi

# --- Prerequisites ---
if [[ "$SKIP_BREW" != true ]]; then
    if ! cmd_exists brew; then
        log_info "Installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        eval "$(get_brew_prefix)/bin/brew shellenv"
    fi
    # Ensure brew is on PATH (e.g. after install or in new shell)
    eval "$(get_brew_prefix)/bin/brew shellenv" 2>/dev/null || true
    log_ok "Homebrew ready"
    brew install git
    brew install python@3.11
    if [[ "$SKIP_TAILSCALE" != true ]]; then
        brew install --cask tailscale 2>/dev/null || true
    fi
else
    require_cmd git
    require_cmd python3
fi

# --- Python venv (must use 3.11+; pyproject.toml requires >=3.11) ---
log_info "Setting up Python environment..."
PYTHON311=""
# Check fixed Homebrew paths first (re-exec'd shell often has no brew on PATH)
for p in /opt/homebrew/opt/python@3.11/bin/python3.11 /usr/local/opt/python@3.11/bin/python3.11 \
         /opt/homebrew/opt/python@3.12/bin/python3.12 /usr/local/opt/python@3.12/bin/python3.12; do
    if [[ -x "$p" ]]; then
        PYTHON311="$p"
        break
    fi
done
if [[ -z "$PYTHON311" ]]; then
    # Try full path to brew (re-exec'd shell often has no brew on PATH)
    for brew_cmd in /opt/homebrew/bin/brew /usr/local/bin/brew; do
        if [[ -x "$brew_cmd" ]]; then
            BREW_PREFIX="$("$brew_cmd" --prefix python@3.11 2>/dev/null)"
            if [[ -n "$BREW_PREFIX" && -x "$BREW_PREFIX/bin/python3.11" ]]; then
                PYTHON311="$BREW_PREFIX/bin/python3.11"
                break
            fi
            BREW_PREFIX="$("$brew_cmd" --prefix python@3.12 2>/dev/null)"
            if [[ -n "$BREW_PREFIX" && -x "$BREW_PREFIX/bin/python3.12" ]]; then
                PYTHON311="$BREW_PREFIX/bin/python3.12"
                break
            fi
        fi
    done
fi
if [[ -z "$PYTHON311" ]] && cmd_exists brew; then
    BREW_PREFIX="$(brew --prefix 2>/dev/null)"
    for p in "$BREW_PREFIX/opt/python@3.11/bin/python3.11" "$BREW_PREFIX/opt/python@3.12/bin/python3.12"; do
        if [[ -x "$p" ]]; then
            PYTHON311="$p"
            break
        fi
    done
fi
if [[ -z "$PYTHON311" ]]; then
    if python3 -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
        PYTHON311="python3"
    fi
fi
if [[ -z "$PYTHON311" ]]; then
    log_fatal "Python 3.11+ required (notes-mcp requires >=3.11). Install with: brew install python@3.11"
fi
# Recreate venv if it exists but was made with Python < 3.11
if [[ -d "$REPO_DIR/.venv" ]]; then
    if ! "$REPO_DIR/.venv/bin/python" -c 'import sys; exit(0 if sys.version_info >= (3, 11) else 1)' 2>/dev/null; then
        log_info "Removing existing .venv (was Python < 3.11), recreating with 3.11+"
        rm -rf "$REPO_DIR/.venv"
    fi
fi
if [[ ! -d "$REPO_DIR/.venv" ]]; then
    "$PYTHON311" -m venv "$REPO_DIR/.venv"
fi
# shellcheck source=/dev/null
. "$REPO_DIR/.venv/bin/activate"
pip install -U pip setuptools wheel -q
pip install -e "$REPO_DIR" -q
log_ok "Virtual env and package installed"

# --- Keychain secrets ---
log_info "Checking Keychain secrets..."
keychain_ensure() {
    local service="$1"
    local prompt_msg="$2"
    local existing
    existing=$(keychain_get "$service")
    if [[ -n "$existing" && "$FORCE" != true ]]; then
        return 0
    fi
    if [[ "$NON_INTERACTIVE" == true ]]; then
        log_fatal "Missing Keychain entry: $service (run without --non-interactive to prompt)"
    fi
    local val
    echo -n "$prompt_msg "
    read -r val
    if [[ -z "$val" ]]; then
        log_fatal "Empty value not allowed for $service"
    fi
    keychain_set "$service" "$val"
}

keychain_ensure "$NOTES_MCP_KEYCHAIN_SERVICE_GITHUB" "GitHub PAT (gist scope):"
keychain_ensure "$NOTES_MCP_KEYCHAIN_SERVICE_GIST_ID" "Gist ID (queue):"

if [[ -z "$(keychain_get "$NOTES_MCP_KEYCHAIN_SERVICE_TOKEN")" ]] || [[ "$FORCE" == true ]]; then
    if [[ "$FORCE" != true ]]; then
        TOKEN=$(openssl rand -hex 32)
        keychain_set "$NOTES_MCP_KEYCHAIN_SERVICE_TOKEN" "$TOKEN"
        log_ok "Generated and stored notes_mcp_token"
        echo "Store this token somewhere safe (e.g. for MCP client): $TOKEN"
    else
        TOKEN=$(openssl rand -hex 32)
        keychain_set "$NOTES_MCP_KEYCHAIN_SERVICE_TOKEN" "$TOKEN"
    fi
fi

# Ingress key optional
if [[ -z "$(keychain_get "$NOTES_MCP_KEYCHAIN_SERVICE_INGRESS_KEY")" ]]; then
    INGRESS_KEY=$(openssl rand -hex 32)
    keychain_set "$NOTES_MCP_KEYCHAIN_SERVICE_INGRESS_KEY" "$INGRESS_KEY"
    log_ok "Generated and stored ingress key (for Tailscale Funnel if needed)"
fi

# --- launchd worker ---
log_info "Installing launchd worker..."
chmod +x "$REPO_DIR/scripts/start_worker.sh"
PLIST_WORKER="$REPO_DIR/com.notes-mcp.worker.plist.template"
if [[ ! -f "$PLIST_WORKER" ]]; then
    PLIST_WORKER="$REPO_DIR/com.notes-mcp.worker.plist"
fi
LAUNCH_AGENTS="$HOME/Library/LaunchAgents"
mkdir -p "$LAUNCH_AGENTS"
WORKER_PLIST_DEST="$LAUNCH_AGENTS/com.notes-mcp.worker.plist"
if [[ -f "$PLIST_WORKER" ]]; then
    sed "s|__INSTALL_DIR__|$REPO_DIR|g" "$PLIST_WORKER" > "$WORKER_PLIST_DEST"
else
    cat > "$WORKER_PLIST_DEST" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.notes-mcp.worker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$REPO_DIR/scripts/start_worker.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$REPO_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/notes-mcp-worker.out</string>
    <key>StandardErrorPath</key>
    <string>/tmp/notes-mcp-worker.err</string>
</dict>
</plist>
PLIST
fi
launchctl bootout "gui/$(id -u)/com.notes-mcp.worker" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$WORKER_PLIST_DEST" 2>/dev/null || launchctl load "$WORKER_PLIST_DEST"
launchctl kickstart -k "gui/$(id -u)/com.notes-mcp.worker" 2>/dev/null || true
log_ok "Worker service loaded and started"

# --- Ingress (Tailscale serve) ---
if [[ "$SKIP_TAILSCALE" != true ]]; then
    if ! tailscale status &>/dev/null; then
        log_warn "Tailscale not logged in. Open Tailscale app, log in, then run: $0 --skip-brew --skip-tailscale"
    else
        log_info "Configuring Tailscale serve and ingress service..."
        tailscale serve --bg --http=8443 http://127.0.0.1:8443 2>/dev/null || true
        chmod +x "$REPO_DIR/scripts/start_ingress.sh"
        INGRESS_PLIST_DEST="$LAUNCH_AGENTS/com.notes-mcp.ingress.plist"
        cat > "$INGRESS_PLIST_DEST" << PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.notes-mcp.ingress</string>
    <key>ProgramArguments</key>
    <array>
        <string>/bin/bash</string>
        <string>$REPO_DIR/scripts/start_ingress.sh</string>
    </array>
    <key>WorkingDirectory</key>
    <string>$REPO_DIR</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/notes-mcp-ingress.out</string>
    <key>StandardErrorPath</key>
    <string>/tmp/notes-mcp-ingress.err</string>
</dict>
</plist>
PLIST
        launchctl bootout "gui/$(id -u)/com.notes-mcp.ingress" 2>/dev/null || true
        launchctl bootstrap "gui/$(id -u)" "$INGRESS_PLIST_DEST" 2>/dev/null || launchctl load "$INGRESS_PLIST_DEST"
        log_ok "Ingress service loaded"
    fi
fi

# --- Verification output ---
echo ""
log_ok "Install complete."
echo ""
echo "Worker status:   launchctl print gui/\$(id -u)/com.notes-mcp.worker"
echo "Worker logs:     tail -f /tmp/notes-mcp-worker.out"
echo "                 tail -f /tmp/notes-mcp-worker.err"
echo "Health (local):  curl http://127.0.0.1:8443/health"
echo "Health (tailnet): curl http://\$(tailscale status --json 2>/dev/null | grep -o '\"HostName\":\"[^\"]*\"' | head -1 | cut -d'\"' -f4):8443/health"
echo "MCP token:       security find-generic-password -s notes_mcp_token -w"
echo ""
