#!/usr/bin/env python3
"""One-shot patch: telegram_digest.py v3.3 -> v3.4
Fixes Facebook page lookup to handle dict response from Upload-Post API.
"""

filepath = "scripts/telegram_digest.py"

with open(filepath, "r") as f:
    content = f.read()

# 1. Update version in docstring
content = content.replace(
    'MindCore AI \u2014 Daily Telegram Digest v3.3',
    'MindCore AI \u2014 Daily Telegram Digest v3.4'
)
content = content.replace(
    'v3.3: Added Facebook debug diagnostics to Telegram output.',
    'v3.4: Fixed Facebook page lookup to handle dict response from Upload-Post API.\nv3.3: Added Facebook debug diagnostics to Telegram output.'
)

# 2. Update version in main()
content = content.replace(
    'Daily Digest v3.3 ==',
    'Daily Digest v3.4 =='
)

# 3. Add the _extract_pages_from_response helper function before get_social_media_stats
new_helper = '''

def _extract_pages_from_response(pages_raw, fb_debug):
    """Extract a list of page objects from the Upload-Post /facebook/pages response.

    The API may return:
    - A list of page dicts (original expected format)
    - A dict wrapping a list under a common key (data, pages, results, items)
    - A dict that IS a single page object (has id or page_id)
    - A dict with some arbitrary key containing a list of page dicts
    """
    fb_debug.append(f"type={type(pages_raw).__name__}")

    if isinstance(pages_raw, list):
        fb_debug.append(f"pages_count={len(pages_raw)}")
        return pages_raw if pages_raw else None

    if isinstance(pages_raw, dict):
        fb_debug.append(f"keys={list(pages_raw.keys())[:8]}")

        for key in ("data", "pages", "results", "items"):
            if key in pages_raw and isinstance(pages_raw[key], list):
                extracted = pages_raw[key]
                fb_debug.append(f"extracted_from={key}")
                fb_debug.append(f"pages_count={len(extracted)}")
                return extracted if extracted else None

        pid = pages_raw.get("id") or pages_raw.get("page_id")
        if pid:
            fb_debug.append("dict_is_single_page")
            fb_debug.append("pages_count=1")
            return [pages_raw]

        for k, v in pages_raw.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                if "id" in v[0] or "page_id" in v[0]:
                    fb_debug.append(f"extracted_from={k}")
                    fb_debug.append(f"pages_count={len(v)}")
                    return v

        fb_debug.append("no_page_id_found_in_dict")

    return None


'''

content = content.replace(
    '\ndef get_social_media_stats():',
    new_helper + 'def get_social_media_stats():'
)

# 4. Replace the old Facebook page lookup block
old_fb_block = '''            if fb_resp.status_code == 200:
                pages = fb_resp.json()
                fb_debug.append(f"pages_count={len(pages) if isinstance(pages, list) else \'not_list\'}")
                if isinstance(pages, list) and pages:
                    fb_page_id = pages[0].get("id", pages[0].get("page_id"))
                    fb_debug.append(f"page_id={fb_page_id}")
                else:
                    fb_debug.append("no_pages_returned")'''

new_fb_block = '''            if fb_resp.status_code == 200:
                pages_raw = fb_resp.json()
                pages = _extract_pages_from_response(pages_raw, fb_debug)
                if pages:
                    fb_page_id = pages[0].get("id") or pages[0].get("page_id")
                    fb_debug.append(f"page_id={fb_page_id}")
                else:
                    fb_debug.append("no_pages_found")'''

assert old_fb_block in content, f"OLD BLOCK NOT FOUND!"
content = content.replace(old_fb_block, new_fb_block)

with open(filepath, "w") as f:
    f.write(content)

print("Patch applied successfully!")

# Verify
with open(filepath, "r") as f:
    patched = f.read()

assert "v3.4" in patched, "Version not updated"
assert "_extract_pages_from_response" in patched, "Helper function not added"
assert "pages_raw = fb_resp.json()" in patched, "New fb block not applied"
assert 'not_list' not in patched, "Old debug line still present"
print("All assertions passed!")
