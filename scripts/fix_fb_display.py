#!/usr/bin/env python3
"""One-shot: Fix Facebook display in digest + add debug logging"""
import re

with open("scripts/telegram_digest.py") as f:
    content = f.read()

changed = False

# Fix 1: Show Facebook even when all values are zero
old = '''            if parts:
                lines.append(f"  {name}: {' | '.join(parts)}")'''
new = '''            if parts:
                lines.append(f"  {name}: {' | '.join(parts)}")
            else:
                lines.append(f"  {name}: no 30-day data")'''
if old in content:
    content = content.replace(old, new)
    changed = True
    print("Fixed: Facebook fallback display added")

# Fix 2: Add debug logging for platform data keys
old2 = '''        results = {}
        for platform in ["tiktok", "facebook", "youtube"]:
            pdata = data.get(platform, {})'''
new2 = '''        results = {}
        for platform in ["tiktok", "facebook", "youtube"]:
            pdata = data.get(platform, {})
            print(f"   [{platform}] keys: {list(pdata.keys()) if isinstance(pdata, dict) else type(pdata)}")'''
if old2 in content:
    content = content.replace(old2, new2)
    changed = True
    print("Fixed: Debug logging for platform keys added")

if changed:
    with open("scripts/telegram_digest.py", "w") as f:
        f.write(content)
    print("Done!")
else:
    print("No changes needed")
