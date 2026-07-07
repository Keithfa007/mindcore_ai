#!/usr/bin/env python3
"""One-shot patch: Fix blog X post missing URL.
Upload-Post ignores x_title for upload_photos endpoint,
so the URL needs to go in the main title field instead.
"""

filepath = "scripts/blog_automation.py"

with open(filepath, "r") as f:
    content = f.read()

# Replace the title field to use x_caption (which has the URL)
# and remove the x_title line (Upload-Post ignores it for photos)
old = '''            ("title", post_title[:280]),
            ("x_title", x_caption),'''

new = '''            ("title", x_caption),'''

assert old in content, f"Target string not found in {filepath}"
content = content.replace(old, new)

with open(filepath, "w") as f:
    f.write(content)

print("Patch applied!")
assert '("title", x_caption),' in content, "title not updated"
assert '("x_title", x_caption)' not in content, "x_title still present"
print("All assertions passed!")
