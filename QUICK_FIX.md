# Quick Fix: Module Not Found Error

If you see `ModuleNotFoundError: No module named 'notes_mcp'`, use one of these solutions:

## Solution 1: Set PYTHONPATH (Quick)

```bash
cd /Users/ajoyce/git-repos/notes_mcp
export PYTHONPATH="src:$PYTHONPATH"

python3 -m notes_mcp.sign_job \
  --title "Note Title" \
  --body "Content" \
  --folder "MCP Inbox" \
  | python3 -m notes_mcp.enqueue_job
```

## Solution 2: Activate Virtual Environment (Recommended)

```bash
cd /Users/ajoyce/git-repos/notes_mcp
source venv/bin/activate
export PYTHONPATH="src:$PYTHONPATH"

python3 -m notes_mcp.sign_job \
  --title "Note Title" \
  --body "Content" \
  --folder "MCP Inbox" \
  | python3 -m notes_mcp.enqueue_job
```

## Solution 3: Install Package (Permanent)

```bash
cd /Users/ajoyce/git-repos/notes_mcp
source venv/bin/activate
python3 -m pip install -e .

# Then you can run without PYTHONPATH:
python3 -m notes_mcp.sign_job --title "Test" --body "Content"
```

## Solution 4: Use Direct Script Path

```bash
cd /Users/ajoyce/git-repos/notes_mcp
source venv/bin/activate
export PYTHONPATH="src:$PYTHONPATH"

python3 src/notes_mcp/sign_job.py \
  --title "Note Title" \
  --body "Content" \
  --folder "MCP Inbox" \
  | python3 src/notes_mcp/enqueue_job.py
```

## Recommended: Add to Your Shell Profile

Add this to your `~/.zshrc` or `~/.bash_profile`:

```bash
# Notes MCP helper
notes_mcp() {
    cd /Users/ajoyce/git-repos/notes_mcp
    source venv/bin/activate 2>/dev/null || true
    export PYTHONPATH="src:$PYTHONPATH"
    "$@"
}

# Then use:
notes_mcp python3 -m notes_mcp.sign_job --title "Test" --body "Content"
```
