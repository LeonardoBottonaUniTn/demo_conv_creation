#!/usr/bin/env python3
"""
Validator for D3-style discussion JSON used by the demo.

Usage:
  python3 validate_discussion.py [path/to/file.json]

Exit codes:
  0 - OK (no issues)
  1 - Validation issues found
  2 - File not found
  3 - JSON parse error / invalid JSON

The validator checks for:
  - well-formed JSON
  - top-level object with expected D3 keys (id, children)
  - each node has an id and non-empty text
  - children (when present) is a list
  - target_id (if present) matches the parent id
  - duplicate ids
"""

import json
import sys
from pathlib import Path


DEFAULT_PATH = Path(__file__).parent.parent / 'backend' / 'bp_130_0_d3.json'


def load_json(path: Path):
    if not path.exists():
        print(f"ERROR: discussion file not found at {path}")
        sys.exit(2)
    try:
        text = path.read_text(encoding='utf-8')
        return json.loads(text)
    except json.JSONDecodeError as e:
        print(f"ERROR: invalid JSON in {path}: {e}")
        sys.exit(3)


def is_node(obj):
    return isinstance(obj, dict)


issues = []
ids = {}


def traverse(node, parent_id=None, path=None):
    if path is None:
        path = []
    # use a readable placeholder for path items
    node_id = node.get('id') if is_node(node) else '<non-node>'
    node_path = path + [str(node_id)]

    if not is_node(node):
        issues.append(("not_an_object", node_path, type(node).__name__))
        return

    nid = node.get('id')
    if nid is None:
        issues.append(("missing_id", node_path, list(node.keys())))
    else:
        ids.setdefault(str(nid), []).append(node_path)

    text = node.get('text')
    if text in (None, ''):
        issues.append(("missing_text", node_path, nid))

    if 'children' in node and not isinstance(node['children'], list):
        issues.append(("children_not_array", node_path, type(node['children']).__name__))

    # if there's a parent, target_id should point to it (if present)
    if parent_id is not None:
        if 'target_id' not in node:
            issues.append(("missing_target_id", node_path, nid))
        else:
            target = node.get('target_id')
            if str(target) != str(parent_id):
                issues.append(("target_mismatch", node_path, nid, parent_id, target))

    for child in node.get('children', []):
        traverse(child, nid, node_path)


def validate(data):
    # top-level should be a dict (a single root node)
    if isinstance(data, list):
        # allow a list of roots, but validate each
        for i, root in enumerate(data):
            traverse(root, parent_id=None, path=[f'<root[{i}]>'])
    elif is_node(data):
        traverse(data, parent_id=None, path=['<root>'])
    else:
        issues.append(("top_level_invalid", [str(type(data).__name__)], None))

    # duplicate ids
    for nid, paths in ids.items():
        if nid and len(paths) > 1:
            issues.append(("duplicate_id", nid, paths))


def format_and_report(issues_list):
    if not issues_list:
        print("No issues found: discussion JSON looks well-formed for D3 hierarchy.")
        return 0

    print(f"Found {len(issues_list)} issue(s):\n")
    for it in issues_list:
        tag = it[0]
        if tag == 'missing_id':
            print(f"- Missing id at path: {' > '.join(it[1])} -- node keys: {it[2]}")
        elif tag == 'missing_text':
            print(f"- Missing text for node id: {it[2]} at path: {' > '.join(it[1])}")
        elif tag == 'children_not_array':
            print(f"- children is not array at path {' > '.join(it[1])}: type={it[2]}")
        elif tag == 'missing_target_id':
            print(f"- missing target_id for node id {it[2]} at path {' > '.join(it[1])}")
        elif tag == 'target_mismatch':
            print(f"- target_id mismatch for node id {it[2]} at path {' > '.join(it[1])}: parent_id={it[3]}, target_id={it[4]}")
        elif tag == 'duplicate_id':
            print(f"- duplicate id '{it[1]}' found in {len(it[2])} locations:\n  " + "\n  ".join([' > '.join(p) for p in it[2]]))
        elif tag == 'not_an_object':
            print(f"- Node at path {' > '.join(it[1])} is not an object: found {it[2]}")
        elif tag == 'top_level_invalid':
            print(f"- Top-level JSON is not an object or array of objects: found {it[1][0]}")
        else:
            print(f"- {it}")

    return 1


def main(argv=None):
    argv = argv or sys.argv[1:]
    path = Path(argv[0]) if argv else DEFAULT_PATH

    data = load_json(path)
    validate(data)
    code = format_and_report(issues)
    sys.exit(code)


if __name__ == '__main__':
    main()
