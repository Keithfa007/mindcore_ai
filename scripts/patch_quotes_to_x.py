#!/usr/bin/env python3
"""One-shot: Switch quotes pipeline from TikTok+Facebook to X only."""

with open("scripts/quotes_pipeline.py") as f:
    content = f.read()

changes = 0

# 1. Replace TK_HASHTAGS with X hashtags
old_tk = 'TK_HASHTAGS = "#mindcoreai #mentalhealth #mentalhealthmatters #fyp #foryou #mentalhealthawareness #healing #selfcare #therapytok #mentalhealthtiktok #quotestoliveby #realtalk"'
new_tk = 'X_HASHTAGS = "#mindcoreai #mentalhealth #mentalhealthmatters #healing #selfcare #recovery #anxiety #mentalwellness"'
if old_tk in content:
    content = content.replace(old_tk, new_tk)
    changes += 1
    print("Replaced TK_HASHTAGS with X_HASHTAGS")

# 2. Replace FB_HASHTAGS reference
old_fb = 'FB_HASHTAGS = "#mentalhealth #mentalhealthmatters #healing #selfcare #mindcoreai #quotestoliveby"'
if old_fb in content:
    content = content.replace(old_fb, '')
    changes += 1
    print("Removed FB_HASHTAGS")

# 3. Replace platform lines in upload function
old_platforms = '''        ("user", UPLOAD_POST_USER),
        ("platform[]", "tiktok"),
        ("platform[]", "facebook"),
        ("tiktok_title", tiktok_title[:90]),
        ("description", description[:4000]),
        ("facebook_title", fb_title[:255]),
        ("facebook_description", fb_description[:5000]),'''
new_platforms = '''        ("user", UPLOAD_POST_USER),
        ("platform[]", "x"),
        ("title", tiktok_title[:280]),'''
if old_platforms in content:
    content = content.replace(old_platforms, new_platforms)
    changes += 1
    print("Changed platforms from TikTok+Facebook to X")

# 4. Update the main() call to use X-specific formatting
old_desc = '''    tiktok_title = quote[:90]
    # description: full caption + hashtags (TikTok shows this below the title)
    description = f"{caption}\\n\\n{TK_HASHTAGS}"
    fb_title = quote[:255]
    fb_description = f"{quote}\\n\\n{caption}\\n\\n{FB_HASHTAGS}"'''
new_desc = '''    tiktok_title = f"{quote}\\n\\n{caption}\\n\\n{X_HASHTAGS}"[:280]
    # X: single text field with quote + caption + hashtags
    description = ""
    fb_title = ""
    fb_description = ""'''
if old_desc in content:
    content = content.replace(old_desc, new_desc)
    changes += 1
    print("Updated main() for X formatting")

with open("scripts/quotes_pipeline.py", "w") as f:
    f.write(content)

print(f"\nDone! {changes} changes applied.")
