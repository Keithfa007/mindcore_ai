#!/usr/bin/env python3
"""
MindCore AI -- Carousel Image Post Pipeline v1.7
=================================================
Generates 5-image TikTok Photo Mode + Facebook carousel posts.
Partner-directed scripts drive saves and shares.

Format:
  - 5 cinematic images (gpt-image-1 HIGH, 1080x1920)
  - QUOTE CARD format: 1 bold sentence per slide, max 10 words
  - Large font -- readable in 2-3 seconds at TikTok auto-scroll speed
  - Text centred vertically on all slides
  - Full prose script as caption
  - MEDIA_UPLOAD mode -- lands in TikTok drafts for music selection
  - Posted to TikTok + Facebook simultaneously

Cost: ~$0.40/post (5 x gpt-image-1 high @ ~$0.08)
Schedule: daily 07:00 UTC (9am Malta --> ~2pm Malta landing)

v1.7: Added Facebook to upload (TikTok + Facebook)
v1.6: Quote-card format, max 10 words/slide, bigger fonts
v1.5: Text centred, MEDIA_UPLOAD mode
v1.4: Correct endpoint /api/upload_photos
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
# Slide image prompts
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
}

SLIDE_FONT_SIZES = {
    "slide_1": 72,
    "slide_2": 62,
    "slide_3": 62,
    "slide_4": 76,
    "slide_5": 64,
}

SLIDE_TEXT_POSITIONS = {
    "slide_1": 0.50,
    "slide_2": 0.50,
    "slide_3": 0.50,
    "slide_4": 0.50,
    "slide_5": 0.50,
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

def _call_claude(prompt, client, max_tokens=1500):
    for attempt in range(1, CLAUDE_MAX_RETRIES+1):
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


# ---------------------------------------------------------------------------
# Step 1: Generate script -- QUOTE CARD format, max 10 words per slide
# ---------------------------------------------------------------------------
def generate_carousel_script(client, history):
    used_topics = [e.get("topic", "") for e in history]
    seed = random.choice(PARTNER_SEEDS)
    avoid = ", ".join(used_topics[-10:]) if used_topics else "none"

    prompt = f"""You are a senior mental wellness content writer for TikTok quote-card carousels.

Write a 5-slide QUOTE CARD carousel in the partner-directed style.
This speaks TO the person who loves someone with a mental health struggle.

SEED TOPIC: "{seed}"
AVOID (already used): {avoid}

CRITICAL FORMAT RULE -- WORD LIMITS:
Each slide displays for only 2-3 seconds. The viewer must read
the ENTIRE slide in one glance. Every word must earn its place.

  - headline_line1: 3-5 words. Ends mid-sentence. No full stop.
    Example: "Loving someone with anxiety"
  - headline_line2: 3-5 words. MUST end with "..."
    Example: "means this..."
  - slide_2_text: EXACTLY 1 sentence. MAX 10 words. Name the core truth.
    Example: "Their mind never gets a day off."
  - slide_3_text: EXACTLY 1 sentence. MAX 10 words. The deeper reframe.
    Example: "That silence isn't distance. It's exhaustion."
  - slide_4_text: EXACTLY 1 sentence. MAX 8 words. The screenshot-worthy payoff.
    THE MOST IMPORTANT LINE. Must be quotable and memorable.
    Example: "You don't have to fix it. Just stay."
  - slide_5_text: EXACTLY 1 sentence. MAX 10 words. Warm earned resolution.
    Example: "That's what love actually looks like."

TONE: Warm, emotionally precise. Like a line from a poem someone saves forever.
If it can be cut, cut it.

  - tiktok_title: Max 80 chars. Punchy version of the headline.
  - full_prose_caption: 200-280 word flowing prose. No bullets. No headers.
    This is read at the viewer's own pace in the caption section.
    Start with the headline concept. End with:
    "Save this for the moments when you need a reminder."
  - topic: 4-7 word description
  - hashtag_topic: single hashtag without # (e.g. anxietysupport)

Return ONLY valid JSON:
{{
  "topic": "...",
  "tiktok_title": "...",
  "headline_line1": "...",
  "headline_line2": "...\u2026",
  "slide_2_text": "...",
  "slide_3_text": "...",
  "slide_4_text": "...",
  "slide_5_text": "...",
  "full_prose_caption": "...",
  "hashtag_topic": "..."
}}"""

    result = _call_claude(prompt, client, max_tokens=1500)

    # Hard trim if Claude over-generates
    for key, limit in [("slide_2_text", 10), ("slide_3_text", 10),
                       ("slide_4_text", 8), ("slide_5_text", 10)]:
        text = result.get(key, "")
        words = text.split()
        if len(words) > limit:
            result[key] = " ".join(words[:limit])
            if not result[key].endswith((".", "!", "?")):
                result[key] = result[key].rstrip(",;") + "."
            print(f"  TRIMMED [{key}]: {len(words)} -> {limit} words")

    print(f"  Topic: {result.get('topic')}")
    print(f"  Slide 1: {result.get('headline_line1')} / {result.get('headline_line2')}")
    print(f"  Slide 2: {result.get('slide_2_text')} ({len(result.get('slide_2_text','').split())}w)")
    print(f"  Slide 3: {result.get('slide_3_text')} ({len(result.get('slide_3_text','').split())}w)")
    print(f"  Slide 4: {result.get('slide_4_text')} ({len(result.get('slide_4_text','').split())}w)")
    print(f"  Slide 5: {result.get('slide_5_text')} ({len(result.get('slide_5_text','').split())}w)")
    return result


# ---------------------------------------------------------------------------
# Step 2: Generate images
# ---------------------------------------------------------------------------
def generate_slide_image(openai_client, slide_key, script):
    base_prompt = SLIDE_IMAGE_PROMPTS[slide_key]
    prompt = f"{base_prompt} Theme: {script.get('topic', '')}" if slide_key == "slide_1" else base_prompt
    print(f"  [gpt-image-1 HIGH] {slide_key} generating...")
    response = openai_client.images.generate(
        model="gpt-image-1", prompt=prompt,
        size="1024x1536", quality="high", n=1,
    )
    data = response.data[0]
    img_bytes = requests.get(data.url, timeout=30).content if getattr(data, "url", None) else base64.b64decode(data.b64_json)
    print(f"  [gpt-image-1 HIGH] {slide_key} ready ({len(img_bytes)//1024:.0f} KB)")
    return img_bytes


# ---------------------------------------------------------------------------
# Step 3: Resize to 1080x1920
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
        padded = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), (0, 0, 0))
        padded.paste(img, (0, (IMAGE_HEIGHT - img.height) // 2))
        img = padded
    return img


# ---------------------------------------------------------------------------
# Step 4: Text overlay -- centred, large font, quote-card style
# ---------------------------------------------------------------------------
def wrap_text(text, font, max_width):
    words = text.split(); lines = []; current = []
    for word in words:
        test = " ".join(current + [word])
        try: w = font.getbbox(test)[2] - font.getbbox(test)[0]
        except: w = len(test) * 35
        if w <= max_width: current.append(word)
        else:
            if current: lines.append(" ".join(current))
            current = [word]
    if current: lines.append(" ".join(current))
    return lines

def load_font(size):
    for path in [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-Bold.ttf",
    ]:
        if Path(path).exists():
            try: return ImageFont.truetype(path, size)
            except: pass
    return ImageFont.load_default()

def add_text_overlay(img, text_lines, slide_key):
    draw = ImageDraw.Draw(img)
    font_size = SLIDE_FONT_SIZES[slide_key]
    font = load_font(font_size)
    max_w = int(IMAGE_WIDTH * 0.85)
    stroke = max(4, font_size // 16)
    spacing = int(font_size * 1.40)
    wrapped = []
    for line in text_lines:
        wrapped.extend(wrap_text(line, font, max_w))
    total_h = len(wrapped) * spacing
    start_y = int(IMAGE_HEIGHT * SLIDE_TEXT_POSITIONS[slide_key]) - total_h // 2
    cx = IMAGE_WIDTH // 2
    for i, line in enumerate(wrapped):
        y = start_y + i * spacing
        for dx in range(-stroke, stroke+1):
            for dy in range(-stroke, stroke+1):
                if dx or dy:
                    draw.text((cx+dx, y+dy), line, font=font, fill=(0,0,0), anchor="mm")
        draw.text((cx, y), line, font=font, fill=(255,255,255), anchor="mm")
    return img

def build_slide_texts(script):
    return {
        "slide_1": [script["headline_line1"], script["headline_line2"]],
        "slide_2": [script["slide_2_text"]],
        "slide_3": [script["slide_3_text"]],
        "slide_4": [script["slide_4_text"]],
        "slide_5": [script["slide_5_text"]],
    }


# ---------------------------------------------------------------------------
# Step 5: TikTok title and description
# ---------------------------------------------------------------------------
def build_tiktok_content(script):
    title = script.get("tiktok_title", "")[:TIKTOK_TITLE_LIMIT]
    prose = script.get("full_prose_caption", "")
    topic_tag = f"#{script.get('hashtag_topic', 'mentalwellness')}"
    description = f"{prose}\n\n{topic_tag} {HASHTAGS}"
    if REQUIRED_BRAND_HASHTAG.lower() not in description.lower():
        description += f" {REQUIRED_BRAND_HASHTAG}"
    return title, description[:TIKTOK_DESC_LIMIT]


# ---------------------------------------------------------------------------
# Step 6: Upload to TikTok + Facebook via Upload-Post
# ---------------------------------------------------------------------------
def upload_carousel(image_paths, tiktok_title, description, cfg):
    """Upload 5 images to TikTok (draft) + Facebook (direct post).

    TikTok: MEDIA_UPLOAD mode -- lands in inbox as draft.
            Open app, pick slow ambient music, then publish.
    Facebook: DIRECT_POST -- auto-detects connected page.

    Docs: https://docs.upload-post.com/api/upload-photo
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
        ("post_mode",         "MEDIA_UPLOAD"),   # TikTok -> inbox/draft
        ("auto_add_music",    "true"),
        ("photo_cover_index", "0"),
        # Facebook uses description as caption automatically
        # If multiple pages connected, add: ("facebook_page_id", "YOUR_PAGE_ID")
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
            if resp.headers.get("content-type", "").startswith("application/json")
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

    print(f"\n  MindCore AI -- Carousel Image Post Pipeline v1.7")
    print(f"  Run #{GITHUB_RUN_NUMBER} | 5 slides | gpt-image-1 HIGH | ~$0.40/post")
    print(f"  Format: quote-card (max 10 words/slide) | Platforms: TikTok + Facebook")
    print(f"  Upload: {'ENABLED' if upload_enabled else 'DISABLED'}")
    print("=" * 60)

    print("\n  Generating quote-card script...")
    script = generate_carousel_script(client, history)
    (OUTPUT_DIR / "carousel_script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")

    slide_keys  = ["slide_1", "slide_2", "slide_3", "slide_4", "slide_5"]
    slide_texts = build_slide_texts(script)
    image_paths = []

    for slide_key in slide_keys:
        print(f"\n  [{slide_key.upper()}]")
        img_bytes = generate_slide_image(openai_client, slide_key, script)
        img = resize_to_tiktok(img_bytes)
        img = add_text_overlay(img, slide_texts[slide_key], slide_key)
        out_path = str(OUTPUT_DIR / f"{slide_key}.jpg")
        img.save(out_path, format="JPEG", quality=92)
        image_paths.append(out_path)
        print(f"  Saved: {Path(out_path).stat().st_size // 1024:.0f} KB")
        time.sleep(1)

    tiktok_title, description = build_tiktok_content(script)
    (OUTPUT_DIR / "carousel_caption.txt").write_text(
        f"TITLE ({len(tiktok_title)} chars):\n{tiktok_title}\n\nDESCRIPTION ({len(description)} chars):\n{description}",
        encoding="utf-8"
    )
    print(f"\n  Title ({len(tiktok_title)} chars): {tiktok_title}")
    print(f"  Description ({len(description)} chars): {description[:80]}...")

    if upload_enabled:
        print("\n  Uploading to TikTok (draft) + Facebook...")
        result = upload_carousel(image_paths, tiktok_title, description, cfg)
        (OUTPUT_DIR / "carousel_upload_result.json").write_text(json.dumps(result, indent=2))
    else:
        print("\n  Upload DISABLED -- images saved to output_carousel/")
        (OUTPUT_DIR / "carousel_upload_result.json").write_text(json.dumps({"skipped": True}))

    save_history(history, {
        "date":     datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "topic":    script.get("topic", ""),
        "headline": f"{script.get('headline_line1')} / {script.get('headline_line2')}",
        "run":      GITHUB_RUN_NUMBER,
    })

    print(f"\n  DONE | {script.get('topic')} | 5 slides | ~$0.40")
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
