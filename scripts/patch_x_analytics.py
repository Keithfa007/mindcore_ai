#!/usr/bin/env python3
"""One-shot: Add X/Twitter analytics to Telegram Digest."""

with open("scripts/telegram_digest.py") as f:
    content = f.read()

changes = 0

# 1. Add X to EU platform fetch
content = content.replace(
    'eu_data = _fetch_platform_stats(eu_url, headers, "tiktok,youtube")',
    'eu_data = _fetch_platform_stats(eu_url, headers, "tiktok,youtube,x")'
)
changes += 1
print("Added X to EU platform fetch")

# 2. Add X to platform_map
content = content.replace(
    '"youtube": ("YouTube", eu_data),',
    '"youtube": ("YouTube", eu_data),\n            "x": ("X", eu_data),'
)
changes += 1
print("Added X to platform_map")

# 3. Add X to display loop
content = content.replace(
    'for platform in ["tiktok", "tiktok_us", "facebook", "youtube"]:',
    'for platform in ["tiktok", "tiktok_us", "x", "facebook", "youtube"]:'
)
changes += 1
print("Added X to display loop")

# 4. Add X label to name mapping
content = content.replace(
    '"tiktok_us": "TikTok (US)", "facebook": "Facebook", "youtube": "YouTube"',
    '"tiktok_us": "TikTok (US)", "x": "X", "facebook": "Facebook", "youtube": "YouTube"'
)
changes += 1
print("Added X label to name mapping")

# 5. Update version
content = content.replace("Daily Telegram Digest v2.9", "Daily Telegram Digest v3.0")
content = content.replace("Daily Digest v2.9 ==", "Daily Digest v3.0 ==")
changes += 1
print("Updated version to v3.0")

with open("scripts/telegram_digest.py", "w") as f:
    f.write(content)

print(f"\nDone! {changes} changes applied.")
