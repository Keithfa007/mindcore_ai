#!/usr/bin/env python3
"""Remove Pinterest from carousel (6 slides exceeds Pinterest 5-image max)."""
import sys

with open("scripts/carousel_pipeline.py") as f:
    c = f.read()

changes = 0

if '("platform[]","pinterest")' in c:
    c = c.replace('        ("platform[]","pinterest"),\n', '')
    changes += 1
    print("Removed Pinterest platform")

if '("pinterest_description",' in c:
    lines = c.split('\n')
    new_lines = [l for l in lines if '("pinterest_description",' not in l]
    c = '\n'.join(new_lines)
    changes += 1
    print("Removed pinterest_description")

if '("pinterest_board_id",' in c:
    lines = c.split('\n')
    new_lines = [l for l in lines if '("pinterest_board_id",' not in l]
    c = '\n'.join(new_lines)
    changes += 1
    print("Removed pinterest_board_id")

if changes == 0:
    print("ERROR: No changes applied")
    sys.exit(1)

with open("scripts/carousel_pipeline.py", "w") as f:
    f.write(c)
print(f"\nDone: {changes} changes (Pinterest removed from carousel)")
