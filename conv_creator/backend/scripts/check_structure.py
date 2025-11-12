#!/usr/bin/env python3
"""
Check that JSON files under backend/files_root are discussion tree files,
draft files or are not correctly structured.

JSON structures:
1) discussion tree files must have top-level keys:
    - 'users': list
    - 'tree': object matching NODE_SCHEMA
2) draft files must have top-level keys:
    - 'fileRef': str
    - 'users': list
    - 'tree': object matching NODE_SCHEMA
    - 'discussion': list of objects matching DISCUSSION_SCHEMA

NODE_SCHEMA:
{
    "id": str,
    "speaker": str,
    "text": str,
    "children": list of NODE_SCHEMA
}

DISCUSSION_SCHEMA:
{
    "id": number,
    "referenceId": str,
    "speaker": str,
    "text": str,
    "addressees": list of str
}

Usage:
  python3 check_structure.py [path/to/files_root]

Exit codes:
  0 - all files match discussion tree structure
  1 - all files match draft structure
  2 - one or more files differ structurally from the json structures we defined

This script skips any file under a directory named `User` or with `user`/`users` in
the filename (case-insensitive).
"""

#!/usr/bin/env python3
import json
import sys
import argparse
from pathlib import Path
from typing import Any, Dict


def is_node_schema(obj: Any) -> bool:
    """Recursively validate NODE_SCHEMA."""
    if not isinstance(obj, dict):
        return False
    required_keys = {"id", "speaker", "text", "children"}
    if set(obj.keys()) != required_keys:
        return False
    if not all(isinstance(obj[k], str) for k in ("id", "speaker", "text")):
        return False
    if not isinstance(obj["children"], list):
        return False
    return all(is_node_schema(child) for child in obj["children"])


def is_discussion_schema(obj: Any) -> bool:
    """Validate DISCUSSION_SCHEMA."""
    if not isinstance(obj, dict):
        return False
    required_keys = {"id", "referenceId", "speaker", "text", "addressees"}
    if set(obj.keys()) != required_keys:
        return False
    if not isinstance(obj["id"], (int, float)):
        return False
    if not all(isinstance(obj[k], str) for k in ("referenceId", "speaker", "text")):
        return False
    if not isinstance(obj["addressees"], list):
        return False
    if not all(isinstance(a, str) for a in obj["addressees"]):
        return False
    return True


def is_discussion_tree_file(data: Dict[str, Any]) -> bool:
    return (
        isinstance(data, dict)
        and set(data.keys()) == {"users", "tree"}
        and isinstance(data["users"], list)
        and is_node_schema(data["tree"])
    )


def is_draft_file(data: Dict[str, Any]) -> bool:
    return (
        isinstance(data, dict)
        and set(data.keys()) == {"fileRef", "users", "tree", "discussion"}
        and isinstance(data["fileRef"], str)
        and isinstance(data["users"], list)
        and is_node_schema(data["tree"])
        and isinstance(data["discussion"], list)
        and all(is_discussion_schema(d) for d in data["discussion"])
    )


def should_skip(path: Path) -> bool:
    """Skip files under directories named User or with 'user' in filename."""
    parts = [p.lower() for p in path.parts]
    if any(part == "user" for part in parts):
        return True
    if any("user" in part for part in parts):
        return True
    return False


def check_file(json_file: Path) -> int:
    """Return exit code per file."""
    if should_skip(json_file):
        return -1  # skipped file

    try:
        with open(json_file, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] Could not read {json_file}: {e}")
        return 2

    if is_discussion_tree_file(data):
        return 0
    elif is_draft_file(data):
        return 1
    else:
        return 2


def main():
    parser = argparse.ArgumentParser(description="Check structure of JSON files in files_root.")
    parser.add_argument("files_root", type=Path, help="Path to files_root")
    args = parser.parse_args()

    json_files = list(args.files_root.rglob("*.json"))
    if not json_files:
        print("No JSON files found.")
        return

    for json_file in json_files:
        code = check_file(json_file)
        if code == -1:
            continue  # skip
        print(f"{json_file} → exit code {code}")


if __name__ == "__main__":
    main()