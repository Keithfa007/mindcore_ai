#!/usr/bin/env python3
"""One-shot: Add Online-Therapy.com affiliate CTA to blog automation footer."""

with open("scripts/blog_automation.py") as f:
    content = f.read()

# 1. Add the CTA constant near the top of the file, after imports
CTA_BLOCK = '''
# -- Online-Therapy.com Affiliate CTA (appended to every blog post) -----------
ONLINE_THERAPY_CTA = """
<div style="background:#1a1a2e;border-radius:12px;padding:28px;margin-top:40px;border:1px solid rgba(212,165,116,0.2);">
  <h3 style="color:#ffffff;font-size:20px;margin:0 0 12px;font-weight:600;">Need Professional Support?</h3>
  <p style="color:rgba(255,255,255,0.75);font-size:15px;line-height:1.7;margin:0 0 20px;">
    If you're ready to take the next step, I personally recommend Online-Therapy.com. It offers CBT-based therapy with licensed therapists, completely online. Worksheets, live sessions, messaging, and a personal therapist you can reach anytime. Affordable, private, and built for people who want real support without the waiting room.
  </p>
  <a href="https://go.online-therapy.com/SHY0" target="_blank" rel="noopener noreferrer" style="display:inline-block;background:#d4a574;color:#1a1a2e;padding:12px 28px;border-radius:8px;font-weight:600;font-size:15px;text-decoration:none;">Try Online-Therapy.com &rarr;</a>
</div>
<img src="https://go.online-therapy.com/aff_i?offer_id=2&aff_id=3963" width="0" height="0" style="position:absolute;visibility:hidden;" border="0" />
"""

'''

# Find a good injection point - after the constants/config section
marker = "# -- Step 1"
if marker in content and "ONLINE_THERAPY_CTA" not in content:
    content = content.replace(marker, CTA_BLOCK + marker)
    print("Added ONLINE_THERAPY_CTA constant")
else:
    if "ONLINE_THERAPY_CTA" in content:
        print("SKIP: CTA constant already exists")
    else:
        print("ERROR: Could not find injection point for constant")

# 2. Append the CTA to content before WordPress publish
old_inject = '''    if media_url:
        content = inject_image_into_content(content, media_url, topic_data["primary_keyword"])'''

new_inject = '''    if media_url:
        content = inject_image_into_content(content, media_url, topic_data["primary_keyword"])

    # Append Online-Therapy.com affiliate CTA to every blog post
    content += ONLINE_THERAPY_CTA'''

if old_inject in content and "content += ONLINE_THERAPY_CTA" not in content:
    content = content.replace(old_inject, new_inject)
    print("Added CTA injection to publish_to_wordpress()")
else:
    if "content += ONLINE_THERAPY_CTA" in content:
        print("SKIP: CTA injection already exists")
    else:
        print("ERROR: Could not find injection point in publish function")

with open("scripts/blog_automation.py", "w") as f:
    f.write(content)

print("Done!")
