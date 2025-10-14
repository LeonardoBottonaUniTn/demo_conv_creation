#!/usr/bin/env python3
"""
Check that JSON files under backend/files_root share the same structure as
the canonical `bp_130_0_d3.json`.

Usage:
  python3 check_structure.py [path/to/files_root]

Exit codes:
  0 - all files match structure
  1 - one or more files differ / errors

This script skips any file under a directory named `User` or with `user`/`users` in
the filename (case-insensitive).
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple


CANONICAL_NAME = 'bp_130_0_d3.json'

# canonical schema to validate against (node shape)
# 'str' means a string is expected, 'list' means a list of nodes matching this schema
NODE_SCHEMA = {
    "id": "str",
    "speaker": "str",
    "text": "str",
    "target_id": "str",  # optional, but if present must be str
    "children": "list",
}


def load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        raise
    except json.JSONDecodeError as e:
        raise


def is_primitive(obj: Any) -> bool:
    return not isinstance(obj, (dict, list))


def compare_structure(canonical: Any, other: Any, path: List[str]=None) -> List[str]:
    """Validate `other` against the NODE_SCHEMA-style `canonical`.

    canonical may be:
      - dict with keys mapping to 'str' or 'list'
      - the special marker 'str' meaning a string is expected
      - the special marker 'list' meaning a list of nodes following NODE_SCHEMA
    """
    path = path or []
    issues: List[str] = []

    # canonical is the schema dict
    if isinstance(canonical, dict):
        if not isinstance(other, dict):
            issues.append(f"Type mismatch at {'/'.join(path) or '<root>'}: expected object, found {type(other).__name__}")
            return issues

        # required keys from schema
        for key, sten in canonical.items():
            if key not in other:
                issues.append(f"Missing key at {'/'.join(path + [key])}")
                continue

            val = other[key]
            if sten == 'str':
                if not isinstance(val, str):
                    issues.append(f"Type mismatch at {'/'.join(path + [key])}: expected string, found {type(val).__name__}")
            elif sten == 'list':
                if not isinstance(val, list):
                    issues.append(f"Type mismatch at {'/'.join(path + [key])}: expected list, found {type(val).__name__}")
                else:
                    # validate each child against NODE_SCHEMA
                    for i, child in enumerate(val):
                        issues += compare_structure(NODE_SCHEMA, child, path + [key, f'[{i}]'])
            else:
                issues.append(f"Unknown schema type for key {key}: {sten}")

        # warn about extra keys but don't fail
        extra = set(other.keys()) - set(canonical.keys())
        if extra:
            issues.append(f"Extra keys at {'/'.join(path) or '<root>'}: {sorted(list(extra))}")

    elif canonical == 'str':
        if not isinstance(other, str):
            issues.append(f"Type mismatch at {'/'.join(path) or '<root>'}: expected string, found {type(other).__name__}")

    elif canonical == 'list':
        if not isinstance(other, list):
            issues.append(f"Type mismatch at {'/'.join(path) or '<root>'}: expected list, found {type(other).__name__}")
        else:
            for i, child in enumerate(other):
                issues += compare_structure(NODE_SCHEMA, child, path + [f'[{i}]'])

    else:
        issues.append(f"Unsupported canonical schema type at {'/'.join(path) or '<root>'}: {repr(canonical)}")

    return issues


def main(argv=None):
    argv = argv or sys.argv[1:]
    files_root = Path(argv[0]) if argv else Path(__file__).parent.parent / 'backend' / 'files_root'

    # use the structural schema instead of reading a canonical file
    canonical = NODE_SCHEMA

    results: List[Tuple[Path, List[str]]] = []

    for p in sorted(files_root.rglob('*.json')):
        # skip canonical itself
        if p.name == CANONICAL_NAME:
            continue
        # skip user files and anything under a User directory
        if any(part.lower() == 'user' for part in p.parts):
            print(f"Skipping user file or folder: {p}")
            continue
        if 'user' in p.name.lower() or 'users' in p.name.lower():
            print(f"Skipping user file: {p}")
            continue

        try:
            other = load_json(p)
        except FileNotFoundError:
            results.append((p, ["File not found"]))
            continue
        except json.JSONDecodeError as e:
            results.append((p, [f"Invalid JSON: {e}"]))
            continue

        # Accept a top-level array of nodes: validate each element as a node
        if isinstance(other, list):
            issues = []
            for i, elem in enumerate(other):
                issues += compare_structure(canonical, elem, path=['<root>', f'[{i}]'])
        else:
            issues = compare_structure(canonical, other, path=['<root>'])

        results.append((p, issues))

    any_errors = False
    for path, issues in results:
        if not issues:
            print(f"OK: {path}")
        else:
            any_errors = True
            print(f"\nISSUES in {path}:")
            for it in issues:
                print(f" - {it}")

    if any_errors:
        print("\nOne or more files differ structurally from the canonical JSON.")
        return 1

    print("\nAll checked JSON files share the same top-level structure as the canonical file.")
    return 0


if __name__ == '__main__':
    code = main()
    sys.exit(code)
