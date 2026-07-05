#!/usr/bin/env python3
"""One-shot patch: Add Pinterest board ID to carousel, quotes, and blog pipelines.
Also adds error body logging where missing."""
import sys

BOARD = "mental-health"
changes = 0

# === CAROUSEL PIPELINE ===
print("=== Carousel Pipeline ===")
with open("scripts/carousel_pipeline.py") as f:
    c = f.read()

# Add pinterest_board after pinterest_description
if "pinterest_board" not in c and "pinterest" in c:
    old = '("pinterest_description",'
    if old in c:
        # Find the full pinterest_description line and add board after it
        lines = c.split('\n')
        new_lines = []
        for line in lines:
            new_lines.append(line)
            if '("pinterest_description",' in line:
                indent = line[:len(line) - len(line.lstrip())]
                new_lines.append(f'{indent}("pinterest_board","{BOARD}"),')
                changes += 1
                print(f"  Added pinterest_board={BOARD}")
        c = '\n'.join(new_lines)

# Add error body logging if not present
if 'resp.text[:400]' not in c:
    old3 = 'print(f"  Upload {\'OK\' if resp.ok else \'WARNING\'}: {resp.status_code}")'
    new3 = old3 + '\n        if not resp.ok: print(f"  {resp.text[:400]}")'
    if old3 in c:
        c = c.replace(old3, new3)
        changes += 1
        print("  Added error body logging")

with open("scripts/carousel_pipeline.py", "w") as f:
    f.write(c)

# === QUOTES PIPELINE ===
print("\n=== Quotes Pipeline ===")
with open("scripts/quotes_pipeline.py") as f:
    q = f.read()

if "pinterest_board" not in q and "pinterest" in q:
    old = '("pinterest_description", pinterest_desc[:500]),'
    new = f'("pinterest_description", pinterest_desc[:500]),\n        ("pinterest_board", "{BOARD}"),'
    if old in q:
        q = q.replace(old, new)
        changes += 1
        print(f"  Added pinterest_board={BOARD}")

with open("scripts/quotes_pipeline.py", "w") as f:
    f.write(q)

# === BLOG PIPELINE ===
print("\n=== Blog Pipeline ===")
with open("scripts/blog_automation.py") as f:
    b = f.read()

if "pinterest_board" not in b and "pin_to_pinterest" in b:
    old = '("pinterest_description", pinterest_desc),'
    new = f'("pinterest_description", pinterest_desc),\n            ("pinterest_board", "{BOARD}"),'
    if old in b:
        b = b.replace(old, new)
        changes += 1
        print(f"  Added pinterest_board={BOARD}")

with open("scripts/blog_automation.py", "w") as f:
    f.write(b)

if changes == 0:
    print("\nERROR: No changes applied")
    sys.exit(1)

print(f"\nDone: {changes} changes across 3 pipelines")
