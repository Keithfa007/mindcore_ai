#!/usr/bin/env python3
"""One-shot: Add the X upload call to ebook promo main()."""

with open("scripts/ebook_promo_pipeline.py") as f:
    content = f.read()

old = '''    print("\\n== Done ==")'''
new = '''        print("6. Uploading to X (cover image + caption)...")
        x_result = upload_to_x(cover, caption, scheduled_date=scheduled_date)
        if x_result.get("status_code") in (200, 202):
            print(f"   X: Scheduled OK")

    print("\\n== Done ==")'''

if "upload_to_x(cover" not in content:
    content = content.replace(old, new, 1)
    with open("scripts/ebook_promo_pipeline.py", "w") as f:
        f.write(content)
    print("Added X upload call to main()")
else:
    print("SKIP: X upload call already exists")
