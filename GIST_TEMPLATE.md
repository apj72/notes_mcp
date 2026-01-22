# GitHub Gist Template for Notes MCP Pull Worker

## Gist Description

Use this description when creating the Gist:

```
Notes MCP Pull Worker Queue

Queue-based job processing for notes-mcp. Add signed job lines to queue.jsonl. 
The worker processes jobs and appends results to results.jsonl.

See: https://github.com/apj72/NOTES_MCP
```

## queue.jsonl

Initial content (comment):

```
# Notes MCP Job Queue
# Add one signed job per line (JSON format)
# Generate jobs using: python3 -m notes_mcp.sign_job --title "..." --body "..."
# The worker will process jobs and move results to results.jsonl
```

## results.jsonl

Initial content (comment):

```
# Notes MCP Job Results
# This file is automatically appended by the pull worker
# Each line contains a JSON result object with status, location, and optional error
# Do not manually edit this file
```

## Alternative: More Detailed Comments

If you want more detailed comments:

### queue.jsonl (detailed)

```
# Notes MCP Job Queue
#
# Format: One JSON object per line (JSONL format)
# Each job must be signed with HMAC-SHA256
#
# Generate signed jobs using:
#   python3 -m notes_mcp.sign_job --title "Title" --body "Body" --folder "MCP Inbox"
#
# Job schema:
# {
#   "job_id": "uuid",
#   "created_at": "ISO-8601",
#   "tool": "notes.create",
#   "args": { "title": "...", "body": "...", "folder": "...", "account": "iCloud" },
#   "sig": "base64(hmac_sha256(...))"
# }
#
# The pull worker polls this file and processes jobs, appending results to results.jsonl
```

### results.jsonl (detailed)

```
# Notes MCP Job Results
#
# This file is automatically maintained by the pull worker.
# DO NOT manually edit this file.
#
# Format: One JSON result object per line (JSONL format)
#
# Result schema:
# {
#   "job_id": "uuid",
#   "processed_at": "ISO-8601",
#   "status": "ok|denied|error",
#   "location": { "account": "...", "folder": "..." },
#   "reference": "timestamp - title",
#   "error": { "code": "...", "message": "..." }  // only for denied/error
# }
#
# Results are appended in order of processing.
```
