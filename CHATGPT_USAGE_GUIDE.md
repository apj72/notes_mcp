# ChatGPT Usage Guide: Notes MCP Pull Worker

This guide explains how ChatGPT (or any AI assistant) can help you create notes in Apple Notes on your Mac using the pull worker queue system.

## What ChatGPT Can and Cannot Do

**ChatGPT CAN:**
- Generate the command to create a signed job
- Provide the exact command syntax
- Help troubleshoot errors
- Explain how the system works

**ChatGPT CANNOT:**
- Execute commands directly on your Mac
- Access your GitHub Gist directly
- Run the pull worker
- Access your environment variables or secrets

**Important**: ChatGPT generates instructions and commands; **you must run them locally** on your Mac.

## Overview

The pull worker runs on your Mac and polls a GitHub Gist for jobs. You can add jobs to the queue (manually or via the `enqueue_job` tool), and the worker will process them automatically.

## Prerequisites

1. **Pull worker must be running** on your Mac (see "Starting the Worker" below)
2. **GitHub Gist** with `queue.jsonl` and `results.jsonl` files
3. **Environment variables** configured:
   - `NOTES_QUEUE_GIST_ID` - Your Gist ID
   - `GITHUB_TOKEN` - GitHub token with gists read/write permissions
   - `NOTES_MCP_TOKEN` - Shared secret for signing jobs
   - `NOTES_MCP_ALLOWED_FOLDERS` - Comma-separated list of allowed folders

## How It Works

1. **You** generate a signed job using the `sign_job` tool (ChatGPT can provide the command)
2. **You** enqueue the job using `enqueue_job` (or manually add to Gist)
3. The pull worker (running on your Mac) picks it up within the poll interval (typically 15 seconds)
4. The note is created in Apple Notes
5. Result is appended to `results.jsonl`

## Recommended Workflow

### Step 1: Generate a Signed Job

**You run this command** on your Mac (ChatGPT can provide the exact command):

```bash
cd /Users/ajoyce/git-repos/notes_mcp
source venv/bin/activate  # If venv exists
export PYTHONPATH="src:$PYTHONPATH"  # Required if package not installed
export NOTES_MCP_TOKEN="your-token-here"  # Use your actual token

python3 -m notes_mcp.sign_job \
  --title "Note Title Here" \
  --body "Note content here" \
  --folder "MCP Inbox" \
  --account "iCloud" \
  --confirm
```

**Note**: If you get `ModuleNotFoundError`, make sure:
1. You're in the project directory
2. `PYTHONPATH="src:$PYTHONPATH"` is set, OR
3. The package is installed with `pip install -e .`

**Output**: A single JSON line that you'll use in the next step.

### Step 2: Enqueue the Job

**Option A: Using enqueue_job tool (Recommended)**

Pipe the output from `sign_job` directly to `enqueue_job`:

```bash
# Make sure PYTHONPATH is set (see Step 1)
python3 -m notes_mcp.sign_job \
  --title "Note Title Here" \
  --body "Note content here" \
  --folder "MCP Inbox" \
  | python3 -m notes_mcp.enqueue_job
```

**Note**: Both commands need the same environment (PYTHONPATH set or package installed).

**Option B: Manual Gist Edit**

1. Copy the JSON output from Step 1
2. Go to your GitHub Gist: `https://gist.github.com/yourusername/YOUR_GIST_ID`
3. Click the pencil icon (Edit) next to `queue.jsonl`
4. Add the JSON line as a new line at the end
5. Click "Update secret gist"

### Step 3: Wait for Processing

The pull worker polls every 15 seconds (configurable via `NOTES_QUEUE_POLL_SECONDS`). Your job will typically be processed within the poll interval; worst case within 2x the poll interval (30 seconds by default).

### Step 4: Check Results

1. **Check Apple Notes**: Open the Notes app and look for your note
2. **Check Gist Results**: View `results.jsonl` in your Gist to see the processing result

## Example Workflow for ChatGPT

When a user asks ChatGPT to create a note, ChatGPT should:

1. **Provide the command** to generate and enqueue the job:
   ```bash
   python3 -m notes_mcp.sign_job \
     --title "Meeting Notes" \
     --body "Discussed project timeline" \
     --folder "MCP Inbox" \
     | python3 -m notes_mcp.enqueue_job
   ```

2. **Explain**: "Run this command on your Mac. It will generate a signed job and automatically add it to your queue. The note will be created in Apple Notes within 15-30 seconds."

3. **If there's an error**: Help troubleshoot based on the error message

## Worker Guarantees

The pull worker enforces the following guarantees:

### 1. Signature Validation
- All jobs must be signed with HMAC-SHA256
- Only jobs signed with the correct secret (`NOTES_MCP_TOKEN`) will be processed
- Invalid signatures result in `status: "denied"`

### 2. Folder Allowlist
- Only folders in `NOTES_MCP_ALLOWED_FOLDERS` are allowed
- "MCP Inbox" is always allowed
- Requests for non-allowlisted folders result in `status: "denied"`

### 3. Deduplication (Idempotency)
- Each job must have a unique `job_id`
- Jobs are tracked in a local SQLite database
- Duplicate `job_id` values result in `status: "skipped_duplicate"` (not re-executed)
- Database keeps the last 5,000 processed jobs (FIFO cleanup)

### 4. Maximum Job Age
- Jobs older than `NOTES_MCP_MAX_JOB_AGE_SECONDS` (default: 24 hours) are rejected
- Prevents replay of old jobs
- Configurable via environment variable

### 5. Result Writing
- **Every job** considered by the worker gets exactly one result line in `results.jsonl`
- Result includes: `job_id`, `processed_at`, `status`, `reason`
- Status values: `"created"`, `"denied"`, `"error"`, `"skipped_duplicate"`

### 6. Confirmation Mode
- If `NOTES_MCP_REQUIRE_CONFIRM=true`, jobs must include `confirm: true` in args
- Jobs without confirmation are denied
- The `confirm` field is part of the signed payload (cannot be tampered with)

### 7. Input Validation
- Title: max 200 characters
- Body: max 50,000 characters
- Folder name: max 200 characters
- Exceeding limits results in `status: "denied"`

### 8. Security
- Secrets (`GITHUB_TOKEN`, `NOTES_MCP_TOKEN`) are never logged
- Only job metadata (job_id, status) is logged
- Full job payloads are not logged

## Quick Reference

### Command Template

```bash
python3 -m notes_mcp.sign_job \
  --title "TITLE" \
  --body "BODY" \
  --folder "FOLDER_NAME" \
  --account "iCloud" \
  --confirm \
  | python3 -m notes_mcp.enqueue_job
```

### Parameters

- `--title` (required): Note title (max 200 chars)
- `--body` (required): Note content (max 50,000 chars)
- `--folder` (optional): Folder name (default: "MCP Inbox", max 200 chars)
- `--account` (optional): "iCloud" or "On My Mac" (default: "iCloud")
- `--confirm` (optional): Include if `NOTES_MCP_REQUIRE_CONFIRM=true`

### Allowed Folders

Only these folders are allowed (configured via `NOTES_MCP_ALLOWED_FOLDERS`):
- MCP Inbox (always allowed)
- Work
- Personal
- (any others you've configured)

### Environment Variables

**Required:**
- `NOTES_QUEUE_GIST_ID` - GitHub Gist ID
- `GITHUB_TOKEN` - GitHub token with gists permissions
- `NOTES_MCP_TOKEN` - Shared secret for signing jobs

**Optional:**
- `NOTES_MCP_ALLOWED_FOLDERS` - Comma-separated folder list (default: "MCP Inbox")
- `NOTES_MCP_REQUIRE_CONFIRM` - Set to "true" to require confirmation
- `NOTES_MCP_MAX_JOB_AGE_SECONDS` - Max job age in seconds (default: 86400 = 24 hours)
- `NOTES_QUEUE_POLL_SECONDS` - Poll interval in seconds (default: 15)
- `NOTES_QUEUE_FILENAME` - Queue filename (default: "queue.jsonl")
- `NOTES_RESULTS_FILENAME` - Results filename (default: "results.jsonl")

## Minimal Smoke Test

To verify everything is working:

1. **Start the worker** (in one terminal):
   ```bash
   cd /Users/ajoyce/git-repos/notes_mcp
   source venv/bin/activate
   export PYTHONPATH="src:$PYTHONPATH"
   # Set all required env vars
   python3 -m notes_mcp.pull_worker
   ```

2. **Enqueue a test job** (in another terminal):
   ```bash
   cd /Users/ajoyce/git-repos/notes_mcp
   source venv/bin/activate
   export PYTHONPATH="src:$PYTHONPATH"
   # Set NOTES_MCP_TOKEN
   python3 -m notes_mcp.sign_job \
     --title "Test Note" \
     --body "This is a test" \
     --folder "MCP Inbox" \
     | python3 -m notes_mcp.enqueue_job
   ```

3. **Verify**:
   - Worker terminal shows: "Processed job ...: created"
   - Check Apple Notes for "Test Note"
   - Check Gist `results.jsonl` for result entry with `"status": "created"`

## Troubleshooting

### If job generation fails:
- Check that `NOTES_MCP_TOKEN` is set
- Verify you're in the project directory
- Ensure virtual environment is activated

### If enqueue fails:
- Verify `NOTES_QUEUE_GIST_ID` and `GITHUB_TOKEN` are set
- Check GitHub token has gists read/write permissions
- Verify Gist exists and has `queue.jsonl` file

### If job doesn't process:
- Verify pull worker is running on the Mac
- Check that job was added correctly to `queue.jsonl` (valid JSON, one line)
- Check `results.jsonl` for error messages
- Verify folder is in allowlist
- Check job age (must be < 24 hours by default)

### Common status values in results.jsonl:
- `"status": "created"` - Note was created successfully
- `"status": "denied"` - Job was rejected (check `reason` field)
- `"status": "error"` - Error during execution (check `reason` field)
- `"status": "skipped_duplicate"` - Job with same `job_id` already processed

### Common denial reasons:
- `"Folder 'X' is not in the allowlist"` - Use an allowed folder
- `"Confirmation required (confirm=true) but not provided"` - Add `--confirm` flag
- `"Job is too old"` - Generate a new job
- `"Invalid signature"` - Token mismatch or job was modified
- `"Title exceeds maximum length"` - Reduce title length
- `"Body exceeds maximum length"` - Reduce body length

## Starting the Worker (One-Time Setup)

The pull worker must be running on your Mac. To start it:

```bash
cd /Users/ajoyce/git-repos/notes_mcp
source venv/bin/activate
export PYTHONPATH="src:$PYTHONPATH"
export NOTES_QUEUE_GIST_ID="your-gist-id"
export GITHUB_TOKEN="your-github-token"
export NOTES_MCP_TOKEN="your-secret-token"
export NOTES_MCP_ALLOWED_FOLDERS="MCP Inbox,Work,Personal"

python3 -m notes_mcp.pull_worker
```

Or set it up as a background service (see README.md for launchd setup).

## Security Notes

- Jobs are signed with HMAC-SHA256 - only jobs signed with the correct secret will be processed
- The `NOTES_MCP_TOKEN` is the signing secret
- Jobs are validated for folder allowlist, confirmation requirements, rate limits, job age, etc.
- All actions are logged to `~/Library/Logs/notes-mcp/notes-mcp.log` (secrets are never logged)
- The `confirm` field is part of the signed payload and cannot be tampered with

## Summary for ChatGPT

**To help a user create a note via the pull worker:**

1. **Provide the command** to generate and enqueue:
   ```bash
   python3 -m notes_mcp.sign_job --title "..." --body "..." --folder "MCP Inbox" | python3 -m notes_mcp.enqueue_job
   ```

2. **Explain**: "Run this command on your Mac. It will create a signed job and add it to your queue. The note will appear in Apple Notes within 15-30 seconds."

3. **If there's an error**: Help troubleshoot based on the error message and the troubleshooting section above.

**Important**: ChatGPT cannot execute commands - the user must run them locally on their Mac.
