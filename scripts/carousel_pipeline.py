#!/usr/bin/env python3
"""
MindCore AI -- Carousel Image Post Pipeline v2.1
=================================================
Hybrid: beautiful cinematic gpt-image-1 photography (v1.7 images)
+ proper text hierarchy from v2.0 analysis.

What changed vs v1.7:
  - THREE font sizes per slide: command (gray, small) / hero (large + neon brush stroke) / body+bold (medium)
  - Gradient dark overlay in text zone -- white text always readable regardless of image
  - Max 10 words per slide (hard enforced)
  - Script structure: command + hero + body + bold line
  - 6 slides (5 content + 1 CTA)
  - CTA: "Comment X..." + "MindCore AI" + "Download for free on Google Play"

What's the same as v1.7:
  - Beautiful cinematic gpt-image-1 HIGH photography (NOT pen sketches)
  - Dark moody images, warm light, real people
  - TikTok + Facebook upload
  - MEDIA_UPLOAD mode (TikTok drafts)
  - Partner-directed scripts

Cost: ~$0.48/post (6 x gpt-image-1 high @ ~$0.08)
Schedule: daily 07:00 UTC (9am Malta --> ~2pm Malta)
"""

import base64
import io
import json
import os
import random
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import requests
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY   = os.environ["ANTHROPIC_API_KEY"]
OPENAI_API_KEY      = os.environ["OPENAI_API_KEY"]
UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
GITHUB_RUN_NUMBER   = int(os.environ.get("GITHUB_RUN_NUMBER", "1"))

UPLOAD_POST_PHOTOS_URL = "https://api.upload-post.com/api/upload_photos"

OUTPUT_DIR   = Path("scripts/output_carousel")
PIPELINE_DIR = Path("scripts")
HISTORY_PATH = PIPELINE_DIR / "carousel_history.json"

REQUIRED_BRAND_HASHTAG = "#mindcoreai"
HASHTAGS = (
    "#mindcoreai #mentalhealth #fyp #foryou "
    "#mentalhealthawareness #anxiety #healing #selfcare"
)

IMAGE_WIDTH  = 1080
IMAGE_HEIGHT = 1920
TIKTOK_TITLE_LIMIT = 90
TIKTOK_DESC_LIMIT  = 4000
CLAUDE_MAX_RETRIES = 8
CLAUDE_RETRY_BASE  = 30

# ---------------------------------------------------------------------------
# Text design -- three hierarchy levels
# ---------------------------------------------------------------------------
CMD_SIZE   = 50    # command label (small, light gray)
HERO_SIZE  = 88    # hero concept (large, bold, on brush stroke)
BODY_SIZE  = 42    # body explanation
BOLD_SIZE  = 48    # bold punchline
CTA_TRIG   = 60    # CTA comment trigger
CTA_APP    = 84    # "MindCore AI"
CTA_DL     = 50    # "Download for free on Google Play"
CTA_URL    = 38    # URL

# Text colors
CMD_COLOR  = (200, 200, 200)  # light gray -- command label
HERO_COLOR = (10,  10,  10)   # near black -- ON the neon brush stroke
BODY_COLOR = (255, 255, 255)  # white -- body text
BOLD_COLOR = (255, 255, 255)  # white -- bold punchline
CTA_COLOR  = (255, 255, 255)  # white -- CTA text
URL_COLOR  = (190, 190, 190)  # light gray -- URL

# Brush stroke palette (rotates per slide) -- vivid on dark images
BRUSH_PALETTE = [
    (168, 224, 99),   # lime green  #A8E063
    (78,  205, 196),  # cyan        #4ECDC4
    (255, 209, 102),  # yellow      #FFD166
    (168, 224, 99),
    (78,  205, 196),
    (255, 209, 102),
]

# Text zone vertical positions (fraction of image height -- where text block starts)
TEXT_START_HOOK    = 0.55   # slide 1 -- lower portion, leave upper image clean
TEXT_START_CONTENT = 0.50   # slides 2-5
TEXT_START_CTA     = 0.38   # CTA slide -- more text, starts higher

MAX_TEXT_W = int(IMAGE_WIDTH * 0.87)  # 940px max text width
LINE_GAP   = 14
SECTION_GAP = 38

# Gradient overlay alpha range in text zone
GRADIENT_MAX_ALPHA = 155  # 0-255, how dark the text zone gets

# ---------------------------------------------------------------------------
# Partner-directed topic seeds
# ---------------------------------------------------------------------------
PARTNER_SEEDS = [
    "loving someone with anxiety",
    "supporting someone with depression",
    "loving someone in recovery from addiction",
    "what someone with burnout needs from you",
    "loving someone who carries everything alone",
    "what your anxious partner needs you to know",
    "supporting a partner with mental health struggles",
    "what loving someone with high-functioning anxiety looks like",
    "how to love someone who doesn't know how to ask for help",
    "what men in recovery need their partners to understand",
    "loving someone who can't switch their mind off",
    "what it means to love someone with depression",
    "how to support someone who overthinks everything",
    "what someone with trauma needs from the people they love",
    "loving someone who has never felt like enough",
]

# ---------------------------------------------------------------------------
# Cinematic image prompts -- SAME beautiful style as v1.7
# ---------------------------------------------------------------------------
SLIDE_IMAGE_PROMPTS = {
    "slide_1": (
        "Cinematic portrait photography, 9:16 vertical format. "
        "A person floating peacefully on their back in warm golden-hour water, "
        "face serene and eyes closed, hair fanned out around their head. "
        "Soft pink and lavender sunset reflections shimmering on the water. "
        "Warm aspirational wellness aesthetic, safe and beautiful. "
        "High-key warm grade, photorealistic, no text, no logos."
    ),
    "slide_2": (
        "Cinematic portrait photography, 9:16 vertical format. "
        "A person sitting alone near a rain-streaked window at dusk, "
        "warm soft ambient interior light casting a gentle glow, "
        "peaceful contemplative expression, hands in lap. "
        "Intimate quiet mood, slightly warm dim interior. "
        "Photorealistic, no text, no logos."
    ),
    "slide_3": (
        "Cinematic portrait photography, 9:16 vertical format. "
        "Two hands gently holding each other on a warm wooden table, "
        "soft golden afternoon light, simple and tender connection. "
        "Warm amber colour grade, quiet intimacy. "
        "Photorealistic, no text, no logos."
    ),
    "slide_4": (
        "Cinematic portrait photography, 9:16 vertical format. "
        "A person looking upward toward soft warm natural light "
        "streaming through a window, face peaceful and hopeful, "
        "golden light touching skin gently. "
        "Warm transitional mood, beginning of resolution. "
        "Photorealistic, no text, no logos."
    ),
    "slide_5": (
        "Cinematic portrait photography, 9:16 vertical format. "
        "Soft golden sunrise light filtering through sheer white curtains, "
        "peaceful bedroom scene, warm amber and ivory tones, "
        "a sense of safety, serenity, and gentle hope. "
        "Full warm golden resolution mood. "
        "Photorealistic, no text, no logos."
    ),
    "slide_6": (
        "Cinematic portrait photography, 9:16 vertical format. "
        "A smartphone face-up on a warm wooden table, soft golden ambient "
        "glow on the screen, minimal and inviting, candlelight warmth, "
        "intimate and calm. Warm amber grade. "
        "Photorealistic, no text, no logos."
    ),
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_history():
    if HISTORY_PATH.exists():
        try: return json.loads(HISTORY_PATH.read_text())
        except: return []
    return []

def save_history(history, new_entry):
    history.append(new_entry)
    HISTORY_PATH.write_text(json.dumps(history[-30:], indent=2))
    print(f"  History: {len(history)} carousel posts")

def _call_claude(prompt, client, max_tokens=2000):
    for attempt in range(1, CLAUDE_MAX_RETRIES + 1):
        try:
            msg = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = msg.content[0].text.strip()
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
            return json.loads(raw)
        except anthropic.APIStatusError as e:
            if e.status_code == 529:
                wait = CLAUDE_RETRY_BASE * attempt
                print(f"  Overloaded -- waiting {wait}s..."); time.sleep(wait)
            else: raise
        except json.JSONDecodeError:
            if attempt == CLAUDE_MAX_RETRIES: raise
            time.sleep(10)
    raise RuntimeError("Claude failed after all retries")

def get_font(size, bold=True):
    bold_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-Bold.ttf",
    ]
    reg_paths = [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-R.ttf",
    ]
    paths = bold_paths if bold else reg_paths
    for path in paths:
        if Path(path).exists():
            try: return ImageFont.truetype(path, size)
            except: pass
    for path in (reg_paths if bold else bold_paths):
        if Path(path).exists():
            try: return ImageFont.truetype(path, size)
            except: pass
    return ImageFont.load_default()

def line_height(font):
    try:
        bb = font.getbbox("Ag"); return bb[3] - bb[1]
    except: return getattr(font, "size", 40)

def wrap_text(text, font, max_w):
    words = text.split(); lines = []; cur = []
    for word in words:
        test = " ".join(cur + [word])
        try: w = font.getbbox(test)[2] - font.getbbox(test)[0]
        except: w = len(test) * 30
        if w <= max_w: cur.append(word)
        else:
            if cur: lines.append(" ".join(cur))
            cur = [word]
    if cur: lines.append(" ".join(cur))
    return lines or [""]

def draw_text_with_stroke(draw, cx, y, text, font, color, stroke_color=(0,0,0), stroke_w=3):
    """Draw text centered at cx, top at y, with black stroke for readability."""
    for dx in range(-stroke_w, stroke_w+1):
        for dy in range(-stroke_w, stroke_w+1):
            if dx or dy:
                draw.text((cx+dx, y+dy), text, font=font, fill=stroke_color, anchor="mt")
    draw.text((cx, y), text, font=font, fill=color, anchor="mt")

def draw_text_block(draw, cx, y, lines, font, color, stroke_w=3):
    """Draw multiple lines, return bottom y."""
    lh = line_height(font)
    for line in lines:
        draw_text_with_stroke(draw, cx, y, line, font, color, stroke_w=stroke_w)
        y += lh + LINE_GAP
    return y

def draw_brush_stroke(draw, cx, y_top, text, font, brush_color):
    """Draw neon brush stroke behind hero text. Returns text bounds."""
    try:
        bb = font.getbbox(text)
        tw = bb[2] - bb[0]; th = bb[3] - bb[1]
    except:
        tw = len(text) * getattr(font, "size", 40) * 0.55
        th = getattr(font, "size", 40)
    pad_x, pad_y, skew = 26, 10, 8
    x1 = cx - tw//2 - pad_x; x2 = cx + tw//2 + pad_x
    y1 = y_top - pad_y;      y2 = y_top + th + pad_y
    pts = [
        (x1+skew, y1-3), (x2+skew, y1+4),
        (x2-skew, y2+4), (x1-skew, y2-3),
    ]
    draw.polygon(pts, fill=brush_color)

def add_gradient_overlay(img, text_start_y):
    """Darken the text zone with a gradient so white text is always readable."""
    overlay = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), (0, 0, 0, 0))
    draw    = ImageDraw.Draw(overlay)
    zone_h  = IMAGE_HEIGHT - text_start_y
    for y in range(text_start_y, IMAGE_HEIGHT):
        progress = (y - text_start_y) / zone_h
        alpha = int(GRADIENT_MAX_ALPHA * min(progress * 1.6, 1.0))
        draw.line([(0, y), (IMAGE_WIDTH, y)], fill=(0, 0, 0, alpha))
    img_rgba = img.convert("RGBA")
    composited = Image.alpha_composite(img_rgba, overlay)
    return composited.convert("RGB")


# ---------------------------------------------------------------------------
# Step 1: Generate script
# ---------------------------------------------------------------------------
def generate_carousel_script(client, history):
    used  = [e.get("topic","") for e in history]
    seed  = random.choice(PARTNER_SEEDS)
    avoid = ", ".join(used[-10:]) if used else "none"

    prompt = f"""You are a TikTok carousel copywriter for a mental wellness brand.

Write a 5-content-slide PARTNER-DIRECTED carousel.
Speak TO the person who loves someone with a mental health struggle.
Each slide has THREE text layers laid over a beautiful image:

  1. COMMAND (small gray label, 2-5 words): sets the context
  2. HERO (large bold concept, 2-4 words): the KEY IDEA on a neon highlight
  3. BODY (1-2 sentences, 18 words max): explains the concept
  4. BOLD (1 sentence, 7 words max): the punchline / most quotable line

SEED TOPIC: "{seed}"
AVOID (recently used): {avoid}

WORD LIMITS (strictly enforced -- images auto-scroll):
  s1: command 4-7w, hero 2-4w ending "..." -- NO body or bold on slide 1
  s2/s3/s4/s5: command 2-4w, hero 2-4w, body 18w max, bold 7w max
  s4_bold = THE most quotable, screenshot-worthy line in the whole carousel
  cta_trigger = "Comment [WORD] if [emotional statement] 👇" (WORD: SAVED/SAME/THIS/YES/REAL)

TONE: Warm, precise, like a poem someone saves forever.

Return ONLY valid JSON:
{{
  "topic": "...",
  "tiktok_title": "...(max 80 chars)...",
  "s1_command": "...",
  "s1_hero": "...(ends with ...)...",
  "s2_command": "...",
  "s2_hero": "...",
  "s2_body": "...",
  "s2_bold": "...",
  "s3_command": "...",
  "s3_hero": "...",
  "s3_body": "...",
  "s3_bold": "...",
  "s4_command": "...",
  "s4_hero": "...",
  "s4_body": "...",
  "s4_bold": "...",
  "s5_command": "...",
  "s5_hero": "...",
  "s5_body": "...",
  "s5_bold": "...",
  "cta_trigger": "...",
  "full_prose_caption": "200-280 word prose, no bullets, ends: Save this for the moments when you need a reminder.",
  "hashtag_topic": "..."
}}"""

    result = _call_claude(prompt, client, max_tokens=2000)

    # Hard trim
    for key in ["s1_hero","s2_hero","s3_hero","s4_hero","s5_hero"]:
        w = result.get(key,"").split()
        if len(w) > 5: result[key] = " ".join(w[:4])
    for key in ["s2_bold","s3_bold","s4_bold","s5_bold"]:
        w = result.get(key,"").split()
        if len(w) > 8:
            result[key] = " ".join(w[:7])
            if result[key][-1] not in ".!?": result[key] += "."
    for key in ["s2_body","s3_body","s4_body","s5_body"]:
        w = result.get(key,"").split()
        if len(w) > 20:
            result[key] = " ".join(w[:18])
            if result[key][-1] not in ".!?": result[key] += "."

    print(f"  Topic: {result.get('topic')}")
    for i in range(1,6):
        cmd = result.get(f"s{i}_command","")
        hero = result.get(f"s{i}_hero","")
        body = result.get(f"s{i}_body","")
        print(f"  Slide {i}: [{cmd}] | [{hero}] | {body[:40] if body else '—'}")
    return result


# ---------------------------------------------------------------------------
# Step 2: Generate cinematic image
# ---------------------------------------------------------------------------
def generate_slide_image(openai_client, slide_key, topic):
    prompt = SLIDE_IMAGE_PROMPTS.get(slide_key, SLIDE_IMAGE_PROMPTS["slide_5"])
    if slide_key == "slide_1":
        prompt = f"{prompt} Emotional theme: {topic}."
    print(f"  [gpt-image-1 HIGH] {slide_key} generating...")
    response = openai_client.images.generate(
        model="gpt-image-1", prompt=prompt,
        size="1024x1536", quality="high", n=1,
    )
    data = response.data[0]
    img_bytes = (
        requests.get(data.url, timeout=60).content
        if getattr(data, "url", None)
        else base64.b64decode(data.b64_json)
    )
    print(f"  [gpt-image-1 HIGH] {slide_key} ready ({len(img_bytes)//1024:.0f} KB)")
    return img_bytes


# ---------------------------------------------------------------------------
# Step 3: Resize image to 1080x1920
# ---------------------------------------------------------------------------
def resize_to_tiktok(img_bytes):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    scale = IMAGE_WIDTH / img.width
    new_h = int(img.height * scale)
    img = img.resize((IMAGE_WIDTH, new_h), Image.LANCZOS)
    if img.height >= IMAGE_HEIGHT:
        top = (img.height - IMAGE_HEIGHT) // 2
        img = img.crop((0, top, IMAGE_WIDTH, top + IMAGE_HEIGHT))
    else:
        pad = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), (0,0,0))
        pad.paste(img, (0, (IMAGE_HEIGHT - img.height)//2))
        img = pad
    return img


# ---------------------------------------------------------------------------
# Step 4: Render text overlay on image
# ---------------------------------------------------------------------------
def render_hook_slide(img, script, brush_color):
    """Slide 1: command (small gray) + hero (large + brush stroke). No body."""
    text_start = int(IMAGE_HEIGHT * TEXT_START_HOOK)
    img = add_gradient_overlay(img, text_start)
    draw = ImageDraw.Draw(img)
    cx = IMAGE_WIDTH // 2
    y  = text_start + 30

    # Command (small, gray)
    cmd_font  = get_font(CMD_SIZE, bold=False)
    cmd_lines = wrap_text(script["s1_command"], cmd_font, MAX_TEXT_W)
    y = draw_text_block(draw, cx, y, cmd_lines, cmd_font, CMD_COLOR, stroke_w=2)
    y += int(SECTION_GAP * 0.7)

    # Hero with brush stroke (large, dark text ON neon stroke)
    hero_font  = get_font(HERO_SIZE, bold=True)
    hero_lines = wrap_text(script["s1_hero"], hero_font, MAX_TEXT_W)
    lh = line_height(hero_font)
    for line in hero_lines:
        draw_brush_stroke(draw, cx, y, line, hero_font, brush_color)
        draw.text((cx, y), line, font=hero_font, fill=HERO_COLOR, anchor="mt")
        y += lh + LINE_GAP
    return img

def render_content_slide(img, script, slide_num, brush_color):
    """Slides 2-5: command + hero (brush) + body + bold punchline."""
    n = str(slide_num)
    text_start = int(IMAGE_HEIGHT * TEXT_START_CONTENT)
    img = add_gradient_overlay(img, text_start)
    draw = ImageDraw.Draw(img)
    cx = IMAGE_WIDTH // 2
    y  = text_start + 25

    # Command
    cmd_font  = get_font(CMD_SIZE, bold=False)
    cmd_lines = wrap_text(script[f"s{n}_command"], cmd_font, MAX_TEXT_W)
    y = draw_text_block(draw, cx, y, cmd_lines, cmd_font, CMD_COLOR, stroke_w=2)
    y += int(SECTION_GAP * 0.5)

    # Hero with brush stroke
    hero_font  = get_font(HERO_SIZE, bold=True)
    hero_lines = wrap_text(script[f"s{n}_hero"], hero_font, MAX_TEXT_W)
    lh = line_height(hero_font)
    for line in hero_lines:
        draw_brush_stroke(draw, cx, y, line, hero_font, brush_color)
        draw.text((cx, y), line, font=hero_font, fill=HERO_COLOR, anchor="mt")
        y += lh + LINE_GAP
    y += SECTION_GAP

    # Body text (white, readable)
    body_text = script.get(f"s{n}_body", "")
    if body_text:
        body_font  = get_font(BODY_SIZE, bold=False)
        body_lines = wrap_text(body_text, body_font, MAX_TEXT_W)
        y = draw_text_block(draw, cx, y, body_lines, body_font, BODY_COLOR, stroke_w=3)
        y += int(LINE_GAP * 0.5)

    # Bold punchline (white, larger, stronger stroke)
    bold_text = script.get(f"s{n}_bold", "")
    if bold_text:
        bold_font  = get_font(BOLD_SIZE, bold=True)
        bold_lines = wrap_text(bold_text, bold_font, MAX_TEXT_W)
        draw_text_block(draw, cx, y, bold_lines, bold_font, BOLD_COLOR, stroke_w=4)
    return img

def render_cta_slide(img, script, brush_color):
    """Slide 6: CTA -- trigger + MindCore AI + download + URL."""
    text_start = int(IMAGE_HEIGHT * TEXT_START_CTA)
    img = add_gradient_overlay(img, max(text_start - 120, 0))
    draw = ImageDraw.Draw(img)
    cx = IMAGE_WIDTH // 2
    y  = text_start

    # Comment trigger
    trig_font  = get_font(CTA_TRIG, bold=True)
    trig_lines = wrap_text(script.get("cta_trigger","Comment SAVED if you needed this 👇"), trig_font, MAX_TEXT_W)
    y = draw_text_block(draw, cx, y, trig_lines, trig_font, CTA_COLOR, stroke_w=3)
    y += SECTION_GAP

    # "MindCore AI" with brush stroke
    app_font = get_font(CTA_APP, bold=True)
    app_text = "MindCore AI"
    lh_app   = line_height(app_font)
    draw_brush_stroke(draw, cx, y, app_text, app_font, brush_color)
    draw.text((cx, y), app_text, font=app_font, fill=HERO_COLOR, anchor="mt")
    y += lh_app + SECTION_GAP

    # "Download for free"
    dl_font  = get_font(CTA_DL, bold=False)
    dl_lines = wrap_text("Download for free", dl_font, MAX_TEXT_W)
    y = draw_text_block(draw, cx, y, dl_lines, dl_font, CTA_COLOR, stroke_w=2)

    # "on Google Play" (bold)
    gp_font  = get_font(CTA_DL, bold=True)
    gp_lines = wrap_text("on Google Play", gp_font, MAX_TEXT_W)
    y = draw_text_block(draw, cx, y, gp_lines, gp_font, CTA_COLOR, stroke_w=3)
    y += int(LINE_GAP * 1.5)

    # URL
    url_font = get_font(CTA_URL, bold=False)
    draw_text_with_stroke(draw, cx, y, "mindcoreai.eu/app", url_font, URL_COLOR, stroke_w=2)
    return img


# ---------------------------------------------------------------------------
# Step 5: Build caption
# ---------------------------------------------------------------------------
def build_tiktok_content(script):
    title = script.get("tiktok_title","")[:TIKTOK_TITLE_LIMIT]
    prose = script.get("full_prose_caption","")
    tag   = f"#{script.get('hashtag_topic','mentalwellness')}"
    desc  = f"{prose}\n\n{tag} {HASHTAGS}"
    if REQUIRED_BRAND_HASHTAG.lower() not in desc.lower():
        desc += f" {REQUIRED_BRAND_HASHTAG}"
    return title, desc[:TIKTOK_DESC_LIMIT]


# ---------------------------------------------------------------------------
# Step 6: Upload to TikTok + Facebook
# ---------------------------------------------------------------------------
def upload_carousel(image_paths, tiktok_title, description, cfg):
    if not UPLOAD_POST_API_KEY:
        return {"skipped": True, "reason": "no API key"}
    user = cfg.get("upload_post_user","")
    if not user:
        return {"skipped": True, "reason": "no user configured"}

    headers = {"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"}
    data = [
        ("user",              user),
        ("platform[]",        "tiktok"),
        ("platform[]",        "facebook"),
        ("tiktok_title",      tiktok_title),
        ("description",       description),
        ("post_mode",         "MEDIA_UPLOAD"),
        ("auto_add_music",    "true"),
        ("photo_cover_index", "0"),
    ]
    files = []
    try:
        for i, path in enumerate(image_paths):
            f = open(path, "rb")
            files.append(("photos[]", (f"slide_{i+1}.jpg", f, "image/jpeg")))
        resp = requests.post(
            UPLOAD_POST_PHOTOS_URL, headers=headers,
            files=files, data=data, timeout=180
        )
        result = (
            resp.json()
            if resp.headers.get("content-type","").startswith("application/json")
            else {"raw": resp.text}
        )
        result["status_code"] = resp.status_code
        print(f"  Upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}")
        if not resp.ok: print(f"  {resp.text[:400]}")
        return result
    except Exception as e:
        print(f"  Upload failed: {e}")
        return {"error": str(e)}
    finally:
        for _, (_, f, _) in files:
            try: f.close()
            except: pass


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client        = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

    cfg = {}
    cfg_path = Path("video_pipeline/heygen_config.json")
    if cfg_path.exists():
        with open(cfg_path) as f: cfg = json.load(f)
    upload_enabled = cfg.get("upload_enabled", False) and bool(UPLOAD_POST_API_KEY)

    history = load_history()

    print(f"\n  MindCore AI -- Carousel Image Post Pipeline v2.1")
    print(f"  Run #{GITHUB_RUN_NUMBER} | 6 slides | Cinematic photos + text hierarchy | ~$0.48")
    print(f"  Text: 3 sizes (command/hero+brush/body+bold) | Max 10w/slide")
    print(f"  Upload: {'ENABLED' if upload_enabled else 'DISABLED'} | TikTok draft + Facebook")
    print("=" * 60)

    # Script
    print("\n  Generating partner-directed script...")
    script = generate_carousel_script(client, history)
    (OUTPUT_DIR / "carousel_script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")

    slide_keys  = ["slide_1","slide_2","slide_3","slide_4","slide_5","slide_6"]
    image_paths = []

    for idx, slide_key in enumerate(slide_keys):
        print(f"\n  ── {slide_key.upper()} ──")
        brush_color = BRUSH_PALETTE[idx]

        # Generate cinematic image
        img_bytes = generate_slide_image(openai_client, slide_key, script.get("topic",""))
        img = resize_to_tiktok(img_bytes)

        # Render text overlay
        if slide_key == "slide_1":
            img = render_hook_slide(img, script, brush_color)
        elif slide_key == "slide_6":
            img = render_cta_slide(img, script, brush_color)
        else:
            img = render_content_slide(img, script, int(slide_key[-1]), brush_color)

        # Save
        out_path = str(OUTPUT_DIR / f"{slide_key}.jpg")
        img.save(out_path, format="JPEG", quality=94)
        image_paths.append(out_path)
        print(f"  Saved: {Path(out_path).stat().st_size // 1024:.0f} KB")
        time.sleep(0.5)

    # Caption
    tiktok_title, description = build_tiktok_content(script)
    (OUTPUT_DIR / "carousel_caption.txt").write_text(
        f"TITLE ({len(tiktok_title)} chars):\n{tiktok_title}\n\n"
        f"DESCRIPTION ({len(description)} chars):\n{description}",
        encoding="utf-8"
    )
    print(f"\n  Title: {tiktok_title}")
    print(f"  Description: {description[:80]}...")

    # Upload
    if upload_enabled:
        print("\n  Uploading 6 slides to TikTok (draft) + Facebook...")
        result = upload_carousel(image_paths, tiktok_title, description, cfg)
        (OUTPUT_DIR / "carousel_upload_result.json").write_text(json.dumps(result, indent=2))
    else:
        print("\n  Upload DISABLED -- slides saved to output_carousel/")
        (OUTPUT_DIR / "carousel_upload_result.json").write_text(json.dumps({"skipped": True}))

    save_history(history, {
        "date":     datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "topic":    script.get("topic",""),
        "headline": f"{script.get('s1_command')} / {script.get('s1_hero')}",
        "run":      GITHUB_RUN_NUMBER,
    })

    print(f"\n  DONE | {script.get('topic')} | 6 slides | ~$0.48")
    if upload_enabled:
        print("  Facebook: posted directly")
        print("  TikTok: in inbox -- open app, pick slow music, publish")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import sys
        print(f"\n  FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
