#!/usr/bin/env python3
"""
MindCore AI — Facebook Daily Automation
Posts inspirational, SEO-optimised mental health content once per day at the
optimal time for that specific weekday (scheduled by GitHub Actions cron).

Reads keyword bank from scripts/fb_keywords.json — refreshed monthly by
refresh_keywords.py.

Required env vars:
  ANTHROPIC_API_KEY  - for content generation
  FB_PAGE_ID         - 61564494039673
  FB_ACCESS_TOKEN    - long-lived Page Access Token
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
FB_PAGE_ID        = os.environ["FB_PAGE_ID"]
FB_ACCESS_TOKEN   = os.environ["FB_ACCESS_TOKEN"]

SITE_URL          = "https://mindcoreai.eu"
KEYWORDS_FILE     = Path("scripts/fb_keywords.json")
HISTORY_FILE      = Path("scripts/fb_post_history.json")
HISTORY_LIMIT     = 25  # don't reuse a topic until 25 posts have passed

# ── Content style rotation ──────────────────────────────────────────────────
STYLES = [
    "vulnerable_confession",
    "reframe_insight",
    "actionable_tip",
    "statement_of_solidarity",
    "mini_story",
]

# ── App fact sheet (single source of truth — no hallucinations) ─────────────
APP_FACTS = """
MindCore AI — voice-first AI mental health companion.
- Available 24/7, no judgment, no waiting rooms.
- Built for men 35+, recovery, anxiety, burnout, loneliness.
- 7-day trial €1.99 (NOT free — never say "free trial").
- Premium €14.99/month or €99.99/year.
- Pro €25/month or €179.99/year.
- Website: https://mindcoreai.eu
- App launches 30 April 2026 on Google Play.
"""

# ── Keyword & history helpers ───────────────────────────────────────────────
def load_keywords() -> list:
    if not KEYWORDS_FILE.exists():
        raise FileNotFoundError(
            f"{KEYWORDS_FILE} missing. Run scripts/refresh_keywords.py "
            f"or commit the seed file."
        )
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
    """Pick a topic that hasn't been used in the last HISTORY_LIMIT posts."""
    recent_keywords = {h["keyword"] for h in history[-HISTORY_LIMIT:]}
    available = [t for t in topics if t["keyword"] not in recent_keywords]
    if not available:
        available = topics
    return random.choice(available)


# ── Content generation ──────────────────────────────────────────────────────
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


# ── Facebook Graph API ──────────────────────────────────────────────────────
def post_to_facebook(message: str) -> dict:
    url = f"https://graph.facebook.com/v21.0/{FB_PAGE_ID}/feed"
    payload = {"message": message, "access_token": FB_ACCESS_TOKEN}
    r = requests.post(url, data=payload, timeout=30)
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

    print("  Publishing to Facebook…")
    result = post_to_facebook(post_text)
    fb_post_id = result.get("id", "unknown")
    print(f"  Published ✓  Post ID: {fb_post_id}")

    history.append({
        "timestamp"  : datetime.now(timezone.utc).isoformat(),
        "keyword"    : topic["keyword"],
        "style"      : style,
        "fb_post_id" : fb_post_id,
        "preview"    : post_text[:140],
    })
    save_history(history)
    print(f"  History updated ({len(history)} total posts)\n")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        sys.exit(1)
