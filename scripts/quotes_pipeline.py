#!/usr/bin/env python3
"""
MindCore AI — Daily Quotes Pipeline v1.0
=========================================
v1.0: Claude-generated raw quotes, Pillow cinematic design, FFmpeg video
      with Ken Burns + fade, Upload-Post to TikTok + Facebook.

Design: Dark gradient background, clean typography, thin accent lines,
        subtle vignette. NOT generic motivational posters — raw 3am truths.

Cost: ~$0.01/post (one Claude API call).
"""

import os, sys, json, random, subprocess, tempfile, datetime, textwrap, math
from pathlib import Path
from anthropic import Anthropic
from PIL import Image, ImageDraw, ImageFont
import requests

ANTHROPIC_API_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
UPLOAD_POST_API_URL = "https://api.upload-post.com/api/upload"
UPLOAD_POST_USER    = "MindCoreAI"
ANTHROPIC_MODEL     = "claude-sonnet-4-6"
GITHUB_RUN_NUMBER   = int(os.environ.get("GITHUB_RUN_NUMBER", "1"))
POST_HOUR_UTC       = int(os.environ.get("POST_HOUR_UTC", "6"))  # default 6:00 UTC = 8am Malta

OUTPUT_DIR = Path("scripts/quotes_output")
WIDTH  = 1080
HEIGHT = 1920

TK_HASHTAGS = "#mindcoreai #mentalhealth #mentalhealthmatters #fyp #foryou #mentalhealthawareness #healing #selfcare #therapytok #mentalhealthtiktok #quotestoliveby #realtalk"
FB_HASHTAGS = "#mentalhealth #mentalhealthmatters #healing #selfcare #mindcoreai #quotestoliveby"

# ── Quote categories -- rotates by run number ────────────────────────────
QUOTE_CATEGORIES = [
    {
        "name": "3am_truth",
        "instruction": "A raw truth that someone thinks at 3am but never says out loud. It should feel like eavesdropping on someone's inner monologue during their hardest moment. Not inspirational — honest.",
        "examples": [
            "You didn't stop feeling things. You just got tired of feeling them alone.",
            "The strongest people I know are exhausted.",
        ],
    },
    {
        "name": "silent_strength",
        "instruction": "About the quiet strength in vulnerability, in asking for help, in admitting you're not okay. Reframe what strength actually means. Not toxic positivity.",
        "examples": [
            "Falling apart quietly doesn't make you weak. It means you've been strong for too long.",
            "Courage isn't loud. Sometimes it's the quiet voice at the end of the day saying: I'll try again tomorrow.",
        ],
    },
    {
        "name": "recovery_wisdom",
        "instruction": "A hard-won insight from the recovery journey. Something only someone who's been through it would know. Written as if spoken by someone 2 years clean looking back.",
        "examples": [
            "Recovery isn't a straight line. Some days the line disappears entirely. You walk it anyway.",
            "The thing about rock bottom is you find out what you're made of. Not who you thought you were.",
        ],
    },
    {
        "name": "the_unsaid",
        "instruction": "Something people feel every day but have never heard articulated. When they read it, their stomach should drop with recognition. Specific enough to feel personal, universal enough to be shared.",
        "examples": [
            "You can miss a version of yourself that nobody else ever met.",
            "The loneliest feeling is being surrounded by people who think you're fine.",
        ],
    },
    {
        "name": "permission",
        "instruction": "Giving the reader permission to feel something they've been told is wrong to feel. Permission to rest, to break, to grieve, to not be okay, to put themselves first. Not preachy — just honest.",
        "examples": [
            "You don't owe anyone a performance of being okay.",
            "Rest is not giving up. It's refusing to break.",
        ],
    },
    {
        "name": "hard_reframe",
        "instruction": "Take something the reader believes about themselves (that they're broken, weak, too sensitive, too much, not enough) and reframe it with precision. The reframe must feel earned and true, not like a bumper sticker.",
        "examples": [
            "You're not too sensitive. You've been in rooms that couldn't hold what you carry.",
            "You didn't fail. You just ran out of reasons to keep pretending.",
        ],
    },
    {
        "name": "midnight_honesty",
        "instruction": "The kind of thought that only comes after midnight when every defence is down. Not dramatic — just quietly devastating in its honesty. Should feel whispered, not shouted.",
        "examples": [
            "Some nights the hardest thing is admitting you need someone.",
            "The version of you that held everything together deserves someone who asks how.",
        ],
    },
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

STYLE EXAMPLES (for tone reference only — do NOT copy these):
{examples_block}

RULES:
- ONE quote only. 8-25 words. No more.
- Raw, honest, human. NOT generic motivational ("believe in yourself", "you are enough", "stay positive")
- No emojis, no hashtags, no attribution
- Must hit emotionally on first read — gut-punch recognition
- Written for someone scrolling at 2am who feels alone
- The quote should feel like it was written BY someone who's been through it, not FOR them
- Do NOT start with "You" more than 40% of the time — vary the opening

Return ONLY the quote text. No quotes marks, no attribution, nothing else."""

    for attempt in range(3):
        try:
            result = client.messages.create(
                model=ANTHROPIC_MODEL, max_tokens=100,
                messages=[{"role": "user", "content": prompt}]
            ).content[0].text.strip().strip('"').strip("'")
            # Clean up any attribution the model might add
            for sep in [" —", " -", " ~", "\n"]:
                if sep in result:
                    result = result.split(sep)[0].strip()
            print(f"  Quote: \"{result}\"")
            return result
        except Exception as e:
            print(f"  Quote generation attempt {attempt+1} failed: {e}")
            if attempt == 2: raise
    raise RuntimeError("Failed to generate quote")


def generate_caption(client, quote, category):
    prompt = f"""Write a SHORT TikTok/Facebook caption for this mental health quote post.

QUOTE: "{quote}"
CATEGORY: {category['name']}
BRAND: MindCore AI

RULES:
- 1-2 short sentences that complement the quote (don't repeat it)
- Raw honest tone, not salesy
- Can ask a question to drive comments
- NO emojis, NO hashtags, NO links
- Example: "Some things only make sense after midnight." or "Tag someone who needs to hear this."

Return ONLY the caption text."""
    try:
        return client.messages.create(
            model=ANTHROPIC_MODEL, max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text.strip()
    except Exception as e:
        print(f"  Caption generation failed: {e}")
        return "Sometimes the truest words are the ones nobody says out loud."


# ── Visual Design ────────────────────────────────────────────────────────

def get_font(size, bold=True):
    bold_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ]
    regular_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    paths = bold_paths if bold else regular_paths
    for p in paths:
        try:
            return ImageFont.truetype(p, size)
        except Exception:
            continue
    return ImageFont.load_default()


def create_gradient_background():
    """Dark cinematic gradient — deep navy to near-black with subtle vignette."""
    img = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(img)

    # Vertical gradient: dark navy top → near-black bottom
    top_r, top_g, top_b = 12, 16, 32        # #0c1020
    bot_r, bot_g, bot_b = 6, 6, 12          # #06060c

    for y in range(HEIGHT):
        ratio = y / HEIGHT
        # Ease the gradient (slower in middle, faster at edges)
        ease = ratio * ratio * (3 - 2 * ratio)
        r = int(top_r + (bot_r - top_r) * ease)
        g = int(top_g + (bot_g - top_g) * ease)
        b = int(top_b + (bot_b - top_b) * ease)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))

    # Subtle vignette overlay
    vignette = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    vdraw = ImageDraw.Draw(vignette)
    cx, cy = WIDTH // 2, HEIGHT // 2
    max_dist = math.sqrt(cx * cx + cy * cy)
    for y in range(0, HEIGHT, 3):
        for x in range(0, WIDTH, 3):
            dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
            alpha = int(min(80, (dist / max_dist) * 120))
            vdraw.rectangle([x, y, x + 3, y + 3], fill=(0, 0, 0, alpha))
    img = Image.alpha_composite(img.convert("RGBA"), vignette).convert("RGB")
    return img


def wrap_text_lines(text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = font.getbbox(test)
        tw = bbox[2] - bbox[0]
        if tw <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def draw_text_centered(draw, y, text, font, fill=(255, 255, 255), stroke_width=0, stroke_fill=(0, 0, 0)):
    bbox = font.getbbox(text)
    tw = bbox[2] - bbox[0]
    x = (WIDTH - tw) // 2
    if stroke_width > 0:
        for dx in range(-stroke_width, stroke_width + 1):
            for dy in range(-stroke_width, stroke_width + 1):
                if dx or dy:
                    draw.text((x + dx, y + dy), text, font=font, fill=stroke_fill)
    draw.text((x, y), text, font=font, fill=fill)


def render_quote_image(quote_text, output_path):
    """Render a cinematic quote image at 1080x1920."""
    img = create_gradient_background()
    draw = ImageDraw.Draw(img)

    # Typography
    quote_font = get_font(62, bold=True)
    attr_font = get_font(32, bold=False)
    max_text_width = int(WIDTH * 0.82)

    # Wrap quote text
    lines = wrap_text_lines(quote_text, quote_font, max_text_width)
    line_height = 82
    total_text_height = len(lines) * line_height

    # Position quote in the golden ratio zone (slightly above center)
    quote_top = int(HEIGHT * 0.38) - (total_text_height // 2)

    # Thin accent line above quote
    line_y_top = quote_top - 50
    accent_color = (180, 160, 120)  # warm gold/amber
    line_left = WIDTH // 2 - 80
    line_right = WIDTH // 2 + 80
    draw.line([(line_left, line_y_top), (line_right, line_y_top)], fill=accent_color, width=2)

    # Draw quote lines
    for i, line in enumerate(lines):
        y = quote_top + i * line_height
        # Subtle text shadow
        draw_text_centered(draw, y, line, quote_font,
                           fill=(255, 255, 255),
                           stroke_width=2,
                           stroke_fill=(0, 0, 0))

    # Thin accent line below quote
    line_y_bottom = quote_top + total_text_height + 30
    draw.line([(line_left, line_y_bottom), (line_right, line_y_bottom)], fill=accent_color, width=2)

    # Attribution
    attr_text = "— MindCore AI"
    attr_y = line_y_bottom + 40
    draw_text_centered(draw, attr_y, attr_text, attr_font, fill=(140, 140, 160))

    # Save
    img.save(output_path, "PNG", quality=95)
    print(f"  Image: {Path(output_path).stat().st_size / 1024:.0f} KB")
    return output_path


def create_video_from_image(image_path, output_path, duration=7):
    """Create a short video with slow Ken Burns zoom and fade in/out."""
    # Scale up slightly for Ken Burns room
    scale = 1.08
    sw = int(WIDTH * scale)
    sh = int(HEIGHT * scale)
    # Slow zoom in over the duration
    crop_filter = (
        f"scale={sw}:{sh},"
        f"crop={WIDTH}:{HEIGHT}:"
        f"'max(0,({sw}-{WIDTH})/2-t/{duration}*({sw}-{WIDTH})/2)':"
        f"'max(0,({sh}-{HEIGHT})/2-t/{duration}*({sh}-{HEIGHT})/2)'"
    )
    fade_filter = f"fade=t=in:st=0:d=1.2,fade=t=out:st={duration-1.2}:d=1.2"

    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", "-i", image_path,
        "-vf", f"{crop_filter},{fade_filter},fps=30",
        "-t", str(duration),
        "-c:v", "libx264", "-crf", "18", "-preset", "slow",
        "-pix_fmt", "yuv420p",
        "-an",  # no audio -- TikTok users add trending sound
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FFmpeg error: {result.stderr[-300:]}")
        raise RuntimeError("Video creation failed")
    print(f"  Video: {Path(output_path).stat().st_size / 1024:.0f} KB | {duration}s | silent (for trending audio)")


def get_scheduled_time(hour_utc):
    now = datetime.datetime.utcnow()
    target = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    if now >= target:
        target += datetime.timedelta(days=1)
    return target.strftime("%Y-%m-%dT%H:%M:%SZ")


def upload_to_platforms(video_path, tiktok_caption, fb_title, fb_description, scheduled_date=None):
    if not UPLOAD_POST_API_KEY:
        return {"skipped": True, "reason": "no API key"}
    data = [
        ("user", UPLOAD_POST_USER),
        ("platform[]", "tiktok"),
        ("platform[]", "facebook"),
        ("title", tiktok_caption[:2200]),
        ("facebook_title", fb_title[:255]),
        ("facebook_description", fb_description[:5000]),
    ]
    if scheduled_date:
        data.append(("scheduled_date", scheduled_date))
    try:
        with open(video_path, "rb") as f:
            resp = requests.post(
                UPLOAD_POST_API_URL,
                headers={"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"},
                files=[("video", ("mindcore_quote.mp4", f, "video/mp4"))],
                data=data, timeout=180,
            )
        result = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
        result["status_code"] = resp.status_code
        if scheduled_date:
            result["scheduled_date"] = scheduled_date
        print(f"  Upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}")
        if not resp.ok:
            print(f"  {resp.text[:300]}")
        return result
    except Exception as e:
        print(f"  Upload failed: {e}")
        return {"error": str(e)}


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"== MindCore AI — Daily Quotes Pipeline v1.0 ==")
    print(f"  Run #{GITHUB_RUN_NUMBER} | Post: {POST_HOUR_UTC:02d}:00 UTC")

    if not ANTHROPIC_API_KEY:
        sys.exit("ERROR: ANTHROPIC_API_KEY not set")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    category = get_category_for_run()
    scheduled_date = get_scheduled_time(POST_HOUR_UTC)

    print("\n1. Generating quote...")
    quote = generate_quote(client, category)

    print("2. Generating caption...")
    caption = generate_caption(client, quote, category)
    print(f"  Caption: {caption}")

    print("3. Rendering image...")
    image_path = str(OUTPUT_DIR / "quote_image.png")
    render_quote_image(quote, image_path)

    print("4. Creating video...")
    video_path = str(OUTPUT_DIR / "quote_video.mp4")
    create_video_from_image(image_path, video_path)

    print("5. Uploading...")
    tiktok_caption = f"{quote}\n\n{caption}\n\n{TK_HASHTAGS}"
    fb_title = quote[:255]
    fb_description = f"{quote}\n\n{caption}\n\n{FB_HASHTAGS}"

    result = upload_to_platforms(video_path, tiktok_caption, fb_title, fb_description, scheduled_date=scheduled_date)
    if result.get("status_code") in (200, 202):
        print(f"  Scheduled: {scheduled_date}")
    elif result.get("skipped"):
        print(f"  Skipped: {result.get('reason')}")

    # Save metadata
    meta = {
        "run": GITHUB_RUN_NUMBER,
        "category": category["name"],
        "quote": quote,
        "caption": caption,
        "scheduled": scheduled_date,
    }
    (OUTPUT_DIR / "quote_metadata.json").write_text(json.dumps(meta, indent=2))

    print("\n== Done ==")


if __name__ == "__main__":
    main()
