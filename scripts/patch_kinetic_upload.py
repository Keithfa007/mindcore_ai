#!/usr/bin/env python3
"""One-shot patch: Fix twitter→x platform name + add error logging in kinetic text pipeline."""
import sys

with open("video_pipeline/kinetic_text_pipeline.py") as f:
    content = f.read()

changes = 0

# 1. Fix platform name twitter → x
old = '("platform[]","twitter")'
new = '("platform[]","x")'
if old in content:
    content = content.replace(old, new)
    changes += 1
    print("Fixed: twitter → x platform name")

# 2. Add error body logging after upload
old_log = '''print(f"  Upload {'OK' if resp.ok else 'WARN'}: {resp.status_code}"); return r'''
new_log = '''print(f"  Upload {'OK' if resp.ok else 'WARN'}: {resp.status_code}")
        if not resp.ok: print(f"  {resp.text[:400]}")
        return r'''
if old_log in content:
    content = content.replace(old_log, new_log)
    changes += 1
    print("Added: error body logging on failed uploads")

if changes == 0:
    print("ERROR: No changes applied")
    sys.exit(1)

with open("video_pipeline/kinetic_text_pipeline.py", "w") as f:
    f.write(content)

print(f"\nDone: {changes} changes applied")
