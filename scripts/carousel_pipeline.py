#!/usr/bin/env python3
"""
MindCore AI -- Carousel Image Post Pipeline v2.0
=================================================
Complete redesign inspired by high-performing carousel analysis.

Format:
  - WHITE background with dark text (maximum readability)
  - Pen & ink sketch illustrations in bottom ~55% of each slide
  - THREE font sizes per slide: command (small gray) / hero (large bold + brush stroke) / body (medium)
  - Colored brush-stroke highlight behind hero concept word
  - 6 slides: 5 content slides + 1 CTA slide
  - Partner-directed scripts drive saves and shares
  - CTA: "Download for free on Google Play"
  - MEDIA_UPLOAD to TikTok drafts + direct to Facebook

Cost: ~$0.48/post (6 x gpt-image-1 high @ ~$0.08) + Claude
Schedule: daily 07:00 UTC (9am Malta --> ~2pm Malta landing)

v2.0: Full redesign -- white bg, pen sketches, 3 font sizes, brush strokes, CTA slide
v1.7: TikTok + Facebook, 5 cinematic dark image slides
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
# Design tokens
# ---------------------------------------------------------------------------
CANVAS_BG   = (255, 255, 255)   # pure white
TEXT_DARK   = (15, 15, 15)      # near black (hero, bold)
TEXT_GRAY   = (110, 110, 110)   # medium gray (command labels)
TEXT_BODY   = (50, 50, 50)      # dark gray (body lines)
TEXT_BOLD   = (10, 10, 10)      # near black (bold emphasis)
TEXT_URL    = (140, 140, 140)   # light gray (URL on CTA)

# Brush stroke palette -- rotates per slide
BRUSH_PALETTE = [
    (168, 224, 99),   # lime green  #A8E063
    (78,  205, 196),  # cyan        #4ECDC4
    (255, 209, 102),  # yellow      #FFD166
    (168, 224, 99),   # lime green  (repeat)
    (78,  205, 196),  # cyan        (repeat)
    (255, 209, 102),  # yellow      (CTA slide)
]

# Font sizes for three hierarchy levels
CMD_SIZE  = 56    # command / label (small gray)
HERO_SIZE = 94    # hero concept (large bold + brush stroke)
BODY_SIZE = 44    # body explanation text
BOLD_SIZE = 50    # bold emphasis line within body
CTA_TRIGGER_SIZE = 62  # "Comment X if..." trigger
CTA_APP_SIZE     = 86  # "MindCore AI" on CTA slide
CTA_DL_SIZE      = 52  # "Download for free on Google Play"
CTA_URL_SIZE     = 40  # URL

MAX_TEXT_W  = int(IMAGE_WIDTH * 0.88)  # 950px -- text wraps within this
TOP_PADDING = 95
LINE_GAP    = 18   # space between lines of same size
SECTION_GAP = 42   # space between text sections

# Illustration starts at this y (text fills above)
# Calculated dynamically per slide, these are soft minimums
MIN_ILLUS_Y_CONTENT = 820
MIN_ILLUS_Y_HOOK    = 720
MIN_ILLUS_Y_CTA     = 880

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
# Pen-sketch illustration prompts per slide (white background, black ink)
# ---------------------------------------------------------------------------
ILLUS_PROMPTS = {
    "slide_1": (
        "Dramatic expressive pen and ink sketch illustration. "
        "A person tenderly holding another in a gentle protective embrace, "
        "one figure supporting the other with warmth and care. "
        "Intricate cross-hatching, expressive fine line work. "
        "Pure white background, black ink only. "
        "High artistic quality, deeply emotional. No text, no watermarks."
    ),
    "slide_2": (
        "Dramatic expressive pen and ink sketch illustration. "
        "A solitary figure sitting with head slightly bowed, surrounded by "
        "swirling spiral lines suggesting a restless overthinking mind. "
        "Heavy, contemplative mood. Fine line work and cross-hatching. "
        "Pure white background, black ink only. No text, no watermarks."
    ),
    "slide_3": (
        "Dramatic expressive pen and ink sketch illustration. "
        "Two hands nearly touching but not quite, fingers reaching toward "
        "each other with tender vulnerability. Delicate fine line work. "
        "Pure white background, black ink only. No text, no watermarks."
    ),
    "slide_4": (
        "Dramatic expressive pen and ink sketch illustration. "
        "A figure with eyes gently closed, chin slightly tilted upward, "
        "expression of quiet realisation and inner peace. "
        "Soft radiating lines suggesting calm. Fine cross-hatching. "
        "Pure white background, black ink only. No text, no watermarks."
    ),
    "slide_5": (
        "Dramatic expressive pen and ink sketch illustration. "
        "A figure standing with arms slightly open at sides, grounded "
        "and resolved, a sense of quiet strength and acceptance. "
        "Expressive flowing line work. "
        "Pure white background, black ink only. No text, no watermarks."
    ),
    "slide_6": (
        "Dramatic expressive pen and ink sketch illustration. "
        "A modern smartphone with a stylised brain and gentle heartbeat "
        "line on its screen, surrounded by small radiating lines of calm "
        "energy. Minimalist and clean. Fine line work. "
        "Pure white background, black ink only. No text, no watermarks."
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
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
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
    """Load Liberation Sans bold or regular."""
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
    # Fallback: try the other weight
    for path in (reg_paths if bold else bold_paths):
        if Path(path).exists():
            try: return ImageFont.truetype(path, size)
            except: pass
    return ImageFont.load_default()

def wrap_text(text, font, max_width):
    """Word-wrap text to fit within max_width pixels."""
    words = text.split(); lines = []; current = []
    for word in words:
        test = " ".join(current + [word])
        try: w = font.getbbox(test)[2] - font.getbbox(test)[0]
        except: w = len(test) * (font.size if hasattr(font, "size") else 30)
        if w <= max_width:
            current.append(word)
        else:
            if current: lines.append(" ".join(current))
            current = [word]
    if current: lines.append(" ".join(current))
    return lines or [""]

def text_line_height(font):
    """Approximate height of one line of text."""
    try:
        bbox = font.getbbox("Ag")
        return bbox[3] - bbox[1]
    except:
        return getattr(font, "size", 40)

def draw_text_block(draw, lines, font, cx, y, color):
    """Draw multiple text lines centered at cx, starting at y. Returns new y."""
    lh = text_line_height(font)
    for line in lines:
        draw.text((cx, y), line, font=font, fill=color, anchor="mt")
        y += lh + LINE_GAP
    return y

def draw_brush_stroke(draw, cx, y_top, text, font, color):
    """Draw irregular parallelogram behind text as brush stroke highlight."""
    try:
        bbox = font.getbbox(text)
        tw = bbox[2] - bbox[0]
        th = bbox[3] - bbox[1]
    except:
        tw = len(text) * getattr(font, "size", 40) * 0.55
        th = getattr(font, "size", 40)
    pad_x, pad_y, skew = 28, 10, 9
    x1 = cx - tw // 2 - pad_x
    x2 = cx + tw // 2 + pad_x
    y1 = y_top - pad_y
    y2 = y_top + th + pad_y
    pts = [
        (x1 + skew, y1 - 3),
        (x2 + skew, y1 + 4),
        (x2 - skew, y2 + 4),
        (x1 - skew, y2 - 3),
    ]
    draw.polygon(pts, fill=color)

def paste_illustration(canvas, illus_bytes, y_start):
    """Open illustration, resize to canvas width, paste at y_start."""
    illus = Image.open(io.BytesIO(illus_bytes)).convert("RGBA")
    # Scale to canvas width
    scale = IMAGE_WIDTH / illus.width
    new_h = int(illus.height * scale)
    illus = illus.resize((IMAGE_WIDTH, new_h), Image.LANCZOS)
    # Available vertical space
    avail_h = IMAGE_HEIGHT - y_start
    if new_h > avail_h:
        illus = illus.crop((0, 0, IMAGE_WIDTH, avail_h))
    # Paste -- white bg so RGBA blending is clean
    bg = Image.new("RGBA", (IMAGE_WIDTH, IMAGE_HEIGHT), (255, 255, 255, 255))
    bg.paste(canvas.convert("RGBA"), (0, 0))
    bg.paste(illus, (0, y_start), illus)
    return bg.convert("RGB")


# ---------------------------------------------------------------------------
# Step 1: Generate 6-slide script
# ---------------------------------------------------------------------------
def generate_carousel_script(client, history):
    used = [e.get("topic", "") for e in history]
    seed = random.choice(PARTNER_SEEDS)
    avoid = ", ".join(used[-10:]) if used else "none"

    prompt = f"""You are a senior TikTok carousel copywriter for a mental wellness brand.

Write a 5-content-slide carousel in the PARTNER-DIRECTED style.
Speak TO the person who loves someone with a mental health struggle.
This doubles the audience: the struggling person shares it ("this is me"),
the partner saves it ("I need to remember this").

SEED TOPIC: "{seed}"
AVOID (recently used): {avoid}

SLIDE STRUCTURE -- Each slide has THREE text layers:
1. COMMAND (small, gray): 2-5 word setup phrase -- the context setter
2. HERO (large, bold, highlighted): 2-4 words -- the KEY CONCEPT on a brush stroke
3. BODY (medium): 1-2 SHORT sentences (20 words max). Then a BOLD LINE (8 words max).

TONE: Warm, emotionally precise. Every word earns its place.
Like a line from a poem someone screenshots and saves.

RULES:
  s1_command: 4-7 words. Emotional setup. Ends mid-thought. ("Loving someone with anxiety")
  s1_hero: 2-4 words. The cliffhanger concept. Ends "..." ("means THIS...")
  (slide 1 has NO body -- just command + hero + illustration)

  s2/s3/s4/s5_command: 2-4 words. The label/setup. ("Their mind", "What looks like", "The truth is")
  s2/s3/s4/s5_hero: 2-4 words. The KEY CONCEPT on the highlight. ("never stops", "distance", "just stay")
  s2/s3_body: 1-2 sentences, 20 words max. Explains the concept.
  s2/s3_bold: 1 sentence, 8 words MAX. The bold punchline below the body.
  s4_body: 1 sentence, 15 words max. Build toward the payoff.
  s4_bold: 1 sentence, 8 words MAX. THE most quotable line in the whole carousel.
  s5_body: 1-2 warm sentences, 20 words max. Resolution.
  s5_bold: 1 sentence, 8 words MAX. Warm close.

  cta_trigger: "Comment [WORD] if [2nd person emotional statement] 👇"
    WORD options: SAVED / SAME / THIS / YES / REAL / NEEDED
    Example: "Comment SAVED if you needed to read this 👇"

  tiktok_title: Max 80 chars. The hook as a title.
  full_prose_caption: 200-280 word flowing prose. No bullets/headers.
    Start with the hero concept. End: "Save this for the moments when you need a reminder."
  topic: 4-7 word description
  hashtag_topic: one hashtag without # (e.g. anxietysupport)

Return ONLY valid JSON:
{{
  "topic": "...",
  "tiktok_title": "...",
  "s1_command": "...",
  "s1_hero": "...",
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
  "full_prose_caption": "...",
  "hashtag_topic": "..."
}}"""

    result = _call_claude(prompt, client, max_tokens=2000)

    # Hard trim hero fields to max 4 words
    for key in ["s1_hero","s2_hero","s3_hero","s4_hero","s5_hero"]:
        words = result.get(key,"").split()
        if len(words) > 5:
            result[key] = " ".join(words[:4])

    # Hard trim bold lines to max 8 words
    for key in ["s2_bold","s3_bold","s4_bold","s5_bold"]:
        words = result.get(key,"").split()
        if len(words) > 8:
            result[key] = " ".join(words[:8])
            if not result[key][-1] in ".!?": result[key] += "."

    print(f"  Topic: {result.get('topic')}")
    for i in range(1,6):
        print(f"  Slide {i}: [{result.get(f's{i}_command')}] + [{result.get(f's{i}_hero')}]")
    return result


# ---------------------------------------------------------------------------
# Step 2: Generate pen-sketch illustration
# ---------------------------------------------------------------------------
def generate_illustration(openai_client, slide_key, topic):
    prompt = ILLUS_PROMPTS.get(slide_key, ILLUS_PROMPTS["slide_1"])
    if slide_key == "slide_1":
        prompt += f" Emotional theme: {topic}."
    print(f"  [gpt-image-1 HIGH] {slide_key} illustration generating...")
    response = openai_client.images.generate(
        model="gpt-image-1",
        prompt=prompt,
        size="1024x1536",
        quality="high",
        n=1,
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
# Step 3: Render each slide
# ---------------------------------------------------------------------------
def render_hook_slide(script, illus_bytes, brush_color):
    """Slide 1: command + large hero with brush stroke + illustration."""
    canvas = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), CANVAS_BG)
    draw   = ImageDraw.Draw(canvas)
    cx     = IMAGE_WIDTH // 2
    y      = TOP_PADDING

    # Command line (small, gray)
    cmd_font  = get_font(CMD_SIZE, bold=False)
    cmd_lines = wrap_text(script["s1_command"], cmd_font, MAX_TEXT_W)
    y = draw_text_block(draw, cmd_lines, cmd_font, cx, y, TEXT_GRAY)
    y += SECTION_GAP

    # Hero with brush stroke
    hero_font  = get_font(HERO_SIZE, bold=True)
    hero_lines = wrap_text(script["s1_hero"], hero_font, MAX_TEXT_W)
    lh = text_line_height(hero_font)
    for line in hero_lines:
        draw_brush_stroke(draw, cx, y, line, hero_font, brush_color)
        draw.text((cx, y), line, font=hero_font, fill=TEXT_DARK, anchor="mt")
        y += lh + LINE_GAP

    illus_y = max(y + SECTION_GAP + 30, MIN_ILLUS_Y_HOOK)
    return paste_illustration(canvas, illus_bytes, illus_y)


def render_content_slide(script, slide_num, illus_bytes, brush_color):
    """Slides 2-5: command + hero (brush) + body + bold line + illustration."""
    canvas = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), CANVAS_BG)
    draw   = ImageDraw.Draw(canvas)
    cx     = IMAGE_WIDTH // 2
    y      = TOP_PADDING

    n = str(slide_num)

    # Command
    cmd_font  = get_font(CMD_SIZE, bold=False)
    cmd_lines = wrap_text(script[f"s{n}_command"], cmd_font, MAX_TEXT_W)
    y = draw_text_block(draw, cmd_lines, cmd_font, cx, y, TEXT_GRAY)
    y += int(SECTION_GAP * 0.6)

    # Hero with brush stroke
    hero_font  = get_font(HERO_SIZE, bold=True)
    hero_lines = wrap_text(script[f"s{n}_hero"], hero_font, MAX_TEXT_W)
    lh_hero = text_line_height(hero_font)
    for line in hero_lines:
        draw_brush_stroke(draw, cx, y, line, hero_font, brush_color)
        draw.text((cx, y), line, font=hero_font, fill=TEXT_DARK, anchor="mt")
        y += lh_hero + LINE_GAP
    y += SECTION_GAP

    # Body text (regular, smaller)
    body_text = script.get(f"s{n}_body", "")
    if body_text:
        body_font  = get_font(BODY_SIZE, bold=False)
        body_lines = wrap_text(body_text, body_font, MAX_TEXT_W)
        y = draw_text_block(draw, body_lines, body_font, cx, y, TEXT_BODY)
        y += int(LINE_GAP * 0.5)

    # Bold punchline
    bold_text = script.get(f"s{n}_bold", "")
    if bold_text:
        bold_font  = get_font(BOLD_SIZE, bold=True)
        bold_lines = wrap_text(bold_text, bold_font, MAX_TEXT_W)
        y = draw_text_block(draw, bold_lines, bold_font, cx, y, TEXT_BOLD)

    illus_y = max(y + SECTION_GAP, MIN_ILLUS_Y_CONTENT)
    return paste_illustration(canvas, illus_bytes, illus_y)


def render_cta_slide(script, illus_bytes, brush_color):
    """Slide 6: CTA -- trigger + MindCore AI brand + download + URL."""
    canvas = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), CANVAS_BG)
    draw   = ImageDraw.Draw(canvas)
    cx     = IMAGE_WIDTH // 2
    y      = TOP_PADDING

    # Comment trigger
    trig_font  = get_font(CTA_TRIGGER_SIZE, bold=True)
    trig_lines = wrap_text(script.get("cta_trigger","Comment SAVED if you needed this 👇"), trig_font, MAX_TEXT_W)
    y = draw_text_block(draw, trig_lines, trig_font, cx, y, TEXT_DARK)
    y += SECTION_GAP

    # "MindCore AI" with brush stroke
    app_font  = get_font(CTA_APP_SIZE, bold=True)
    app_text  = "MindCore AI"
    lh_app    = text_line_height(app_font)
    draw_brush_stroke(draw, cx, y, app_text, app_font, brush_color)
    draw.text((cx, y), app_text, font=app_font, fill=TEXT_DARK, anchor="mt")
    y += lh_app + SECTION_GAP

    # "Download for free"
    dl_font  = get_font(CTA_DL_SIZE, bold=False)
    dl_lines = wrap_text("Download for free", dl_font, MAX_TEXT_W)
    y = draw_text_block(draw, dl_lines, dl_font, cx, y, TEXT_BODY)

    # "on Google Play" (bold)
    gp_font  = get_font(CTA_DL_SIZE, bold=True)
    gp_lines = wrap_text("on Google Play", gp_font, MAX_TEXT_W)
    y = draw_text_block(draw, gp_lines, gp_font, cx, y, TEXT_DARK)
    y += int(LINE_GAP * 1.5)

    # URL
    url_font = get_font(CTA_URL_SIZE, bold=False)
    draw.text((cx, y), "mindcoreai.eu/app", font=url_font, fill=TEXT_URL, anchor="mt")
    y += text_line_height(url_font) + SECTION_GAP

    illus_y = max(y + 20, MIN_ILLUS_Y_CTA)
    return paste_illustration(canvas, illus_bytes, illus_y)


# ---------------------------------------------------------------------------
# Step 4: Build TikTok caption
# ---------------------------------------------------------------------------
def build_tiktok_content(script):
    title = script.get("tiktok_title", "")[:TIKTOK_TITLE_LIMIT]
    prose = script.get("full_prose_caption", "")
    tag   = f"#{script.get('hashtag_topic','mentalwellness')}"
    desc  = f"{prose}\n\n{tag} {HASHTAGS}"
    if REQUIRED_BRAND_HASHTAG.lower() not in desc.lower():
        desc += f" {REQUIRED_BRAND_HASHTAG}"
    return title, desc[:TIKTOK_DESC_LIMIT]


# ---------------------------------------------------------------------------
# Step 5: Upload to TikTok + Facebook
# ---------------------------------------------------------------------------
def upload_carousel(image_paths, tiktok_title, description, cfg):
    """Upload 6 images to TikTok (draft) + Facebook (direct).
    TikTok MEDIA_UPLOAD: opens in TikTok app to pick slow ambient music.
    """
    if not UPLOAD_POST_API_KEY:
        return {"skipped": True, "reason": "no API key"}
    user = cfg.get("upload_post_user", "")
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

    print(f"\n  MindCore AI -- Carousel Image Post Pipeline v2.0")
    print(f"  Run #{GITHUB_RUN_NUMBER} | 6 slides | gpt-image-1 HIGH | ~$0.48/post")
    print(f"  White bg + pen sketches + 3 font sizes + brush strokes + CTA slide")
    print(f"  Upload: {'ENABLED' if upload_enabled else 'DISABLED'} | TikTok draft + Facebook")
    print("=" * 60)

    # Script
    print("\n  Generating partner-directed script...")
    script = generate_carousel_script(client, history)
    (OUTPUT_DIR / "carousel_script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")

    # Build slides
    slide_keys    = ["slide_1","slide_2","slide_3","slide_4","slide_5","slide_6"]
    image_paths   = []

    for idx, slide_key in enumerate(slide_keys):
        print(f"\n  ── {slide_key.upper()} ──")
        brush_color = BRUSH_PALETTE[idx]

        # Generate pen sketch illustration
        illus_bytes = generate_illustration(openai_client, slide_key, script.get("topic",""))
        time.sleep(0.5)

        # Render slide
        if slide_key == "slide_1":
            img = render_hook_slide(script, illus_bytes, brush_color)
        elif slide_key == "slide_6":
            img = render_cta_slide(script, illus_bytes, brush_color)
        else:
            slide_num = int(slide_key[-1])
            img = render_content_slide(script, slide_num, illus_bytes, brush_color)

        # Save
        out_path = str(OUTPUT_DIR / f"{slide_key}.jpg")
        img.save(out_path, format="JPEG", quality=94)
        image_paths.append(out_path)
        print(f"  Saved: {Path(out_path).stat().st_size // 1024:.0f} KB")

    # Caption
    tiktok_title, description = build_tiktok_content(script)
    (OUTPUT_DIR / "carousel_caption.txt").write_text(
        f"TITLE ({len(tiktok_title)} chars):\n{tiktok_title}\n\n"
        f"DESCRIPTION ({len(description)} chars):\n{description}",
        encoding="utf-8"
    )
    print(f"\n  Title ({len(tiktok_title)} chars): {tiktok_title}")
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
        print("  TikTok: in inbox -- open app, pick slow ambient music, publish")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import sys
        print(f"\n  FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
