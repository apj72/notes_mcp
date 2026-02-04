# Launchd Service Configuration

This directory contains launchd plist files for running Notes MCP services automatically.

## Services

### 1. Ingress API (`com.notes-mcp-ingress.plist`)

Runs the Tailscale ingress API service.

**Installation:**
```bash
# Copy plist
cp com.notes-mcp-ingress.plist ~/Library/LaunchAgents/

# Edit paths in plist to match your setup
# Update: /Users/ajoyce/git-repos/notes_mcp to your actual path

# Load service (use bootstrap on newer macOS)
# For macOS 13+ (Ventura and later):
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.notes-mcp-ingress.plist

# Or if that doesn't work, try:
launchctl bootstrap ~/Library/LaunchAgents/com.notes-mcp-ingress.plist

# For older macOS (if bootstrap doesn't work):
# launchctl load ~/Library/LaunchAgents/com.notes-mcp-ingress.plist

# Start immediately (if not auto-started)
launchctl kickstart -k gui/$(id -u)/com.notes-mcp-ingress
```

**Management:**
```bash
# Check status (newer macOS)
launchctl list | grep notes-mcp-ingress
# Or:
launchctl print gui/$(id -u)/com.notes-mcp-ingress

# Stop service
launchctl bootout gui/$(id -u)/com.notes-mcp-ingress
# Or (older macOS):
# launchctl stop com.notes-mcp-ingress

# Unload service (newer macOS)
launchctl bootout gui/$(id -u)/com.notes-mcp-ingress
# Or (older macOS):
# launchctl unload ~/Library/LaunchAgents/com.notes-mcp-ingress.plist

# Restart service
launchctl bootout gui/$(id -u)/com.notes-mcp-ingress
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.notes-mcp-ingress.plist

# View logs
tail -f ~/Library/Logs/notes-mcp/ingress.log
```

### 2. Notes Export (`com.notes-mcp-export.plist`)

Runs notes export on a schedule (every hour).

**Installation:**
```bash
# Copy plist
cp com.notes-mcp-export.plist ~/Library/LaunchAgents/

# Edit paths in plist to match your setup

# Load service
launchctl load ~/Library/LaunchAgents/com.notes-mcp-export.plist
```

**Configuration:**
- Runs every hour (StartInterval: 3600)
- Exports notes from last 7 days
- Includes note bodies
- Max 500 notes
- Output: `.data/notes_export.jsonl`

**Customize:**
Edit the plist to change:
- `--since-days` value
- `--max-notes` value
- `--include-body` flag
- `StartInterval` (seconds between runs)

## Tailscale Serve Setup

After installing the ingress service, expose it via Tailscale:

```bash
# Expose on Tailnet (use full path)
sudo /Applications/Tailscale.app/Contents/MacOS/tailscale serve --bg --http=8443 http://127.0.0.1:8443

# Verify
/Applications/Tailscale.app/Contents/MacOS/tailscale status

# Test
curl http://taila02178.ts.net:8443/health
```

**Note:** Tailscale serve persists across reboots, but you may need to restart it if the service restarts.

**If you prefer to use `tailscale` command directly:**
```bash
# Add to PATH for current session
export PATH="/Applications/Tailscale.app/Contents/MacOS:$PATH"

# Then use normally
sudo tailscale serve --bg --http=8443 http://127.0.0.1:8443
```

## Troubleshooting

### Service Not Starting

1. Check logs:
   ```bash
   tail -f ~/Library/Logs/notes-mcp/ingress.log
   tail -f ~/Library/Logs/notes-mcp/ingress.error.log
   ```

2. Verify paths in plist match your setup

3. Check environment variables are set (in start_worker.sh or ENV_SCRIPT_PATH)

4. Test manually:
   ```bash
   cd /path/to/notes_mcp
   ./start_ingress.sh
   ```
   (Use the same `start_ingress.sh` you use for the launchd plist; copy from `start_ingress.sh.example` if needed.)

### Port Already in Use

If port 8443 is already in use:
1. Change port in plist and script
2. Update Tailscale serve command
3. Update client URLs

### Permission Errors

Ensure:
- `start_ingress.sh` is executable: `chmod +x start_ingress.sh`
- Python has Automation permissions for Notes
- Tailscale has necessary permissions
