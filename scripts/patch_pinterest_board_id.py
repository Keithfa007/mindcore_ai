#!/usr/bin/env python3
"""Fix Pinterest board ID across all pipelines.
Field must be pinterest_board_id (not pinterest_board) with numeric ID."""
import sys

BOARD_ID = "1123366769493611180"
changes = 0

# === CAROUSEL ===
print("=== Carousel ===")
with open("scripts/carousel_pipeline.py") as f:
    c = f.read()
# Fix wrong field name
if '("pinterest_board","mental-health")' in c:
    c = c.replace('("pinterest_board","mental-health")', f'("pinterest_board_id","{BOARD_ID}")')
    changes += 1
    print("  Fixed: pinterest_board → pinterest_board_id")
elif "pinterest_board_id" not in c and "pinterest" in c:
    c = c.replace('("pinterest_description",', f'("pinterest_board_id","{BOARD_ID}"),\n        ("pinterest_description",')
    changes += 1
    print("  Added pinterest_board_id")
# Add error logging
if 'resp.text[:400]' not in c:
    old = 'print(f"  Upload {\'OK\' if resp.ok else \'WARNING\'}: {resp.status_code}")'
    if old in c:
        c = c.replace(old, old + '\n        if not resp.ok: print(f"  {resp.text[:400]}")')
        changes += 1
        print("  Added error logging")
with open("scripts/carousel_pipeline.py", "w") as f:
    f.write(c)

# === QUOTES ===
print("\n=== Quotes ===")
with open("scripts/quotes_pipeline.py") as f:
    q = f.read()
if '("pinterest_board", "mental-health")' in q:
    q = q.replace('("pinterest_board", "mental-health")', f'("pinterest_board_id", "{BOARD_ID}")')
    changes += 1
    print("  Fixed: pinterest_board → pinterest_board_id")
elif "pinterest_board_id" not in q and "pinterest" in q:
    q = q.replace('("pinterest_description", pinterest_desc[:500]),', f'("pinterest_description", pinterest_desc[:500]),\n        ("pinterest_board_id", "{BOARD_ID}"),')
    changes += 1
    print("  Added pinterest_board_id")
with open("scripts/quotes_pipeline.py", "w") as f:
    f.write(q)

# === BLOG ===
print("\n=== Blog ===")
with open("scripts/blog_automation.py") as f:
    b = f.read()
if '("pinterest_board", "mental-health")' in b:
    b = b.replace('("pinterest_board", "mental-health")', f'("pinterest_board_id", "{BOARD_ID}")')
    changes += 1
    print("  Fixed: pinterest_board → pinterest_board_id")
elif "pinterest_board_id" not in b and "pin_to_pinterest" in b:
    b = b.replace('("pinterest_description", pinterest_desc),', f'("pinterest_description", pinterest_desc),\n            ("pinterest_board_id", "{BOARD_ID}"),')
    changes += 1
    print("  Added pinterest_board_id")
with open("scripts/blog_automation.py", "w") as f:
    f.write(b)

if changes == 0:
    print("\nERROR: No changes applied")
    sys.exit(1)
print(f"\nDone: {changes} changes across 3 pipelines (board_id={BOARD_ID})")
