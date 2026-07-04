#!/usr/bin/env python3
"""One-shot patch: Add Pinterest to carousel pipeline upload function."""
import sys

with open("scripts/carousel_pipeline.py") as f:
    content = f.read()

changes = 0

# Add Pinterest platform line after Facebook
old = '''        ("platform[]","facebook"),'''
new = '''        ("platform[]","facebook"),
        ("platform[]","pinterest"),'''
if old in content:
    content = content.replace(old, new)
    changes += 1
    print("Added Pinterest platform line")

# Add Pinterest description after facebook_description line
old2 = '''        ("facebook_description",facebook_description or description),'''
new2 = '''        ("facebook_description",facebook_description or description),
        ("pinterest_description",f"{tiktok_title}\\n\\n{description[:300]}\\n\\nmindcoreai.eu"),'''
if old2 in content:
    content = content.replace(old2, new2)
    changes += 1
    print("Added Pinterest description field")

# Update version comment
old3 = "Carousel Image Post Pipeline v3.0"
new3 = "Carousel Image Post Pipeline v3.1"
if old3 in content:
    content = content.replace(old3, new3)
    changes += 1
    print("Updated version to v3.1")

# Update the print line in main
old4 = '''print(f"  Scheduled OK -- fires at {scheduled_date} (TikTok + Facebook)")'''
new4 = '''print(f"  Scheduled OK -- fires at {scheduled_date} (TikTok + Facebook + Pinterest)")'''
if old4 in content:
    content = content.replace(old4, new4)
    changes += 1
    print("Updated scheduled OK message")

if changes == 0:
    print("ERROR: No changes applied - anchor strings not found")
    sys.exit(1)

with open("scripts/carousel_pipeline.py", "w") as f:
    f.write(content)

print(f"\nDone: {changes} changes applied to carousel_pipeline.py")
