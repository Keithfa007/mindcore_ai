#!/usr/bin/env python3
"""
MindCore AI — Instagram Daily Carousel Automation

Generates a 7-slide educational carousel each day at the optimal IG time and
publishes it via Upload-Post (which handles the Meta Graph API plumbing).

Format is rotated through 6 proven IG carousel archetypes for the men's mental
health niche (signs/reframe/myth-bust/how-to/truth-bomb/comparison). Reads the
format bank from scripts/ig_formats.json and the same keyword bank as the FB
pipeline (scripts/fb_keywords.json) so topics stay aligned across platforms.

Design: warm calm minimal illustrations (DALL-E 3 with brand-locked style anchor)
overlaid with text rendered server-side via Pillow, since DALL-E renders text
poorly. Output is 1080x1080 JPEG per slide.

Graceful degradation: if image generation fails, the run skips IG entirely
rather than posting a broken carousel. The FB pipeline is unaffected.

Required env vars:
  ANTHROPIC_API_KEY     - content & format selection
  OPENAI_API_KEY        - DALL-E 3 backgrounds
  UPLOADPOST_API_KEY    - Upload-Post account API key
  UPLOADPOST_USER       - the IG profile name configured in Upload-Post (usually 'mybrand' or your project slug)
"""

import os
import io
import json
import random
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Config ──────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
OPENAI_API_KEY     = os.environ["OPENAI_API_KEY"]
UPLOADPOST_API_KEY = os.environ["UPLOADPOST_API_KEY"]
UPLOADPOST_USER    = os.environ.get("UPLOADPOST_USER", "mindcoreai")

KEYWORDS_FILE = Path("scripts/fb_keywords.json")          # shared with FB pipeline
FORMATS_FILE  = Path("scripts/ig_formats.json")
HISTORY_FILE  = Path("scripts/ig_post_history.json")
WORK_DIR      = Path("/tmp/ig_carousel")

SLIDE_COUNT      = 7
SLIDE_SIZE       = 1080  # square 1:1
HISTORY_LIMIT    = 25     # don't reuse a topic until 25 posts have passed
FORMAT_HISTORY_LIMIT = 4  # don't reuse a format within last 4 posts

SITE_URL = "https://mindcoreai.eu"

# ── Brand visual style anchor (matches FB pipeline) ─────────────────────
STYLE_ANCHOR = (
    "Calm, minimal editorial illustration. Warm muted palette: soft beige, "
    "dusty rose, sage green, terracotta, cream. Soft natural lighting. "
    "Hand-drawn quality with subtle texture. Lots of negative space — leave "
    "the upper third or one whole side relatively empty so text can be added. "
    "Quiet, contemplative mood. No text, no logos, no words anywhere in the image. "
    "If people appear, show them in soft silhouette or from behind — never close-up faces. "
    "Square 1:1 composition."
)

APP_FACTS = """
MindCore AI — voice-first AI mental health companion.
- Available 24/7, no judgment, no waiting rooms.
- Built for men 35+, recovery, anxiety, burnout, loneliness.
- 7-day trial €1.99 (NOT free — never say "free trial").
- Premium €14.99/month. Pro €25/month.
- Website: https://mindcoreai.eu
"""

# ── Helpers: load data, history ─────────────────────────────────────────
def load_json(path: Path):
    if not path.exists():
        raise FileNotFoundError(f"{path} missing")
    return json.loads(path.read_text())

def load_history() -> list:
    if HISTORY_FILE.exists():
        try:
            return json.loads(HISTORY_FILE.read_text())
        except Exception:
            return []
    return []

def save_history(history: list) -> None:
    HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    HISTORY_FILE.write_text(json.dumps(history[-200:], indent=2))

def pick_topic(topics: list, history: list) -> dict:
    recent = {h["keyword"] for h in history[-HISTORY_LIMIT:]}
    available = [t for t in topics if t["keyword"] not in recent]
    return random.choice(available or topics)

def pick_format(formats: list, history: list) -> dict:
    recent = {h.get("format") for h in history[-FORMAT_HISTORY_LIMIT:]}
    available = [f for f in formats if f["id"] not in recent]
    return random.choice(available or formats)


# ── Step 1: generate carousel content with Claude ───────────────────────
def generate_carousel_content(topic: dict, fmt: dict) -> dict:
    """Returns dict with: hook, slides (list of {title, body}), caption."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""You are writing an Instagram carousel post for MindCore AI, an AI mental
health companion app for men 35+. Today's post must follow this format:

FORMAT: {fmt['name']}
FORMAT GUIDE: {fmt['description']}
SLIDE PATTERN: {fmt['slide_pattern']}
HOOK STYLE EXAMPLES: {' | '.join(fmt['examples'])}

TOPIC SEED: {topic['keyword']}
ANGLE: {topic['angle']}

APP FACTS (for the final CTA slide and caption):
{APP_FACTS}

CAROUSEL STRUCTURE — EXACTLY {SLIDE_COUNT} slides:
- Slide 1: HOOK. Big, scroll-stopping. Max 8 words. Title only.
- Slides 2 to {SLIDE_COUNT-1}: ONE concept per slide, following the SLIDE PATTERN above.
  Each has a short title (3-6 words) and a body (1-2 sentences, max 25 words total).
- Slide {SLIDE_COUNT}: CTA. Title: "Save this. Send to a friend who needs it."
  Body: "24/7 voice-first mental health support — link in bio. 🔗"

VOICE:
- Plain, direct, second-person ("you").
- Like a man who's been through it talking to a friend, not a therapist or marketer.
- No clichés, no corporate tone, no toxic positivity.
- Concrete language. Use specific everyday situations (the car after work, 3am, dinner table).

ALSO WRITE A CAPTION (separate from slides) for the post:
- 100-180 words.
- First 125 chars must work as a standalone preview before "... more" truncation.
- Expand the carousel's theme without just summarising it. Add a single insight or story beat.
- End with: "→ Link in bio for MindCore AI. 7-day trial €1.99."
- Then on a NEW LINE, 10 hashtags. Always include #MensMentalHealth #MentalHealthMatters.
  Plus 8 niche tags relevant to {topic['keyword']}. No spaces between # and word. No commas.

Return ONLY valid JSON in this exact shape, no markdown fences, no preamble:

{{
  "hook": "slide 1 title",
  "slides": [
    {{"title": "slide 2 title", "body": "slide 2 body"}},
    {{"title": "slide 3 title", "body": "slide 3 body"}},
    {{"title": "slide 4 title", "body": "slide 4 body"}},
    {{"title": "slide 5 title", "body": "slide 5 body"}},
    {{"title": "slide 6 title", "body": "slide 6 body"}}
  ],
  "cta_title": "Save this. Send to a friend who needs it.",
  "cta_body": "24/7 voice-first mental health support — link in bio. 🔗",
  "caption": "the full IG caption with hashtags on a final line"
}}"""

    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    # Strip code fences if Claude adds them despite the instruction
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    # Find first balanced JSON object
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON in carousel content response")
    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                data = json.loads(text[start:i+1])
                break
    else:
        raise ValueError("Unterminated JSON in carousel content response")

    if len(data.get("slides", [])) != SLIDE_COUNT - 2:
        raise ValueError(f"Expected {SLIDE_COUNT-2} middle slides, got {len(data.get('slides', []))}")
    return data


# ── Step 2: generate scene prompts for each slide ────────────────────────
def generate_scene_prompts(content: dict, topic: dict) -> list:
    """Return one DALL-E prompt per slide. Slide 1 and last slide are softer/wider."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    slide_briefs = [
        f"Slide 1 (cover): {content['hook']}",
    ] + [
        f"Slide {i+2}: {s['title']} — {s['body']}"
        for i, s in enumerate(content['slides'])
    ] + [
        f"Slide {SLIDE_COUNT} (CTA): {content['cta_title']}",
    ]

    prompt = f"""You are an art director. For each Instagram carousel slide below, write a
40-70 word scene description for an editorial illustration. The scenes should
flow as a sequence — different but tonally coherent.

TOPIC: {topic['keyword']}
FORMAT: educational mental-health carousel for men 35+

SLIDES:
{chr(10).join(slide_briefs)}

RULES:
- Pick a concrete moment (a kitchen at dawn, a man's hands on a coffee cup, an empty park bench, light through curtains).
- NO close-up faces. People in silhouette, from behind, or just hands/objects.
- NO clichés (head in hands, rain on windows, person under cloud).
- Avoid showing any text, words, signs, or logos in the image.
- Slides 1 and {SLIDE_COUNT} should have especially strong negative space (top third empty) since they get largest text overlays.
- Each scene should be different from the others.

Return EXACTLY {SLIDE_COUNT} scene descriptions as a JSON array of strings.
Return ONLY the JSON array, no preamble, no markdown:

["scene 1", "scene 2", ..., "scene {SLIDE_COUNT}"]"""

    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=1500,
        messages=[{"role": "user", "content": prompt}],
    )
    text = msg.content[0].text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1:
        raise ValueError("No JSON array in scene prompts response")
    scenes = json.loads(text[start:end+1])
    if len(scenes) != SLIDE_COUNT:
        raise ValueError(f"Expected {SLIDE_COUNT} scenes, got {len(scenes)}")
    return [f"{s}\n\nStyle: {STYLE_ANCHOR}" for s in scenes]


# ── Step 3: DALL-E backgrounds ───────────────────────────────────────────
def generate_dalle_image(prompt: str) -> bytes:
    url = "https://api.openai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model":   "dall-e-3",
        "prompt":  prompt,
        "n":       1,
        "size":    "1024x1024",
        "quality": "standard",
        "style":   "natural",
    }
    r = requests.post(url, headers=headers, json=payload, timeout=90)
    if not r.ok:
        try:
            err = r.json().get("error", {})
            print(f"  ✗ DALL-E error: {err.get('message')}")
        except Exception:
            print(f"  ✗ DALL-E error: {r.text[:300]}")
        r.raise_for_status()
    img_url = r.json()["data"][0]["url"]
    img_bytes = requests.get(img_url, timeout=60).content
    return img_bytes


# ── Step 4: text overlay with Pillow ───────────────────────────────────────
def _font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    """Find a system font on the GitHub runner (Ubuntu)."""
    candidates_bold = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ]
    candidates_reg = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
    ]
    for p in (candidates_bold if bold else candidates_reg):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _wrap(draw: ImageDraw.ImageDraw, text: str, font, max_w: int) -> list:
    words = text.split()
    lines, line = [], ""
    for w in words:
        test = f"{line} {w}".strip()
        if draw.textlength(test, font=font) <= max_w:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def compose_slide(
    bg_bytes: bytes,
    title: str,
    body: str = "",
    slide_number: int = 0,
    is_cover: bool = False,
    is_cta: bool = False,
) -> bytes:
    """Composite background + warm overlay + text. Returns JPEG bytes."""
    bg = Image.open(io.BytesIO(bg_bytes)).convert("RGB")
    # Resize/crop to square 1080
    bg = bg.resize((SLIDE_SIZE, SLIDE_SIZE), Image.LANCZOS)

    # Soft top gradient for text legibility
    overlay = Image.new("RGBA", (SLIDE_SIZE, SLIDE_SIZE), (0, 0, 0, 0))
    draw_o = ImageDraw.Draw(overlay)
    # Cream wash on top half for readability
    for y in range(SLIDE_SIZE // 2):
        alpha = int(180 * (1 - y / (SLIDE_SIZE // 2)) ** 1.5)
        draw_o.line([(0, y), (SLIDE_SIZE, y)], fill=(250, 244, 230, alpha))

    composed = Image.alpha_composite(bg.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(composed)

    text_color = (60, 47, 37)        # warm dark brown
    accent_color = (180, 100, 70)    # terracotta

    margin = 90
    max_w = SLIDE_SIZE - 2 * margin

    if is_cover:
        title_font = _font(86, bold=True)
        title_lines = _wrap(draw, title, title_font, max_w)
        line_h = title_font.size + 18
        total_h = len(title_lines) * line_h
        y = margin + 40
        for ln in title_lines:
            w = draw.textlength(ln, font=title_font)
            draw.text(((SLIDE_SIZE - w) / 2, y), ln, font=title_font, fill=text_color)
            y += line_h
        # Small "swipe →" cue at bottom
        cue_font = _font(34, bold=True)
        cue = "swipe →"
        cw = draw.textlength(cue, font=cue_font)
        draw.text(((SLIDE_SIZE - cw) / 2, SLIDE_SIZE - 130), cue, font=cue_font, fill=accent_color)

    elif is_cta:
        title_font = _font(64, bold=True)
        body_font = _font(36)
        title_lines = _wrap(draw, title, title_font, max_w)
        body_lines = _wrap(draw, body, body_font, max_w)
        title_h = title_font.size + 14
        body_h = body_font.size + 10
        block_h = len(title_lines) * title_h + 30 + len(body_lines) * body_h
        y = (SLIDE_SIZE - block_h) // 2
        for ln in title_lines:
            w = draw.textlength(ln, font=title_font)
            draw.text(((SLIDE_SIZE - w) / 2, y), ln, font=title_font, fill=text_color)
            y += title_h
        y += 20
        for ln in body_lines:
            w = draw.textlength(ln, font=body_font)
            draw.text(((SLIDE_SIZE - w) / 2, y), ln, font=body_font, fill=text_color)
            y += body_h

    else:
        # Numbered middle slide
        num_font = _font(120, bold=True)
        title_font = _font(56, bold=True)
        body_font = _font(38)

        num_text = str(slide_number)
        draw.text((margin, margin - 20), num_text, font=num_font, fill=accent_color)

        y = margin + 130
        title_lines = _wrap(draw, title, title_font, max_w)
        for ln in title_lines:
            draw.text((margin, y), ln, font=title_font, fill=text_color)
            y += title_font.size + 14
        y += 30
        body_lines = _wrap(draw, body, body_font, max_w)
        for ln in body_lines:
            draw.text((margin, y), ln, font=body_font, fill=text_color)
            y += body_font.size + 12

    out = io.BytesIO()
    composed.save(out, format="JPEG", quality=92, optimize=True)
    return out.getvalue()


# ── Step 5: Upload-Post posting ─────────────────────────────────────────────
def post_carousel_via_uploadpost(image_paths: list, caption: str) -> dict:
    """
    Upload-Post /api/upload_photos:
      - photos[] = multiple files for a carousel
      - caption  = post text
      - platform[] = ['instagram']
      - user     = the configured profile slug in Upload-Post
    """
    url = "https://api.upload-post.com/api/upload_photos"
    headers = {"Authorization": f"Apikey {UPLOADPOST_API_KEY}"}

    files = []
    open_files = []
    for i, p in enumerate(image_paths):
        fh = open(p, "rb")
        open_files.append(fh)
        files.append(("photos[]", (f"slide_{i+1}.jpg", fh, "image/jpeg")))

    data = {
        "caption":    caption,
        "user":       UPLOADPOST_USER,
        "platform[]": "instagram",
    }

    try:
        r = requests.post(url, headers=headers, data=data, files=files, timeout=180)
    finally:
        for fh in open_files:
            try:
                fh.close()
            except Exception:
                pass

    if not r.ok:
        try:
            print(f"  ✗ Upload-Post error: {r.json()}")
        except Exception:
            print(f"  ✗ Upload-Post error (non-JSON): {r.text[:500]}")
        r.raise_for_status()

    return r.json()


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  MindCore AI — Instagram Daily Carousel")
    print(f"  Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    WORK_DIR.mkdir(parents=True, exist_ok=True)

    keywords = load_json(KEYWORDS_FILE).get("topics", [])
    formats  = load_json(FORMATS_FILE).get("formats", [])
    history  = load_history()

    if not keywords or not formats:
        raise RuntimeError("Keywords or formats file empty")

    topic = pick_topic(keywords, history)
    fmt   = pick_format(formats, history)
    print(f"\n  Topic   : {topic['keyword']}")
    print(f"  Angle   : {topic['angle']}")
    print(f"  Format  : {fmt['name']} ({fmt['id']})\n")

    print("  Generating carousel content with Claude…")
    content = generate_carousel_content(topic, fmt)
    print(f"  Hook    : {content['hook']}")
    print(f"  Slides  : {len(content['slides'])} middle + 1 cover + 1 CTA = {SLIDE_COUNT} total\n")

    print("  Generating scene prompts…")
    scene_prompts = generate_scene_prompts(content, topic)
    print(f"  ✓ {len(scene_prompts)} scene prompts ready\n")

    print(f"  Generating {SLIDE_COUNT} DALL-E backgrounds (this is the slow step — ~60s)…")
    image_paths = []
    for i, sp in enumerate(scene_prompts):
        print(f"    Slide {i+1}/{SLIDE_COUNT}…")
        bg = generate_dalle_image(sp)

        if i == 0:
            jpg = compose_slide(bg, content["hook"], is_cover=True)
        elif i == SLIDE_COUNT - 1:
            jpg = compose_slide(bg, content["cta_title"], content["cta_body"], is_cta=True)
        else:
            slide = content["slides"][i - 1]
            jpg = compose_slide(bg, slide["title"], slide["body"], slide_number=i + 1)

        path = WORK_DIR / f"slide_{i+1:02d}.jpg"
        path.write_bytes(jpg)
        image_paths.append(str(path))
    print(f"  ✓ All {SLIDE_COUNT} slides composed\n")

    print("  Posting carousel to Instagram via Upload-Post…")
    print(f"  Caption preview: {content['caption'][:140]}…\n")
    result = post_carousel_via_uploadpost(image_paths, content["caption"])

    job_id = result.get("job_id") or result.get("id") or "unknown"
    print(f"  Published ✓  Upload-Post job: {job_id}\n")

    history.append({
        "timestamp" : datetime.now(timezone.utc).isoformat(),
        "keyword"   : topic["keyword"],
        "format"    : fmt["id"],
        "hook"      : content["hook"],
        "job_id"    : job_id,
    })
    save_history(history)
    print(f"  History updated ({len(history)} total carousels)\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        sys.exit(1)
