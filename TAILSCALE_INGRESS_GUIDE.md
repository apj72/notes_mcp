# Tailscale Ingress API Guide

## Overview

The Tailscale Ingress API provides a secure, Tailnet-only endpoint for creating notes in Apple Notes without requiring copy/paste of commands. This removes the clunky workflow and enables integration with iOS Shortcuts, webhooks, and other automation tools.

## Architecture

```
┌─────────────┐         ┌──────────────┐         ┌─────────────┐
│  Client     │         │  Tailscale   │         │  Your Mac   │
│  (iOS/Web)  │  ────>  │  Ingress API │  ────>  │  (localhost)│
│             │         │  :8443       │         │  :8443      │
└─────────────┘         └──────────────┘         └─────────────┘
                                                         │
                                                         ▼
                                                   ┌──────────────┐
                                                   │  Gist Queue  │
                                                   │  (queue.jsonl)│
                                                   └──────────────┘
                                                         │
                                                         ▼
                                                   ┌──────────────┐
                                                   │ Pull Worker  │
                                                   │ (processes)  │
                                                   └──────────────┘
                                                         │
                                                         ▼
                                                   ┌──────────────┐
                                                   │ Apple Notes  │
                                                   └──────────────┘
```

**Key Points:**
- ✅ **Write remains local**: Apple Notes read/write happens only on your Mac
- ✅ **Tailnet-only**: API is only accessible over Tailscale (not public internet)
- ✅ **No copy/paste**: Direct HTTP API calls
- ✅ **Secure**: Optional header authentication + Tailscale ACLs

## Prerequisites

1. **Tailscale installed and configured** on your Mac
2. **Tailnet hostname**: Find your hostname with:
   ```bash
   /Applications/Tailscale.app/Contents/MacOS/tailscale status --json | python3 -c "import sys, json; print(json.load(sys.stdin)['Self']['DNSName'])"
   ```
   Or check in Tailscale admin console. Your hostname will be something like `yourmachine.tailnet-name.ts.net`
3. **FastAPI dependencies installed**:
   ```bash
   python3 -m pip install fastapi uvicorn pydantic
   ```
   Or install the project:
   ```bash
   python3 -m pip install -e .
   ```

## Setup

### 1. Install Launchd Service

```bash
# Copy plist to LaunchAgents
cp docs/launchd/com.notes-mcp-ingress.plist ~/Library/LaunchAgents/

# Update the paths in the plist to match your setup
# Edit ~/Library/LaunchAgents/com.notes-mcp-ingress.plist
# Update: /Users/ajoyce/git-repos/notes_mcp to your actual path

# Load the service (use bootstrap on macOS 13+)
# For newer macOS (Ventura and later):
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.notes-mcp-ingress.plist

# For older macOS (if bootstrap doesn't work):
# launchctl load ~/Library/LaunchAgents/com.notes-mcp-ingress.plist

# Check status
launchctl list | grep notes-mcp-ingress
# Or (newer macOS):
# launchctl print gui/$(id -u)/com.notes-mcp-ingress
```

### 2. Expose via Tailscale

**Important:** Tailscale serve must **forward** to the local service, not replace it. The local service listens on `127.0.0.1:8443`, and Tailscale serve forwards external requests to it.

**Use the full path to Tailscale binary:**
```bash
# Reset any existing config (including admin console config)
sudo /Applications/Tailscale.app/Contents/MacOS/tailscale serve reset

# Expose the local service on Tailnet (forwards to localhost:8443)
sudo /Applications/Tailscale.app/Contents/MacOS/tailscale serve --bg --http=8443 http://127.0.0.1:8443

# Verify it's configured correctly
/Applications/Tailscale.app/Contents/MacOS/tailscale serve status
# Should show: http=8443 -> http://127.0.0.1:8443
```

**Note:** If you configured Tailscale serve in the admin console JSON config, the CLI command above will override it. This is the recommended approach. See `docs/TAILSCALE_ADMIN_CONSOLE_CONFIG.md` for details.

**Alternative: Add to PATH (optional)**
```bash
# Add to PATH for current session
export PATH="/Applications/Tailscale.app/Contents/MacOS:$PATH"

# Then you can use:
sudo tailscale serve --bg --http=8443 http://127.0.0.1:8443
tailscale status
```

**Note:** Tailscale serve persists across reboots, but you may need to restart it if the ingress service restarts.

### 3. Optional: Set Ingress Key

For additional security (beyond Tailnet ACLs), set an optional ingress key:

```bash
export NOTES_MCP_INGRESS_KEY="your-secret-key-here"
```

Add this to your `start_worker.sh` or environment script.

## Usage

### Create a Note via curl

**First, find your Tailscale hostname or IP:**
```bash
# Get hostname
./scripts/get-tailscale-hostname.sh

# Or use IP from status
/Applications/Tailscale.app/Contents/MacOS/tailscale status | head -1 | awk '{print "IP: " $1}'
```

**Then create a note:**
```bash
# Using hostname (replace with your actual hostname)
curl -X POST http://yourmachine.your-tailnet.ts.net:8443/notes \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Note",
    "body": "This is a test note created via Tailscale ingress",
    "folder": "MCP Inbox",
    "account": "iCloud"
  }'

# Or using IP address directly
curl -X POST http://100.102.14.6:8443/notes \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Test Note",
    "body": "This is a test note",
    "folder": "MCP Inbox"
  }'

# With optional ingress key
curl -X POST http://100.102.14.6:8443/notes \
  -H "Content-Type: application/json" \
  -H "X-Notes-MCP-Key: your-secret-key-here" \
  -d '{
    "title": "Test Note",
    "body": "This is a test note",
    "folder": "MCP Inbox"
  }'
```

### Create a Note via iOS Shortcut

1. **Create a new Shortcut** in iOS Shortcuts app
2. **Add "Get Contents of URL"** action:
   - URL: `http://taila02178.ts.net:8443/notes`
   - Method: POST
   - Headers:
     - `Content-Type: application/json`
     - `X-Notes-MCP-Key: your-key` (if set)
   - Request Body: JSON
     ```json
     {
       "title": "Shortcut Note",
       "body": "Created from iOS Shortcut",
       "folder": "MCP Inbox"
     }
     ```
3. **Run the shortcut** - note will be created in Apple Notes

### API Reference

#### POST /notes

Create a note by enqueueing a job.

**Request Body:**
```json
{
  "title": "Note Title",           // Required, max 200 chars
  "body": "Note content",           // Required, max 50,000 chars
  "folder": "MCP Inbox",            // Optional, defaults to "MCP Inbox"
  "account": "iCloud",               // Optional, "iCloud" or "On My Mac", defaults to "iCloud"
  "confirm": true                   // Optional, required if NOTES_MCP_REQUIRE_CONFIRM=true
}
```

**Headers:**
- `Content-Type: application/json` (required)
- `X-Notes-MCP-Key: your-key` (optional, if NOTES_MCP_INGRESS_KEY is set)

**Response:**
```json
{
  "status": "queued",
  "job_id": "uuid-here",
  "message": "Note creation job enqueued successfully",
  "folder": "MCP Inbox",
  "account": "iCloud"
}
```

**Status Codes:**
- `202 Accepted` - Job enqueued successfully
- `400 Bad Request` - Invalid request (validation error)
- `401 Unauthorized` - Invalid or missing X-Notes-MCP-Key
- `403 Forbidden` - Folder not in allowlist
- `429 Too Many Requests` - Rate limit exceeded
- `500 Internal Server Error` - Server error

#### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "ok",
  "service": "notes-mcp-ingress"
}
```

## Security

### Tailnet-Only Access

The API is **only accessible over Tailscale**. It:
- Binds to `127.0.0.1:8443` (localhost only)
- Is exposed via `tailscale serve` (Tailnet-only)
- Is **not** accessible from the public internet

### Optional Header Authentication

If `NOTES_MCP_INGRESS_KEY` is set, all requests must include:
```
X-Notes-MCP-Key: your-secret-key-here
```

If not set, the API relies solely on Tailscale ACLs.

### Rate Limiting

- **30 requests per minute** per client IP
- Tracks by IP address (from X-Forwarded-For header)
- Returns `429 Too Many Requests` if exceeded

### Input Validation

- Title: max 200 characters
- Body: max 50,000 characters
- Folder: max 200 characters, must be in allowlist
- No null bytes allowed
- Folder allowlist enforced (from `NOTES_MCP_ALLOWED_FOLDERS`)

### Logging

- **No secrets logged** (tokens, keys, full bodies)
- Only logs: action, title_length, body_length, folder, outcome
- Logs to: `~/Library/Logs/notes-mcp/notes-mcp.log`

## Troubleshooting

### Service Not Starting

```bash
# Check comprehensive status
./scripts/check-ingress-status.sh

# Check logs
tail -f ~/Library/Logs/notes-mcp/ingress.log
tail -f ~/Library/Logs/notes-mcp/ingress.error.log

# Check service status
launchctl list | grep notes-mcp-ingress

# Restart service (newer macOS)
launchctl bootout gui/$(id -u)/com.notes-mcp-ingress
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.notes-mcp-ingress.plist

# For older macOS:
# launchctl unload ~/Library/LaunchAgents/com.notes-mcp-ingress.plist
# launchctl load ~/Library/LaunchAgents/com.notes-mcp-ingress.plist
```

### Port 8443 Already in Use

If you get "address already in use" when starting the ingress service:

1. **Find what's using the port:**
   ```bash
   ./scripts/find-port-8443.sh
   # Or manually:
   lsof -i :8443
   ```

2. **If launchd service is running, stop it:**
   ```bash
   # Check if service is loaded
   launchctl list | grep notes-mcp-ingress
   
   # Stop it (newer macOS)
   launchctl bootout gui/$(id -u)/com.notes-mcp-ingress
   
   # For older macOS:
   # launchctl unload ~/Library/LaunchAgents/com.notes-mcp-ingress.plist
   ```

3. **If a manual process is running, kill it:**
   ```bash
   # Find the PID
   lsof -i :8443 | grep LISTEN
   
   # Kill it (replace PID with actual process ID)
   kill <PID>
   ```

4. **Then start the service again:**
   ```bash
   ./start_ingress.sh
   ```

### Getting 404 from Tailscale

If you get "404 page not found" when accessing via Tailscale:
1. **Check if service is running locally:**
   ```bash
   curl http://127.0.0.1:8443/health
   ```
   If this fails, the ingress service isn't running.

2. **Check Tailscale serve configuration:**
   ```bash
   /Applications/Tailscale.app/Contents/MacOS/tailscale serve status
   ```
   Make sure it's pointing to `http://127.0.0.1:8443`

3. **Restart Tailscale serve:**
   ```bash
   sudo /Applications/Tailscale.app/Contents/MacOS/tailscale serve reset
   sudo /Applications/Tailscale.app/Contents/MacOS/tailscale serve --bg --http=8443 http://127.0.0.1:8443
   ```

### Tailscale Serve Not Working

```bash
# Check Tailscale status
/Applications/Tailscale.app/Contents/MacOS/tailscale status

# Restart serve
sudo /Applications/Tailscale.app/Contents/MacOS/tailscale serve reset
sudo /Applications/Tailscale.app/Contents/MacOS/tailscale serve --bg --http=8443 http://127.0.0.1:8443

# Verify (use your actual hostname or IP)
curl http://100.102.14.6:8443/health
# Or:
curl http://yourmachine.your-tailnet.ts.net:8443/health
```

### Hostname Not Resolving

If your hostname doesn't resolve:
1. **Use IP address directly** (from `tailscale status` output)
2. **Check Tailscale admin console** for correct hostname
3. **Verify DNS is enabled** in Tailscale settings
4. **Use the helper script**: `./scripts/get-tailscale-hostname.sh`

### Connection Refused

- Ensure service is running: `launchctl list | grep notes-mcp-ingress`
- Check port is bound: `lsof -i :8443`
- Verify Tailscale serve is active: `tailscale status`

### Rate Limit Errors

- Wait 1 minute and retry
- Rate limit is 30 requests/minute per IP
- Consider increasing if needed (edit `ingress.py`)

## Notes Export (Read Access)

The system also includes a **local export** component for reading notes. See the export documentation for details.

**Important**: Notes export is **local only** by default. It does not expose your notes publicly. You can:
- Export to local `.data/notes_export.jsonl` file
- Export to local SQLite database
- Choose metadata-only or include bodies
- Filter by folder, date, and max count

ChatGPT **cannot** directly access these files. You would need to:
- Manually share the export file
- Build a separate mechanism to expose selected notes
- Use the export as input to other tools

## What ChatGPT Can and Cannot Do

**ChatGPT CAN:**
- Generate curl commands for you to run
- Help you create iOS Shortcuts
- Explain how the API works
- Troubleshoot errors

**ChatGPT CANNOT:**
- Execute commands directly on your Mac
- Access the Tailscale API directly
- Read your exported notes automatically
- Access local files on your Mac

**You must:**
- Run curl commands yourself
- Set up iOS Shortcuts yourself
- Manually share export files if you want ChatGPT to see them

## Quick Test

After setup, test the API:

```bash
# Using the test script
./scripts/test_ingress.sh

# Or manually
curl http://taila02178.ts.net:8443/health
curl -X POST http://taila02178.ts.net:8443/notes \
  -H "Content-Type: application/json" \
  -d '{"title": "Test", "body": "Test content", "folder": "MCP Inbox"}'
```

## Next Steps

1. **Set up the ingress service** (see Setup above)
2. **Test with curl** to verify it works
3. **Create iOS Shortcuts** for quick note creation
4. **Set up notes export** (optional, for read access)
5. **Configure Tailscale ACLs** (optional, for additional security)

## Example Workflows

### Quick Note from iPhone

1. Create iOS Shortcut with your note content
2. Run shortcut
3. Note appears in Apple Notes within 60 seconds (poll interval)

### Webhook Integration

1. Set up webhook endpoint pointing to `http://taila02178.ts.net:8443/notes`
2. Configure webhook to send JSON payload
3. Notes created automatically from webhook events

### Automation Script

```bash
#!/bin/bash
# Quick note creation script

curl -X POST http://taila02178.ts.net:8443/notes \
  -H "Content-Type: application/json" \
  -H "X-Notes-MCP-Key: your-key" \
  -d "{
    \"title\": \"Automated Note\",
    \"body\": \"Created at $(date)\",
    \"folder\": \"MCP Inbox\"
  }"
```
