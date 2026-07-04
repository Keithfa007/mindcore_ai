#!/usr/bin/env python3
"""One-shot patch: Add Pinterest pin for each new blog post."""
import sys

with open("scripts/blog_automation.py") as f:
    content = f.read()

changes = 0

# 1. Add UPLOAD_POST constants near the top (after existing imports/constants)
old_import = 'SERP_API_KEY = os.environ.get("SERP_API_KEY", "")'
new_import = '''SERP_API_KEY = os.environ.get("SERP_API_KEY", "")
UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
UPLOAD_POST_PHOTOS_URL = "https://api.upload-post.com/api/upload_photos"'''
if old_import in content and "UPLOAD_POST_API_KEY" not in content:
    content = content.replace(old_import, new_import)
    changes += 1
    print("Added Upload-Post constants")

# 2. Add the Pinterest pin function before main()
pin_func = '''

def pin_to_pinterest(image_data, post_title, post_url, primary_keyword):
    """Pin the blog featured image to Pinterest via Upload-Post."""
    if not UPLOAD_POST_API_KEY:
        print("   Pinterest: skipped (no UPLOAD_POST_API_KEY)")
        return
    import tempfile
    try:
        tmp = tempfile.NamedTemporaryFile(suffix=".jpg", delete=False)
        tmp.write(image_data)
        tmp.close()
        pinterest_desc = (
            f"{post_title}\\n\\n"
            f"Read the full article: {post_url}\\n\\n"
            f"#mentalhealth #mentalhealthmatters #mindcoreai #healing #selfcare "
            f"#recovery #anxiety #mentalwellness #{primary_keyword.replace(' ', '').lower()}"
        )[:500]
        data = [
            ("user", "MindCoreAI"),
            ("platform[]", "pinterest"),
            ("title", post_title[:280]),
            ("pinterest_description", pinterest_desc),
            ("post_mode", "DIRECT_POST"),
            ("photo_cover_index", "0"),
        ]
        f = open(tmp.name, "rb")
        files = [("photos[]", ("blog_pin.jpg", f, "image/jpeg"))]
        resp = requests.post(
            UPLOAD_POST_PHOTOS_URL,
            headers={"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"},
            files=files, data=data, timeout=180,
        )
        f.close()
        os.unlink(tmp.name)
        if resp.ok:
            print(f"   Pinterest: pinned OK ({resp.status_code})")
        else:
            print(f"   Pinterest: WARNING {resp.status_code} - {resp.text[:200]}")
    except Exception as e:
        print(f"   Pinterest: failed - {e}")


'''

old_main = 'def main():'
if old_main in content and "pin_to_pinterest" not in content:
    content = content.replace(old_main, pin_func + old_main)
    changes += 1
    print("Added pin_to_pinterest function")

# 3. Add Pinterest call after publish_to_wordpress in main()
old_publish = '''    post = publish_to_wordpress(topic_data, content, media_id, media_url)'''
new_publish = '''    post = publish_to_wordpress(topic_data, content, media_id, media_url)

    # Pin to Pinterest
    if image_data and post.get("link"):
        print("\\n6. Pinning to Pinterest...")
        pin_to_pinterest(image_data, topic_data["topic"], post["link"], topic_data["primary_keyword"])
    elif image_data:
        post_slug = keyword_to_slug(topic_data["primary_keyword"])
        print("\\n6. Pinning to Pinterest...")
        pin_to_pinterest(image_data, topic_data["topic"], f"https://mindcoreai.eu/{post_slug}/", topic_data["primary_keyword"])'''
if old_publish in content and "Pin to Pinterest" not in content:
    content = content.replace(old_publish, new_publish)
    changes += 1
    print("Added Pinterest call in main()")

# 4. Move image_data to outer scope so it's available after the try/except
old_try = '''    media_id  = None
    media_url = None
    try:
        image_data          = generate_illustration(topic_data["image_prompt"])
        media_id, media_url = upload_image_to_wordpress(image_data, alt_text=topic_data["primary_keyword"])
    except Exception as exc:
        print(f"   Image failed: {exc}")'''
new_try = '''    media_id  = None
    media_url = None
    image_data = None
    try:
        image_data          = generate_illustration(topic_data["image_prompt"])
        media_id, media_url = upload_image_to_wordpress(image_data, alt_text=topic_data["primary_keyword"])
    except Exception as exc:
        print(f"   Image failed: {exc}")'''
if old_try in content:
    content = content.replace(old_try, new_try)
    changes += 1
    print("Moved image_data to outer scope")

if changes == 0:
    print("ERROR: No changes applied")
    sys.exit(1)

with open("scripts/blog_automation.py", "w") as f:
    f.write(content)

print(f"\nDone: {changes} changes applied")
