#!/usr/bin/env python3
"""
MindCore AI — Facebook Daily Automation
Posts inspirational, SEO-optimised mental health content once per day at the
optimal time for that specific weekday (scheduled by GitHub Actions cron).

Each post includes a custom DALL-E 3 illustration tailored to the post's
emotional moment, using a locked brand style (calm, minimal, warm tones).

Reads keyword bank from scripts/fb_keywords.json (men's topics) AND
scripts/neutral_keywords.json (audience-agnostic topics).

PHASE 1 AUDIENCE STRATEGY:
  70% men's content (preserves men 35+ wedge positioning)
  30% neutral content (broadens reach without losing focus)
  No women-specific content on social yet (blog only).
  Revisit ratio after first 100 app installs.

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
OPENAI_API_KEY    = os.environ.get("OPENAI_API_KEY")
FB_PAGE_ID        = os.environ["FB_PAGE_ID"]
FB_ACCESS_TOKEN   = os.environ["FB_ACCESS_TOKEN"]

SITE_URL              = "https://mindcoreai.eu"
MENS_KEYWORDS_FILE    = Path("scripts/fb_keywords.json")
NEUTRAL_KEYWORDS_FILE = Path("scripts/neutral_keywords.json")
HISTORY_FILE          = Path("scripts/fb_post_history.json")
HISTORY_LIMIT         = 25

# Phase 1 audience mix — adjust here when ready to evolve
MENS_WEIGHT    = 0.70
NEUTRAL_WEIGHT = 0.30

STYLE_ANCHOR = (
    "Calm, minimal editorial illustration. Warm muted palette: soft beige, "
    "dusty rose, sage green, terracotta, cream. Soft natural lighting. "
    "Hand-drawn quality with subtle texture. Generous negative space. "
    "Quiet, contemplative mood. No text, no logos, no words anywhere in the image. "
    "If people appear, show them in soft silhouette or from behind — never close-up faces. "
    "Square 1:1 composition."
)

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
    # Tag each topic with its audience so the post generator can adjust voice
    for t in topics:
        t["audience"] = audience_tag
    print(f"  Loaded {len(topics)} {audience_tag} keywords (last updated: {data.get('last_updated', 'unknown')})")
    return topics


def load_topic_pools() -> dict:
    """Returns {'men': [...], 'neutral': [...]}."""
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
    """
    Weighted pick: 70% chance to pull from men's pool, 30% from neutral.
    Within the chosen pool, avoid topics used in the last HISTORY_LIMIT posts.
    Falls back to the other pool if the chosen one is fully on cooldown.
    """
    audience = random.choices(
        ["men", "neutral"],
        weights=[MENS_WEIGHT, NEUTRAL_WEIGHT],
        k=1,
    )[0]

    recent_keywords = {h["keyword"] for h in history[-HISTORY_LIMIT:]}
    available = [t for t in pools[audience] if t["keyword"] not in recent_keywords]

    # Fallback: if the chosen pool is fully on cooldown, use the other pool
    if not available:
        other = "neutral" if audience == "men" else "men"
        available = [t for t in pools[other] if t["keyword"] not in recent_keywords]
        if available:
            print(f"  {audience} pool on cooldown — falling back to {other}")
        else:
            available = pools[audience]  # all on cooldown, pick anyway

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
    else:  # neutral
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


# ── Image prompt generation ─────────────────────────────────────────────────
def generate_image_prompt(topic: dict, post_text: str) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    audience = topic.get("audience", "men")

    if audience == "men":
        person_guidance = (
            "If a person is in the scene, describe them in silhouette, from behind, or from the side. "
            "NEVER a close-up face. For men-focused content the figure (if any) reads as male."
        )
    else:
        person_guidance = (
            "If a person is in the scene, describe them in silhouette, from behind, or from the side. "
            "NEVER a close-up face. For neutral content, prefer no people at all — focus on still life, "
            "objects, light, environment. If a figure is unavoidable, keep gender ambiguous."
        )

    prompt = f"""You are an art director writing a DALL-E 3 prompt for an illustration that will
accompany this Facebook post on mental health.

TOPIC: {topic['keyword']}
AUDIENCE: {audience}

POST TEXT:
{post_text}

Write ONE descriptive sentence (40–70 words) describing a SCENE that captures
the emotional core of this post. The scene should be evocative but quiet —
think editorial illustration, not stock photo.

GUIDELINES:
- Pick a single concrete moment, not an abstract concept.
- Use objects, light, posture, and environment to convey emotion. Never spell it out.
- {person_guidance}
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
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")
    url = "https://api.openai.com/v1/images/generations"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "model":   "dall-e-3",
        "prompt":  image_prompt,
        "n":       1,
        "size":    "1024x1024",
        "quality": "standard",
        "style":   "natural",
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
    url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/photos"
    payload = {"url": image_url, "caption": message, "access_token": page_token}
    r = requests.post(url, data=payload, timeout=60)
    if not r.ok:
        try:
            err = r.json().get("error", {})
            print(f"  ✗ Facebook /photos error: {err.get('message')} | code={err.get('code')} | subcode={err.get('error_subcode')}")
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
    print("  MindCore AI — Facebook Daily Automation")
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

    image_url    = None
    image_prompt = None
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
        "audience"    : topic.get("audience", "unknown"),
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
