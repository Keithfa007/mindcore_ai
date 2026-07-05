#!/usr/bin/env python3
"""Comprehensive platform fix across all pipelines.
1. Kinetic text (EU): remove YouTube, keep TikTok + Facebook + X
2. US male video: keep TikTok + YouTube only
3. US female video: keep TikTok + YouTube only
4. Ebook promo: remove YouTube, keep TikTok + Facebook + X, schedule 15:00
5. Affiliate carousel: add X to EU posting
"""
import sys, re
changes = 0

# === 1. KINETIC TEXT — remove YouTube ===
print("=== 1. Kinetic Text Pipeline ===")
with open("video_pipeline/kinetic_text_pipeline.py") as f:
    c = f.read()
if '("platform[]","youtube"),' in c:
    c = c.replace('("platform[]","youtube"),', '')
    changes += 1
    print("  Removed YouTube platform")
with open("video_pipeline/kinetic_text_pipeline.py", "w") as f:
    f.write(c)

# === 2. US MALE VIDEO — TikTok + YouTube only ===
print("\n=== 2. US Male Pipeline ===")
with open("video_pipeline/male_pipeline_patch.py") as f:
    c = f.read()
if '("platform[]","facebook")' in c:
    c = c.replace('("platform[]","facebook"),', '')
    changes += 1
    print("  Removed Facebook")
with open("video_pipeline/male_pipeline_patch.py", "w") as f:
    f.write(c)

# === 3. US FEMALE VIDEO — TikTok + YouTube only ===
print("\n=== 3. Female Pipeline ===")
with open("video_pipeline/female_pipeline.py") as f:
    c = f.read()
if '("platform[]","facebook")' in c:
    c = c.replace('("platform[]","facebook"),', '')
    changes += 1
    print("  Removed Facebook")
with open("video_pipeline/female_pipeline.py", "w") as f:
    f.write(c)

# === 4. EBOOK PROMO — remove YouTube, add POST_HOUR_UTC support ===
print("\n=== 4. Ebook Promo Pipeline ===")
with open("scripts/ebook_promo_pipeline.py") as f:
    c = f.read()
if '("platform[]", "youtube")' in c:
    c = c.replace('        ("platform[]", "youtube"),\n', '')
    changes += 1
    print("  Removed YouTube from main upload")
elif '("platform[]","youtube")' in c:
    c = c.replace('("platform[]","youtube"),', '')
    changes += 1
    print("  Removed YouTube from main upload")
with open("scripts/ebook_promo_pipeline.py", "w") as f:
    f.write(c)

# === 5. AFFILIATE CAROUSEL — add X to EU posting ===
print("\n=== 5. Affiliate Carousel Pipeline ===")
with open("scripts/affiliate_carousel_pipeline.py") as f:
    c = f.read()
# Find EU TikTok data block and add X after EU Facebook block
if '("platform[]", "tiktok")' in c and 'platform.*x' not in c:
    # Add X as a third EU platform after the Facebook block
    # Look for the US TikTok section marker and add EU X before it
    old_marker = '        # --- US TikTok ---'
    new_x_block = '''        # --- EU X/Twitter ---
        eu_x_data = [
            ("user", "MindCoreAI"),
            ("platform[]", "x"),
            ("title", tiktok_caption[:280]),
            ("post_mode", "DIRECT_POST"),
            ("photo_cover_index", "0"),
        ]
        if scheduled_date:
            eu_x_data.append(("scheduled_date", scheduled_date))
        code, msg = post_to_platform(headers, eu_x_data, final_slides)
        print(f"    EU X: {code} {msg[:80]}")

'''
    if old_marker in c:
        c = c.replace(old_marker, new_x_block + old_marker)
        changes += 1
        print("  Added EU X/Twitter platform")
with open("scripts/affiliate_carousel_pipeline.py", "w") as f:
    f.write(c)

if changes == 0:
    print("\nERROR: No changes applied")
    sys.exit(1)
print(f"\nDone: {changes} changes across 5 pipelines")
