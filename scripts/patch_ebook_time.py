#!/usr/bin/env python3
"""Fix ebook promo posting time: 10:00 UTC -> 06:00 UTC (08:00 Malta).
Old time clashed with kinetic pipeline at 10:00 UTC on odd days."""

filepath = "scripts/ebook_promo_pipeline.py"

with open(filepath, "r") as f:
    content = f.read()

old = "scheduled_date = get_scheduled_time(10)"
new = "scheduled_date = get_scheduled_time(6)"

assert old in content, "Target string not found"
content = content.replace(old, new)

with open(filepath, "w") as f:
    f.write(content)

print("Posting time updated: 10:00 UTC -> 06:00 UTC (08:00 Malta)")
assert new in content
print("Verified!")
