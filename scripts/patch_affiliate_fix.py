#!/usr/bin/env python3
"""Fix affiliate carousel: replace remaining Amazon references with Online-Therapy logic."""

filepath = "scripts/affiliate_carousel_pipeline.py"

with open(filepath, "r") as f:
    content = f.read()

# 1. Replace pick_product function with pick_angle
old_func = '''def pick_product():
    categories = load_products()
    history = load_history()
    recent_products = [h.get("product_name", "") for h in history[-15:]]
    recent_categories = [h.get("category", "") for h in history[-5:]]
    candidates = []
    for cat in categories:
        if cat["category"] in recent_categories:
            continue
        for prod in cat["products"]:
            if prod["name"] not in recent_products:
                candidates.append((cat, prod))
    if not candidates:
        for cat in categories:
            for prod in cat["products"]:
                if prod["name"] not in recent_products:
                    candidates.append((cat, prod))
    if not candidates:
        cat = random.choice(categories)
        prod = random.choice(cat["products"])
        candidates = [(cat, prod)]
    cat, prod = random.choice(candidates)
    print(f"  Selected: {prod['name']} from {cat['category']}")
    return cat, prod'''

new_func = '''def pick_angle():
    history = load_history()
    recent_angles = [h.get("angle", "") for h in history[-4:]]
    available = [a for a in THERAPY_ANGLES if a["angle"] not in recent_angles]
    if not available:
        available = list(THERAPY_ANGLES)
    angle = random.choice(available)
    print(f"  Angle: {angle['angle']} -- {angle['hook']}")
    return angle'''

assert old_func in content, "pick_product function not found"
content = content.replace(old_func, new_func)

# 2. Fix generate_content signature
content = content.replace(
    'def generate_content(client, product, category):',
    'def generate_content(client, angle):'
)

# 3. Fix generate_content call in main
content = content.replace(
    'content = generate_content(client, product, category)',
    'content = generate_content(client, angle)'
)

# 4. Fix "Selecting product" print
content = content.replace(
    'print("\\n1. Selecting product...")',
    'print("\\n1. Selecting angle...")'
)

# 5. Fix slide 3 product reference
content = content.replace(
    '''lines = [(sd.get("product", ""), BOLD_SIZE, BOLD_COLOR, True)]
            img = render_slide(bg, lines, badge_text=product.get("price_range", ""))''',
    '''lines = [(sd.get("heading", ""), BOLD_SIZE, BOLD_COLOR, True)]
            img = render_slide(bg, lines)'''
)

with open(filepath, "w") as f:
    f.write(content)

# Verify
assert "def pick_angle():" in content, "pick_angle not defined"
assert "def pick_product" not in content, "pick_product still exists"
assert "generate_content(client, angle)" in content, "generate_content call not fixed"
assert 'product.get("price_range"' not in content, "price_range still referenced"
print("All fixes applied:")
print("  1. pick_product -> pick_angle (with history rotation)")
print("  2. generate_content signature fixed")
print("  3. main() call fixed")
print("  4. Slide rendering fixed")
print("  5. All product/category references removed")
