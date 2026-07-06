#!/usr/bin/env python3
"""One-shot patch: blog_automation.py — add missing UPLOAD_POST variables
Fixes NameError: name 'UPLOAD_POST_API_KEY' is not defined in pin_to_pinterest()
"""

filepath = "scripts/blog_automation.py"

with open(filepath, "r") as f:
    content = f.read()

old_line = 'SERP_API_KEY     = os.environ.get("SERP_API_KEY", "")'

new_lines = '''SERP_API_KEY     = os.environ.get("SERP_API_KEY", "")
UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
UPLOAD_POST_PHOTOS_URL = "https://api.upload-post.com/api/upload"'''

assert old_line in content, "SERP_API_KEY line not found!"
assert "UPLOAD_POST_API_KEY" not in content.split("def pin_to_pinterest")[0], "Already defined!"
content = content.replace(old_line, new_lines, 1)

with open(filepath, "w") as f:
    f.write(content)

print("Patch applied!")

with open(filepath, "r") as f:
    patched = f.read()

assert 'UPLOAD_POST_API_KEY = os.environ.get' in patched, "API key not added"
assert 'UPLOAD_POST_PHOTOS_URL = "https://api.upload-post.com/api/upload"' in patched, "URL not added"
print("All assertions passed!")
