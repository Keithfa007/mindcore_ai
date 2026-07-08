#!/usr/bin/env python3
"""
Patch: Convert affiliate carousel from Amazon products to Online-Therapy.com
Replaces product-picking logic with therapy angle rotation.
Keeps same visual style, posting mechanism, and 5-slide format.
"""
import re

filepath = "scripts/affiliate_carousel_pipeline.py"
with open(filepath, "r") as f:
    content = f.read()

# 1. Update docstring
content = content.replace(
    'Promotes affiliate products from affiliate_products.json as\npersonal recommendation carousels.',
    'Promotes Online-Therapy.com as personal recommendation carousels.\nRotates through different therapy angles (individual, couples, CBT, affordability, etc.).'
)

# 2. Remove PRODUCTS_PATH import
content = content.replace(
    'PRODUCTS_PATH = Path("scripts/affiliate_products.json")\n',
    ''
)

# 3. Update hashtags
content = content.replace(
    'TIKTOK_HASHTAGS = "#mindcoreai #mentalhealth #wellness #selfcare #fyp #ad #affiliate"',
    'TIKTOK_HASHTAGS = "#mindcoreai #mentalhealth #onlinetherapy #therapy #CBT #selfcare #fyp #ad"'
)
content = content.replace(
    'FB_HASHTAGS = "#mindcoreai #mentalhealth #wellness #selfcare #ad"',
    'FB_HASHTAGS = "#mindcoreai #mentalhealth #onlinetherapy #therapy #selfcare #ad"'
)
content = content.replace(
    'US_HASHTAGS = "#mindcoreai #mentalhealth #mentalhealthmatters #mentalhealthtiktok #therapytok #anxietyrelief #healing #selfcare #fyp #ad #affiliate"',
    'US_HASHTAGS = "#mindcoreai #mentalhealth #mentalhealthmatters #onlinetherapy #therapytok #CBT #healing #selfcare #fyp #ad"'
)

# 4. Replace load_products and pick_product with therapy angle system
old_load = '''def load_products():
    data = json.loads(PRODUCTS_PATH.read_text())
    return data.get("product_categories", [])'''

new_load = '''THERAPY_ANGLES = [
    {
        "angle": "individual_therapy",
        "name": "Online-Therapy.com",
        "hook": "Individual therapy from home",
        "focus": "Licensed therapists, CBT-based sessions, worksheets, and messaging. Real therapy without the waiting room.",
        "audience": "anyone struggling with anxiety, depression, stress, or just needing someone to talk to"
    },
    {
        "angle": "couples_therapy",
        "name": "Online-Therapy.com",
        "hook": "Couples therapy you can do together from home",
        "focus": "Work on your relationship with a licensed therapist. Video sessions, messaging, and tools designed for couples.",
        "audience": "couples dealing with communication issues, trust, distance, or wanting to strengthen their relationship"
    },
    {
        "angle": "affordability",
        "name": "Online-Therapy.com",
        "hook": "Therapy that does not break the bank",
        "focus": "Quality CBT-based therapy at a fraction of in-person costs. No insurance needed. Cancel anytime.",
        "audience": "people who want therapy but think they cannot afford it"
    },
    {
        "angle": "mens_mental_health",
        "name": "Online-Therapy.com",
        "hook": "Built for men who find it hard to ask for help",
        "focus": "Private, no waiting room, no judgment. Text your therapist when talking feels too hard. CBT tools that actually work.",
        "audience": "men dealing with anger, isolation, stress, or emotional shutdown"
    },
    {
        "angle": "anxiety_focus",
        "name": "Online-Therapy.com",
        "hook": "Too anxious to sit in a waiting room?",
        "focus": "Start therapy from your couch. CBT-based tools, live video sessions, and a therapist who gets it. Built for people with anxiety.",
        "audience": "people with social anxiety, general anxiety, or who feel overwhelmed by traditional therapy settings"
    },
    {
        "angle": "recovery_support",
        "name": "Online-Therapy.com",
        "hook": "Extra support alongside your recovery",
        "focus": "Sobriety is the start, not the finish. Get ongoing CBT-based therapy to work through what drove you there in the first place.",
        "audience": "people in recovery from addiction who need ongoing emotional support"
    },
    {
        "angle": "first_step",
        "name": "Online-Therapy.com",
        "hook": "Not ready for in-person? Start here.",
        "focus": "Your first therapy session from home. No commute, no small talk in a waiting room. Just you and a licensed therapist.",
        "audience": "people who have never tried therapy and feel nervous about starting"
    },
    {
        "angle": "cbt_tools",
        "name": "Online-Therapy.com",
        "hook": "CBT therapy that gives you real tools",
        "focus": "Not just talking. Worksheets, journal exercises, yoga, and live sessions. A complete toolkit for your mental health.",
        "audience": "people who want practical, evidence-based mental health tools, not just conversation"
    }
]

AFFILIATE_LINK = "https://go.online-therapy.com/SHY0"'''

content = content.replace(old_load, new_load)

# 5. Replace pick_product function
old_pick = '''def pick_product():
    categories = load_products()
    history = load_history()
    recent_products = [h.get("product_name", "") for h in history[-15:]]
    recent_categories = [h.get("category", "") for h in history[-5:]]
    available = []
    for cat in categories:
        if cat["category"] in recent_categories:
            continue
        for prod in cat["products"]:
            if prod["name"] not in recent_products:
                available.append((cat, prod))
    if not available:
        for cat in categories:
            for prod in cat["products"]:
                if prod["name"] not in recent_products:
                    available.append((cat, prod))
    if not available:
        cat = random.choice(categories)
        prod = random.choice(cat["products"])
        available = [(cat, prod)]
    cat, prod = random.choice(available)
    print(f"  Selected: {prod['name']} from {cat['category']}")
    return cat, prod'''

new_pick = '''def pick_angle():
    history = load_history()
    recent_angles = [h.get("angle", "") for h in history[-4:]]
    available = [a for a in THERAPY_ANGLES if a["angle"] not in recent_angles]
    if not available:
        available = THERAPY_ANGLES
    angle = random.choice(available)
    print(f"  Angle: {angle['angle']} -- {angle['hook']}")
    return angle'''

content = content.replace(old_pick, new_pick)

# 6. Replace the generate_script prompt section
# Find and replace the prompt that generates slide content
old_prompt_start = '    prompt = f"""Write a 5-slide TikTok carousel promoting this product as a personal recommendation.'
# Find the full prompt block - search for the next function or the raw = _call_claude line
prompt_pattern = re.compile(
    r'    prompt = f"""Write a 5-slide TikTok carousel promoting this product as a personal recommendation\..*?"""',
    re.DOTALL
)
match = prompt_pattern.search(content)
if match:
    old_prompt = match.group(0)
    new_prompt = '''    prompt = f"""Write a 5-slide TikTok carousel promoting Online-Therapy.com as a personal recommendation.

Angle: {angle['hook']}
Focus: {angle['focus']}
Target audience: {angle['audience']}

RULES:
- Slide 1: Emotional hook that stops the scroll. Short, raw, personal. No product name yet.
- Slide 2: Name the pain point. Make the reader feel seen.
- Slide 3: Introduce Online-Therapy.com naturally. What it offers: licensed therapists, CBT-based, worksheets, live sessions, messaging.
- Slide 4: Why it works. Practical benefits: from home, affordable, no waiting room, cancel anytime.
- Slide 5: Warm CTA. Not salesy. "If you have been thinking about it, this is your sign."
- Each slide: 1 bold heading (5 words max), 2-3 lines of body text (15 words max each)
- Voice: First person, warm, like telling a friend. No clinical language.
- NEVER use em dashes. Use commas or periods instead.
- Do NOT start any slide with "I" or "You know"

Also write:
- tiktok_title: 1 emotional line under 80 chars (no hashtags)
- fb_title: 1-2 sentences, warm and personal (under 200 chars)

Return valid JSON:
{{"slides": [{{"heading": "...", "body": "..."}}, ...], "tiktok_title": "...", "fb_title": "..."}}
"""'''
    content = content.replace(old_prompt, new_prompt)

# 7. Replace references to product/category with angle
content = content.replace('cat, prod = pick_product()', 'angle = pick_angle()')
content = content.replace('category, product = pick_product()', 'angle = pick_angle()')

# Fix the generate_script function signature and calls
content = content.replace('def generate_script(product, category):', 'def generate_script(angle):')
content = content.replace('generate_script(product, category)', 'generate_script(angle)')
content = content.replace('generate_script(prod, cat)', 'generate_script(angle)')

# 8. Replace affiliate_link references
content = content.replace(
    '    affiliate_link = product.get("affiliate_link", "")',
    '    affiliate_link = AFFILIATE_LINK'
)

# 9. Replace product name references in history saving
content = content.replace(
    '"product_name": product["name"]',
    '"product_name": angle["name"]'
)
content = content.replace(
    '"category": category["category"]',
    '"angle": angle["angle"]'
)

# 10. Replace print statements that reference product
content = content.replace(
    'f"  Affiliate link: {affiliate_link}"',
    'f"  Affiliate link: {AFFILIATE_LINK}"'
)

with open(filepath, "w") as f:
    f.write(content)

# Verify key changes
assert "THERAPY_ANGLES" in content, "THERAPY_ANGLES not found"
assert "AFFILIATE_LINK" in content, "AFFILIATE_LINK not found"
assert "pick_angle" in content, "pick_angle not found"
assert "Online-Therapy.com" in content, "Online-Therapy.com not found"
assert "affiliate_products.json" not in content, "Still references affiliate_products.json"

print("Patch applied successfully!")
print("- Amazon product logic replaced with Online-Therapy angle rotation")
print("- 8 therapy angles: individual, couples, affordability, mens health, anxiety, recovery, first step, CBT tools")
print("- Affiliate link: https://go.online-therapy.com/SHY0")
print("- Hashtags updated for therapy focus")
