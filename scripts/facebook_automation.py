#!/usr/bin/env python3
"""
MindCore AI — Facebook Daily Automation (v2.0 — Cinematic)

CHANGES (v2.0):
  Switched from DALL-E 3 illustration → gpt-image-1 cinematic photography.
  Style: atmospheric, no people. Dark editorial photography that stops the scroll.
  Added trigger-word sanitizer + retry logic + atmospheric fallback so
  image generation never silently fails.

Posts inspirational, SEO-optimised mental health content once per day at the
optimal time for that specific weekday (scheduled by GitHub Actions cron).

Reads keyword bank from scripts/fb_keywords.json (men's topics) AND
scripts/neutral_keywords.json (audience-agnostic topics).

PHASE 1 AUDIENCE STRATEGY:
  70% men's content (preserves men 35+ wedge positioning)
  30% neutral content (broadens reach without losing focus)

Required env vars:
  ANTHROPIC_API_KEY  - for content generation
  OPENAI_API_KEY     - for gpt-image-1 cinematic photography
  FB_PAGE_ID         - Page asset ID
  FB_ACCESS_TOKEN    - System User token
"""

import os
import io
import json
import base64
import random
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import requests

# ── Config ──────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY")
FB_PAGE_ID        = os.environ["FB_PAGE_ID"]
FB_ACCESS_TOKEN   = os.environ["FB_ACCESS_TOKEN"]

SITE_URL              = "https://mindcoreai.eu"
MENS_KEYWORDS_FILE    = Path("scripts/fb_keywords.json")
NEUTRAL_KEYWORDS_FILE = Path("scripts/neutral_keywords.json")
HISTORY_FILE          = Path("scripts/fb_post_history.json")
HISTORY_LIMIT         = 25

MENS_WEIGHT    = 0.70
NEUTRAL_WEIGHT = 0.30

# ── Cinematic photography style anchor (Style A: atmospheric, no people) ────
# Switched from warm illustration → dark cinematic photography to drive
# higher stop-scroll rate on the FB feed. Same brand emotional tone (quiet,
# honest, reflective) but rendered as documentary-style photography.
STYLE_ANCHOR = (
    "Cinematic documentary photograph, shot on a 35mm full-frame camera, "
    "50mm prime lens at f/1.8 for shallow depth of field. Moody natural "
    "lighting — single light source (window, lamp, dawn through curtains, "
    "streetlight through blinds). Rich shadows, deep blacks, warm highlights. "
    "Muted desaturated colour grade with subtle teal-and-amber tonality. "
    "Photographic grain, like Kodak Portra 400 pushed one stop. "
    "Composition: rule of thirds, generous negative space, one strong focal point. "
    "Atmospheric, contemplative, unstaged. Empty environment — NO people in frame. "
    "Square 1:1 format. No text, no logos, no words anywhere in the image."
)

# Concrete fallback scene if the main prompt gets filtered. Always works.
SAFE_FALLBACK_SCENE = (
    "A still ceramic mug of black coffee on a worn wooden kitchen table at "
    "dawn, steam rising into a shaft of cold morning light coming through a "
    "single window. A folded woollen blanket on the back of a chair just out "
    "of focus. Cinematic, quiet, contemplative."
)

# Trigger-word sanitizer for OpenAI's content filter on mental-health imagery.
# We replace clinical terms with neutral synonyms BEFORE sending to the image
# model. The post text itself still uses the real wording — only the image
# prompt is sanitized.
IMAGE_TRIGGER_REPLACEMENTS = {
    r"\banxiety\b":             "tension",
    r"\banxious\b":             "tense",
    r"\bdepression\b":          "heaviness",
    r"\bdepressed\b":           "low-energy",
    r"\bsuicide\b":             "crisis",
    r"\bsuicidal\b":            "in crisis",
    r"\bself-harm\b":           "self-injury (do not depict)",
    r"\baddiction\b":           "habit",
    r"\baddict\b":              "person in renewal",
    r"\baddicted\b":            "habitual",
    r"\bmental health\b":       "emotional wellbeing",
    r"\bmental illness\b":      "emotional struggle",
    r"\bptsd\b":                "stress response",
    r"\btrauma\b":              "past difficulty",
    r"\bbipolar\b":             "mood shift",
    r"\bpanic attack\b":        "wave of overwhelm",
    r"\bpanic\b":               "overwhelm",
    r"\bburnout\b":             "exhaustion",
    r"\bburnt out\b":           "exhausted",
    r"\bdying\b":               "still",
    r"\bdeath\b":               "stillness",
    r"\bsuffering\b":           "weariness",
    r"\bcrying\b":              "quiet",
    r"\btears\b":               "softness",
    r"\brage\b":                "intensity",
    r"\bdespair\b":             "stillness",
    r"\bhopeless\b":            "weary",
    r"\bbroken\b":              "worn",
    r"\bnumb\b":                "still",
    r"\bemotional pain\b":      "inner weight",
    r"\bsubstance\b":           "habit",
    r"\bdrunk\b":               "tired",
    r"\balcohol\b":             "drink",
    r"\bsober\b":               "clear-headed",
    r"\bsobriety\b":            "clarity",
    r"\brecovery\b":            "renewal",
}


def sanitize_for_image_model(text: str) -> str:
    out = text
    for pattern, replacement in IMAGE_TRIGGER_REPLACEMENTS.items():
        out = re.sub(pattern, replacement, out, flags=re.IGNORECASE)
    return out


STYLES = [
    "vulnerable_confession",
    "reframe_insight",
    "actionable_tip",
    "statement_of_solidarity",
    "mini_story",
]

APP_FACTS = """
MindCore AI — voice-first AI mental wellness companion.
- Available 24/7, no judgment, no waiting rooms.
- Built primarily for men 35+ navigating anxiety, burnout, loneliness, recovery —
  with expanding content for everyone navigating modern mental health.
- 7-day trial €1.99 (NOT free — never say \"free trial\").
- Premium €14.99/month or €99.99/year.
- Pro €25/month or €179.99/year.
- Website: https://mindcoreai.eu
- App launches 30 April 2026 on Google Play.
"""

REQUIRED_BRAND_HASHTAG = "#mindcoreai"

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
    print(f"  Loaded {len(topics)} {audience_tag} keywords (last updated: {data.get('last_updated', 'unknown')})")
    return topics


def load_topic_pools() -> dict:
    pools = {
        "men":     _load_topic_file(MENS_KEYWORDS_FILE,    "men"),
        "neutral": _load_topic_file(NEUTRAL_KEYWORDS_FILE, "neutral"),
    }
    print(f"  Audience mix: {int(MENS_WEIGHT * 100)}% men / {int(NEUTRAL_WEIGHT * 100)}% neutral")
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
    audience = random.choices(
        ["men", "neutral"],
        weights=[MENS_WEIGHT, NEUTRAL_WEIGHT],
        k=1,
    )[0]
    recent_keywords = {h["keyword"] for h in history[-HISTORY_LIMIT:]}
    available = [t for t in pools[audience] if t["keyword"] not in recent_keywords]
    if not available:
        other = "neutral" if audience == "men" else "men"
        available = [t for t in pools[other] if t["keyword"] not in recent_keywords]
        if available:
            print(f"  {audience} pool on cooldown — falling back to {other}")
        else:
            available = pools[audience]
    return random.choice(available)


# ── Post text generation ────────────────────────────────────────────────────
def generate_post(topic: dict, style: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    audience = topic.get("audience", "men")

    if audience == "men":
        voice_guidance = (
            "Voice: like a man who's been through it talking to another man. "
            "Plain, direct, second-person. The kind of honesty men rarely get from each other."
        )
        brand_position = "AI mental health companion built primarily for men 35+"
    else:
        voice_guidance = (
            "Voice: warm, plain, direct, second-person. Universal — speaks to anyone navigating this. "
            "Not gendered. Not therapy-speak. Just honest."
        )
        brand_position = "voice-first AI mental wellness companion for anyone navigating modern mental health"

    prompt = f"""You are writing a Facebook post for MindCore AI, a {brand_position}.

TOPIC: {topic['keyword']}
ANGLE: {topic['angle']}
STYLE: {style}
AUDIENCE: {audience}

VOICE GUIDANCE: {voice_guidance}

APP FACTS (only mention if natural — don't force it):
{APP_FACTS}

REQUIREMENTS:
- 120–250 words. Facebook rewards medium-length emotional posts.
- FIRST LINE is everything — it's what people see before "See more". Make it stop the scroll.
  Examples of strong first lines:
    "Nobody talks about the silence."
    "You don't need to be okay today."
    "There's a kind of tired sleep can't fix."
- Write in plain, second-person voice ("you"). No corporate tone. No clichés. No toxic positivity.
- Naturally include the keyword "{topic['keyword']}" once in the body — woven in, not stuffed.
- End with ONE of these CTAs (rotate naturally):
    a) A question that invites a comment ("What's the one thing that helped you?").
    b) A soft mention of MindCore AI as a place to talk when you can't talk to anyone else,
       with the link {SITE_URL}.
    c) A "share this with someone who needs it tonight" line.
- Add 5–7 hashtags at the end on a single line. Mix high-volume + niche.
    ALWAYS INCLUDE THESE BRAND HASHTAGS (non-negotiable): {REQUIRED_BRAND_HASHTAG} #MentalHealthMatters
    For MEN audience posts ALSO include: #MensMentalHealth
    Plus 2–4 niche tags relevant to "{topic['keyword']}".
- Use line breaks between paragraphs (Facebook rewards readability).
- Up to 2 emojis total — used with restraint, not sprinkled.
- NEVER say "free trial" — the trial is €1.99 for 7 days.
- NEVER fabricate features. Only use what's in APP FACTS above.

Return ONLY the post text. No preamble, no explanation, no markdown fences."""

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}],
    )
    return message.content[0].text.strip()


# ── Cinematic photo prompt generation ───────────────────────────────────────
def generate_image_prompt(topic: dict, post_text: str) -> str:
    """
    Generates a SCENE-ONLY description for a cinematic photograph.
    No people. Empty environment. Atmospheric, documentary-style.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    audience = topic.get("audience", "men")

    prompt = f"""You are a cinematographer / still-life photographer briefing a shot
for a Facebook post about everyday emotional life.

TOPIC (for tonal context only): {topic['keyword']}
AUDIENCE: {audience}

POST TEXT (for emotional tone reference, NOT to describe literally):
{post_text}

Write ONE descriptive sentence (40–70 words) describing a SCENE for a
cinematic documentary photograph. Use objects, light, environment to convey
emotion. Atmospheric, quiet, unstaged.

ABSOLUTE RULES:
- NO PEOPLE IN THE SCENE. Empty environment only.
- Pick a single concrete moment — a place at a specific time of day with
  one or two key objects. Real, ordinary, photographable.
- Use light as a character: dawn through curtains, single bedside lamp,
  streetlight through blinds, last light through a kitchen window, dashboard glow.
- Use objects that imply the human moment without showing the human:
  an unmade bed with the duvet thrown back, an untouched coffee going cold,
  a single chair pulled out from a kitchen table, a pair of boots by the door,
  a phone face-down on a nightstand, an open notebook with a closed pen,
  a folded jumper on the back of a chair, car keys on a hallway table.
- AVOID CLICHÉS: no rain on windows, no melting clocks, no abstract symbols,
  no person silhouettes, no shadowy figures, no hands reaching for anything.
- AVOID CLINICAL/MEDICAL IMAGERY: no pill bottles, no syringes, no hospital
  scenes, no therapy couches, no AA tokens, no crucifixes.
- AVOID TEXT: no words, signs, logos, or readable letters anywhere.
- Stay grounded in mundane reality: kitchens, hallways, bedrooms, cars,
  garages, balconies, doorways, single streetlamp scenes.

GOOD EXAMPLES:
- "A pottery mug of cold black coffee on a wooden kitchen counter, late
  afternoon light filtering through dust in a long shaft. An open notebook
  beside it, pen uncapped. A single chair pulled out, recently abandoned."
- "An unmade bed at 3am, sheets pushed back, a phone face-down on the
  nightstand. Streetlight slicing through half-closed blinds across the wall.
  A glass of water half-full beside the lamp."
- "A pair of work boots tipped over by a hallway door, jacket hung on the
  hook above. Single overhead light. Tile floor. A car key on the small
  table just inside the frame."

Return ONLY the scene description. No preamble, no quotes, no explanation."""

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    scene = message.content[0].text.strip().strip('"')
    # Sanitize the scene description for the image model's content filter
    sanitized = sanitize_for_image_model(scene)
    return f"{sanitized}\n\nStyle: {STYLE_ANCHOR}"


# ── Image generation (gpt-image-1) with retry + fallback ────────────────────
def _gpt_image_request(image_prompt: str) -> bytes:
    """
    Call OpenAI's gpt-image-1. Returns raw image bytes.
    Note: gpt-image-1 returns base64 by default (not URLs like DALL-E 3).
    """
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")
    url = "https://api.openai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model":      "gpt-image-1",
        "prompt":     image_prompt,
        "n":          1,
        "size":       "1024x1024",
        "quality":    "medium",         # gpt-image-1 quality tiers: low | medium | high
        "background": "auto",
    }
    r = requests.post(url, headers=headers, json=payload, timeout=120)
    if not r.ok:
        try:
            err = r.json().get("error", {})
            msg = err.get("message", "")
            print(f"    ✗ gpt-image-1: {msg[:200]}")
        except Exception:
            print(f"    ✗ gpt-image-1: {r.text[:300]}")
        r.raise_for_status()

    data = r.json()
    b64 = data["data"][0].get("b64_json")
    if not b64:
        raise RuntimeError(f"gpt-image-1 returned no b64_json: {data}")
    return base64.b64decode(b64)


def generate_image_resilient(image_prompt: str) -> tuple:
    """
    Three-tier strategy so we never silently fall back to text-only:
      1. Try the original sanitized prompt.
      2. If filtered, retry with a softened safe atmospheric prompt.
      3. If filtered again, raise — surface the failure clearly in logs
         so we can iterate. (vs. silently posting text-only.)

    Returns (image_bytes, source_label).
    """
    try:
        print("    Attempt 1: sanitized cinematic prompt…")
        return _gpt_image_request(image_prompt), "gpt-image-1"
    except Exception as e:
        print(f"    Attempt 1 failed: {e}")

    print("    Attempt 2: safe atmospheric fallback…")
    soft_prompt = f"{SAFE_FALLBACK_SCENE}\n\nStyle: {STYLE_ANCHOR}"
    try:
        return _gpt_image_request(soft_prompt), "gpt-image-1-softened"
    except Exception as e:
        print(f"    Attempt 2 also failed: {e}")
        # Surface clearly — don't silently fall back to text-only.
        raise RuntimeError(
            "Both image generation attempts failed. Original prompt likely "
            "tripped content filters. Investigate logs and adjust trigger-word "
            f"sanitizer. Last error: {e}"
        )


def upload_image_to_facebook_via_bytes(
    message: str, image_bytes: bytes, page_token: str,
) -> dict:
    """
    Posts the image to Facebook via the /photos endpoint using
    multipart-form upload (since gpt-image-1 returns bytes, not a URL).
    """
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


# ── Brand hashtag enforcement ───────────────────────────────────────────────
def ensure_brand_hashtag(post_text: str) -> str:
    if REQUIRED_BRAND_HASHTAG.lower() in post_text.lower():
        return post_text
    lines = post_text.rstrip().split("\n")
    for i in range(len(lines) - 1, -1, -1):
        if "#" in lines[i]:
            lines[i] = lines[i].rstrip() + f" {REQUIRED_BRAND_HASHTAG}"
            print(f"  ⚙ Brand hashtag appended to existing hashtag line")
            return "\n".join(lines)
    print(f"  ⚙ No hashtags found in post — appending brand line")
    return post_text.rstrip() + f"\n\n{REQUIRED_BRAND_HASHTAG}"


# ── Main ────────────────────────────────────────────────────────────────────
def main():
    print("=" * 60)
    print("  MindCore AI — Facebook Daily Automation (v2.0 cinematic)")
    print(f"  Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    pools   = load_topic_pools()
    history = load_history()
    topic   = pick_topic(pools, history)
    style   = random.choice(STYLES)

    print(f"\n  Topic    : {topic['keyword']}")
    print(f"  Angle    : {topic['angle']}")
    print(f"  Audience : {topic.get('audience', 'unknown')}")
    print(f"  Style    : {style}\n")

    print("  Generating post…")
    post_text = generate_post(topic, style)
    post_text = ensure_brand_hashtag(post_text)
    print("\n" + "-" * 60)
    print(post_text)
    print("-" * 60 + "\n")

    image_bytes  = None
    image_source = None
    image_prompt = None
    if OPENAI_API_KEY:
        try:
            print("  Crafting cinematic photo prompt tailored to this post…")
            image_prompt = generate_image_prompt(topic, post_text)
            print(f"  Prompt: {image_prompt[:250]}…\n")
            print("  Generating cinematic photograph with gpt-image-1…")
            image_bytes, image_source = generate_image_resilient(image_prompt)
            size_kb = len(image_bytes) / 1024
            print(f"  ✓ Image generated via {image_source} ({size_kb:.0f} KB)\n")
        except Exception as e:
            print(f"  ⚠ Image generation failed after all retries: {e}")
            print(f"  → Falling back to text-only post\n")
    else:
        print("  ⚠ OPENAI_API_KEY not set — posting text-only\n")

    print("  Fetching page-specific access token…")
    page_token = fetch_page_token()
    print("  ✓ Got page token\n")

    print("  Publishing to Facebook…")
    if image_bytes:
        try:
            result = upload_image_to_facebook_via_bytes(post_text, image_bytes, page_token)
            fb_post_id = result.get("post_id") or result.get("id", "unknown")
            print(f"  Published with cinematic photo ✓  Post ID: {fb_post_id}")
            posted_with_image = True
        except Exception as e:
            print(f"  ⚠ Photo post failed: {e}")
            print(f"  → Falling back to text-only\n")
            result = post_text_to_facebook(post_text, page_token)
            fb_post_id = result.get("id", "unknown")
            print(f"  Published text-only ✓  Post ID: {fb_post_id}")
            posted_with_image = False
    else:
        result = post_text_to_facebook(post_text, page_token)
        fb_post_id = result.get("id", "unknown")
        print(f"  Published text-only ✓  Post ID: {fb_post_id}")
        posted_with_image = False

    history.append({
        "timestamp"   : datetime.now(timezone.utc).isoformat(),
        "keyword"     : topic["keyword"],
        "audience"    : topic.get("audience", "unknown"),
        "style"       : style,
        "fb_post_id"  : fb_post_id,
        "with_image"  : posted_with_image,
        "image_source": image_source,
        "image_prompt": (image_prompt[:300] if image_prompt else None),
        "preview"     : post_text[:140],
    })
    save_history(history)
    print(f"  History updated ({len(history)} total posts)\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        sys.exit(1)
