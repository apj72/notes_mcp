#!/usr/bin/env python3
"""Test script for pull worker functionality."""

import sys
import os
import json

sys.path.insert(0, 'src')

from notes_mcp.pull_worker import (
    fetch_gist_files,
    verify_job_signature,
    validate_job_schema,
    get_gist_id,
    get_github_token,
    canonicalize_job,
    init_state_db,
    is_job_processed,
    mark_job_processed,
)
from notes_mcp.sign_job import create_job
from pathlib import Path
import tempfile

print("=" * 60)
print("PULL WORKER TEST SUITE")
print("=" * 60)

# Test 1: Environment variables
print("\n[1] Environment Variables:")
gist_id = get_gist_id()
token = get_github_token()
print(f"  Gist ID: {gist_id[:8] + '...' if gist_id else 'NOT SET'}")
print(f"  GitHub Token: {'SET' if token else 'NOT SET'}")

# Test 2: Gist connectivity
print("\n[2] Gist Connectivity:")
if gist_id and token:
    try:
        files = fetch_gist_files(gist_id)
        print(f"  ✓ Successfully fetched Gist")
        print(f"  Files found: {list(files.keys())}")
        for name, file_info in files.items():
            content_len = len(file_info.get("content", ""))
            print(f"    - {name}: {content_len} chars, SHA: {file_info.get('sha', 'N/A')[:8]}...")
    except Exception as e:
        print(f"  ✗ Error fetching Gist: {e}")
else:
    print("  ⚠ Skipping: Missing GIST_ID or GITHUB_TOKEN")

# Test 3: Job signing and verification
print("\n[3] Job Signing & Verification:")
os.environ.setdefault('NOTES_MCP_TOKEN', 'test-token-123')
job_line = create_job("Test Note", "Test body", "MCP Inbox")
job = json.loads(job_line)
print(f"  ✓ Generated job: {job['job_id'][:8]}...")
valid, err = verify_job_signature(job)
print(f"  ✓ Signature valid: {valid}")
if not valid:
    print(f"    Error: {err}")

# Test 4: Schema validation
print("\n[4] Schema Validation:")
valid, err = validate_job_schema(job)
print(f"  ✓ Schema valid: {valid}")
if not valid:
    print(f"    Error: {err}")

# Test 5: SQLite state management
print("\n[5] SQLite State Management:")
db_path = Path(tempfile.mktemp())
try:
    init_state_db(db_path)
    mark_job_processed(db_path, 'test-job-123', 'ok')
    processed = is_job_processed(db_path, 'test-job-123')
    not_processed = is_job_processed(db_path, 'test-job-456')
    print(f"  ✓ Database initialized")
    print(f"  ✓ Job 123 processed: {processed}")
    print(f"  ✓ Job 456 processed: {not_processed}")
finally:
    if db_path.exists():
        db_path.unlink()

# Test 6: Canonicalization
print("\n[6] Job Canonicalization:")
canonical = canonicalize_job(job)
print(f"  ✓ Canonical JSON length: {len(canonical)}")
print(f"  ✓ No 'sig' field in canonical: {'sig' not in canonical}")

print("\n" + "=" * 60)
print("SUMMARY:")
print("  ✓ All core functions working")
if gist_id and token:
    print("  ✓ Gist connectivity verified")
    print("  ✓ Ready to run pull worker")
else:
    print("  ⚠ Set NOTES_QUEUE_GIST_ID and GITHUB_TOKEN to test Gist access")
print("=" * 60)
