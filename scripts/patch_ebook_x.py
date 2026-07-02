#!/usr/bin/env python3
"""One-shot: Add X posting to ebook promo pipeline."""

with open("scripts/ebook_promo_pipeline.py") as f:
    content = f.read()

changes = 0

# 1. Add X upload function after upload_all_platforms
x_func = '''

def upload_to_x(cover_path, caption, scheduled_date=None):
    """Upload ebook cover image + caption to X (no links in tweet, link in bio)."""
    if not UPLOAD_POST_API_KEY: return {"skipped": True, "reason": "no API key"}
    x_caption = f"{caption}\\n\\nChapter 1 is free. Link in bio.\\n\\n#mentalhealth #mindcoreai"[:280]
    data = [
        ("user", UPLOAD_POST_USER),
        ("platform[]", "x"),
        ("title", x_caption),
        ("post_mode", "DIRECT_POST"),
        ("photo_cover_index", "0"),
    ]
    if scheduled_date: data.append(("scheduled_date", scheduled_date))
    try:
        f = open(cover_path, "rb")
        files = [("photos[]", ("ebook_cover.png", f, "image/png"))]
        resp = requests.post("https://api.upload-post.com/api/upload_photos",
                             headers={"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"},
                             files=files, data=data, timeout=180)
        f.close()
        result = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
        print(f"   X Upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}")
        if not resp.ok: print(f"   {resp.text[:300]}")
        return result
    except Exception as e:
        print(f"   X Upload failed: {e}"); return {"error": str(e)}

'''

marker = "def main():"
if "upload_to_x" not in content:
    content = content.replace(marker, x_func + marker)
    changes += 1
    print("Added upload_to_x function")

# 2. Add X upload call in main() after the main upload
old_upload = '''        if result.get("status_code") in (200, 202):
            print(f"   All platforms: Scheduled OK  - {scheduled_date}")
        elif result.get("skipped"):
            print(f"   Skipped  - {result.get('reason')}")
        else:
            print(f"   Check result  - {result.get('status_code', 'unknown')}")'''

new_upload = '''        if result.get("status_code") in (200, 202):
            print(f"   All platforms: Scheduled OK  - {scheduled_date}")
        elif result.get("skipped"):
            print(f"   Skipped  - {result.get('reason')}")
        else:
            print(f"   Check result  - {result.get('status_code', 'unknown')}")

        print("6. Uploading to X (cover image + caption)...")
        x_result = upload_to_x(cover, caption, scheduled_date=scheduled_date)
        if x_result.get("status_code") in (200, 202):
            print(f"   X: Scheduled OK")'''

if "upload_to_x(cover" not in content:
    content = content.replace(old_upload, new_upload)
    changes += 1
    print("Added X upload call in main()")

with open("scripts/ebook_promo_pipeline.py", "w") as f:
    f.write(content)

print(f"\nDone! {changes} changes applied.")
