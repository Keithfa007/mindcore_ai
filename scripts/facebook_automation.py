#!/usr/bin/env python3
"""
MindCore AI — Facebook Daily Automation
Posts inspirational, SEO-optimised mental health content once per day at the
optimal time for that specific weekday (scheduled by GitHub Actions cron).

Each post includes a custom DALL-E 3 illustration tailored to the post's
emotional moment, using a locked brand style (calm, minimal, warm tones).

Reads keyword bank from scripts/fb_keywords.json — refreshed monthly by
refresh_keywords.py.

Required env vars:
  ANTHROPIC_API_KEY  - for content generation
  OPENAI_API_KEY     - for DALL-E 3 image generation
  FB_PAGE_ID         - Page asset ID (Graph API ID, not public profile.php ID)
  FB_ACCESS_TOKEN    - System User token
"""

import os
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import requests

# ── Config ──────────────────────────────────────────────────────────────────
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY")  # optional — falls back to text-only
FB_PAGE_ID        = os.environ["FB_PAGE_ID"]
FB_ACCESS_TOKEN   = os.environ["FB_ACCESS_TOKEN"]

SITE_URL          = "https://mindcoreai.eu"
KEYWORDS_FILE     = Path("scripts/fb_keywords.json")
HISTORY_FILE      = Path("scripts/fb_post_history.json")
HISTORY_LIMIT     = 25

# ── Brand visual style anchor ───────────────────────────────────────────────
# Locked across every post so the feed looks coherent.
STYLE_ANCHOR = (
    "Calm, minimal editorial illustration. Warm muted palette: soft beige, "
    "dusty rose, sage green, terracotta, cream. Soft natural lighting. "
    "Hand-drawn quality with subtle texture. Generous negative space. "
    "Quiet, contemplative mood. No text, no logos, no words anywhere in the image. "
    "If people appear, show them in soft silhouette or from behind — never close-up faces. "
    "Square 1:1 composition."
)

# ── Content style rotation ──────────────────────────────────────────────────
STYLES = [
    "vulnerable_confession",
    "reframe_insight",
    "actionable_tip",
    "statement_of_solidarity",
    "mini_story",
]

# ── App fact sheet ──────────────────────────────────────────────────────────
APP_FACTS = """
MindCore AI — voice-first AI mental health companion.
- Available 24/7, no judgment, no waiting rooms.
- Built for men 35+, recovery, anxiety, burnout, loneliness.
- 7-day trial €1.99 (NOT free — never say \"free trial\").
- Premium €14.99/month or €99.99/year.
- Pro €25/month or €179.99/year.
- Website: https://mindcoreai.eu
- App launches 30 April 2026 on Google Play.
"""

# ── Keyword & history helpers ───────────────────────────────────────────────
def load_keywords() -> list:
    if not KEYWORDS_FILE.exists():
        raise FileNotFoundError(f"{KEYWORDS_FILE} missing.")
    data = json.loads(KEYWORDS_FILE.read_text())
    topics = data.get("topics", [])
    if not topics:
        raise ValueError(f"{KEYWORDS_FILE} contains no topics.")
    print(f"  Loaded {len(topics)} keywords (last updated: {data.get('last_updated', 'unknown')})")
    return topics


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
    recent_keywords = {h["keyword"] for h in history[-HISTORY_LIMIT:]}
    available = [t for t in topics if t["keyword"] not in recent_keywords]
    if not available:
        available = topics
    return random.choice(available)


# ── Post text generation ────────────────────────────────────────────────────
def generate_post(topic: dict, style: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""You are writing a Facebook post for MindCore AI, an AI mental health companion app for men 35+.

TOPIC: {topic['keyword']}
ANGLE: {topic['angle']}
STYLE: {style}

APP FACTS (only mention if natural — don't force it):
{APP_FACTS}

REQUIREMENTS:
- 120–250 words. Facebook rewards medium-length emotional posts.
- FIRST LINE is everything — it's what people see before "See more". Make it stop the scroll.
  Examples of strong first lines:
    "Nobody talks about the silence."
    "You don't need to be okay today."
    "There's a kind of tired sleep can't fix."
- Write in plain, direct, second-person voice ("you"). No corporate tone. No clichés.
- Naturally include the keyword "{topic['keyword']}" once in the body — woven in, not stuffed.
- End with ONE of these CTAs (rotate naturally):
    a) A question that invites a comment ("What's the one thing that helped you?").
    b) A soft mention of MindCore AI as a place to talk when you can't talk to anyone else,
       with the link {SITE_URL}.
    c) A "share this with someone who needs it tonight" line.
- Add 5–7 hashtags at the end on a single line. Mix high-volume + niche:
    Always include: #MensMentalHealth #MentalHealthMatters
    Plus 3–5 niche tags relevant to "{topic['keyword']}".
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


# ── Image prompt generation ─────────────────────────────────────────────────
def generate_image_prompt(topic: dict, post_text: str) -> str:
    """
    Use Claude to read the post and write a tailored DALL-E prompt that captures
    the emotional moment of THIS specific post. Returns a single descriptive
    sentence — the style anchor is appended separately.
    """
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""You are an art director writing a DALL-E 3 prompt for an illustration that will
accompany this Facebook post on men's mental health.

TOPIC: {topic['keyword']}

POST TEXT:
{post_text}

Write ONE descriptive sentence (40–70 words) describing a SCENE that captures
the emotional core of this post. The scene should be evocative but quiet —
think editorial illustration, not stock photo.

GUIDELINES:
- Pick a single concrete moment, not an abstract concept.
  Good: "A man sitting alone on the edge of an unmade bed at dawn, soft light coming through curtains."
  Bad: "A representation of loneliness and emotional struggle."
- Use objects, light, posture, and environment to convey emotion. Never spell it out.
- If a person is in the scene, describe them in silhouette, from behind, or from the side. NEVER a close-up face.
- Avoid clichés: no head-in-hands, no rain on windows, no person with a dark cloud overhead.
- Stay grounded in everyday reality — kitchens, cars, hallways, parks, mornings, late nights.
- Don't mention any text, words, logos, or signs in the image.

Return ONLY the scene description. No preamble, no quotes, no explanation."""

    message = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    scene = message.content[0].text.strip().strip('"')
    return f"{scene}\n\nStyle: {STYLE_ANCHOR}"


# ── Image generation (DALL-E 3) ─────────────────────────────────────────────
def generate_image(image_prompt: str) -> str:
    """Generate an image with DALL-E 3 and return its URL (valid ~60 minutes)."""
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")

    url = "https://api.openai.com/v1/images/generations"
    headers = {
        "Authorization": f"Bearer {OPENAI_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model":   "dall-e-3",
        "prompt":  image_prompt,
        "n":       1,
        "size":    "1024x1024",
        "quality": "standard",  # "hd" doubles the cost — standard is plenty for FB feed
        "style":   "natural",   # "natural" is less stylized than "vivid" — better for editorial illustration
    }
    r = requests.post(url, headers=headers, json=payload, timeout=60)

    if not r.ok:
        try:
            err = r.json().get("error", {})
            print(f"  ✗ DALL-E error: {err.get('message')} (type: {err.get('type')})")
        except Exception:
            print(f"  ✗ DALL-E error: {r.text[:300]}")
        r.raise_for_status()

    return r.json()["data"][0]["url"]


# ── Facebook Graph API ──────────────────────────────────────────────────────
def fetch_page_token() -> str:
    """Exchange the System User token for a page-specific access token."""
    url = f"https://graph.facebook.com/v21.0/me/accounts"
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


def post_photo_to_facebook(message: str, image_url: str, page_token: str) -> dict:
    """Post a photo + caption to the page in a single API call."""
    url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/photos"
    payload = {
        "url":          image_url,
        "caption":      message,
        "access_token": page_token,
    }
    r = requests.post(url, data=payload, timeout=60)

    if not r.ok:
        try:
            err = r.json().get("error", {})
            print(f"  ✗ Facebook /photos error:")
            print(f"      message : {err.get('message')}")
            print(f"      type    : {err.get('type')}")
            print(f"      code    : {err.get('code')}")
            print(f"      subcode : {err.get('error_subcode')}")
            print(f"      trace   : {err.get('fbtrace_id')}")
        except Exception:
            print(f"  ✗ Facebook /photos error (non-JSON): {r.text[:500]}")
        r.raise_for_status()

    return r.json()


def post_text_to_facebook(message: str, page_token: str) -> dict:
    """Fallback — post text-only when image generation fails."""
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
    print("  MindCore AI — Facebook Daily Automation")
    print(f"  Run at: {datetime.now(timezone.utc).isoformat()}")
    print("=" * 60)

    topics  = load_keywords()
    history = load_history()
    topic   = pick_topic(topics, history)
    style   = random.choice(STYLES)

    print(f"\n  Topic   : {topic['keyword']}")
    print(f"  Angle   : {topic['angle']}")
    print(f"  Style   : {style}\n")

    print("  Generating post…")
    post_text = generate_post(topic, style)
    print("\n" + "-" * 60)
    print(post_text)
    print("-" * 60 + "\n")

    # Try to generate an image — but don't fail the whole post if it errors
    image_url     = None
    image_prompt  = None
    if OPENAI_API_KEY:
        try:
            print("  Crafting image prompt tailored to this post…")
            image_prompt = generate_image_prompt(topic, post_text)
            print(f"  Prompt: {image_prompt[:200]}…\n")

            print("  Generating illustration with DALL-E 3…")
            image_url = generate_image(image_prompt)
            print(f"  ✓ Image URL received (valid ~60 min)\n")
        except Exception as e:
            print(f"  ⚠ Image generation failed: {e}")
            print(f"  → Falling back to text-only post\n")
    else:
        print("  ⚠ OPENAI_API_KEY not set — posting text-only\n")

    print("  Fetching page-specific access token…")
    page_token = fetch_page_token()
    print("  ✓ Got page token\n")

    print("  Publishing to Facebook…")
    if image_url:
        try:
            result = post_photo_to_facebook(post_text, image_url, page_token)
            fb_post_id = result.get("post_id") or result.get("id", "unknown")
            print(f"  Published with image ✓  Post ID: {fb_post_id}")
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
        "style"       : style,
        "fb_post_id"  : fb_post_id,
        "with_image"  : posted_with_image,
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
