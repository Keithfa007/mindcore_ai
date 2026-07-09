#!/usr/bin/env python3
"""
Patch: Replace dark gradient quote backgrounds with warm rotating palettes + grain texture.
8 distinct color palettes rotate randomly for visual variety on Pinterest/X feeds.
"""

filepath = "scripts/quotes_pipeline.py"

with open(filepath, "r") as f:
    content = f.read()

old_bg = '''def create_gradient_background():
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    top_r, top_g, top_b = 12, 16, 32
    bot_r, bot_g, bot_b = 6, 6, 12
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        ease = ratio * ratio * (3 - 2 * ratio)
        r = int(top_r + (bot_r - top_r) * ease)
        g = int(top_g + (bot_g - top_g) * ease)
        b = int(top_b + (bot_b - top_b) * ease)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    vignette = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    cx, cy = WIDTH // 2, HEIGHT // 2
    max_dist = math.sqrt(cx * cx + cy * cy)
    for y in range(0, HEIGHT, 4):
        for x in range(0, WIDTH, 4):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            alpha = int(min(80, (dist / max_dist) * 120))
            vdraw.rectangle([x, y, x + 4, y + 4], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), vignette).convert("RGB")'''

new_bg = '''QUOTE_PALETTES = [
    {
        "name": "warm_amber",
        "top": (180, 130, 60),
        "bot": (120, 75, 30),
        "text": (255, 255, 255),
        "accent": (255, 240, 200)
    },
    {
        "name": "deep_brown",
        "top": (90, 60, 45),
        "bot": (45, 28, 18),
        "text": (255, 255, 255),
        "accent": (230, 210, 180)
    },
    {
        "name": "parchment",
        "top": (210, 195, 170),
        "bot": (175, 155, 130),
        "text": (35, 30, 25),
        "accent": (80, 65, 50)
    },
    {
        "name": "sage_green",
        "top": (95, 120, 85),
        "bot": (55, 75, 50),
        "text": (255, 255, 255),
        "accent": (220, 235, 210)
    },
    {
        "name": "deep_navy",
        "top": (30, 45, 80),
        "bot": (15, 20, 45),
        "text": (255, 255, 255),
        "accent": (180, 200, 235)
    },
    {
        "name": "muted_purple",
        "top": (95, 70, 110),
        "bot": (50, 35, 65),
        "text": (255, 255, 255),
        "accent": (220, 200, 235)
    },
    {
        "name": "terracotta",
        "top": (170, 95, 60),
        "bot": (110, 55, 35),
        "text": (255, 255, 255),
        "accent": (255, 220, 190)
    },
    {
        "name": "teal_ocean",
        "top": (40, 100, 110),
        "bot": (20, 55, 65),
        "text": (255, 255, 255),
        "accent": (180, 230, 235)
    }
]

def create_gradient_background(palette=None):
    if palette is None:
        palette = random.choice(QUOTE_PALETTES)
    print(f"  BG palette: {palette['name']}")
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)
    top_r, top_g, top_b = palette["top"]
    bot_r, bot_g, bot_b = palette["bot"]
    for y in range(HEIGHT):
        ratio = y / HEIGHT
        ease = ratio * ratio * (3 - 2 * ratio)
        r = int(top_r + (bot_r - top_r) * ease)
        g = int(top_g + (bot_g - top_g) * ease)
        b = int(top_b + (bot_b - top_b) * ease)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    # Grain texture overlay for organic feel
    import numpy as np
    grain = np.random.normal(0, 12, (HEIGHT, WIDTH, 3)).astype(np.int16)
    img_arr = np.array(img, dtype=np.int16)
    img_arr = np.clip(img_arr + grain, 0, 255).astype(np.uint8)
    img = Image.fromarray(img_arr)
    # Subtle vignette
    vignette = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    cx, cy = WIDTH // 2, HEIGHT // 2
    max_dist = math.sqrt(cx * cx + cy * cy)
    for y in range(0, HEIGHT, 4):
        for x in range(0, WIDTH, 4):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            alpha = int(min(50, (dist / max_dist) * 80))
            vdraw.rectangle([x, y, x + 4, y + 4], fill=(0, 0, 0, alpha))
    return Image.alpha_composite(img.convert("RGBA"), vignette).convert("RGB"), palette'''

assert old_bg in content, "Target background function not found"
content = content.replace(old_bg, new_bg)

# Update render_quote_image to use palette colors for text
old_render_call = "    img = create_gradient_background()"
new_render_call = "    img, palette = create_gradient_background()"
content = content.replace(old_render_call, new_render_call)

# Update text color to use palette
old_quote_draw = 'draw_text_centered(draw, text_y, line, quote_font, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))'
new_quote_draw = 'draw_text_centered(draw, text_y, line, quote_font, fill=palette["text"], stroke_width=2, stroke_fill=(0, 0, 0) if palette["text"] == (255, 255, 255) else (255, 255, 255))'
if old_quote_draw in content:
    content = content.replace(old_quote_draw, new_quote_draw)

# Update MindCore AI branding text color
old_brand = 'draw_text_centered(draw, brand_y, "MindCore AI", brand_font, fill=(180, 180, 180))'
new_brand = 'draw_text_centered(draw, brand_y, "MindCore AI", brand_font, fill=palette.get("accent", (180, 180, 180)))'
if old_brand in content:
    content = content.replace(old_brand, new_brand)

# Add numpy import if not present
if "import numpy" not in content:
    content = content.replace("from PIL import", "import numpy as np\nfrom PIL import")

with open(filepath, "w") as f:
    f.write(content)

assert "QUOTE_PALETTES" in content, "QUOTE_PALETTES not added"
assert "palette['name']" in content or 'palette["name"]' in content, "Palette name print not added"
assert "np.random.normal" in content, "Grain texture not added"
print("Patch applied successfully!")
print("8 quote background palettes added:")
for p in ["warm_amber", "deep_brown", "parchment", "sage_green", "deep_navy", "muted_purple", "terracotta", "teal_ocean"]:
    print(f"  - {p}")
print("Each quote gets a random palette with grain texture and subtle vignette.")
print("Parchment palette uses dark text; all others use white text with stroke.")
