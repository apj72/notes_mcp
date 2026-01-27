# Notes MCP Server

A comprehensive system for creating and managing notes in Apple Notes on macOS. This project provides these main components:

1. **MCP Server** - Direct MCP (Model Context Protocol) server for creating notes via stdio/JSON-RPC
2. **Pull Worker** - Background service that processes note creation jobs from a GitHub Gist queue
3. **Tailscale Ingress API** - HTTP API endpoint (Tailnet-only) for creating notes without copy/paste
4. **Notes Export** - Local tool for exporting Apple Notes metadata/content to SQLite or JSONL

All components share the same security controls: authentication, rate limiting, folder allowlisting, confirmation modes, and audit logging.

## Prerequisites

- **macOS** (required for Apple Notes integration)
- **Python 3.11 or higher**
- **Apple Notes app** installed and configured
- **Automation permissions** granted to Terminal/Python for controlling Notes (see Permissions section)

## Installation

1. Clone or download this repository:
```bash
cd /path/to/notes_mcp
```

2. Create a virtual environment (recommended):
```bash
python3 -m venv venv
source venv/bin/activate
```

3. Install dependencies:
```bash
python3 -m pip install -e .
```

**Note**: On macOS, use `python3 -m pip` instead of just `pip` if the `pip` command is not found.

## Configuration

### Initial Setup

1. **Copy the configuration template:**
   ```bash
   cp start_worker.sh.example start_worker.sh
   ```

2. **Edit `start_worker.sh`** and replace all placeholder values with your actual tokens and IDs.

3. **Generate secure tokens:**
   ```bash
   # MCP Authentication Token
   openssl rand -hex 32
   
   # Ingress API Key (for Tailscale Funnel)
   openssl rand -hex 32
   ```

**Important:** `start_worker.sh` is gitignored and contains sensitive secrets. Never commit it to version control.

### Required Environment Variables

- **`NOTES_MCP_TOKEN`**: Shared secret token for authentication
- **`GITHUB_TOKEN`**: GitHub Personal Access Token (for Gist queue, requires 'gist' scope)
- **`NOTES_QUEUE_GIST_ID`**: Your GitHub Gist ID (from the Gist URL)

### Optional Environment Variables

- **`NOTES_MCP_ALLOWED_FOLDERS`**: Comma-separated list of allowed folder names (default: "MCP Inbox")
- **`NOTES_MCP_INGRESS_KEY`**: Ingress API key for Tailscale Funnel public access
- **`NOTES_MCP_REQUIRE_CONFIRM`**: If `"true"`, all create requests must include `confirm: true`
- **`NOTES_QUEUE_POLL_SECONDS`**: Polling interval in seconds (default: 60)
- **`NOTES_MCP_MAX_JOB_AGE_SECONDS`**: Maximum age for jobs in seconds (default: 86400 = 24 hours)

## Quick Start

### Option 1: Direct MCP Server (for Cursor/IDE integration)

The server uses stdio transport (standard input/output) for MCP communication. Run it directly:

```bash
python3 -m notes_mcp.server
```

**Note**: On macOS, use `python3` instead of `python` if the `python` command is not found.

The server will read JSON-RPC requests from stdin and write responses to stdout.

### Option 2: Pull Worker (for async processing via Gist queue)

Set up environment variables (see Pull Worker section below) and run:

```bash
python3 -m notes_mcp.pull_worker
```

Or set up as a background service:

```bash
./setup_service.sh
```

### Option 3: Tailscale Ingress API (for HTTP access)

Start the ingress service:

```bash
./start_ingress.sh
```

Then expose via Tailscale:

```bash
# For Tailnet-only access (private)
sudo /Applications/Tailscale.app/Contents/MacOS/tailscale serve --bg --http=8443 http://127.0.0.1:8443

# For public access via Funnel (requires ingress key)
sudo /Applications/Tailscale.app/Contents/MacOS/tailscale funnel --bg http://127.0.0.1:8443
```

**Note:** For public Funnel access, ensure `NOTES_MCP_INGRESS_KEY` is set in `start_worker.sh` and include it in requests as `X-Notes-MCP-Key` header.

## Cursor MCP Client Configuration

To use this server with Cursor, add the following to your Cursor MCP configuration file (typically `~/.cursor/mcp.json` or similar):

```json
{
  "mcpServers": {
    "notes-mcp": {
      "command": "python3",
      "args": ["-m", "notes_mcp.server"],
      "env": {
        "NOTES_MCP_TOKEN": "your-secret-token-here",
        "NOTES_MCP_ALLOWED_FOLDERS": "MCP Inbox,Work,Personal",
        "NOTES_MCP_REQUIRE_CONFIRM": "false"
      }
    }
  }
}
```

**Important**: Make sure the `NOTES_MCP_TOKEN` in the Cursor config matches the token you set in your environment, or pass it via the `_token` field in tool calls.

### Alternative: Using a Wrapper Script

If you prefer to load environment variables from a file, create a wrapper script:

```bash
#!/bin/bash
# ~/bin/notes-mcp-server.sh
source ~/.notes-mcp-env
exec python -m notes_mcp.server
```

Then reference it in your Cursor config:

```json
{
  "mcpServers": {
    "notes-mcp": {
      "command": "/Users/yourusername/bin/notes-mcp-server.sh"
    }
  }
}
```

**Note**: In the wrapper script, use `python3` instead of `python` if needed.

## macOS Permissions

The server requires Automation permissions to control Apple Notes. When you first run the server, macOS will prompt you to grant these permissions.

### Granting Permissions

1. **Automatic Prompt**: When the server first tries to create a note, macOS will show a permission dialog. Click "OK" to grant access.

2. **Manual Setup**: If you need to grant permissions manually:
   - Open **System Settings** (or System Preferences on older macOS)
   - Go to **Privacy & Security** → **Automation**
   - Find **Terminal** (or **Python**) in the list
   - Enable **Notes** in the allowed apps list

3. **Troubleshooting**: If permissions are denied:
   - Check System Settings → Privacy & Security → Automation
   - Remove and re-add the permission if needed
   - Restart Terminal/Python after granting permissions

## API Reference

### Tool: `notes.create`

Creates a new note in Apple Notes.

**Parameters:**
- `title` (string, required): Note title (max 200 characters)
- `body` (string, required): Note body (max 50,000 characters)
- `folder` (string, optional): Target folder name (default: "MCP Inbox")
- `account` (string, optional): Target account - `"iCloud"` or `"On My Mac"` (default: "iCloud")
- `confirm` (boolean, optional): Confirmation flag (required if `NOTES_MCP_REQUIRE_CONFIRM=true`)
- `_token` (string, **required**): Authentication token (must match `NOTES_MCP_TOKEN` environment variable)

**Returns:**
```json
{
  "ok": true,
  "location": {
    "account": "iCloud",
    "folder": "MCP Inbox"
  },
  "reference": "timestamp - title"
}
```

**Errors:**
- `-32000`: Validation error (invalid input, rate limit, permission denied, etc.)
- `-32601`: Unknown tool or method
- `-32700`: Parse error

## Manual Testing

### Using Python

Create a test script `test_notes_mcp.py`:

```python
import json
import subprocess
import os

# Set token
os.environ["NOTES_MCP_TOKEN"] = "test-token-123"
os.environ["NOTES_MCP_ALLOWED_FOLDERS"] = "MCP Inbox"

# Initialize request
init_request = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {}
}

# Create note request
create_request = {
    "jsonrpc": "2.0",
    "id": 2,
    "method": "tools/call",
    "params": {
        "name": "notes.create",
        "arguments": {
            "title": "Test Note",
            "body": "This is a test note created via MCP",
            "folder": "MCP Inbox",
            "account": "iCloud",
            "_token": "test-token-123"
        }
    }
}

# Run server
proc = subprocess.Popen(
    ["python3", "-m", "notes_mcp.server"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    text=True
)

# Send requests
proc.stdin.write(json.dumps(init_request) + "\n")
proc.stdin.write(json.dumps(create_request) + "\n")
proc.stdin.close()

# Read responses
for line in proc.stdout:
    print(json.loads(line))
```

Run it:
```bash
python test_notes_mcp.py
```

### Using echo and pipe

```bash
export NOTES_MCP_TOKEN="test-token-123"
export NOTES_MCP_ALLOWED_FOLDERS="MCP Inbox"

echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | python3 -m notes_mcp.server

echo '{"jsonrpc":"2.0","id":2,"method":"tools/call","params":{"name":"notes.create","arguments":{"title":"Test","body":"Test body","_token":"test-token-123"}}}' | python3 -m notes_mcp.server
```

## Pull Worker (Queue-Based Processing)

The pull worker allows you to process note creation jobs from a remote GitHub Gist queue. Jobs are signed with HMAC to prevent tampering, and the worker maintains idempotency using SQLite to prevent duplicate execution.

### Overview

- **Queue**: Private GitHub Gist with `queue.jsonl` (newline-delimited JSON jobs)
- **Results**: Same Gist with `results.jsonl` (appended results)
- **Security**: HMAC-SHA256 signatures on all jobs
- **Idempotency**: SQLite database tracks processed job IDs
- **Reuses**: All existing security controls (allowlist, confirmation, rate limiting, logging)

### Job Schema

**Job line (queue.jsonl):**
```json
{
  "job_id": "uuid",
  "created_at": "ISO-8601",
  "tool": "notes.create",
  "args": {
    "title": "...",
    "body": "...",
    "folder": "MCP Inbox",
    "account": "iCloud",
    "confirm": true
  },
  "sig": "base64(hmac_sha256(canonical_json))"
}
```

**Result line (results.jsonl):**
```json
{
  "job_id": "uuid",
  "processed_at": "ISO-8601",
  "status": "ok|denied|error",
  "location": {
    "account": "iCloud",
    "folder": "MCP Inbox"
  },
  "reference": "timestamp - title",
  "error": {
    "code": "...",
    "message": "..."
  }
}
```

### Setup

#### 1. Create a Private GitHub Gist

1. Go to https://gist.github.com
2. Create a new **private** gist
3. Add two files:
   - `queue.jsonl` (initially empty or with a comment)
   - `results.jsonl` (initially empty)
4. Copy the Gist ID from the URL (e.g., `https://gist.github.com/username/abc123def456` → ID is `abc123def456`)

#### 2. Create a GitHub Fine-Grained Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Create a new token with:
   - **Repository access**: Only select gists
   - **Permissions**: `gists` (read and write)
   - **Expiration**: Set as needed
3. Copy the token

#### 3. Configure Environment Variables

Edit `start_worker.sh` (created from `start_worker.sh.example`) and set:

- `NOTES_QUEUE_GIST_ID` - Your GitHub Gist ID
- `GITHUB_TOKEN` - Your GitHub Personal Access Token
- `NOTES_MCP_TOKEN` - Your MCP authentication token
- `NOTES_MCP_ALLOWED_FOLDERS` - Comma-separated list of allowed folders
- `NOTES_MCP_INGRESS_KEY` - (Optional) Ingress API key for Tailscale Funnel

**Important**: 
- `start_worker.sh` is gitignored and contains sensitive secrets. Never commit it.
- The HMAC secret defaults to `NOTES_MCP_TOKEN` if `NOTES_QUEUE_HMAC_SECRET` is not set.

#### 4. Generate a Signed Job

Use the helper script to generate a signed job line:

```bash
python3 -m notes_mcp.sign_job \
  --title "My Note Title" \
  --body "Note content here" \
  --folder "MCP Inbox" \
  --account "iCloud" \
  --confirm
```

This outputs a JSON line that you can paste into `queue.jsonl` in your Gist.

#### 5. Run the Worker

**Foreground (for testing):**
```bash
python3 -m notes_mcp.pull_worker
```

**Background with launchd (macOS):**

```bash
# Automated setup
./setup_service.sh

# Or manually
cp com.notes-mcp.worker.plist ~/Library/LaunchAgents/
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.notes-mcp.worker.plist
```

**Managing the service:**
- Start: `launchctl kickstart -k gui/$(id -u)/com.notes-mcp.worker`
- Stop: `launchctl bootout gui/$(id -u)/com.notes-mcp.worker`
- Check status: `launchctl list | grep notes-mcp`
- View logs: Check `~/Library/Logs/notes-mcp/` directory

### Security Notes

1. **HMAC Signatures**: Jobs are signed with HMAC-SHA256 over a canonical JSON representation. The signature covers all fields except `sig` itself. This prevents anyone with gist access from injecting malicious jobs.

2. **Canonicalization**: Jobs are canonicalized by:
   - Sorting keys alphabetically
   - Removing the `sig` field
   - Using compact JSON (no spaces)

3. **Least Privilege**: 
   - GitHub token should only have gists read/write permissions
   - Worker only reads `queue.jsonl` and appends to `results.jsonl` (never deletes or modifies existing lines)
   - All existing security controls (allowlist, confirmation, rate limiting) apply

4. **Idempotency**: SQLite database at `~/.notes-mcp-queue/worker.sqlite3` tracks processed job IDs to prevent replay attacks.

5. **Risks**:
   - If your GitHub token is compromised, an attacker could read/write the gist but cannot create valid jobs without the HMAC secret
   - If your HMAC secret is compromised, an attacker could create valid jobs (but still subject to allowlist, confirmation, rate limits)
   - Keep both secrets secure

### Troubleshooting

**GitHub 401/403 errors:**
- Verify `GITHUB_TOKEN` is set and valid
- Check token has gists read/write permissions
- Verify token hasn't expired

**Gist file missing:**
- Ensure `queue.jsonl` and `results.jsonl` exist in the gist
- Check `NOTES_QUEUE_GIST_ID` is correct

**Invalid signature:**
- Verify `NOTES_QUEUE_HMAC_SECRET` (or `NOTES_MCP_TOKEN`) matches what was used to sign the job
- Check job wasn't modified after signing
- Ensure canonicalization matches (use `sign_job.py` helper)

**Already processed job:**
- This is expected - jobs are only processed once
- Check SQLite database: `sqlite3 ~/.notes-mcp-queue/worker.sqlite3 "SELECT * FROM processed_jobs;"`

**Notes automation permissions:**
- Same as MCP server - grant in System Settings → Privacy & Security → Automation

## Security Features

1. **Authentication**: All requests require a valid token via `NOTES_MCP_TOKEN`
2. **Rate Limiting**: Maximum 10 create calls per minute per token
3. **Folder Allowlisting**: Only specified folders can be used (configured via `NOTES_MCP_ALLOWED_FOLDERS`)
4. **Confirmation Mode**: Optional requirement for explicit confirmation on write operations
5. **Input Validation**: Title max 200 chars, body max 50,000 chars, no null bytes
6. **AppleScript Injection Defense**: User input is passed as arguments, never concatenated into script strings
7. **Audit Logging**: All actions logged to `~/Library/Logs/notes-mcp/notes-mcp.log`

## Audit Logging

All actions are logged to `~/Library/Logs/notes-mcp/notes-mcp.log` in JSON format. Each log entry includes:

- `timestamp`: UTC timestamp
- `action`: Action performed (e.g., "create")
- `title_length`: Length of note title
- `body_length`: Length of note body
- `account`: Target account
- `folder`: Target folder
- `outcome`: "allowed", "denied", or "error"
- `error`: Error message (if outcome is "error" or "denied")

**Note**: The log does NOT include the full body content for privacy.

## Troubleshooting

### Common Issues

1. **"AppleScript error: Notes got an error: Can't get account"**
   - Ensure Notes app is installed and configured
   - Check that you have an iCloud account or "On My Mac" account set up in Notes
   - Grant Automation permissions (see Permissions section)

2. **"Invalid or missing authentication token"**
   - Ensure `NOTES_MCP_TOKEN` environment variable is set
   - Verify the token matches between server and client

3. **"Folder 'X' is not in the allowlist"**
   - Add the folder to `NOTES_MCP_ALLOWED_FOLDERS` environment variable
   - Or use "MCP Inbox" which is always allowed

4. **"Confirmation required but not provided"**
   - Set `confirm: true` in the tool call arguments
   - Or set `NOTES_MCP_REQUIRE_CONFIRM="false"` to disable confirmation mode

5. **"Rate limit exceeded"**
   - Wait 60 seconds before making another request
   - Maximum 10 calls per minute per token

6. **Permission Denied**
   - Check System Settings → Privacy & Security → Automation
   - Ensure Terminal/Python has permission to control Notes
   - Restart Terminal after granting permissions

### Pull Worker Issues

7. **GitHub 401/403 errors**
   - Verify `GITHUB_TOKEN` is set and valid
   - Check token has gists read/write permissions
   - Verify token hasn't expired
   - **Rate limit exceeded**:
     - Wait 5-10 minutes and try again
     - Check your token's rate limit: `curl -H "Authorization: token YOUR_TOKEN" https://api.github.com/rate_limit`
     - Increase poll interval: `export NOTES_QUEUE_POLL_SECONDS="30"`

8. **Gist file missing**
   - Ensure `queue.jsonl` and `results.jsonl` exist in the gist
   - Check `NOTES_QUEUE_GIST_ID` is correct

9. **Invalid signature**
   - Verify `NOTES_QUEUE_HMAC_SECRET` (or `NOTES_MCP_TOKEN`) matches what was used to sign the job
   - Check job wasn't modified after signing
   - Use `sign_job.py` helper to generate correctly signed jobs

10. **Already processed job**
    - This is expected - jobs are only processed once (idempotency)
    - Check SQLite database: `sqlite3 ~/.notes-mcp-queue/worker.sqlite3 "SELECT * FROM processed_jobs;"`

### Viewing Logs

```bash
tail -f ~/Library/Logs/notes-mcp/notes-mcp.log
```

## Tailscale Ingress API

The Tailscale Ingress API provides a secure HTTP endpoint for creating notes without requiring copy/paste of commands. It's accessible only over your Tailnet (not the public internet).

### Features

- **Tailnet-only access** - Only accessible via Tailscale VPN
- **HTTP API** - Simple POST requests to create notes
- **No copy/paste** - Direct API calls from iOS Shortcuts, webhooks, etc.
- **Optional authentication** - Additional header-based auth (beyond Tailscale ACLs)
- **Rate limiting** - 30 requests per minute per IP
- **Reuses all security controls** - Folder allowlist, confirmation, validation

### Quick Start

1. **Install dependencies:**
   ```bash
   python3 -m pip install fastapi uvicorn pydantic
   ```

2. **Start the ingress service:**
   ```bash
   ./start_ingress.sh
   ```

3. **Expose via Tailscale:**
   ```bash
   sudo /Applications/Tailscale.app/Contents/MacOS/tailscale serve --bg --http=8443 http://127.0.0.1:8443
   ```

4. **Test it:**
   ```bash
   curl -X POST http://yourmachine.tailnet.ts.net:8443/notes \
     -H "Content-Type: application/json" \
     -d '{"title": "Test", "body": "Test content", "folder": "MCP Inbox"}'
   ```

**API Endpoints:**
- `GET /health` - Health check
- `POST /notes` - Create a note (requires `X-Notes-MCP-Key` header if `NOTES_MCP_INGRESS_KEY` is set)

**Request format:**
```json
{
  "title": "Note Title",
  "body": "Note content",
  "folder": "MCP Inbox",
  "account": "iCloud"
}
```

## Notes Export

The export tool allows you to read and export Apple Notes content locally for search, summarization, or backup purposes.

### Features

- **Local-only** - All data stays on your Mac
- **Privacy-first** - Metadata-only export by default (bodies excluded unless explicitly requested)
- **Multiple formats** - Export to SQLite or JSONL
- **Filtering** - Filter by date, limit count, include/exclude bodies
- **Tag extraction** - Automatically extracts tags from title prefixes (e.g., `[WORK]`)
- **All folders** - Export all notes regardless of folder allowlist
- **Duplicate detection** - Identify duplicate notes based on title and body similarity

### Usage

```bash
# Export metadata only from allowed folders (default)
python3 -m notes_mcp.export_notes

# Export ALL notes from ALL folders (for organization/cleanup)
python3 -m notes_mcp.export_notes --all-folders --max-notes 0 --include-body

# Export with duplicate detection
python3 -m notes_mcp.export_notes --all-folders --find-duplicates --include-body

# Export to SQLite for analysis
python3 -m notes_mcp.export_notes --all-folders --format sqlite --include-body --find-duplicates
```

### Organizing and Cleaning Notes

To organize all your notes and find duplicates:

```bash
# Export all notes with bodies and duplicate detection
python3 -m notes_mcp.export_notes --all-folders --max-notes 0 --include-body --find-duplicates --format sqlite

# Then query the SQLite database
sqlite3 .data/notes_export.db "SELECT * FROM notes_export WHERE is_duplicate = 1 ORDER BY duplicate_group, modified_at"
```

Output files are saved to `.data/` directory (gitignored).

## Development

### Project Structure

```
notes_mcp/
├── pyproject.toml                    # Project configuration
├── README.md                          # This file
├── start_worker.sh.example            # Configuration template
├── start_ingress.sh.example           # Ingress template
├── setup_service.sh                   # Worker service setup
├── com.notes-mcp.worker.plist        # Worker launchd config
├── scripts/                           # Helper scripts
│   ├── setup-tailscale-serve.sh      # Tailscale setup
│   ├── setup-funnel.sh               # Funnel setup
│   ├── generate-ingress-key.sh       # Key generation
│   ├── install-ingress-service.sh    # Ingress installer
│   ├── start-notes-mcp-ingress.sh    # Ingress startup
│   └── smoke_test.sh                 # Smoke test
├── docs/                              # Additional documentation
│   ├── launchd/                       # Launchd configs
│   └── TAILSCALE_ADMIN_CONSOLE_CONFIG.md
└── src/
    └── notes_mcp/
        ├── __init__.py               # Package initialization
        ├── server.py                 # MCP server (stdio)
        ├── pull_worker.py             # Queue-based worker
        ├── ingress.py                 # Tailscale ingress API
        ├── export_notes.py           # Notes export tool
        ├── applescript.py             # AppleScript integration
        ├── security.py                # Security utilities
        ├── logging.py                 # Audit logging
        ├── formatting.py              # Text normalization
        ├── sign_job.py                # Job signing helper
        └── enqueue_job.py             # Job enqueue helper
```

### Current Status

**✅ Implemented:**
- MCP server with stdio transport
- Pull worker with GitHub Gist queue
- Tailscale Ingress API (HTTP endpoint)
- Notes export tool (local read access)
- Comprehensive security controls
- Launchd service setup for worker and ingress
- Queue clearing and idempotency
- Text formatting normalization
- Rate limit handling improvements

**📚 Documentation:**
- Complete setup guides for all components
- API reference documentation
- Security review
- Troubleshooting guides

**🔒 Security:**
- HMAC-signed jobs
- Folder allowlisting
- Rate limiting
- Optional confirmation modes
- Audit logging (no secrets)
- Input validation
- AppleScript injection defense

### Running Tests

```bash
python3 -m pip install -e ".[dev]"
pytest
```

## License

This project is provided as-is for local use.
