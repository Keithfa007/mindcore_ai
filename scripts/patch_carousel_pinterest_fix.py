#!/usr/bin/env python3
"""One-shot patch: Remove Pinterest from carousel until board ID is configured.
Also adds error body logging."""
import sys

with open("scripts/carousel_pipeline.py") as f:
    content = f.read()

changes = 0

# Remove Pinterest platform line
old = '''        ("platform[]","facebook"),
        ("platform[]","pinterest"),'''
new = '''        ("platform[]","facebook"),'''
if old in content:
    content = content.replace(old, new)
    changes += 1
    print("Removed Pinterest platform (needs board ID)")

# Remove Pinterest description field
old2 = '''        ("pinterest_description",f"{tiktok_title}\\n\\n{description[:300]}\\n\\nmindcoreai.eu"),'''
if old2 in content:
    content = content.replace(old2, "")
    changes += 1
    print("Removed pinterest_description field")

# Add error body logging if not present
old3 = '''print(f"  Upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}")'''
new3 = '''print(f"  Upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}")
        if not resp.ok: print(f"  {resp.text[:400]}")'''
if old3 in content and "resp.text[:400]" not in content:
    content = content.replace(old3, new3)
    changes += 1
    print("Added error body logging")

if changes == 0:
    print("ERROR: No changes applied")
    sys.exit(1)

with open("scripts/carousel_pipeline.py", "w") as f:
    f.write(content)

print(f"\nDone: {changes} changes applied")
