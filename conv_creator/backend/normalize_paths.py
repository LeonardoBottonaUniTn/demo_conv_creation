#!/usr/bin/env python3
import os
import sqlite3
from pprint import pprint

BACKEND_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BACKEND_DIR, 'db.sqlite3')
FILES_ROOT = os.path.join(BACKEND_DIR, 'files_root')

def find_on_disk(basename):
    for root, _, files in os.walk(FILES_ROOT):
        if basename in files:
            return os.path.join(root, basename)
    return None

def normalize():
    if not os.path.exists(DB_PATH):
        print('DB not found at', DB_PATH)
        return
    # create backup copy
    bak = DB_PATH + '.normalize.bak'
    if not os.path.exists(bak):
        import shutil
        shutil.copy2(DB_PATH, bak)
        print('Backup created at', bak)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute('SELECT id, name, path FROM files')
    rows = cur.fetchall()
    updated = []
    missing = []

    for rid, name, stored in rows:
        chosen = None
        reasons = []
        # 1) if stored already looks like files_root/..., resolve from BACKEND_DIR
        if stored and str(stored).startswith(os.path.normpath('files_root')):
            cand = os.path.normpath(os.path.join(BACKEND_DIR, stored))
            reasons.append(('stored_as_files_root', cand))
            if os.path.exists(cand):
                chosen = cand

        # 2) if not chosen, try FILES_ROOT + stored (legacy or plain filename)
        if not chosen and stored:
            cand2 = os.path.normpath(os.path.join(FILES_ROOT, stored))
            reasons.append(('stored_under_files_root', cand2))
            if os.path.exists(cand2):
                chosen = cand2

        # 3) try interpreting stored as absolute under BACKEND_DIR
        if not chosen and stored:
            cand3 = os.path.normpath(os.path.join(BACKEND_DIR, stored))
            reasons.append(('stored_under_backend', cand3))
            if os.path.exists(cand3):
                chosen = cand3

        # 4) fallback: search by basename under FILES_ROOT
        if not chosen:
            found = find_on_disk(name)
            reasons.append(('search_by_basename', found))
            if found:
                chosen = found

        if chosen:
            rel = os.path.relpath(chosen, BACKEND_DIR)
            if rel != stored:
                cur.execute('UPDATE files SET path = ? WHERE id = ?', (rel, rid))
                updated.append({'id': rid, 'name': name, 'old': stored, 'new': rel, 'chosen': chosen})
        else:
            missing.append({'id': rid, 'name': name, 'stored': stored, 'reasons': reasons})

    conn.commit()
    conn.close()

    print('Normalization complete')
    print('Updated rows:')
    pprint(updated)
    print('\nMissing / not found on disk:')
    pprint(missing)

if __name__ == '__main__':
    normalize()
