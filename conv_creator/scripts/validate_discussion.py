#!/usr/bin/env python3
import json
import sys
from pathlib import Path

p = Path(__file__).parent.parent / 'backend' / 'bp_130_0_d3.json'
if not p.exists():
    print(f"ERROR: discussion file not found at {p}")
    sys.exit(2)

data = json.loads(p.read_text(encoding='utf-8'))

issues = []
ids = {}

# traverse

def traverse(node, parent_id=None, path=None):
    if path is None:
        path = []
    node_path = path + [node.get('id', '<no-id>')]
    nid = node.get('id')
    if nid is None:
        issues.append(("missing_id", node_path, node))
    else:
        if nid in ids:
            ids[nid].append(node_path)
        else:
            ids[nid] = [node_path]
    if 'text' not in node or node.get('text') in (None, ''):
        issues.append(("missing_text", node_path, nid))
    if 'children' in node and not isinstance(node['children'], list):
        issues.append(("children_not_array", node_path, type(node['children']).__name__))
    # check target_id matches parent
    if parent_id is not None:
        target = node.get('target_id')
        if target is None:
            issues.append(("missing_target_id", node_path, nid))
        else:
            if str(target) != str(parent_id):
                issues.append(("target_mismatch", node_path, nid, parent_id, target))
    # recurse
    for child in node.get('children', []):
        traverse(child, nid, node_path)

traverse(data, parent_id=None)

# duplicates
for nid, paths in ids.items():
    if nid and len(paths) > 1:
        issues.append(("duplicate_id", nid, paths))

# output
if not issues:
    print("No issues found: discussion JSON looks well-formed for D3 hierarchy.")
    sys.exit(0)

print(f"Found {len(issues)} issue(s):\n")
for it in issues:
    tag = it[0]
    if tag == 'missing_id':
        print(f"- Missing id at path: {' > '.join(it[1])} -- node keys: {list(it[2].keys())}")
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
    else:
        print(f"- {it}")

# Exit non-zero to indicate warning
sys.exit(1)
