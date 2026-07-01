#!/usr/bin/env python3
"""One-shot: Change quotes image from vertical (1080x1920) to horizontal (1200x675) for X."""

with open("scripts/quotes_pipeline.py") as f:
    content = f.read()

changes = 0

# 1. Dimensions
content = content.replace("WIDTH  = 1080", "WIDTH  = 1200")
content = content.replace("HEIGHT = 1920", "HEIGHT = 675")
changes += 1
print("Changed dimensions to 1200x675")

# 2. Font sizes (smaller for horizontal)
content = content.replace("quote_font = get_font(62, bold=True)", "quote_font = get_font(44, bold=True)")
content = content.replace("attr_font = get_font(32, bold=False)", "attr_font = get_font(24, bold=False)")
changes += 1
print("Adjusted font sizes for horizontal")

# 3. Line height
content = content.replace("line_height = 82", "line_height = 58")
changes += 1
print("Adjusted line height")

# 4. Quote vertical position (center it better)
content = content.replace("quote_top = int(HEIGHT * 0.38) - (total_text_height // 2)", "quote_top = int(HEIGHT * 0.45) - (total_text_height // 2)")
changes += 1
print("Centered quote vertically")

# 5. Decorative line spacing
content = content.replace("quote_top - 50", "quote_top - 35")
content = content.replace("total_text_height + 30", "total_text_height + 20")
content = content.replace("line_y_bottom + 40", "line_y_bottom + 25")
changes += 1
print("Adjusted decorative spacing")

with open("scripts/quotes_pipeline.py", "w") as f:
    f.write(content)

print(f"\nDone! {changes} groups of changes applied.")
