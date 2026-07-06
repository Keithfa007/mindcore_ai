#!/usr/bin/env python3
"""One-shot patch: blog_automation.py — fix Pinterest pin by bundling X platform
Upload-Post rejects Pinterest-only photo posts. Quotes pipeline works because
it sends X + Pinterest together. Fix: add X as second platform to blog pin call.
"""

filepath = "scripts/blog_automation.py"

with open(filepath, "r") as f:
    content = f.read()

# Replace the pin_to_pinterest data list to include X platform
old_data = '''        data = [
            ("user", "MindCoreAI"),
            ("platform[]", "pinterest"),
            ("title", post_title[:280]),
            ("pinterest_description", pinterest_desc),
            ("pinterest_board_id", "1123366769493611180"),
            ("post_mode", "DIRECT_POST"),
            ("photo_cover_index", "0"),
        ]'''

new_data = '''        x_caption = (
            f"{post_title}\\n\\n"
            f"Read more: {post_url}\\n\\n"
            f"#mentalhealth #mindcoreai #mentalwellness"
        )[:280]
        data = [
            ("user", "MindCoreAI"),
            ("platform[]", "x"),
            ("platform[]", "pinterest"),
            ("title", post_title[:280]),
            ("x_title", x_caption),
            ("pinterest_description", pinterest_desc),
            ("pinterest_board_id", "1123366769493611180"),
            ("post_mode", "DIRECT_POST"),
            ("photo_cover_index", "0"),
        ]'''

assert old_data in content, "Old data block not found!"
content = content.replace(old_data, new_data)

# Also fix the print message
content = content.replace(
    '   Pinterest: skipped (no UPLOAD_POST_API_KEY)',
    '   Pinterest+X: skipped (no UPLOAD_POST_API_KEY)'
)
content = content.replace(
    '   Pinterest: pinned OK',
    '   Pinterest+X: posted OK'
)
content = content.replace(
    '   Pinterest: WARNING',
    '   Pinterest+X: WARNING'
)
content = content.replace(
    '   Pinterest: failed',
    '   Pinterest+X: failed'
)

with open(filepath, "w") as f:
    f.write(content)

print("Patch applied!")

with open(filepath, "r") as f:
    patched = f.read()

assert '("platform[]", "x")' in patched, "X platform not added"
assert '("platform[]", "pinterest")' in patched, "Pinterest platform missing"
assert '("x_title", x_caption)' in patched, "x_title not added"
assert 'x_caption = (' in patched, "x_caption not defined"
print("All assertions passed!")
