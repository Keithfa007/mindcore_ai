#!/usr/bin/env python3
"""
MindCore AI — Monthly Keyword Refresh
Uses Claude with web search to research fresh high-search / low-competition
keywords in the men's mental health niche, then writes them to
scripts/fb_keywords.json so the daily Facebook automation reads the new bank.

Runs on the 1st of every month via GitHub Actions.

Required env vars:
  ANTHROPIC_API_KEY
"""

import os
import json
import re
import sys
from datetime import date
from pathlib import Path

import anthropic

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
KEYWORDS_FILE     = Path("scripts/fb_keywords.json")
TARGET_COUNT      = 25  # how many keywords to keep in the bank


RESEARCH_PROMPT = """You are an SEO researcher for MindCore AI — a voice-first AI mental health
companion app targeting men 35+ dealing with anxiety, depression, burnout,
recovery from addiction, and emotional isolation.

YOUR TASK
Use web search to research the highest-opportunity long-tail keywords RIGHT NOW
(this month) in the men's mental health niche. We want phrases that score
HIGH SEARCH VOLUME × LOW COMPETITION — the gap nobody is filling well.

SEARCH STRATEGY — actually run these searches:
1. Search Google Trends and SEO blog roundups for "men's mental health long tail keywords [current month/year]"
2. Search "People Also Ask" patterns around: emotional numbness, high functioning anxiety, burnout, sobriety + mental health, panic attacks, loneliness in men, dad mental health
3. Look at what ranks on the first page — gaps where mental health BIG brands (BetterHelp, Calm, Headspace) AREN'T ranking are the openings we want.
4. Prioritise question-style queries ("how to…", "why do I…", "what does it mean when…") — these are low-competition gold.

OUTPUT REQUIREMENTS
Return EXACTLY 25 keywords, each with a 1-sentence "angle" — the emotional hook
or reframe that a Facebook post on that keyword would use. The angle should be
written in plain, direct language (not corporate). Read like someone who's
been there, not a copywriter.

CONSTRAINTS
- Each keyword: 3–8 words, lowercase, no special characters.
- Each angle: ONE sentence, under 130 characters, ends with a period.
- Mix evergreen topics (always relevant) with timely topics if you found any.
- Stay strictly inside the men's mental health / recovery / emotional wellbeing niche.
- AVOID generic single-word keywords like "anxiety" or "depression" — too competitive.
- AVOID anything clinical-sounding ("PTSD treatment guidelines", "DSM-5 criteria") — wrong audience.

OUTPUT FORMAT
After your research, return ONLY a single JSON object — no preamble, no
explanation, no markdown fences. Schema:

{
  "topics": [
    {"keyword": "…", "angle": "…"},
    {"keyword": "…", "angle": "…"},
    ... 25 total
  ]
}
"""


def extract_json(text: str) -> dict:
    """Pull the first {...} JSON object out of the model's final text."""
    # Strip code fences if present
    text = re.sub(r"^```(?:json)?\s*", "", text.strip())
    text = re.sub(r"\s*```$", "", text)

    # Find first balanced JSON object
    start = text.find("{")
    if start == -1:
        raise ValueError("No JSON object found in model response.")

    depth = 0
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return json.loads(text[start:i + 1])
    raise ValueError("Unterminated JSON object in model response.")


def validate_topics(data: dict) -> list:
    """Ensure shape is right and trim/pad to TARGET_COUNT."""
    topics = data.get("topics", [])
    cleaned = []
    seen = set()
    for t in topics:
        kw = (t.get("keyword") or "").strip().lower()
        ang = (t.get("angle") or "").strip()
        if not kw or not ang or kw in seen:
            continue
        if len(kw.split()) < 2 or len(kw.split()) > 10:
            continue
        seen.add(kw)
        cleaned.append({"keyword": kw, "angle": ang})

    if len(cleaned) < 15:
        raise ValueError(f"Only {len(cleaned)} valid topics returned — need at least 15.")

    return cleaned[:TARGET_COUNT]


def main():
    print("=" * 60)
    print("  MindCore AI — Monthly Keyword Refresh")
    print(f"  Date: {date.today().isoformat()}")
    print("=" * 60)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    print("\n  Asking Claude to research fresh keywords (with web search)…")
    response = client.messages.create(
        model="claude-sonnet-4-5",
        max_tokens=4096,
        tools=[{
            "type": "web_search_20250305",
            "name": "web_search",
            "max_uses": 8,
        }],
        messages=[{"role": "user", "content": RESEARCH_PROMPT}],
    )

    # Extract the FINAL text block from the response
    final_text = ""
    for block in response.content:
        if getattr(block, "type", None) == "text":
            final_text = block.text  # last text block wins

    if not final_text:
        raise RuntimeError("No text content returned from Claude.")

    print("\n  Parsing JSON…")
    data = extract_json(final_text)
    topics = validate_topics(data)
    print(f"  ✓ {len(topics)} valid keywords")

    output = {
        "last_updated"   : date.today().isoformat(),
        "research_method": "claude_web_search",
        "topics"         : topics,
    }

    KEYWORDS_FILE.parent.mkdir(parents=True, exist_ok=True)
    KEYWORDS_FILE.write_text(json.dumps(output, indent=2, ensure_ascii=False))
    print(f"\n  Wrote {KEYWORDS_FILE}")

    print("\n  Sample of new bank:")
    for t in topics[:5]:
        print(f"    • {t['keyword']}  →  {t['angle']}")
    print()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n❌ ERROR: {e}", file=sys.stderr)
        sys.exit(1)
