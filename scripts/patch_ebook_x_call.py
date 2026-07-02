#!/usr/bin/env python3
"""One-shot: Add the X upload call to ebook promo main()."""

with open("scripts/ebook_promo_pipeline.py") as f:
    content = f.read()

# Check if the CALL (not definition) exists
if "x_result = upload_to_x" in content:
    print("SKIP: X upload call already exists in main()")
else:
    old = '    print("\\n== Done ==")'
    new = '''        print("6. Uploading to X (cover image + caption)...")
        x_result = upload_to_x(cover, caption, scheduled_date=scheduled_date)

    print("\\n== Done ==")'''
    content = content.replace(old, new, 1)
    with open("scripts/ebook_promo_pipeline.py", "w") as f:
        f.write(content)
    print("Added X upload call to main()")
