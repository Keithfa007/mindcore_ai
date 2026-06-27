#!/usr/bin/env python3
"""
MindCore AI  - Facebook Daily Automation (v3.1  - Text-as-Image + 3-Pool Audience)

CHANGES (v3.1):
  Audience mix expanded from 70/30 (men/neutral) to 40/30/30 (men/female/neutral).
  Added scripts/fb_keywords_female.json keyword pool, mirrored from the female
  cinematic video pipeline's niche research (perimenopause, women's mental
  health, female AI-companion angle, women's anxiety SOS). Refreshed
  scripts/fb_keywords.json to align with the male video pipeline's niches
  (recovery, men's mental health, men's AI-companion angle, mood wellness)
  so both audience pools draw from the same SEO research that's feeding
  the cinematic videos.

  Voice prompts updated: explicit female audience guidance added, neutral
  guidance refined to truly be universal rather than male-leaning.

CHANGES (v3.0):
  Replaced cinematic gpt-image-1 photography with Pillow-rendered text-as-image
  typography graphics. Caption tone shortened to 30-80 words, conversational.

PHASE 1 AUDIENCE STRATEGY (now multi-audience):
  40% men's content    (men 35+ wedge, our anchor)
  30% women's content  (matches female video pipeline expansion)
  30% neutral content  (universal  - no gender framing)

Required env vars:
  ANTHROPIC_API_KEY  - for content + headline generation
  FB_PAGE_ID         - Page asset ID
  FB_ACCESS_TOKEN    - System User token
"""

import os
import io
import json
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import requests
from PIL import Image, ImageDraw, ImageFont, ImageFilter

# ── Config ──────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY")  # no longer used; kept for compat
FB_PAGE_ID        = os.environ["FB_PAGE_ID"]
FB_ACCESS_TOKEN   = os.environ["FB_ACCESS_TOKEN"]

SITE_URL                = "https://mindcoreai.eu"
WATERMARK_TEXT          = "mindcoreai.eu"
MENS_KEYWORDS_FILE      = Path("scripts/fb_keywords.json")
FEMALE_KEYWORDS_FILE    = Path("scripts/fb_keywords_female.json")
NEUTRAL_KEYWORDS_FILE   = Path("scripts/neutral_keywords.json")
HISTORY_FILE            = Path("scripts/fb_post_history.json")
HISTORY_LIMIT           = 25

# Audience mix  - keep the men's wedge primary but explicitly serve women + everyone.
AUDIENCE_WEIGHTS = {
    "men":     0.40,
    "female":  0.30,
    "neutral": 0.30,
}

# ── Brand palette (warm, muted  - same as IG carousels & YouTube banner) ─────
PALETTE = {
    "cream":      (250, 244, 230),
    "beige":      (236, 222, 196),
    "dusty_rose": (208, 162, 152),
    "sage":       (158, 175, 145),
    "terracotta": (180, 100, 70),
    "warm_dark":  (40, 30, 22),    # near-black for text
    "soft_dark":  (90, 75, 60),    # secondary text
}

GRADIENTS = [
    ("cream",      "beige"),
    ("cream",      "dusty_rose"),
    ("beige",      "sage"),
    ("cream",      "sage"),
    ("beige",      "terracotta"),
    ("cream",      "terracotta"),
]

IMAGE_SIZE = 1080
HEADLINE_MIN_WORDS = 6
HEADLINE_MAX_WORDS = 15
REQUIRED_BRAND_HASHTAG = "#mindcoreai"

APP_FACTS = """
MindCore AI  - voice-first AI mental wellness companion.
- Available 24/7, no judgment, no waiting rooms.
- Built primarily for men 35+ navigating anxiety, burnout, loneliness, recovery  -
  with expanding content for women and for anyone navigating modern mental health.
- 7-day trial €1.99 (NOT free  - never say \"free trial\").
- Premium €14.99/month or €99.99/year.
- Pro €25/month or €179.99/year.
- Website: https://mindcoreai.eu
- App launches 30 April 2026 on Google Play.
"""

STYLES = [
    "vulnerable_confession",
    "reframe_insight",
    "actionable_tip",
    "statement_of_solidarity",
    "mini_story",
]

HEADLINE_REFERENCE_EXAMPLES = [
    "Nobody talks about the silence.",
    "You don't need to be okay today.",
    "There's a kind of tired sleep can't fix.",
    "Acting okay is exhausting.",
    "Strong doesn't mean fine.",
    "Carrying it alone is the heaviest part.",
    "Some days, getting through is the win.",
    "You're not behind. You're tired.",
    "It's okay to not have the words yet.",
    "The brave thing is asking for help.",
]

# ── Audience-specific voice guidance ────────────────────────────────────────
VOICE_BY_AUDIENCE = {
    "men": {
        "description": "AI mental health companion built primarily for men 35+",
        "voice": (
            "Voice: like a man who's been through it talking to another man. "
            "Plain, direct, second-person. The kind of honesty men rarely get "
            "from each other. No fluff, no therapy-speak."
        ),
        "extra_hashtags": "#MensMentalHealth",
    },
    "female": {
        "description": "voice-first AI mental wellness companion for women carrying invisible weight",
        "voice": (
            "Voice: a woman who's been the one everyone leans on, finally hearing "
            "her own experience named back to her. Warm, direct, second-person. "
            "Not therapy-speak, not motivational. The quiet kind of true."
        ),
        "extra_hashtags": "#WomensMentalHealth",
    },
    "neutral": {
        "description": "voice-first AI mental wellness companion for anyone navigating modern mental health",
        "voice": (
            "Voice: warm, plain, direct, second-person. Universal  - speaks to "
            "anyone navigating this. Not gendered. Not therapy-speak. Just honest."
        ),
        "extra_hashtags": "",  # nothing extra  - brand + #MentalHealthMatters cover it
    },
}

# ── Keyword & history helpers ───────────────────────────────────────────────
def _load_topic_file(path: Path, audience_tag: str) -> list:
    if not path.exists():
        raise FileNotFoundError(f"{path} missing.")
    data = json.loads(path.read_text())
    topics = data.get("topics", [])
    if not topics:
        raise ValueError(f"{path} contains no topics.")
    for t in topics:
        t["audience"] = audience_tag
    print(f"  Loaded {len(topics):>3} {audience_tag:>7} keywords (last updated: {data.get('last_updated', 'unknown')})")
    return topics


def load_topic_pools() -> dict:
    pools = {
        "men":     _load_topic_file(MENS_KEYWORDS_FILE,    "men"),
        "female":  _load_topic_file(FEMALE_KEYWORDS_FILE,  "female"),
        "neutral": _load_topic_file(NEUTRAL_KEYWORDS_FILE, "neutral"),
    }
    weights_str = " / ".join(
        f"{int(AUDIENCE_WEIGHTS[k]*100)}% {k}" for k in ("men", "female", "neutral")
    )
    print(f"  Audience mix: {weights_str}")
    return pools


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


def pick_topic(pools: dict, history: list) -> dict:
    """
    Pick an audience by weight, then pick a topic from that pool, avoiding
    recently-used keywords. If the chosen pool is fully on cooldown, cascade
    through the remaining pools in a sensible order before giving up.
    """
    audiences = list(AUDIENCE_WEIGHTS.keys())
    weights   = [AUDIENCE_WEIGHTS[a] for a in audiences]
    audience  = random.choices(audiences, weights=weights, k=1)[0]

    recent_keywords = {h["keyword"] for h in history[-HISTORY_LIMIT:]}
    available = [t for t in pools[audience] if t["keyword"] not in recent_keywords]

    if not available:
        # Cascade: try the other pools rather than repeat a recent keyword.
        cascade_order = [a for a in audiences if a != audience]
        random.shuffle(cascade_order)
        for other in cascade_order:
            available = [t for t in pools[other] if t["keyword"] not in recent_keywords]
            if available:
                print(f"  {audience} pool on cooldown  - falling back to {other}")
                break
        if not available:
            # Everything's on cooldown  - accept a repeat from the originally chosen audience.
            print(f"  All pools on cooldown  - picking from {audience} anyway")
            available = pools[audience]

    return random.choice(available)


# ── Headline generation (the BIG text on the image) ────────────────────────
def generate_headline(topic: dict, style: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    examples_block = "\n".join(f'  - "{h}"' for h in HEADLINE_REFERENCE_EXAMPLES)
    audience = topic.get("audience", "neutral")

    # Even women's and men's keyword pools should produce universal-pronoun
    # headlines, because the image is read by everyone scrolling FB. The
    # *body* of the post can lean audience-coded; the headline stays open.
    audience_note = (
        "Universal pronouns ('you', 'anyone', 'someone'). The headline must "
        "feel like 'that's me' on first read for anyone scrolling  - even "
        "though the post's audience leans "
        f"{audience}. Do NOT mention gender in the headline. The headline "
        "is the image  - everyone scrolling will read it."
    )

    prompt = f"""You are writing the BIG TEXT that will be printed across an
image for a Facebook post about everyday emotional life. This text is what
people see in the feed  - it must stop the scroll on its own.

TOPIC: {topic['keyword']}
ANGLE: {topic['angle']}
STYLE: {style}
AUDIENCE: {audience_note}

REFERENCE EXAMPLES (the register we want  - plain spoken truth, not poetry):
{examples_block}

RULES:
- Between {HEADLINE_MIN_WORDS} and {HEADLINE_MAX_WORDS} words. Shorter is stronger.
- One sentence (or two very short ones). Plain, direct, recognisable.
- Universal pronouns  - 'you', 'anyone', 'someone'. Never 'men' or 'women' explicitly.
- The reader should think 'that's me' on first read.
- NO poetry. NO metaphors. NO clever wordplay. Just one true sentence.
- NO clinical jargon (no 'mental illness', 'depression', 'anxiety disorder').
- AVOID anything that sounds like it's romanticising self-harm or suicide.
  ❌ "close to the edge", "can't take it anymore", "the end", "give up", "ready to go"
  ✅ "carrying it alone", "tired of pretending", "everything feels heavy"
- Must work as huge bold text on a square image.


WRITING STYLE (MANDATORY):
- NEVER use em dashes. Use commas, periods, or separate sentences instead.
- NEVER use these AI-tell words: "delve", "tapestry", "landscape", "realm", "navigate", "leverage", "foster", "cultivate", "embark", "comprehensive", "multifaceted", "ever-evolving", "game-changer", "unlock", "unleash", "empower", "supercharge", "revolutionize", "it's important to note", "it's worth noting", "in today's world", "in today's fast-paced world", "harness", "pivotal", "seasoned", "cutting-edge", "spearhead".
- Write like a real person. Vary sentence length. No corporate jargon or motivational-poster tone.
- Prefer simple words: "help" not "facilitate", "use" not "utilize", "start" not "commence".

Return ONLY the headline text. No quotes, no preamble, no explanation."""

    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=120,
        messages=[{"role": "user", "content": prompt}],
    )
    headline = msg.content[0].text.strip().strip('"').strip("'").strip()
    headline = " ".join(headline.split())
    words = headline.split()
    if len(words) > HEADLINE_MAX_WORDS + 2:
        headline = " ".join(words[:HEADLINE_MAX_WORDS])
    return headline


# ── Caption generation (the conversational text BELOW the image) ───────────
def generate_caption(topic: dict, style: str, headline: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    audience = topic.get("audience", "neutral")
    voice_pack = VOICE_BY_AUDIENCE.get(audience, VOICE_BY_AUDIENCE["neutral"])

    cta_options = (
        "  a) A short question that invites a comment "
        '("anyone else?", "what helped you?", "do you get this?").\n'
        "  b) A soft mention of MindCore AI as a place to talk when you "
        "can't talk to anyone else  - keep it casual, one sentence  - "
        f"with the link {SITE_URL}.\n"
        '  c) A "share this with someone who needs it tonight" line.'
    )

    extra_tag_line = (
        f"    For this {audience}-audience post also include: {voice_pack['extra_hashtags']}"
        if voice_pack["extra_hashtags"]
        else f"    No audience-specific tag for neutral posts  - keep the set universal."
    )

    prompt = f"""You are writing the caption that sits BELOW the image on Facebook.
The image already shows this big text: "{headline}"

The caption should NOT repeat the image text. It expands or adds a personal beat.

TOPIC: {topic['keyword']}
ANGLE: {topic['angle']}
STYLE: {style}
AUDIENCE: {audience}

VOICE GUIDANCE: {voice_pack['voice']}

APP FACTS (only mention if it fits naturally  - never force it):
{APP_FACTS}

GENERAL RULES (this is the most important part):
- 30 to 80 words MAX. Shorter is better.
- Tone: a friend texting you, NOT a brand posting. Conversational, slightly
  loose. Lowercase is fine. Broken sentences are fine. One emoji at the end
  is fine if it fits naturally (🫶 ☕ 💙 🙏  - never more than one).
- DO NOT sound like a magazine column. NO polished editorial prose.
- NO toxic positivity. NO "you got this!". NO "stay strong queen/king".
- Speak in second person ("you") or universal ("we"). For audience-coded
  posts you may use 'as a woman' or 'as a man' if it fits naturally  - but
  never in a way that excludes the other.
- First line still has to hook  - first ~12 words are visible before truncation.
- End with ONE of these CTAs (pick whichever fits the post best):
{cta_options}
- 4 to 6 hashtags at the very end on a single line.
    ALWAYS INCLUDE: {REQUIRED_BRAND_HASHTAG} #MentalHealthMatters
{extra_tag_line}
    Plus 1-2 niche tags relevant to "{topic['keyword']}".

NEVER:
- NEVER say "free trial"  - the trial is €1.99 for 7 days.
- NEVER use "close to the edge", "can't go on", "end it", or any suicidal-
  ideation flavoured phrasing.
- NEVER fabricate features. Only use APP FACTS above.


WRITING STYLE (MANDATORY):
- NEVER use em dashes. Use commas, periods, or separate sentences instead.
- NEVER use these AI-tell words: "delve", "tapestry", "landscape", "realm", "navigate", "leverage", "foster", "cultivate", "embark", "comprehensive", "multifaceted", "ever-evolving", "game-changer", "unlock", "unleash", "empower", "supercharge", "revolutionize", "it's important to note", "it's worth noting", "in today's world", "in today's fast-paced world", "harness", "pivotal", "seasoned", "cutting-edge", "spearhead".
- Write like a real person. Vary sentence length. No corporate jargon or motivational-poster tone.
- Prefer simple words: "help" not "facilitate", "use" not "utilize", "start" not "commence".

Return ONLY the caption text. No preamble, no markdown, no explanation."""

    msg = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=500,
        messages=[{"role": "user", "content": prompt}],
    )
    return msg.content[0].text.strip()


# ── Brand hashtag enforcement ───────────────────────────────────────────────
def ensure_brand_hashtag(caption: str) -> str:
    if REQUIRED_BRAND_HASHTAG.lower() in caption.lower():
        return caption
    lines = caption.rstrip().split("\n")
    for i in range(len(lines) - 1, -1, -1):
        if "#" in lines[i]:
            lines[i] = lines[i].rstrip() + f" {REQUIRED_BRAND_HASHTAG}"
            print(f"  ⚙ Brand hashtag appended to existing hashtag line")
            return "\n".join(lines)
    print(f"  ⚙ No hashtags found in caption  - appending brand line")
    return caption.rstrip() + f"\n\n{REQUIRED_BRAND_HASHTAG}"


# ── Image rendering (Pillow, text-as-image typography) ──────────────────────
def _find_font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates_bold = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSansBold.ttf",
    ]
    candidates_reg = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
        "/usr/share/fonts/truetype/freefont/FreeSans.ttf",
    ]
    for p in (candidates_bold if bold else candidates_reg):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()


def _wrap_lines(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> list:
    words = text.split()
    lines, line = [], ""
    for w in words:
        test = f"{line} {w}".strip()
        if draw.textlength(test, font=font) <= max_width:
            line = test
        else:
            if line:
                lines.append(line)
            line = w
    if line:
        lines.append(line)
    return lines


def _fit_font_size(draw: ImageDraw.ImageDraw, text: str, max_width: int,
                   max_height: int, start_size: int = 130, min_size: int = 60) -> tuple:
    size = start_size
    while size >= min_size:
        font = _find_font(size, bold=True)
        lines = _wrap_lines(draw, text, font, max_width)
        line_height = int(size * 1.15)
        block_height = line_height * len(lines)
        widest = max((draw.textlength(ln, font=font) for ln in lines), default=0)
        if block_height <= max_height and widest <= max_width:
            return font, lines, line_height
        size -= 6
    font = _find_font(min_size, bold=True)
    lines = _wrap_lines(draw, text, font, max_width)
    return font, lines, int(min_size * 1.15)


def render_text_image(headline: str) -> bytes:
    top_key, bottom_key = random.choice(GRADIENTS)
    c_top = PALETTE[top_key]
    c_bot = PALETTE[bottom_key]

    img = Image.new("RGB", (IMAGE_SIZE, IMAGE_SIZE), c_top)
    draw = ImageDraw.Draw(img)
    for y in range(IMAGE_SIZE):
        t = y / IMAGE_SIZE
        r = int(c_top[0] * (1 - t) + c_bot[0] * t)
        g = int(c_top[1] * (1 - t) + c_bot[1] * t)
        b = int(c_top[2] * (1 - t) + c_bot[2] * t)
        draw.line([(0, y), (IMAGE_SIZE, y)], fill=(r, g, b))

    blob_layer = Image.new("RGBA", (IMAGE_SIZE, IMAGE_SIZE), (0, 0, 0, 0))
    bd = ImageDraw.Draw(blob_layer)
    accent_key = random.choice(["dusty_rose", "sage", "terracotta", "beige"])
    accent = PALETTE[accent_key] + (random.randint(28, 50),)
    bx, by = random.randint(-180, 260), random.randint(-180, 260)
    bd.ellipse([bx, by, bx + 640, by + 640], fill=accent)
    blob_layer = blob_layer.filter(ImageFilter.GaussianBlur(radius=130))
    img = Image.alpha_composite(img.convert("RGBA"), blob_layer).convert("RGB")
    draw = ImageDraw.Draw(img)

    margin = 90
    text_max_w = IMAGE_SIZE - 2 * margin
    text_max_h = IMAGE_SIZE - 2 * margin - 60

    font, lines, line_height = _fit_font_size(
        draw, headline, text_max_w, text_max_h, start_size=140, min_size=64
    )
    block_h = line_height * len(lines)
    y_start = (IMAGE_SIZE - block_h) // 2
    text_colour = PALETTE["warm_dark"]
    for i, ln in enumerate(lines):
        w = draw.textlength(ln, font=font)
        x = (IMAGE_SIZE - w) // 2
        y = y_start + i * line_height
        draw.text((x, y), ln, font=font, fill=text_colour)

    wm_font = _find_font(28, bold=True)
    wm_w = draw.textlength(WATERMARK_TEXT, font=wm_font)
    wm_x = IMAGE_SIZE - wm_w - 40
    wm_y = IMAGE_SIZE - 60
    draw.text((wm_x + 1, wm_y + 1), WATERMARK_TEXT, font=wm_font, fill=(255, 255, 255, 160))
    draw.text((wm_x, wm_y), WATERMARK_TEXT, font=wm_font, fill=PALETTE["terracotta"])

    out = io.BytesIO()
    img.save(out, format="JPEG", quality=92, optimize=True)
    return out.getvalue()


# ── Facebook Graph API ──────────────────────────────────────────────────────
def fetch_page_token() -> str:
    url = "https://graph.facebook.com/v21.0/me/accounts"
    params = {"access_token": FB_ACCESS_TOKEN, "fields": "id,name,access_token,tasks"}
    r = requests.get(url, params=params, timeout=30)
    if not r.ok:
        try:
            err = r.json().get("error", {})
            print(f"  ✗ /me/accounts error: {err.get('message')}")
        except Exception:
            print(f"  ✗ /me/accounts error: {r.text[:500]}")
        r.raise_for_status()
    pages = r.json().get("data", [])
    print(f"  /me/accounts returned {len(pages)} page(s)")
    for page in pages:
        if str(page.get("id")) == str(FB_PAGE_ID):
            tasks = page.get("tasks", [])
            print(f"  Matched page: {page.get('name')} (tasks: {', '.join(tasks)})")
            page_token = page.get("access_token")
            if not page_token:
                raise RuntimeError("Page found but no access_token returned.")
            return page_token
    raise RuntimeError(
        f"Page ID {FB_PAGE_ID} not found in System User's accessible pages. "
        f"Available IDs: {[p.get('id') for p in pages]}"
    )


def upload_image_to_facebook_via_bytes(
    message: str, image_bytes: bytes, page_token: str,
) -> dict:
    url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/photos"
    files = {"source": ("mindcore_fb_image.jpg", image_bytes, "image/jpeg")}
    data  = {"caption": message, "access_token": page_token}
    r = requests.post(url, data=data, files=files, timeout=120)
    if not r.ok:
        try:
            err = r.json().get("error", {})
            print(
                f"  ✗ Facebook /photos error: {err.get('message')} "
                f"| code={err.get('code')} | subcode={err.get('error_subcode')}"
            )
        except Exception:
            print(f"  ✗ Facebook /photos error: {r.text[:500]}")
        r.raise_for_status()
    return r.json()


def post_text_to_facebook(message: str, page_token: str) -> dict:
    url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/feed"
    payload = {"message": message, "access_token": page_token}
    r = requests.post(url, data=payload, timeout=30)
    if not r.ok:
        try:
            err = r.json().get("error", {})
            print(f"  ✗ Facebook /feed error: {err.get('message')}")
        except Exception:
            print(f"  ✗ Facebook /feed error: {r.text[:500]}")
        r.raise_for_status()
    return r.json()


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  MindCore AI  - Facebook Daily Automation (v3.1 text-as-image + 3-pool)")
    print(f"  Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    pools   = load_topic_pools()
    history = load_history()
    topic   = pick_topic(pools, history)
    style   = random.choice(STYLES)

    print(f"\n  Topic    : {topic['keyword']}")
    print(f"  Angle    : {topic['angle']}")
    print(f"  Audience : {topic.get('audience', 'unknown')}")
    if 'niche' in topic:
        print(f"  Niche    : {topic['niche']}")
    print(f"  Style    : {style}\n")

    print("  Generating headline (the big on-image text)…")
    headline = generate_headline(topic, style)
    print(f"  Headline : {headline}\n")

    print("  Generating conversational caption…")
    caption = generate_caption(topic, style, headline)
    caption = ensure_brand_hashtag(caption)
    print("\n" + "-" * 60)
    print(caption)
    print("-" * 60 + "\n")

    print("  Rendering text-as-image typography graphic…")
    try:
        image_bytes = render_text_image(headline)
        size_kb = len(image_bytes) / 1024
        print(f"  ✓ Image rendered ({size_kb:.0f} KB)\n")
        image_ok = True
    except Exception as e:
        print(f"  ⚠ Image render failed: {e}")
        print(f"  → Falling back to text-only post\n")
        image_bytes = None
        image_ok = False

    print("  Fetching page-specific access token…")
    page_token = fetch_page_token()
    print("  ✓ Got page token\n")

    print("  Publishing to Facebook…")
    if image_ok and image_bytes is not None:
        try:
            result = upload_image_to_facebook_via_bytes(caption, image_bytes, page_token)
            fb_post_id = result.get("post_id") or result.get("id", "unknown")
            print(f"  Published with text-as-image ✓  Post ID: {fb_post_id}")
            posted_with_image = True
        except Exception as e:
            print(f"  ⚠ Photo post failed: {e}")
            print(f"  → Falling back to text-only\n")
            result = post_text_to_facebook(caption, page_token)
            fb_post_id = result.get("id", "unknown")
            print(f"  Published text-only ✓  Post ID: {fb_post_id}")
            posted_with_image = False
    else:
        result = post_text_to_facebook(caption, page_token)
        fb_post_id = result.get("id", "unknown")
        print(f"  Published text-only ✓  Post ID: {fb_post_id}")
        posted_with_image = False

    history.append({
        "timestamp"  : datetime.now(timezone.utc).isoformat(),
        "keyword"    : topic["keyword"],
        "audience"   : topic.get("audience", "unknown"),
        "niche"      : topic.get("niche"),
        "style"      : style,
        "format"     : "text_as_image",
        "headline"   : headline,
        "fb_post_id" : fb_post_id,
        "with_image" : posted_with_image,
        "preview"    : caption[:140],
    })
    save_history(history)
    print(f"  History updated ({len(history)} total posts)\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        sys.exit(1)
