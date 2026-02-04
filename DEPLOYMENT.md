# Deployment: Minimum Artifacts

These are the files needed in the repo to get the notes service up and running.

## Required in repository

| Path | Purpose |
|------|---------|
| `pyproject.toml` | Package definition and dependencies |
| `README.md` | Setup and usage |
| `start_worker.sh.example` | Template for worker env (copy to `start_worker.sh`, edit, never commit) |
| `start_ingress.sh.example` | Template for ingress (copy to `start_ingress.sh`, edit, never commit) |
| `setup_service.sh` | Install pull worker as launchd service |
| `gpt_action.json.example` | OpenAPI schema for Custom GPT (copy to `gpt_action.json`, set URL/key, never commit) |
| `openapi-schema.json` | OpenAPI schema (alternative for Custom GPT) |
| `CUSTOM_GPT_CONFIG.md` | How to configure ChatGPT Custom GPT |
| `docs/launchd/` | Launchd plists and README for ingress/export services |
| `src/notes_mcp/` | Application code (see below) |
| `.gitignore` | Ignore secrets, venv, `_unsynced/`, etc. |

## Source code (src/notes_mcp)

| File | Purpose |
|------|---------|
| `__init__.py` | Package init |
| `applescript.py` | Create notes via AppleScript |
| `bridge_client.py` | HTTP client for bridge (container) |
| `bridge_server.py` | Bridge API (host-side for container) |
| `enqueue_job.py` | Enqueue jobs to Gist |
| `export_notes.py` | Export notes to SQLite/JSONL |
| `formatting.py` | Body normalization |
| `ingress.py` | Tailscale ingress API |
| `logging.py` | Audit logging |
| `pull_worker.py` | Process Gist queue |
| `security.py` | Validation, allowlists, rate limit |
| `server.py` | MCP server (stdio) |
| `sign_job.py` | HMAC job signing |

## Optional user-facing docs (kept in repo)

| Path | Purpose |
|------|---------|
| `NOTE_TAGS.md` | How tags (hashtags) work |
| `APPLE_NOTES_FORMATTING_SUPPORT.md` | HTML formatting support in Notes |

## Not in repository (gitignored)

- `start_worker.sh`, `start_ingress.sh` – contain secrets
- `gpt_action.json` – contains URL and key
- `com.notes-mcp.*.plist` – launchd plists (may contain paths/tokens)
- `.env`, `*.secret`, `*.key`
- `venv/`, `_unsynced/`

## Unsynced folder (_unsynced/)

The folder `_unsynced/` is gitignored. It holds testing scripts, container files, experimental docs, and experimental source. Use it locally only; it is not required to deploy.

## Quick deploy

1. Clone repo, create venv, `pip install -e .`
2. `cp start_worker.sh.example start_worker.sh` and edit (GITHUB_TOKEN, Gist ID, etc.)
3. Run worker: `./start_worker.sh` or use `./setup_service.sh` for launchd
4. For ingress: `cp start_ingress.sh.example start_ingress.sh`, edit, then `./start_ingress.sh`
5. For Custom GPT: use `gpt_action.json.example` and `CUSTOM_GPT_CONFIG.md`
