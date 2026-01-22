# Testing the Pull Worker

## Quick Test Guide

### Step 1: Create a Private GitHub Gist

1. Go to https://gist.github.com
2. Click "New gist" (or the "+" icon)
3. Make sure it's set to **"Create secret gist"** (private)
4. Add two files:
   - **Filename**: `queue.jsonl` (leave empty or add a comment like `# Job queue`)
   - **Filename**: `results.jsonl` (leave empty or add a comment like `# Results`)
5. Click "Create secret gist"
6. **Copy the Gist ID** from the URL:
   - URL looks like: `https://gist.github.com/yourusername/abc123def456`
   - The ID is: `abc123def456` (the last part)

### Step 2: Create a GitHub Fine-Grained Token

1. Go to GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens
2. Click "Generate new token"
3. Configure:
   - **Token name**: `notes-mcp-worker` (or any name)
   - **Expiration**: Set as needed (e.g., 90 days)
   - **Repository access**: Select "Only select repositories" → choose "None" (we only need gists)
   - **Permissions**: Under "Account permissions" → find "Gists" → select "Read and write"
4. Click "Generate token"
5. **Copy the token immediately** (you won't see it again)

### Step 3: Set Environment Variables

In your terminal:

```bash
cd /Users/ajoyce/git-repos/notes_mcp

# Required
export NOTES_QUEUE_GIST_ID="your-gist-id-here"  # From Step 1
export GITHUB_TOKEN="your-github-token-here"    # From Step 2
export NOTES_MCP_TOKEN="test-token-123"        # Or use your existing token

# Optional (these are defaults, but you can set them)
export NOTES_MCP_ALLOWED_FOLDERS="MCP Inbox"
export NOTES_QUEUE_POLL_SECONDS="15"
```

### Step 4: Generate a Signed Job

Use the helper script to create a signed job:

```bash
python3 -m notes_mcp.sign_job \
  --title "Test Note from Pull Worker" \
  --body "This note was created via the pull worker queue system!" \
  --folder "MCP Inbox" \
  --account "iCloud"
```

This will output a JSON line like:
```json
{"job_id":"abc-123-def","created_at":"2025-01-20T...","tool":"notes.create","args":{"title":"Test Note from Pull Worker","body":"This note was created via the pull worker queue system!","folder":"MCP Inbox","account":"iCloud"},"sig":"base64signature..."}
```

**Copy this entire line.**

### Step 5: Add Job to Gist Queue

1. Go back to your Gist: https://gist.github.com/yourusername/your-gist-id
2. Click the pencil icon (Edit) next to `queue.jsonl`
3. Paste the JSON line you copied (it should be on one line)
4. Click "Update secret gist"

### Step 6: Run the Pull Worker

In your terminal:

```bash
python3 -m notes_mcp.pull_worker
```

You should see output like:
```
Worker started. Polling every 15 seconds.
Gist ID: your-gist-id
Queue file: queue.jsonl
Results file: results.jsonl
State DB: /Users/ajoyce/.notes-mcp-queue/worker.sqlite3
Processed job abc-123-def: ok
Processed 1 job(s)
```

### Step 7: Verify Results

1. **Check Apple Notes**: Open Apple Notes and look for "Test Note from Pull Worker" in the "MCP Inbox" folder
2. **Check Gist Results**: Go back to your Gist and check `results.jsonl` - it should have a result entry
3. **Check Logs**: 
   ```bash
   tail -f ~/Library/Logs/notes-mcp/notes-mcp.log
   ```

### Step 8: Test Multiple Jobs

Add more jobs to the queue:

```bash
# Generate another job
python3 -m notes_mcp.sign_job \
  --title "Second Test Note" \
  --body "Another test" \
  --folder "MCP Inbox"

# Copy the output and add it to queue.jsonl in your Gist
# (add it as a new line)
```

The worker will pick it up on the next poll (within 15 seconds).

## Troubleshooting

### "Error: GITHUB_TOKEN environment variable is required"
- Make sure you exported `GITHUB_TOKEN` in the same terminal session
- Verify the token is valid and has gists permissions

### "Error: NOTES_QUEUE_GIST_ID environment variable is required"
- Make sure you exported `NOTES_QUEUE_GIST_ID` with the correct Gist ID
- The ID is the last part of the Gist URL

### "Invalid signature"
- Make sure `NOTES_MCP_TOKEN` (or `NOTES_QUEUE_HMAC_SECRET`) matches what was used to sign the job
- Regenerate the job with the correct token set

### "Folder 'X' is not in the allowlist"
- Add the folder to `NOTES_MCP_ALLOWED_FOLDERS`
- Or use "MCP Inbox" which is always allowed

### "AppleScript error"
- Grant Automation permissions: System Settings → Privacy & Security → Automation
- Enable Notes for Terminal/Python
- Restart Terminal after granting permissions

### Job not being processed
- Check the worker is running and polling
- Verify the job JSON is valid (one line, proper JSON)
- Check for errors in the worker output
- Verify the job hasn't already been processed (check SQLite DB)

## Advanced Testing

### Test Idempotency (Prevent Duplicate Execution)

1. Add the same job twice to `queue.jsonl` (same `job_id`)
2. Run the worker
3. It should only process the job once
4. Check SQLite: `sqlite3 ~/.notes-mcp-queue/worker.sqlite3 "SELECT * FROM processed_jobs;"`

### Test Rate Limiting

Add 15 jobs quickly to the queue. The worker should process them but respect the 10/minute rate limit.

### Test Confirmation Mode

```bash
export NOTES_MCP_REQUIRE_CONFIRM="true"

# Generate job WITHOUT --confirm flag
python3 -m notes_mcp.sign_job --title "Test" --body "Test"

# Add to queue - should be denied
# Then generate WITH --confirm
python3 -m notes_mcp.sign_job --title "Test" --body "Test" --confirm
# This one should succeed
```

### Test Folder Allowlist

```bash
export NOTES_MCP_ALLOWED_FOLDERS="MCP Inbox,Work"

# Try a job with folder "Personal" - should be denied
python3 -m notes_mcp.sign_job --title "Test" --body "Test" --folder "Personal"

# Try with "Work" - should succeed
python3 -m notes_mcp.sign_job --title "Test" --body "Test" --folder "Work"
```

## Clean Up

To reset the worker state (if needed):

```bash
rm ~/.notes-mcp-queue/worker.sqlite3
```

This will allow jobs to be processed again (but be careful - this defeats idempotency protection).
