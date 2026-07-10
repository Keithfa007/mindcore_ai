#!/usr/bin/env python3
"""Fix affiliate carousel: content['description'] -> fb_title, fix slide keys."""

filepath = "scripts/affiliate_carousel_pipeline.py"

with open(filepath, "r") as f:
    content = f.read()

# 1. Replace content["description"] with content["fb_title"] (3 occurrences)
content = content.replace(
    'tiktok_desc = content["description"].strip()',
    'tiktok_desc = content["fb_title"].strip()'
)
content = content.replace(
    'fb_desc = content["description"].strip()',
    'fb_desc = content["fb_title"].strip()'
)
content = content.replace(
    'us_desc = content["description"].strip()',
    'us_desc = content["fb_title"].strip()'
)

# 2. Fix slide rendering to use heading/body keys from new prompt
# Slide 0: was hook -> heading + body
content = content.replace(
    '''if i == 0:
            lines = [(sd.get("hook", ""), HOOK_SIZE, HOOK_COLOR, True)]
            img = render_slide(bg, lines, badge_text="PERSONAL PICK")''',
    '''if i == 0:
            lines = [(sd.get("heading", ""), HOOK_SIZE, HOOK_COLOR, True),
                     (sd.get("body", ""), BODY_SIZE, BODY_COLOR, False)]
            img = render_slide(bg, lines, badge_text="PERSONAL PICK")'''
)

# Slide 1: was story -> heading + body
content = content.replace(
    '''elif i == 1:
            lines = [(sd.get("story", ""), BODY_SIZE, BODY_COLOR, False)]
            img = render_slide(bg, lines)''',
    '''elif i == 1:
            lines = [(sd.get("heading", ""), BOLD_SIZE, BOLD_COLOR, True),
                     (sd.get("body", ""), BODY_SIZE, BODY_COLOR, False)]
            img = render_slide(bg, lines)'''
)

# Slide 2: was shift -> heading + body
content = content.replace(
    '''elif i == 2:
            lines = [(sd.get("shift", ""), BODY_SIZE, BODY_COLOR, False)]
            img = render_slide(bg, lines)''',
    '''elif i == 2:
            lines = [(sd.get("heading", ""), BOLD_SIZE, BOLD_COLOR, True),
                     (sd.get("body", ""), BODY_SIZE, BODY_COLOR, False)]
            img = render_slide(bg, lines)'''
)

# Slide 3: heading was correct, add body
content = content.replace(
    '''elif i == 3:
            lines = [(sd.get("heading", ""), BOLD_SIZE, BOLD_COLOR, True)]
            img = render_slide(bg, lines)''',
    '''elif i == 3:
            lines = [(sd.get("heading", ""), BOLD_SIZE, BOLD_COLOR, True),
                     (sd.get("body", ""), BODY_SIZE, BODY_COLOR, False)]
            img = render_slide(bg, lines)'''
)

# Slide 4: was cta -> heading + body
content = content.replace(
    '''elif i == 4:
            cta_text = sd.get("cta", "Check the link below")
            lines = [
                (cta_text, CTA_TRIG, CTA_COLOR, True),
                ("MindCore AI", CTA_APP, ACCENT_COLOR, True),
            ]
            img = render_slide(bg, lines)''',
    '''elif i == 4:
            lines = [
                (sd.get("heading", "Your sign to start"), CTA_TRIG, CTA_COLOR, True),
                (sd.get("body", ""), BODY_SIZE, BODY_COLOR, False),
                ("MindCore AI", CTA_APP, ACCENT_COLOR, True),
            ]
            img = render_slide(bg, lines)'''
)

with open(filepath, "w") as f:
    f.write(content)

assert 'content["description"]' not in content, "description still referenced"
assert 'content["fb_title"]' in content, "fb_title not added"
assert 'sd.get("hook"' not in content, "old hook key still present"
assert 'sd.get("story"' not in content, "old story key still present"
assert 'sd.get("shift"' not in content, "old shift key still present"
print("All fixes applied:")
print("  1. content['description'] -> content['fb_title'] (3 places)")
print("  2. All 5 slides now use heading + body keys")
