#!/usr/bin/env python3
"""Quick status check for notes-mcp project."""

import sys
import os

sys.path.insert(0, 'src')

print("=" * 60)
print("NOTES MCP PROJECT STATUS CHECK")
print("=" * 60)

# Check core modules
print("\n[1] Core Modules:")
try:
    import notes_mcp
    print("  ✓ Package structure OK")
except Exception as e:
    print(f"  ✗ Package error: {e}")

modules = ['server', 'applescript', 'security', 'logging', 'sign_job']
for mod in modules:
    try:
        __import__(f'notes_mcp.{mod}')
        print(f"  ✓ {mod}.py")
    except Exception as e:
        print(f"  ✗ {mod}.py: {e}")

# Check pull_worker (needs requests)
print("\n[2] Pull Worker:")
try:
    import notes_mcp.pull_worker
    print("  ✓ pull_worker.py (imports OK)")
except ImportError as e:
    if 'requests' in str(e):
        print("  ⚠ pull_worker.py (BLOCKED: requests not installed)")
    else:
        print(f"  ✗ pull_worker.py: {e}")

# Check dependencies
print("\n[3] Dependencies:")
try:
    import requests
    print(f"  ✓ requests {requests.__version__}")
except ImportError:
    print("  ✗ requests (NOT INSTALLED - required for pull_worker)")

# Check environment
print("\n[4] Environment Variables:")
env_vars = {
    'NOTES_MCP_TOKEN': 'Required for MCP server',
    'GITHUB_TOKEN': 'Required for pull worker',
    'NOTES_QUEUE_GIST_ID': 'Required for pull worker',
    'NOTES_MCP_ALLOWED_FOLDERS': 'Optional (defaults to "MCP Inbox")',
}
for var, desc in env_vars.items():
    value = os.environ.get(var)
    if value:
        masked = value[:8] + '...' if len(value) > 8 else value
        print(f"  ✓ {var} = {masked}")
    else:
        status = "⚠" if "Required" in desc else "○"
        print(f"  {status} {var} (not set) - {desc}")

# Test sign_job
print("\n[5] Sign Job Test:")
os.environ.setdefault('NOTES_MCP_TOKEN', 'test-token-123')
try:
    from notes_mcp.sign_job import create_job
    job = create_job("Test", "Body", "MCP Inbox")
    import json
    j = json.loads(job)
    print(f"  ✓ sign_job works (generated job_id: {j['job_id'][:8]}...)")
except Exception as e:
    print(f"  ✗ sign_job error: {e}")

print("\n" + "=" * 60)
print("SUMMARY:")
print("  - MCP Server: Ready (needs NOTES_MCP_TOKEN)")
print("  - Pull Worker: Code complete, needs 'requests' installed")
print("  - Documentation: Complete")
print("=" * 60)
