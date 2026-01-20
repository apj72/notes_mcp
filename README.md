# Notes MCP Server

A local MCP (Model Context Protocol) server for creating notes in Apple Notes on macOS. This server provides a secure, authenticated interface for creating notes with comprehensive security controls including authentication, rate limiting, folder allowlisting, and audit logging.

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

Set the following environment variables before running the server:

### Required

- **`NOTES_MCP_TOKEN`**: Shared secret token for authentication. Choose a strong, random value:
```bash
export NOTES_MCP_TOKEN="your-secret-token-here"
```

### Optional

- **`NOTES_MCP_ALLOWED_FOLDERS`**: Comma-separated list of allowed folder names. The folder "MCP Inbox" is always allowed by default:
```bash
export NOTES_MCP_ALLOWED_FOLDERS="MCP Inbox,Work,Personal"
```

- **`NOTES_MCP_REQUIRE_CONFIRM`**: If set to `"true"`, all create requests must include `confirm: true`:
```bash
export NOTES_MCP_REQUIRE_CONFIRM="true"
```

### Example Configuration

Create a `.env` file or add to your shell profile:

```bash
export NOTES_MCP_TOKEN="$(openssl rand -hex 32)"
export NOTES_MCP_ALLOWED_FOLDERS="MCP Inbox,Work,Personal"
export NOTES_MCP_REQUIRE_CONFIRM="false"
```

## Running the Server

The server uses stdio transport (standard input/output) for MCP communication. Run it directly:

```bash
python3 -m notes_mcp.server
```

Or if installed as a package:

```bash
notes-mcp-server
```

**Note**: On macOS, use `python3` instead of `python` if the `python` command is not found.

The server will read JSON-RPC requests from stdin and write responses to stdout.

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

```bash
export NOTES_QUEUE_GIST_ID="your-gist-id-here"
export GITHUB_TOKEN="your-github-token-here"
export NOTES_QUEUE_POLL_SECONDS="15"  # Optional, default 15
export NOTES_QUEUE_FILENAME="queue.jsonl"  # Optional
export NOTES_RESULTS_FILENAME="results.jsonl"  # Optional
export NOTES_QUEUE_DB="~/.notes-mcp-queue/worker.sqlite3"  # Optional
export NOTES_QUEUE_HMAC_SECRET="..."  # Optional, uses NOTES_MCP_TOKEN if not set
```

**Important**: The HMAC secret defaults to `NOTES_MCP_TOKEN` if `NOTES_QUEUE_HMAC_SECRET` is not set. This keeps secrets in sync, but you can use a separate secret if preferred.

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

Create `~/Library/LaunchAgents/com.notes-mcp.worker.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.notes-mcp.worker</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/python3</string>
        <string>-m</string>
        <string>notes_mcp.pull_worker</string>
    </array>
    <key>EnvironmentVariables</key>
    <dict>
        <key>NOTES_QUEUE_GIST_ID</key>
        <string>your-gist-id</string>
        <key>GITHUB_TOKEN</key>
        <string>your-github-token</string>
        <key>NOTES_MCP_TOKEN</key>
        <string>your-mcp-token</string>
        <key>NOTES_MCP_ALLOWED_FOLDERS</key>
        <string>MCP Inbox,Work,Personal</string>
    </dict>
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
```

Load it:
```bash
launchctl load ~/Library/LaunchAgents/com.notes-mcp.worker.plist
```

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

## Development

### Project Structure

```
notes_mcp/
├── pyproject.toml          # Project configuration
├── README.md               # This file
└── src/
    └── notes_mcp/
        ├── __init__.py     # Package initialization
        ├── server.py       # MCP server implementation
        ├── applescript.py  # AppleScript integration
        ├── security.py     # Security utilities
        ├── logging.py      # Audit logging
        ├── pull_worker.py  # Queue-based pull worker
        └── sign_job.py     # Helper for signing jobs
```

### Running Tests

```bash
python3 -m pip install -e ".[dev]"
pytest
```

## License

This project is provided as-is for local use.
