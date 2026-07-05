#!/usr/bin/env python3
"""Patch: Add Pinterest to Telegram digest + fix Facebook analytics."""
import sys

with open("scripts/telegram_digest.py") as f:
    c = f.read()

changes = 0

# 1. Add Pinterest to EU fetch
old_fetch = '_fetch_platform_stats(eu_url, headers, "tiktok,youtube,x")'
new_fetch = '_fetch_platform_stats(eu_url, headers, "tiktok,youtube,x,pinterest")'
if old_fetch in c:
    c = c.replace(old_fetch, new_fetch)
    changes += 1
    print("Added Pinterest to EU fetch")

# 2. Add Pinterest to platform_map
old_map = '''            "x": ("X", eu_data),
        }'''
new_map = '''            "x": ("X", eu_data),
            "pinterest": ("Pinterest", eu_data),
        }'''
if old_map in c and '"pinterest"' not in c.split("platform_map")[1][:200]:
    c = c.replace(old_map, new_map)
    changes += 1
    print("Added Pinterest to platform_map")

# 3. Add Pinterest to display loop
old_loop = 'for platform in ["tiktok", "tiktok_us", "x", "facebook", "youtube"]:'
new_loop = 'for platform in ["tiktok", "tiktok_us", "x", "facebook", "youtube", "pinterest"]:'
if old_loop in c:
    c = c.replace(old_loop, new_loop)
    changes += 1
    print("Added Pinterest to display loop")

# 4. Add Pinterest to name map
old_names = '"youtube": "YouTube"'
new_names = '"youtube": "YouTube", "pinterest": "Pinterest"'
if old_names in c and '"pinterest"' not in c.split("name =")[1][:200] if "name =" in c else True:
    c = c.replace(old_names, new_names)
    changes += 1
    print("Added Pinterest to name map")

# 5. Add Facebook page_id debug logging
old_fb_debug = 'print(f"   Facebook pages lookup: {e}")'
new_fb_debug = 'print(f"   Facebook pages lookup failed: {e}")'
if old_fb_debug in c:
    c = c.replace(old_fb_debug, new_fb_debug)

# 6. Add fallback for empty Facebook data
old_fb_no_data = '                lines.append(f"  {name}: no 30-day data")'
new_fb_no_data = '''                if platform == "facebook":
                    lines.append(f"  {name}: no 30-day data (check Upload-Post connection)")
                else:
                    lines.append(f"  {name}: no 30-day data")'''
if old_fb_no_data in c:
    c = c.replace(old_fb_no_data, new_fb_no_data)
    changes += 1
    print("Added Facebook connection hint")

if changes == 0:
    print("ERROR: No changes applied")
    sys.exit(1)

with open("scripts/telegram_digest.py", "w") as f:
    f.write(c)
print(f"\nDone: {changes} changes")
