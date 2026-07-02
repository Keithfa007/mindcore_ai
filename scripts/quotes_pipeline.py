#!/usr/bin/env python3
"""
MindCore AI  - Daily Quotes Pipeline v1.3
=========================================
v1.3: Reduced X hashtags to 2 (from 8). Cleaner tweets.
v1.2: Fixed Upload-Post fields -- tiktok_title (90 chars) + description
      (full caption), matching carousel pipeline. Added post_mode=DIRECT_POST.
v1.1: Photo upload with auto_add_music.
v1.0: Claude-generated raw quotes, Pillow cinematic design.

Cost: ~$0.01/post (one Claude API call).
"""

import os, sys, json, random, datetime, math
from pathlib import Path
from anthropic import Anthropic
from PIL import Image, ImageDraw, ImageFont
import requests

ANTHROPIC_API_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
UPLOAD_POST_PHOTOS_URL = "https://api.upload-post.com/api/upload_photos"
UPLOAD_POST_USER    = "MindCoreAI"
ANTHROPIC_MODEL     = "claude-sonnet-4-6"
GITHUB_RUN_NUMBER   = int(os.environ.get("GITHUB_RUN_NUMBER", "1"))
POST_HOUR_UTC       = int(os.environ.get("POST_HOUR_UTC", "6"))

OUTPUT_DIR = Path("scripts/quotes_output")
WIDTH  = 1200
HEIGHT = 675

X_HASHTAGS = "#mentalhealth #mindcoreai"


QUOTE_CATEGORIES = [
    {"name": "3am_truth", "instruction": "A raw truth that someone thinks at 3am but never says out loud. It should feel like eavesdropping on someone's inner monologue during their hardest moment. Not inspirational  - honest.", "examples": ["You didn't stop feeling things. You just got tired of feeling them alone.", "The strongest people I know are exhausted."]},
    {"name": "silent_strength", "instruction": "About the quiet strength in vulnerability, in asking for help, in admitting you're not okay. Reframe what strength actually means. Not toxic positivity.", "examples": ["Falling apart quietly doesn't make you weak. It means you've been strong for too long.", "Courage isn't loud. Sometimes it's the quiet voice at the end of the day saying: I'll try again tomorrow."]},
    {"name": "recovery_wisdom", "instruction": "A hard-won insight from the recovery journey. Something only someone who's been through it would know. Written as if spoken by someone 2 years clean looking back.", "examples": ["Recovery isn't a straight line. Some days the line disappears entirely. You walk it anyway.", "The thing about rock bottom is you find out what you're made of. Not who you thought you were."]},
    {"name": "the_unsaid", "instruction": "Something people feel every day but have never heard articulated. When they read it, their stomach should drop with recognition. Specific enough to feel personal, universal enough to be shared.", "examples": ["You can miss a version of yourself that nobody else ever met.", "The loneliest feeling is being surrounded by people who think you're fine."]},
    {"name": "permission", "instruction": "Giving the reader permission to feel something they've been told is wrong to feel. Permission to rest, to break, to grieve, to not be okay, to put themselves first. Not preachy  - just honest.", "examples": ["You don't owe anyone a performance of being okay.", "Rest is not giving up. It's refusing to break."]},
    {"name": "hard_reframe", "instruction": "Take something the reader believes about themselves (that they're broken, weak, too sensitive, too much, not enough) and reframe it with precision. The reframe must feel earned and true, not like a bumper sticker.", "examples": ["You're not too sensitive. You've been in rooms that couldn't hold what you carry.", "You didn't fail. You just ran out of reasons to keep pretending."]},
    {"name": "midnight_honesty", "instruction": "The kind of thought that only comes after midnight when every defence is down. Not dramatic  - just quietly devastating in its honesty. Should feel whispered, not shouted.", "examples": ["Some nights the hardest thing is admitting you need someone.", "The version of you that held everything together deserves someone who asks how."]},
]


def get_category_for_run():
    idx = GITHUB_RUN_NUMBER % len(QUOTE_CATEGORIES)
    cat = QUOTE_CATEGORIES[idx]
    print(f"  Category: {cat['name']} ({idx+1}/{len(QUOTE_CATEGORIES)})")
    return cat


def generate_quote(client, category):
    examples_block = "\n".join(f'  - "{e}"' for e in category["examples"])
    prompt = f"""You are generating a single powerful quote for a mental health brand called MindCore AI.

CATEGORY: {category['name']}
INSTRUCTION: {category['instruction']}

STYLE EXAMPLES (for tone reference only  - do NOT copy these):
{examples_block}

RULES:
- ONE quote only. 8-25 words. No more.
- Raw, honest, human. NOT generic motivational ("believe in yourself", "you are enough", "stay positive")
- No emojis, no hashtags, no attribution
- Must hit emotionally on first read  - gut-punch recognition
- Written for someone scrolling at 2am who feels alone
- The quote should feel like it was written BY someone who's been through it, not FOR them
- Do NOT start with "You" more than 40% of the time  - vary the opening

WRITING STYLE (MANDATORY):
- NEVER use em dashes. Use commas, periods, or separate sentences instead.
- NEVER use these AI-tell words: "delve", "tapestry", "landscape", "realm", "navigate", "leverage", "foster", "cultivate", "embark", "comprehensive", "multifaceted", "ever-evolving", "game-changer", "unlock", "unleash", "empower", "supercharge", "revolutionize", "it's important to note", "it's worth noting", "in today's world", "in today's fast-paced world", "harness", "pivotal", "seasoned", "cutting-edge", "spearhead".
- Write like a real person. Vary sentence length. No corporate jargon or motivational-poster tone.
- Prefer simple words: "help" not "facilitate", "use" not "utilize", "start" not "commence".

Return ONLY the quote text. No quotes marks, no attribution, nothing else."""

    for attempt in range(3):
        try:
            result = client.messages.create(
                model=ANTHROPIC_MODEL, max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            ).content[0].text.strip().strip('"').strip("'")
            for sep in ["  -", " -", " ~", "\n"]:
                if sep in result:
                    result = result.split(sep)[0].strip()
            print(f'  Quote: "{result}"')
            return result
        except Exception as e:
            print(f"  Quote generation attempt {attempt+1} failed: {e}")
            if attempt == 2: raise
    raise RuntimeError("Failed to generate quote")


def generate_caption(client, quote, category):
    prompt = f"""Write a SHORT X/Twitter caption for this mental health quote post.

QUOTE: "{quote}"
CATEGORY: {category['name']}
BRAND: MindCore AI

RULES:
- 1-2 short sentences that complement the quote (don't repeat it)
- Raw honest tone, not salesy
- Can ask a question to drive replies
- NO emojis, NO hashtags, NO links

WRITING STYLE (MANDATORY):
- NEVER use em dashes. Use commas, periods, or separate sentences instead.
- NEVER use these AI-tell words: "delve", "tapestry", "landscape", "realm", "navigate", "leverage", "foster", "cultivate", "embark", "comprehensive", "multifaceted", "ever-evolving", "game-changer", "unlock", "unleash", "empower", "supercharge", "revolutionize", "it's important to note", "it's worth noting", "in today's world", "in today's fast-paced world", "harness", "pivotal", "seasoned", "cutting-edge", "spearhead".
- Write like a real person. Vary sentence length. No corporate jargon or motivational-poster tone.
- Prefer simple words: "help" not "facilitate", "use" not "utilize", "start" not "commence".

Return ONLY the caption text."""
    try:
        return client.messages.create(
            model=ANTHROPIC_MODEL, max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text.strip()
    except Exception as e:
        print(f"  Caption generation failed: {e}")
        return "Sometimes the truest words are the ones nobody says out loud."


def get_font(size, bold=True):
    bold_paths = ["/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"]
    regular_paths = ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for p in (bold_paths if bold else regular_paths):
        try: return ImageFont.truetype(p, size)
        except: continue
    return ImageFont.load_default()


def create_gradient_background():
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
    return Image.alpha_composite(img.convert("RGBA"), vignette).convert("RGB")


def wrap_text_lines(text, font, max_width):
    words = text.split(); lines = []; current = ""
    for word in words:
        test = f"{current} {word}".strip()
        tw = font.getbbox(test)[2] - font.getbbox(test)[0]
        if tw <= max_width: current = test
        else:
            if current: lines.append(current)
            current = word
    if current: lines.append(current)
    return lines


def draw_text_centered(draw, y, text, font, fill=(255, 255, 255), stroke_width=0, stroke_fill=(0, 0, 0)):
    tw = font.getbbox(text)[2] - font.getbbox(text)[0]
    x = (WIDTH - tw) // 2
    if stroke_width > 0:
        for dx in range(-stroke_width, stroke_width + 1):
            for dy in range(-stroke_width, stroke_width + 1):
                if dx or dy: draw.text((x + dx, y + dy), text, font=font, fill=stroke_fill)
    draw.text((x, y), text, font=font, fill=fill)


def render_quote_image(quote_text, output_path):
    img = create_gradient_background()
    draw = ImageDraw.Draw(img)
    quote_font = get_font(44, bold=True)
    attr_font = get_font(24, bold=False)
    lines = wrap_text_lines(quote_text, quote_font, int(WIDTH * 0.82))
    line_height = 58
    total_text_height = len(lines) * line_height
    quote_top = int(HEIGHT * 0.45) - (total_text_height // 2)
    accent_color = (180, 160, 120)
    line_left, line_right = WIDTH // 2 - 80, WIDTH // 2 + 80
    draw.line([(line_left, quote_top - 35), (line_right, quote_top - 35)], fill=accent_color, width=2)
    for i, line in enumerate(lines):
        draw_text_centered(draw, quote_top + i * line_height, line, quote_font, fill=(255, 255, 255), stroke_width=2, stroke_fill=(0, 0, 0))
    line_y_bottom = quote_top + total_text_height + 20
    draw.line([(line_left, line_y_bottom), (line_right, line_y_bottom)], fill=accent_color, width=2)
    draw_text_centered(draw, line_y_bottom + 25, " - MindCore AI", attr_font, fill=(140, 140, 160))
    img.save(output_path, "PNG", quality=95)
    jpg_path = output_path.replace(".png", ".jpg")
    img.convert("RGB").save(jpg_path, "JPEG", quality=92)
    print(f"  Image: {Path(output_path).stat().st_size / 1024:.0f} KB (PNG) | {Path(jpg_path).stat().st_size / 1024:.0f} KB (JPG)")
    return jpg_path


def get_scheduled_time(hour_utc):
    now = datetime.datetime.utcnow()
    target = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    if now >= target: target += datetime.timedelta(days=1)
    return target.strftime("%Y-%m-%dT%H:%M:%SZ")


def upload_photo_to_platforms(image_path, tiktok_title, description, fb_title, fb_description, scheduled_date=None):
    """Upload quote image to X via Upload-Post."""
    if not UPLOAD_POST_API_KEY:
        return {"skipped": True, "reason": "no API key"}
    data = [
        ("user", UPLOAD_POST_USER),
        ("platform[]", "x"),
        ("title", tiktok_title[:280]),
        ("post_mode", "DIRECT_POST"),
        ("photo_cover_index", "0"),
    ]
    if scheduled_date:
        data.append(("scheduled_date", scheduled_date))
    try:
        f = open(image_path, "rb")
        files = [("photos[]", ("quote.jpg", f, "image/jpeg"))]
        resp = requests.post(
            UPLOAD_POST_PHOTOS_URL,
            headers={"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"},
            files=files, data=data, timeout=180,
        )
        f.close()
        result = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
        result["status_code"] = resp.status_code
        if scheduled_date: result["scheduled_date"] = scheduled_date
        print(f"  Upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}")
        if not resp.ok: print(f"  {resp.text[:300]}")
        return result
    except Exception as e:
        print(f"  Upload failed: {e}")
        return {"error": str(e)}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"== MindCore AI  - Daily Quotes Pipeline v1.3 ==")
    print(f"  Run #{GITHUB_RUN_NUMBER} | Post: {POST_HOUR_UTC:02d}:00 UTC | X quote")

    if not ANTHROPIC_API_KEY: sys.exit("ERROR: ANTHROPIC_API_KEY not set")
    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    category = get_category_for_run()
    scheduled_date = get_scheduled_time(POST_HOUR_UTC)

    print("\n1. Generating quote...")
    quote = generate_quote(client, category)

    print("2. Generating caption...")
    caption = generate_caption(client, quote, category)
    print(f"  Caption: {caption}")

    print("3. Rendering image...")
    jpg_path = render_quote_image(quote, str(OUTPUT_DIR / "quote_image.png"))

    print("4. Uploading to X...")
    tiktok_title = f"{quote}\n\n{caption}\n\n{X_HASHTAGS}"[:280]
    description = ""
    fb_title = ""
    fb_description = ""

    result = upload_photo_to_platforms(jpg_path, tiktok_title, description, fb_title, fb_description, scheduled_date=scheduled_date)
    if result.get("status_code") in (200, 202):
        print(f"  Scheduled: {scheduled_date}")
    elif result.get("skipped"):
        print(f"  Skipped: {result.get('reason')}")

    (OUTPUT_DIR / "quote_metadata.json").write_text(json.dumps({
        "run": GITHUB_RUN_NUMBER, "category": category["name"],
        "quote": quote, "caption": caption, "tweet_text": tiktok_title,
        "scheduled": scheduled_date, "upload_type": "photo", "platform": "x",
    }, indent=2))
    print("\n== Done ==")


if __name__ == "__main__":
    main()
