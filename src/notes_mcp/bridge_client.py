"""HTTP client for communicating with the host-side bridge service for Apple Notes."""

import os
import requests
from typing import Optional


def get_bridge_url() -> Optional[str]:
    """Get the bridge service URL from environment."""
    return os.environ.get("NOTES_MCP_BRIDGE_URL")


def create_note_via_bridge(
    title: str,
    body: str,
    folder: Optional[str] = None,
    account: Optional[str] = None,
    tags: Optional[list] = None,
) -> tuple[bool, Optional[str], Optional[dict]]:
    """
    Create a note via the host-side bridge service.

    Args:
        title: Note title
        body: Note body
        folder: Target folder (default: "MCP Inbox")
        account: Target account ("iCloud" or "On My Mac", default: "iCloud")
        tags: Optional list of tags; appended as hashtags to body for searchability

    Returns:
        Tuple of (success, error_message, result_dict)
        result_dict contains: {account, folder, reference}
    """
    bridge_url = get_bridge_url()
    if not bridge_url:
        return False, "NOTES_MCP_BRIDGE_URL not configured", None

    if folder is None:
        folder = "MCP Inbox"
    if account is None:
        account = "iCloud"

    # Get bridge auth token
    bridge_token = os.environ.get("NOTES_MCP_BRIDGE_TOKEN")
    if not bridge_token:
        return False, "NOTES_MCP_BRIDGE_TOKEN not configured", None

    payload = {
        "title": title,
        "body": body,
        "folder": folder,
        "account": account,
    }
    if tags:
        payload["tags"] = tags

    try:
        response = requests.post(
            f"{bridge_url}/create",
            json=payload,
            headers={
                "Authorization": f"Bearer {bridge_token}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )

        if response.status_code == 200:
            data = response.json()
            return (
                True,
                None,
                {
                    "account": data.get("account", account),
                    "folder": data.get("folder", folder),
                    "reference": data.get("reference", ""),
                },
            )
        else:
            error_msg = response.json().get("error", f"HTTP {response.status_code}")
            return False, error_msg, None

    except requests.exceptions.RequestException as e:
        return False, f"Bridge service error: {str(e)}", None
