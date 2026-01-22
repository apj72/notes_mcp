# Quick Start: Pull Worker

## Setup

1. **Edit `start_worker.sh`** and replace the placeholder values:
   - `NOTES_QUEUE_GIST_ID` - Your GitHub Gist ID
   - `GITHUB_TOKEN` - Your GitHub token
   - `NOTES_MCP_TOKEN` - Your signing secret token

2. **Run the worker**:
   ```bash
   ./start_worker.sh
   ```

## Alternative: Manual Setup

If you prefer to set variables manually:

```bash
cd /Users/ajoyce/git-repos/notes_mcp
source venv/bin/activate
export PYTHONPATH="src:$PYTHONPATH"

# Set your actual values (no quotes needed if no spaces)
export NOTES_QUEUE_GIST_ID=your-gist-id-here
export GITHUB_TOKEN=your-github-token-here
export NOTES_MCP_TOKEN=your-token-here
export NOTES_MCP_ALLOWED_FOLDERS="MCP Inbox,Work,Personal"

python3 -m notes_mcp.pull_worker
```

## Troubleshooting

**If you get `dquote>` prompt:**
- Press `Ctrl+C` to cancel
- Check for unclosed quotes in your commands
- Use single quotes if your values contain special characters
- Or use the `start_worker.sh` script instead

**If module not found:**
- Make sure `PYTHONPATH="src:$PYTHONPATH"` is set
- Or install package: `pip install -e .`
