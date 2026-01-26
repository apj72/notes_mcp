# Quick Start: Tailscale Ingress API

## Installation

1. **Install dependencies:**
   ```bash
   python3 -m pip install -e .
   ```

2. **Set up launchd service:**
   ```bash
   # Copy plist
   cp docs/launchd/com.notes-mcp-ingress.plist ~/Library/LaunchAgents/
   
   # Edit paths in plist (update /Users/ajoyce/git-repos/notes_mcp to your path)
   nano ~/Library/LaunchAgents/com.notes-mcp-ingress.plist
   
   # Load service (use bootstrap on macOS 13+)
   launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.notes-mcp-ingress.plist
   
   # For older macOS:
   # launchctl load ~/Library/LaunchAgents/com.notes-mcp-ingress.plist
   ```

3. **Expose via Tailscale:**
   ```bash
   # Use full path to Tailscale binary
   sudo /Applications/Tailscale.app/Contents/MacOS/tailscale serve --bg --http=8443 http://127.0.0.1:8443
   
   # Verify
   /Applications/Tailscale.app/Contents/MacOS/tailscale status
   ```

4. **Test:**
   ```bash
   curl http://taila02178.ts.net:8443/health
   ```

## Create a Note

```bash
curl -X POST http://taila02178.ts.net:8443/notes \
  -H "Content-Type: application/json" \
  -d '{
    "title": "My Note",
    "body": "Note content here",
    "folder": "MCP Inbox"
  }'
```

## Notes Export (Read Access)

Export notes locally:

```bash
# Metadata only (default)
python3 -m notes_mcp.export_notes

# With bodies
python3 -m notes_mcp.export_notes --include-body

# Recent notes only
python3 -m notes_mcp.export_notes --since-days 7 --max-notes 100
```

Output: `.data/notes_export.jsonl`

## Full Documentation

See `TAILSCALE_INGRESS_GUIDE.md` for complete documentation.
