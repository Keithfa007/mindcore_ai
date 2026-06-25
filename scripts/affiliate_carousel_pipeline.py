#!/usr/bin/env python3
"""
MindCore AI -- Affiliate Product Carousel Pipeline v1.1
========================================================
Promotes affiliate products from affiliate_products.json as
personal recommendation carousels. Visually distinct from
the main emotional carousel (warm amber tones, centered layout,
lifestyle backgrounds, 5 slides).

v1.1: Facebook posts include direct affiliate link in description.
      TikTok uses "Link in bio" (no clickable links in captions).

Schedule: Wednesday + Friday
Cost: ~$0.025/post (5 x fal.ai Flux Schnell @ ~$0.005)
"""

import base64, io, json, os, random, time, math
from datetime import datetime, timedelta, timezone
from pathlib import Path
import anthropic, requests
from PIL import Image, ImageDraw, ImageFont
from scripts.fal_image import generate_fal_image

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
GITHUB_RUN_NUMBER = int(os.environ.get("GITHUB_RUN_NUMBER", "1"))

UPLOAD_POST_PHOTOS_URL = "https://api.upload-post.com/api/upload_photos"
OUTPUT_DIR = Path("scripts/output_affiliate_carousel")
PRODUCTS_PATH = Path("scripts/affiliate_products.json")
HISTORY_PATH = Path("scripts/affiliate_carousel_history.json")

IMAGE_WIDTH = 1080
IMAGE_HEIGHT = 1920
TIKTOK_TITLE_LIMIT = 90
TIKTOK_DESC_LIMIT = 4000
CLAUDE_MAX_RETRIES = 8
CLAUDE_RETRY_BASE = 30
POST_HOUR_UTC = 12
REQUIRED_BRAND_HASHTAG = "#mindcoreai"
TIKTOK_HASHTAGS = "#mindcoreai #mentalhealth #wellness #selfcare #fyp #ad #affiliate"
FB_HASHTAGS = "#mindcoreai #mentalhealth #wellness #selfcare #ad"
SLIDE_COUNT = 5

BADGE_BG = (212, 165, 116)
BADGE_TEXT = (20, 15, 10)
HOOK_COLOR = (255, 255, 255)
BODY_COLOR = (240, 235, 225)
BOLD_COLOR = (255, 255, 255)
CTA_COLOR = (255, 255, 255)
ACCENT_COLOR = (212, 165, 116)
URL_COLOR = (200, 190, 175)
GRADIENT_TOP_ALPHA = 60
GRADIENT_BOTTOM_ALPHA = 200

BADGE_SIZE = 32
HOOK_SIZE = 78
BODY_SIZE = 44
BOLD_SIZE = 50
CTA_TRIG = 56
CTA_APP = 72
CTA_URL = 36

TEXT_CENTER_Y = 0.48
MAX_TEXT_W = int(IMAGE_WIDTH * 0.82)
LINE_GAP = 16
SECTION_GAP = 40


def get_scheduled_post_time():
    now = datetime.now(timezone.utc)
    target = now.replace(hour=POST_HOUR_UTC, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    s = target.strftime("%Y-%m-%dT%H:%M:%SZ")
    print(f"  Scheduled: {s} ({POST_HOUR_UTC:02d}:00 UTC)")
    return s


def load_products():
    data = json.loads(PRODUCTS_PATH.read_text())
    return data.get("product_categories", [])


def load_history():
    if HISTORY_PATH.exists():
        try:
            return json.loads(HISTORY_PATH.read_text())
        except:
            return []
    return []


def save_history(h, entry):
    h.append(entry)
    HISTORY_PATH.write_text(json.dumps(h[-60:], indent=2))


def pick_product():
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
    return cat, prod


LIFESTYLE_PROMPTS = {
    "slide_1": [
        "Cinematic overhead shot of a cosy reading nook at night, warm amber lamp light, soft blankets, steaming mug. 9:16 vertical. No text, no people, no faces.",
        "Warm golden hour light streaming through sheer curtains into a peaceful bedroom. Soft textures, muted tones. 9:16 vertical. No text, no people.",
        "Close-up of warm candlelight on a wooden table, soft bokeh background, amber and honey tones. 9:16 vertical. No text, no watermarks.",
        "Moody cosy evening scene: soft blanket, warm lamp, rain on window. Amber tones, intimate warmth. 9:16 vertical. No text, no people.",
    ],
    "slide_2": [
        "Warm morning light on rumpled white bed sheets, peaceful, minimal. Golden hour tones. 9:16 vertical. No text, no people.",
        "Soft focus on a steaming cup of tea on a wooden surface, warm amber background light. 9:16 vertical. No text, no watermarks.",
        "Rain drops on a window at night, warm interior light blurred behind. Intimate, reflective mood. 9:16 vertical. No text.",
        "Close-up of hands wrapped around a warm mug, soft golden light, wooden table. 9:16 vertical. No faces, no text.",
    ],
    "slide_3": [
        "Warm flat lay of self-care items on a wooden surface: candle, journal, warm drink. Soft golden light from above. 9:16 vertical. No text.",
        "Peaceful morning scene: open book on a sunlit table beside a window, warm tones. 9:16 vertical. No text, no people.",
        "Soft golden light on a wooden shelf with plants, books, and a candle. Warm cosy aesthetic. 9:16 vertical. No text.",
        "Morning sunlight casting warm shadows through blinds onto a peaceful desk. Minimal, warm. 9:16 vertical. No text.",
    ],
    "slide_4": [
        "Beautiful lifestyle flat lay on warm wood: journal, pen, coffee, soft morning light. Clean and aspirational. 9:16 vertical. No text.",
        "Warm sunset light through a window onto a wooden table with a book and warm drink. Peaceful evening. 9:16 vertical. No text.",
        "Close-up of soft fabrics and warm textures in golden amber light. Cosy, tactile, inviting. 9:16 vertical. No text.",
        "Soft golden light on an open notebook beside a window, morning, peaceful. 9:16 vertical. No text, no people.",
    ],
    "slide_5": [
        "Warm inviting phone on a wooden table, soft amber candlelight, cosy evening setting. 9:16 vertical. No text, no watermarks.",
        "Smartphone face-up on a warm wooden surface, soft golden morning light. Clean, minimal, inviting. 9:16 vertical. No text.",
        "Phone on a cosy bedside table with warm lamp light, soft evening tones. 9:16 vertical. No text.",
        "Clean minimal shot of a phone on a marble surface beside a warm drink, golden light. 9:16 vertical. No text.",
    ],
}


def generate_slide_image(slide_key):
    prompts = LIFESTYLE_PROMPTS.get(slide_key, LIFESTYLE_PROMPTS["slide_3"])
    idx = (GITHUB_RUN_NUMBER + int(slide_key.split("_")[1]) - 1) % len(prompts)
    for attempt in range(3):
        pick = (idx + attempt) % len(prompts)
        prompt = prompts[pick]
        print(f"  [fal.ai] {slide_key} generating... (attempt {attempt + 1}/3)")
        try:
            ib = generate_fal_image(prompt)
            print(f"  [fal.ai] {slide_key} ready ({len(ib) // 1024:.0f} KB)")
            return ib
        except Exception as e:
            if "safety" in str(e).lower() or "moderation" in str(e).lower():
                print(f"  [fal.ai] {slide_key} BLOCKED, trying next...")
                continue
            raise
    raise RuntimeError(f"All image prompts for {slide_key} were blocked")


def get_font(size, bold=False):
    paths = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf" if bold else "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in paths:
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def wrap_text(text, font, max_w, draw):
    words = text.split()
    lines = []
    current = ""
    for w in words:
        test = f"{current} {w}".strip()
        bbox = draw.textbbox((0, 0), test, font=font)
        if bbox[2] - bbox[0] > max_w and current:
            lines.append(current)
            current = w
        else:
            current = test
    if current:
        lines.append(current)
    return lines


def draw_warm_gradient(draw, w, h):
    for y in range(h // 3):
        alpha = int(GRADIENT_TOP_ALPHA * (1 - y / (h / 3)))
        draw.rectangle([(0, y), (w, y + 1)], fill=(15, 10, 5, alpha))
    grad_start = int(h * 0.35)
    for y in range(grad_start, h):
        progress = (y - grad_start) / (h - grad_start)
        alpha = int(GRADIENT_BOTTOM_ALPHA * progress)
        draw.rectangle([(0, y), (w, y + 1)], fill=(15, 10, 5, alpha))


def draw_badge(draw, text, cx, y, font):
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 24, 10
    rx = cx - tw // 2 - pad_x
    ry = y
    draw.rounded_rectangle(
        [rx, ry, rx + tw + pad_x * 2, ry + th + pad_y * 2],
        radius=20, fill=BADGE_BG,
    )
    draw.text((cx - tw // 2, ry + pad_y), text, fill=BADGE_TEXT, font=font)
    return th + pad_y * 2 + 20


def render_slide(bg_bytes, lines_data, slide_type="body", badge_text=None):
    bg = Image.open(io.BytesIO(bg_bytes)).convert("RGBA").resize((IMAGE_WIDTH, IMAGE_HEIGHT), Image.LANCZOS)
    overlay = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    draw_warm_gradient(od, IMAGE_WIDTH, IMAGE_HEIGHT)
    bg = Image.alpha_composite(bg, overlay)
    draw = ImageDraw.Draw(bg)
    cx = IMAGE_WIDTH // 2
    total_h = 0
    rendered_lines = []
    for text, size, color, bold in lines_data:
        font = get_font(size, bold)
        wrapped = wrap_text(text, font, MAX_TEXT_W, draw)
        line_h = draw.textbbox((0, 0), "Ay", font=font)[3]
        block_h = len(wrapped) * (line_h + LINE_GAP)
        rendered_lines.append((wrapped, font, color, line_h))
        total_h += block_h + SECTION_GAP
    y = int(IMAGE_HEIGHT * TEXT_CENTER_Y) - total_h // 2
    if badge_text:
        badge_font = get_font(BADGE_SIZE, bold=True)
        badge_h = draw_badge(draw, badge_text, cx, y, badge_font)
        y += badge_h
    for wrapped, font, color, line_h in rendered_lines:
        for line in wrapped:
            bbox = draw.textbbox((0, 0), line, font=font)
            tw = bbox[2] - bbox[0]
            draw.text((cx - tw // 2 + 2, y + 2), line, fill=(0, 0, 0, 120), font=font)
            draw.text((cx - tw // 2, y), line, fill=color, font=font)
            y += line_h + LINE_GAP
        y += SECTION_GAP
    return bg.convert("RGB")


def _call_claude(prompt, client, max_tokens=2000):
    for a in range(1, CLAUDE_MAX_RETRIES + 1):
        try:
            r = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            return r.content[0].text.strip()
        except Exception as e:
            if "overloaded" in str(e).lower() or "529" in str(e):
                wait = CLAUDE_RETRY_BASE * a + random.randint(0, 30)
                print(f"  Claude overloaded, waiting {wait}s (attempt {a}/{CLAUDE_MAX_RETRIES})")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Claude unavailable after all retries")


def generate_content(client, product, category):
    prompt = f"""Write a 5-slide TikTok carousel promoting this product as a personal recommendation.

PRODUCT: {product['name']}
CATEGORY: {category['category']}
BEST FOR: {product.get('best_for', '')}
HIGHLIGHT: {product.get('highlight', '')}
PRICE: {product.get('price_range', '')}

VOICE: You are Keith, founder of MindCore AI. You struggled with anxiety, addiction, and sleepless nights for 20 years. You're 2 years clean. This product genuinely helped you. Write as if recommending to a friend.

FORMAT — respond with EXACTLY this JSON structure, nothing else:
{{
  "tiktok_title": "Short hook title under 85 chars",
  "description": "Longer caption 2-3 sentences, include why you personally use it. End with: Link in bio.",
  "slides": [
    {{"slide": 1, "hook": "Short punchy hook question (8-12 words max)"}},
    {{"slide": 2, "story": "Personal 1-2 sentence connection to the problem"}},
    {{"slide": 3, "shift": "What changed when you found this (1-2 sentences)"}},
    {{"slide": 4, "product": "Product name + key benefit (1-2 sentences)"}},
    {{"slide": 5, "cta": "Call to action (short, warm)"}}
  ]
}}

RULES:
- Slide 1: Hook the viewer with a relatable problem. No product name yet.
- Slide 2: Brief personal story connecting to that problem. Raw and real.
- Slide 3: The turning point. What shifted.
- Slide 4: Introduce the product naturally. What it does and why it works.
- Slide 5: Warm CTA. "Link in bio" must appear.
- Keep ALL text SHORT. These are image overlays, not paragraphs.
- Do NOT use quotation marks in any slide text.
- Sound like a real person, not a marketer."""

    raw = _call_claude(prompt, client)
    raw = raw.replace("```json", "").replace("```", "").strip()
    return json.loads(raw)


def main():
    print("=" * 60)
    print("MindCore AI — Affiliate Product Carousel v1.1")
    print("=" * 60)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    print("\n1. Selecting product...")
    category, product = pick_product()
    affiliate_link = product.get("affiliate_link", "")

    print("\n2. Generating content...")
    content = generate_content(client, product, category)
    print(f"  TikTok title: {content['tiktok_title']}")

    print("\n3. Generating slide images...")
    slide_images = {}
    for i in range(1, SLIDE_COUNT + 1):
        key = f"slide_{i}"
        slide_images[key] = generate_slide_image(key)
        time.sleep(1)

    print("\n4. Rendering slides...")
    final_slides = []
    slides_data = content["slides"]

    for i, sd in enumerate(slides_data):
        key = f"slide_{i + 1}"
        bg = slide_images[key]

        if i == 0:
            lines = [(sd.get("hook", ""), HOOK_SIZE, HOOK_COLOR, True)]
            img = render_slide(bg, lines, badge_text="PERSONAL PICK")
        elif i == 1:
            lines = [(sd.get("story", ""), BODY_SIZE, BODY_COLOR, False)]
            img = render_slide(bg, lines)
        elif i == 2:
            lines = [(sd.get("shift", ""), BODY_SIZE, BODY_COLOR, False)]
            img = render_slide(bg, lines)
        elif i == 3:
            lines = [(sd.get("product", ""), BOLD_SIZE, BOLD_COLOR, True)]
            img = render_slide(bg, lines, badge_text=product.get("price_range", ""))
        elif i == 4:
            cta_text = sd.get("cta", "Link in bio")
            lines = [
                (cta_text, CTA_TRIG, CTA_COLOR, True),
                ("MindCore AI", CTA_APP, ACCENT_COLOR, True),
                ("Link in bio", CTA_URL, URL_COLOR, False),
            ]
            img = render_slide(bg, lines)

        path = OUTPUT_DIR / f"{key}.jpg"
        img.save(path, "JPEG", quality=92)
        final_slides.append(path)
        print(f"  {key} saved ({path})")

    print("\n5. Posting...")
    if not UPLOAD_POST_API_KEY:
        print("  SKIP: UPLOAD_POST_API_KEY not set")
    else:
        title = content["tiktok_title"][:TIKTOK_TITLE_LIMIT]
        tiktok_desc = content["description"]
        if REQUIRED_BRAND_HASHTAG not in tiktok_desc:
            tiktok_desc += f" {REQUIRED_BRAND_HASHTAG}"
        if "#ad" not in tiktok_desc.lower():
            tiktok_desc += " #ad"
        tiktok_desc += f"\n\n{TIKTOK_HASHTAGS}"

        # Facebook description includes direct affiliate link
        fb_desc = content["description"].replace("Link in bio.", "").replace("Link in bio", "").strip()
        if affiliate_link:
            fb_desc += f"\n\nGet it here: {affiliate_link}"
        fb_desc += f"\n\n{FB_HASHTAGS}"
        if "#ad" not in fb_desc.lower():
            fb_desc += " #ad"

        files = []
        for p in final_slides:
            files.append(("files", (p.name, open(p, "rb"), "image/jpeg")))

        headers = {"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"}
        scheduled = get_scheduled_post_time()

        # TikTok — no clickable links, uses "Link in bio"
        payload = {
            "user": "MindCoreAI",
            "platforms": "tiktok",
            "tiktok_title": title,
            "description": tiktok_desc[:TIKTOK_DESC_LIMIT],
            "scheduled_date": scheduled,
        }
        try:
            r = requests.post(UPLOAD_POST_PHOTOS_URL, headers=headers, data=payload, files=files, timeout=120)
            print(f"  TikTok: {r.status_code} — {r.text[:200]}")
        except Exception as e:
            print(f"  TikTok error: {e}")

        # Facebook — includes direct affiliate link
        files2 = []
        for p in final_slides:
            files2.append(("files", (p.name, open(p, "rb"), "image/jpeg")))

        payload_fb = {
            "user": "MindCoreAI",
            "platforms": "facebook",
            "description": fb_desc[:TIKTOK_DESC_LIMIT],
            "scheduled_date": scheduled,
        }
        try:
            r2 = requests.post(UPLOAD_POST_PHOTOS_URL, headers=headers, data=payload_fb, files=files2, timeout=120)
            print(f"  Facebook: {r2.status_code} — {r2.text[:200]}")
        except Exception as e:
            print(f"  Facebook error: {e}")

        print(f"  Affiliate link: {affiliate_link}")

    print("\n6. Saving history...")
    history = load_history()
    save_history(history, {
        "date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "product_name": product["name"],
        "category": category["category"],
        "title": content["tiktok_title"],
        "affiliate_link": affiliate_link,
    })

    print("\n" + "=" * 60)
    print("DONE — Affiliate carousel posted!")
    print("=" * 60)


if __name__ == "__main__":
    main()
