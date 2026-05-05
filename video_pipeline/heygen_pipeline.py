#!/usr/bin/env python3
"""
MindCore AI Video Pipeline v5.5
=================================

CHANGES (v5.5):
  Ad script completely rewritten. Content-first approach: hook and problem
  are pure education (no selling), story introduces MindCore AI naturally
  as the solution with specific features, CTA is a soft genuine recommendation.
  8 rotating ad pain points so each ad covers a different aspect of the app.
  Word limits relaxed to match content video targets — ads are now full-length
  videos, not 20-second hard sells.

CHANGES (v5.4):
  Script variety: 6 rotating structures, 20 content angles, topic history.
  Visual variety: 5 visual style categories for cinematic B-roll.

CHANGES (v5.3):
  Update Fish Audio voice ID to 4ea1bbc944004fa89ea67021d86129ef.

CHANGES (v5.2):
  Remove burned-in subtitles from cinematic videos.

CHANGES (v5.1):
  Fix cinematic video length: clips loop to fill full duration.

CHANGES (v5.0):
  Cinematic format: Fish Audio TTS + Pexels B-roll + FFmpeg assembly.

CHANGES (v4.7):
  YouTube Shorts as 4th platform. Brand hashtag enforcement.
"""

import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

ANTHROPIC_API_KEY   = os.environ["ANTHROPIC_API_KEY"]
HEYGEN_API_KEY      = os.environ["HEYGEN_API_KEY"]
FISH_AUDIO_API_KEY  = os.environ.get("FISH_AUDIO_API_KEY", "")
PEXELS_API_KEY      = os.environ.get("PEXELS_API_KEY", "")
SERP_API_KEY        = os.environ.get("SERP_API_KEY", "")
UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
FORCE_FORMAT        = os.environ.get("FORCE_FORMAT", "").strip().lower()

GITHUB_RUN_NUMBER = int(os.environ.get("GITHUB_RUN_NUMBER", "1"))

HEYGEN_V3_URL       = "https://api.heygen.com/v3/videos"
HEYGEN_STATUS_URL   = "https://api.heygen.com/v1/video_status.get"
FISH_AUDIO_TTS_URL  = "https://api.fish.audio/v1/tts"
PEXELS_VIDEO_URL    = "https://api.pexels.com/videos/search"
SERP_API_URL        = "https://serpapi.com/search"
UPLOAD_POST_API_URL = "https://api.upload-post.com/api/upload"

FISH_AUDIO_VOICE_ID = "4ea1bbc944004fa89ea67021d86129ef"

OUTPUT_DIR         = Path("video_pipeline/output")
PIPELINE_DIR       = Path("video_pipeline")
TOPIC_HISTORY_PATH = PIPELINE_DIR / "topic_history.json"
SCENE_ORDER        = ["hook", "problem", "story", "solution_cta"]

POLL_INTERVAL = 15
VIDEO_TIMEOUT = 1200

CLAUDE_MAX_RETRIES = 10
CLAUDE_RETRY_BASE  = 30

SERP_SEEDS_PER_RUN         = 3
AUTOCOMPLETE_SEEDS_PER_RUN = 2

TIKTOK_CAPTION_LIMIT      = 2200
YOUTUBE_TITLE_LIMIT       = 100
YOUTUBE_DESCRIPTION_LIMIT = 5000

PEXELS_CLIPS_PER_VIDEO = 5
TOPIC_HISTORY_SIZE     = 5

REQUIRED_BRAND_HASHTAG = "#mindcoreai"

# ---------------------------------------------------------------------------
# Script structures (content videos)
# ---------------------------------------------------------------------------

SCRIPT_STRUCTURES = {
    "hook_contradiction": (
        "HOOK: Start with a statement that contradicts common belief about this topic. "
        "One punchy sentence that makes men stop scrolling."
    ),
    "hook_statistic": (
        "HOOK: Lead with a surprising or little-known statistic or research fact "
        "directly related to the topic. Make it land hard."
    ),
    "hook_question": (
        "HOOK: Open with a direct, uncomfortable question that the target man is "
        "already asking himself silently. No fluff."
    ),
    "hook_confession": (
        "HOOK: Begin as if confessing something most men are ashamed to admit. "
        "First person, raw, immediate. Do NOT start with 'I remember sitting...' "
        "or any birthday party / barbecue memory."
    ),
    "hook_observation": (
        "HOOK: Open with a sharp observation about male behaviour that feels "
        "uncomfortably accurate. Like something a close friend would say."
    ),
    "hook_provocation": (
        "HOOK: Start with a mildly provocative or counterintuitive claim that "
        "challenges what men think they know about themselves."
    ),
}

BANNED_OPENINGS = [
    "I remember sitting at my kid",
    "I remember sitting at a",
    "I was sitting at",
    "There I was, sitting",
    "Picture this",
    "Let me tell you something",
    "Here's the thing",
]

# ---------------------------------------------------------------------------
# Ad topics -- rotate so each ad covers a different pain point / use case
# ---------------------------------------------------------------------------

AD_TOPICS = [
    {
        "pain_point": "talking to yourself at 3am trying to figure out why you can't sleep",
        "insight":    "Most men don't have a safe space to process what's going on in their head — without judgment, without advice they didn't ask for.",
        "feature":    "MindCore AI gives you a private, calm space to talk through whatever's keeping you up. It's built for men, available 24/7, and it actually listens.",
    },
    {
        "pain_point": "the anger that comes out of nowhere in recovery",
        "insight":    "Sobriety doesn't remove your emotions. It removes the thing you were using to numb them. And suddenly all that feeling has nowhere to go.",
        "feature":    "MindCore AI helps men in recovery understand and process what's underneath the anger — without judgment, without a waiting list.",
    },
    {
        "pain_point": "feeling like no one around you actually gets what you're going through",
        "insight":    "Men are wired to solve problems, not talk about them. Which means the pain just builds. And eventually it comes out sideways.",
        "feature":    "MindCore AI is built specifically for men's mental health. No small talk. No generic advice. Just honest, private conversations whenever you need them.",
    },
    {
        "pain_point": "the emotional numbness that creeps in after years of staying strong",
        "insight":    "Emotional shutdown isn't weakness. It's your brain protecting you from overwhelm. But over time, it cuts you off from everything — the good stuff too.",
        "feature":    "MindCore AI helps men reconnect with what they're actually feeling, one conversation at a time. It's on Google Play and your first week is free.",
    },
    {
        "pain_point": "anxiety that shows up as irritability and short fuses, not panic attacks",
        "insight":    "Most men with anxiety don't recognise it as anxiety. It looks like anger, withdrawal, or just constantly feeling on edge for no obvious reason.",
        "feature":    "MindCore AI understands how anxiety actually shows up in men — and helps you work through it in a way that actually fits how you think.",
    },
    {
        "pain_point": "lying awake wondering if what you're feeling is normal",
        "insight":    "The number of men silently asking that question every night is staggering. And most of them never ask anyone out loud.",
        "feature":    "MindCore AI exists for exactly that moment. A private AI mental health companion for men — honest, non-judgmental, available any time.",
    },
    {
        "pain_point": "going through the motions every day but feeling completely disconnected from your own life",
        "insight":    "That disconnect has a name. And it's more common in men over 35 than almost any other mental health experience. But nobody talks about it.",
        "feature":    "MindCore AI was built to help men name what they're feeling and start actually dealing with it — privately, on their own terms.",
    },
    {
        "pain_point": "not wanting to burden your family with what's going on in your head",
        "insight":    "That instinct to protect the people you love can become its own trap. You end up carrying everything alone, and they can tell something's off anyway.",
        "feature":    "MindCore AI gives you somewhere to put it that isn't your partner, your kids, or your mates. Just you, and a tool that was built for this.",
    },
]

# Word targets — ads now match content video length, not a 20-second hard sell
WORD_TARGETS_AD = {
    "hook":         (10, 15),
    "problem":      (30, 40),
    "story":        (40, 55),
    "solution_cta": (20, 30),
}

WORD_TARGETS_CONTENT = {
    "hook":         (10, 15),
    "problem":      (30, 40),
    "story":        (50, 65),
    "solution_cta": (25, 35),
}

SEO_KEYWORDS = [
    "AI mental health coach for men",
    "recovery support anxiety depression",
    "sobriety mental wellness app",
]

BANNED_PHRASE_REPLACEMENTS = [
    (r"try\s+it\s+for\s+free", "try it"),
    (r"download\s+now",        "find MindCore AI on Google Play"),
    (r"free\s+trial",          "free first week"),
]


# ---------------------------------------------------------------------------
# Topic history
# ---------------------------------------------------------------------------

def load_topic_history() -> list:
    if TOPIC_HISTORY_PATH.exists():
        try:
            return json.loads(TOPIC_HISTORY_PATH.read_text())
        except Exception:
            return []
    return []


def save_topic_history(history: list, new_topic: str):
    history.append(new_topic)
    TOPIC_HISTORY_PATH.write_text(json.dumps(history[-TOPIC_HISTORY_SIZE:], indent=2))


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def determine_mode() -> str:
    return "ad" if GITHUB_RUN_NUMBER % 10 == 0 else "content"


def load_config() -> dict:
    with open(PIPELINE_DIR / "heygen_config.json") as f:
        return json.load(f)


def pick_avatar_look(cfg: dict) -> str:
    looks = cfg.get("avatar_look_ids", [])
    if not looks:
        raise RuntimeError("No avatar_look_ids found in heygen_config.json")
    chosen = random.choice(looks)
    print(f"  Avatar look: {chosen} (1 of {len(looks)} looks)")
    return chosen


def load_app_facts() -> dict:
    with open(PIPELINE_DIR / "app_facts.json") as f:
        return json.load(f)


def load_niche_keywords() -> dict:
    path = PIPELINE_DIR / "niche_keywords.json"
    if not path.exists():
        return {"seed_queries": ["men mental health tips"], "content_angles": ["real talk"],
                "visual_styles": []}
    with open(path) as f:
        return json.load(f)


def pick_visual_style(keywords: dict) -> dict:
    styles = keywords.get("visual_styles", [])
    if not styles:
        return {"name": "atmospheric_solitude",
                "query_templates": ["lonely man window", "empty room", "man thinking alone"]}
    return random.choice(styles)


def ensure_brand_hashtag(text: str) -> str:
    if not text:
        return REQUIRED_BRAND_HASHTAG
    if REQUIRED_BRAND_HASHTAG.lower() in text.lower():
        return text
    lines = text.rstrip().split("\n")
    for i in range(len(lines) - 1, -1, -1):
        if "#" in lines[i]:
            lines[i] = lines[i].rstrip() + f" {REQUIRED_BRAND_HASHTAG}"
            return "\n".join(lines)
    return text.rstrip() + f"\n{REQUIRED_BRAND_HASHTAG}"


def sanitize_script(script: dict) -> dict:
    for scene in SCENE_ORDER:
        if scene not in script:
            continue
        original = script[scene]["voiceover"]
        cleaned  = original
        for pattern, replacement in BANNED_PHRASE_REPLACEMENTS:
            cleaned = re.sub(pattern, replacement, cleaned, flags=re.IGNORECASE)
        if cleaned != original:
            print(f"  SANITIZED [{scene}]: '{original}' -> '{cleaned}'")
            script[scene]["voiceover"] = cleaned
    return script


def _call_claude_raw(prompt: str, client: anthropic.Anthropic, max_tokens: int = 1000) -> dict:
    for attempt in range(1, CLAUDE_MAX_RETRIES + 1):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
            return json.loads(raw)
        except anthropic.APIStatusError as e:
            if e.status_code == 529:
                if attempt == CLAUDE_MAX_RETRIES:
                    raise RuntimeError("Anthropic API overloaded after max retries.")
                wait = CLAUDE_RETRY_BASE * attempt
                print(f"  Anthropic overloaded -- waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
        except json.JSONDecodeError:
            if attempt == CLAUDE_MAX_RETRIES:
                raise RuntimeError("Claude returned invalid JSON after all retries")
            print(f"  JSON parse error -- retrying in 10s...")
            time.sleep(10)
    raise RuntimeError("Unexpected exit from retry loop")


# ---------------------------------------------------------------------------
# SERP Keyword Research
# ---------------------------------------------------------------------------

def _serp_google_query(seed: str) -> dict:
    params = {"engine": "google", "q": seed, "api_key": SERP_API_KEY, "num": 10, "hl": "en", "gl": "us"}
    resp = requests.get(SERP_API_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _serp_autocomplete_query(seed: str) -> list:
    params = {"engine": "google_autocomplete", "q": seed, "api_key": SERP_API_KEY, "hl": "en", "gl": "us"}
    try:
        resp = requests.get(SERP_API_URL, params=params, timeout=30)
        resp.raise_for_status()
        return [s.get("value", "").strip() for s in resp.json().get("suggestions", []) if s.get("value")]
    except Exception as e:
        print(f"  Autocomplete failed for '{seed}': {e}")
        return []


def _word_count(text: str) -> int:
    return len(text.split())


def _keyword_type(text: str) -> str:
    wc = _word_count(text)
    if wc <= 3:   return "short_tail"
    elif wc <= 5: return "mid_tail"
    else:         return "long_tail"


def research_keyword_candidates_from_serp(seeds: list) -> list:
    candidates = []
    seen = set()
    regular_seeds = random.sample(seeds, min(SERP_SEEDS_PER_RUN, len(seeds)))
    for seed in regular_seeds:
        try:
            data = _serp_google_query(seed)
            total_results = int(
                str(data.get("search_information", {}).get("total_results", "0"))
                    .replace(",", "").replace(".", "") or "0"
            )
            paa_count = 0
            for q in data.get("related_questions", []):
                text = q.get("question", "").strip()
                if text and text.lower() not in seen:
                    seen.add(text.lower())
                    candidates.append({"text": text, "source": "people_also_ask",
                                       "tail_type": _keyword_type(text), "word_count": _word_count(text),
                                       "seed": seed, "total_results": total_results})
                    paa_count += 1
            rs_count = 0
            for r in data.get("related_searches", []):
                text = r.get("query", "").strip()
                if text and text.lower() not in seen:
                    seen.add(text.lower())
                    candidates.append({"text": text, "source": "related_search",
                                       "tail_type": _keyword_type(text), "word_count": _word_count(text),
                                       "seed": seed, "total_results": 0})
                    rs_count += 1
            for org in data.get("organic_results", [])[:3]:
                title = org.get("title", "").strip()
                if title and title.lower() not in seen and len(title) < 120:
                    seen.add(title.lower())
                    candidates.append({"text": title, "source": "organic_title",
                                       "tail_type": _keyword_type(title), "word_count": _word_count(title),
                                       "seed": seed, "total_results": total_results})
            print(f"  [GOOGLE] '{seed[:45]}': {paa_count} PAA | {rs_count} related | {total_results:,} results")
            time.sleep(0.5)
        except Exception as e:
            print(f"  Google search failed for '{seed}': {e}")

    autocomplete_bases = []
    for seed in seeds:
        words = seed.split()
        if len(words) >= 3:
            autocomplete_bases.extend([" ".join(words[:2]), " ".join(words[:3])])
        else:
            autocomplete_bases.append(seed)
    ac_seeds = random.sample(list(set(autocomplete_bases)), min(AUTOCOMPLETE_SEEDS_PER_RUN, len(set(autocomplete_bases))))
    for ac_seed in ac_seeds:
        suggestions = _serp_autocomplete_query(ac_seed)
        ac_count = 0
        for text in suggestions:
            if text and text.lower() not in seen and _word_count(text) <= 6:
                seen.add(text.lower())
                candidates.append({"text": text, "source": "autocomplete",
                                   "tail_type": _keyword_type(text), "word_count": _word_count(text),
                                   "seed": ac_seed, "total_results": 0})
                ac_count += 1
        if ac_count:
            print(f"  [AUTOCOMPLETE] '{ac_seed}': {ac_count} suggestions")
        time.sleep(0.5)

    short = sum(1 for c in candidates if c["tail_type"] == "short_tail")
    mid   = sum(1 for c in candidates if c["tail_type"] == "mid_tail")
    long  = sum(1 for c in candidates if c["tail_type"] == "long_tail")
    print(f"  Total candidates: {len(candidates)} ({short} short | {mid} mid | {long} long tail)")
    return candidates


def rank_and_select_keyword_claude(candidates: list, client: anthropic.Anthropic,
                                   topic_history: list, visual_style: dict) -> dict:
    if not candidates:
        raise ValueError("No SERP candidates to rank")

    type_order   = {"short_tail": 0, "mid_tail": 1, "long_tail": 2}
    source_order = {"autocomplete": 0, "people_also_ask": 1, "related_search": 2, "organic_title": 3}
    sorted_cands = sorted(candidates, key=lambda c: (type_order.get(c["tail_type"], 3), source_order.get(c["source"], 4)))
    candidate_list = "\n".join([
        f"{i+1}. [{c['tail_type'].upper()} | {c['source'].upper()} | {c['word_count']}w] {c['text']}"
        for i, c in enumerate(sorted_cands[:50])
    ])

    history_note = ""
    if topic_history:
        history_note = f"\nRECENT TOPICS (DO NOT REPEAT these or anything closely related):\n"
        history_note += "\n".join(f"  - {t}" for t in topic_history)
        history_note += "\nPick something DIFFERENT in theme, emotion, and angle.\n"

    style_templates = visual_style.get("query_templates", ["lonely man window", "empty road", "man thinking"])
    style_name      = visual_style.get("name", "atmospheric_solitude")
    style_desc      = visual_style.get("description", "moody atmospheric")

    prompt = f"""Expert in SEO for men's mental health, recovery, sobriety on TikTok/Reels/YouTube Shorts.

Below are REAL Google search queries. Choose the SINGLE BEST keyword for a short video today.
{history_note}
FAVOUR SHORT-TAIL emotional phrases (sobriety anger, men crying, emotional numbness).
Big health brands ignore raw emotional short phrases -- individual creators own this space.

SCORING:
1. Emotional resonance for men 35-55 struggling silently
2. Low competition: under big-brand radar?
3. Niche fit: men's mental health, sobriety, recovery
4. Video potential: powerful in 30-45 seconds?

FORMAT DECISION:
- "cinematic": abstract emotional states, reflective/introspective, atmospheric
  (loneliness, grief, numbness, 3am anxiety, emptiness, silent depression)
- "avatar": direct advice, testimony, how-to, practical tips

VISUAL STYLE FOR THIS RUN: {style_name} ({style_desc})
If you choose cinematic, generate Pexels queries in THIS visual style.
Style query examples: {style_templates}
Generate 4 specific, varied Pexels search queries that match this style AND the chosen topic.
Make each query distinct -- different shots, not just the same scene rephrased.

CANDIDATES (short-tail first):
{candidate_list}

Return ONLY valid JSON, no markdown:
{{
  "topic": "exact text of chosen candidate",
  "question": "how a man types this into Google",
  "keyword": "primary 1-5 word SEO keyword",
  "tail_type": "short_tail|mid_tail|long_tail",
  "competition_signal": "low|medium|high",
  "why": "one sentence: why this beats the others",
  "source": "autocomplete|people_also_ask|related_search|organic_title",
  "format": "avatar|cinematic",
  "visual_style": "{style_name}",
  "pexels_queries": ["specific query 1", "specific query 2", "specific query 3", "specific query 4"]
}}"""

    result = _call_claude_raw(prompt, client, max_tokens=700)

    if FORCE_FORMAT in ("avatar", "cinematic"):
        result["format"] = FORCE_FORMAT
        print(f"  Format: FORCED to {FORCE_FORMAT.upper()}")
    else:
        print(f"  Format: {result.get('format', 'avatar').upper()} (Claude's choice)")

    print(f"  Winner: '{result.get('keyword')}' [{result.get('tail_type','?')} | {result.get('competition_signal','?')} competition]")
    print(f"  Visual style: {result.get('visual_style', style_name)}")
    print(f"  Reason: {result.get('why', '')}")
    return result


def fetch_trending_topic_claude_fallback(seeds: list, topic_history: list,
                                          visual_style: dict, client: anthropic.Anthropic) -> dict:
    seed = random.choice(seeds)
    history_note = ""
    if topic_history:
        history_note = f"AVOID these recent topics: {', '.join(topic_history)}. Pick something different.\n"
    style_name = visual_style.get("name", "atmospheric_solitude")
    prompt = f"""SEO expert for men's mental health, recovery, anxiety, sobriety.
Generate ONE keyword/topic for a short video. Related to: "{seed}"
{history_note}Return ONLY valid JSON:
{{
  "topic": "the keyword or question",
  "question": "how a man types this into Google",
  "keyword": "primary 1-5 word SEO keyword",
  "tail_type": "short_tail|mid_tail|long_tail",
  "competition_signal": "low|medium|high",
  "why": "one sentence rationale",
  "source": "claude_generated",
  "format": "avatar",
  "visual_style": "{style_name}",
  "pexels_queries": ["lonely man window", "man thinking dark room", "empty street night", "person silhouette fog"]
}}"""
    result = _call_claude_raw(prompt, client, max_tokens=400)
    if FORCE_FORMAT in ("avatar", "cinematic"):
        result["format"] = FORCE_FORMAT
    return result


def fetch_trending_topic(client: anthropic.Anthropic) -> dict:
    keywords      = load_niche_keywords()
    seeds         = keywords["seed_queries"]
    topic_history = load_topic_history()
    visual_style  = pick_visual_style(keywords)

    print(f"  Visual style this run: {visual_style.get('name')} ({visual_style.get('description')})")
    if topic_history:
        print(f"  Avoiding recent topics: {topic_history}")

    if SERP_API_KEY:
        print(f"  Keyword research: {SERP_SEEDS_PER_RUN} Google + {AUTOCOMPLETE_SEEDS_PER_RUN} autocomplete...")
        try:
            candidates = research_keyword_candidates_from_serp(seeds)
            if candidates:
                topic = rank_and_select_keyword_claude(candidates, client, topic_history, visual_style)
                topic["source"] = f"serp_{topic.get('source', 'research')}"
                (OUTPUT_DIR / "keyword_research.json").write_text(json.dumps(
                    {"run": GITHUB_RUN_NUMBER, "candidates": candidates, "winner": topic}, indent=2
                ))
                return topic
            print("  No candidates -- falling back to Claude")
        except Exception as e:
            print(f"  SERP research failed ({e}) -- falling back to Claude")

    print("  Generating topic with Claude (no SERP)...")
    topic = fetch_trending_topic_claude_fallback(seeds, topic_history, visual_style, client)
    print(f"  Topic: {topic.get('topic')} [{topic.get('tail_type','?')} | {topic.get('competition_signal','?')}]")
    return topic


# ---------------------------------------------------------------------------
# Script Generation
# ---------------------------------------------------------------------------

def generate_content_script(topic: dict, client: anthropic.Anthropic) -> dict:
    print(f"  Generating CONTENT script for: {topic['topic']}")
    keyword   = topic.get("keyword", topic["topic"])
    question  = topic.get("question", topic["topic"])
    tail_type = topic.get("tail_type", "long_tail")
    angles    = load_niche_keywords().get("content_angles", [])
    angle     = random.choice(angles) if angles else "real talk"
    fmt       = topic.get("format", "avatar")

    structure_key  = random.choice(list(SCRIPT_STRUCTURES.keys()))
    structure_note = SCRIPT_STRUCTURES[structure_key]

    lo_hook,  hi_hook  = WORD_TARGETS_CONTENT["hook"]
    lo_prob,  hi_prob  = WORD_TARGETS_CONTENT["problem"]
    lo_story, hi_story = WORD_TARGETS_CONTENT["story"]
    lo_cta,   hi_cta   = WORD_TARGETS_CONTENT["solution_cta"]

    kw_guidance = (
        f"SHORT-TAIL keyword '{keyword}'. Explore the full emotional depth. LIVE it from the inside."
        if tail_type == "short_tail" else
        f"SPECIFIC keyword '{keyword}'. Answer the exact question implied. Be precise and emotionally honest."
    )

    cinematic_note = (
        "\nNOTE: This script will be delivered as a VOICEOVER over cinematic B-roll footage."
        "\nWrite for the ear only -- no visual references. The voice carries everything."
        if fmt == "cinematic" else ""
    )

    banned_openings_str = "\n".join(f'  - "{p}..."' for p in BANNED_OPENINGS)

    prompt = f"""Top-performing TikTok/Reels creator, men's mental health + recovery space.
Content gets millions of views -- RAW TRUTH, REAL STORIES men 35+ recognise.{cinematic_note}

Create a 4-scene script:
TOPIC: {topic['topic']}
SEARCH QUESTION: {question}
PRIMARY SEO KEYWORD: {keyword}
KEYWORD GUIDANCE: {kw_guidance}
CONTENT ANGLE: {angle}
COMPETITION: {topic.get('competition_signal', 'unknown')}

SCRIPT STRUCTURE FOR THIS VIDEO:
{structure_note}
The remaining 3 scenes follow: Problem/Truth -> Real Story or Insight -> Genuine Takeaway.

AUDIENCE: Men 35+, struggling silently with anxiety, depression, isolation, recovery.

PURE VALUE -- NOT AN AD:
- No MindCore AI mentions. No download CTA. No product plugs.
- Last scene = genuine human takeaway, not promotion.

WRITE FOR THE EAR:
- Natural spoken language, contractions, conversational connectors
- "And the thing is...", "Because here's what nobody tells you...", "The truth is..."
- Each scene flows naturally into the next.

BANNED OPENING PHRASES (do not start the hook with any of these):
{banned_openings_str}

WORD COUNTS:
- hook: {lo_hook}-{hi_hook} words
- problem: {lo_prob}-{hi_prob} words
- story: {lo_story}-{hi_story} words
- solution_cta: {lo_cta}-{hi_cta} words

Total ~130-150 words. No "hey guys". No "in today's video".
Weave '{keyword}' naturally at least once.

Return ONLY valid JSON, no markdown:
{{
  "video_type": "content",
  "topic": "{topic['topic']}",
  "seo_keyword": "{keyword}",
  "render_format": "{fmt}",
  "script_structure": "{structure_key}",
  "hook": {{"voiceover": "..."}},
  "problem": {{"voiceover": "..."}},
  "story": {{"voiceover": "..."}},
  "solution_cta": {{"voiceover": "..."}}
}}"""
    return _call_claude_raw(prompt, client, max_tokens=1200)


def generate_ad_script(app_facts: dict, client: anthropic.Anthropic) -> dict:
    """
    Informational, content-first ad script.
    Hook and Problem are pure education -- no selling.
    Story introduces MindCore AI naturally as the solution with specific detail.
    CTA is a soft, genuine recommendation -- not a hard sell.
    """
    ad_topic      = random.choice(AD_TOPICS)
    structure_key = random.choice(list(SCRIPT_STRUCTURES.keys()))

    print(f"  Generating INFORMATIONAL AD script...")
    print(f"  Pain point: {ad_topic['pain_point'][:65]}...")

    lo_hook,  hi_hook  = WORD_TARGETS_AD["hook"]
    lo_prob,  hi_prob  = WORD_TARGETS_AD["problem"]
    lo_story, hi_story = WORD_TARGETS_AD["story"]
    lo_cta,   hi_cta   = WORD_TARGETS_AD["solution_cta"]

    banned_openings_str = "\n".join(f'  - "{p}..."' for p in BANNED_OPENINGS)

    prompt = f"""Expert men's mental health content creator and performance marketer.

Write an informational, engaging video script for MindCore AI.
This is an AD but it MUST feel like content for the first two scenes.
The audience should feel understood and nodding before they realise it's an ad.

STRUCTURE: Hook -> Insight/Truth -> How MindCore AI Helps -> Soft Recommendation
AUDIENCE: Men 35+, struggling with mental health, anxiety, recovery or emotional numbness.
TONE: Knowledgeable, warm, honest. Like a trusted friend who found something that actually works.
LENGTH: ~120-140 words total. A proper, full-length video — not a 20-second pitch.

PAIN POINT FOR THIS AD:
{ad_topic['pain_point']}

CORE INSIGHT (what the problem/truth scene should convey):
{ad_topic['insight']}

HOW MINDCORE AI HELPS (what the story scene should convey — be specific):
{ad_topic['feature']}
Also mention: private, available 24/7, built for men, on Google Play, free first week.

SCENE RULES:
- hook: Stops the scroll. No MindCore AI. Pure emotional truth.
- problem: Expands the insight. No MindCore AI. Just honest, informed content.
- story: Introduce MindCore AI naturally as the solution.
  Start with something like "There's a tool built specifically for men called MindCore AI..."
  Be specific — what does it actually do? How does it help with THIS pain point?
- solution_cta: One sentence of genuine encouragement + one soft recommendation.
  Must end with: "Find MindCore AI on Google Play."
  Make it feel like advice, not an advert.

BANNED: "download now", "try it for free", "free trial"
BANNED OPENING PHRASES for hook:
{banned_openings_str}

SCRIPT STRUCTURE FOR HOOK:
{SCRIPT_STRUCTURES[structure_key]}

WORD COUNTS:
- hook: {lo_hook}-{hi_hook} words
- problem: {lo_prob}-{hi_prob} words
- story: {lo_story}-{hi_story} words
- solution_cta: {lo_cta}-{hi_cta} words

Return ONLY valid JSON, no markdown:
{{
  "video_type": "ad",
  "topic": "{ad_topic['pain_point'][:55]}",
  "seo_keyword": "AI mental health coach for men",
  "render_format": "avatar",
  "script_structure": "{structure_key}",
  "hook": {{"voiceover": "..."}},
  "problem": {{"voiceover": "..."}},
  "story": {{"voiceover": "..."}},
  "solution_cta": {{"voiceover": "..."}}
}}"""
    return _call_claude_raw(prompt, client, max_tokens=1200)


def build_full_script(script: dict) -> str:
    parts = []
    for scene in SCENE_ORDER:
        vo = script[scene]["voiceover"].strip()
        if vo and vo[-1] not in ".!?":
            vo += "."
        parts.append(vo)
    return "  ".join(parts)


# ---------------------------------------------------------------------------
# AVATAR PATH -- HeyGen /v3/videos
# ---------------------------------------------------------------------------

def submit_heygen_video(script_text: str, avatar_id: str, voice_id: str,
                        background_color: str, natural_gestures: bool) -> str:
    headers = {"X-Api-Key": HEYGEN_API_KEY, "Content-Type": "application/json"}
    MOTION_PROMPT = (
        "Gesturing naturally with hands while presenting. "
        "Warm eye contact. Nodding gently on emotional points. "
        "Open palm gestures when sharing insights. "
        "Grounded upper body movement throughout."
    )
    payload = {
        "type":                "avatar",
        "avatar_id":           avatar_id,
        "voice_id":            voice_id,
        "script":              script_text,
        "motion_prompt":       MOTION_PROMPT,
        "expressiveness":      "high",
        "dimension":           {"width": 1080, "height": 1920},
        "aspect_ratio":        "9:16",
        "use_avatar_iv_model": True,
        "super_resolution":    True,
        "talking_style":       "expressive",
    }
    print(f"  HeyGen: POST /v3/videos | type=avatar | expressiveness=high")
    resp = requests.post(HEYGEN_V3_URL, headers=headers, json=payload, timeout=30)
    print(f"  v3/videos response [{resp.status_code}]: {resp.text[:200]}")
    if not resp.ok:
        raise RuntimeError(f"HeyGen v3/videos failed {resp.status_code}: {resp.text}")
    data     = resp.json()
    video_id = (data.get("data", {}).get("video_id") or data.get("video_id")
                or data.get("data", {}).get("id") or data.get("id"))
    if not video_id:
        raise RuntimeError(f"No video_id in HeyGen response: {data}")
    print(f"  Submitted -- video_id: {video_id}")
    return video_id


def poll_heygen_video(video_id: str) -> str:
    headers  = {"X-Api-Key": HEYGEN_API_KEY}
    deadline = time.time() + VIDEO_TIMEOUT
    while time.time() < deadline:
        resp = requests.get(HEYGEN_STATUS_URL, headers=headers,
                            params={"video_id": video_id}, timeout=30)
        resp.raise_for_status()
        data   = resp.json().get("data", {})
        status = data.get("status", "unknown")
        if status == "completed":
            url = data.get("video_url")
            if not url:
                raise RuntimeError(f"Completed but no video_url: {data}")
            print("  HeyGen render complete!")
            return url
        if status in ("failed", "error"):
            raise RuntimeError(f"HeyGen render failed: {data}")
        elapsed = int(time.time() - (deadline - VIDEO_TIMEOUT))
        print(f"    waiting... status={status} ({elapsed}s elapsed)")
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"HeyGen timed out after {VIDEO_TIMEOUT}s")


def render_avatar_video(script_text: str, cfg: dict) -> str:
    avatar_id        = pick_avatar_look(cfg)
    voice_id         = cfg.get("voice_id", "")
    background_color = cfg.get("background_color", "#07071a")
    natural_gestures = cfg.get("use_natural_gestures", True)
    video_id  = submit_heygen_video(script_text, avatar_id, voice_id, background_color, natural_gestures)
    video_url = poll_heygen_video(video_id)
    raw_path   = str(OUTPUT_DIR / "mindcore_ai_raw.mp4")
    final_path = str(OUTPUT_DIR / "mindcore_ai_video.mp4")
    download_video(video_url, raw_path)
    crop_to_portrait(raw_path, final_path)
    return final_path


# ---------------------------------------------------------------------------
# CINEMATIC PATH -- Fish Audio TTS + Pexels B-roll + FFmpeg
# ---------------------------------------------------------------------------

def generate_fish_audio_tts(script_text: str, output_path: str) -> str:
    if not FISH_AUDIO_API_KEY:
        raise RuntimeError("FISH_AUDIO_API_KEY not set")
    headers = {
        "Authorization": f"Bearer {FISH_AUDIO_API_KEY}",
        "Content-Type":  "application/json",
    }
    payload = {
        "text":         script_text,
        "reference_id": FISH_AUDIO_VOICE_ID,
        "format":       "mp3",
        "mp3_bitrate":  192,
        "latency":      "normal",
    }
    print(f"  Fish Audio TTS: voice={FISH_AUDIO_VOICE_ID[:8]}... | {len(script_text)} chars")
    resp = requests.post(FISH_AUDIO_TTS_URL, headers=headers, json=payload,
                         stream=True, timeout=120)
    if not resp.ok:
        raise RuntimeError(f"Fish Audio TTS failed {resp.status_code}: {resp.text[:300]}")
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65_536):
            if chunk:
                f.write(chunk)
    size_kb = Path(output_path).stat().st_size / 1024
    print(f"  TTS saved: {output_path} ({size_kb:.0f} KB)")
    return output_path


def get_audio_duration(audio_path: str) -> float:
    cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
           "-of", "csv=p=0", audio_path]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


def search_pexels_clips(queries: list, num_clips: int = PEXELS_CLIPS_PER_VIDEO) -> list:
    if not PEXELS_API_KEY:
        raise RuntimeError("PEXELS_API_KEY not set")
    headers  = {"Authorization": PEXELS_API_KEY}
    clips    = []
    seen_ids = set()

    for query in queries:
        if len(clips) >= num_clips:
            break
        for orientation in ("portrait", None):
            if len(clips) >= num_clips:
                break
            params = {"query": query, "per_page": 5, "size": "medium"}
            if orientation:
                params["orientation"] = orientation
            try:
                resp = requests.get(PEXELS_VIDEO_URL, headers=headers, params=params, timeout=30)
                if not resp.ok:
                    print(f"  Pexels [{query}] {resp.status_code} -- skipping")
                    break
                for video in resp.json().get("videos", []):
                    vid_id = video["id"]
                    if vid_id in seen_ids:
                        continue
                    seen_ids.add(vid_id)
                    files          = video.get("video_files", [])
                    portrait_files = [f for f in files if f.get("width", 1) < f.get("height", 1)]
                    chosen_files   = portrait_files if portrait_files else files
                    chosen_files   = [f for f in chosen_files if f.get("height", 0) <= 1920]
                    chosen_files.sort(key=lambda x: x.get("height", 0), reverse=True)
                    if chosen_files:
                        clips.append({"url": chosen_files[0]["link"], "query": query,
                                      "id": vid_id, "duration": video.get("duration", 10)})
                        if len(clips) >= num_clips:
                            break
                time.sleep(0.3)
            except Exception as e:
                print(f"  Pexels search error for '{query}': {e}")
                break

    print(f"  Pexels: found {len(clips)} clips from {len(queries)} queries")
    return clips[:num_clips]


def download_clip(url: str, output_path: str) -> str:
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65_536):
            if chunk:
                f.write(chunk)
    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"  Downloaded: {Path(output_path).name} ({size_mb:.1f} MB)")
    return output_path


def process_clip_to_portrait(clip_path: str, output_path: str, duration: float) -> str:
    cmd = [
        "ffmpeg",
        "-stream_loop", "-1",
        "-i", clip_path,
        "-vf", (
            "scale=1080:1920:force_original_aspect_ratio=increase,"
            "crop=1080:1920,"
            "fps=30"
        ),
        "-t", str(duration),
        "-an",
        "-c:v", "libx264", "-crf", "20", "-preset", "fast",
        "-y", output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Clip processing failed: {result.stderr[-300:]}")
    return output_path


def assemble_cinematic_video(clip_paths: list, audio_path: str, output_path: str):
    audio_duration = get_audio_duration(audio_path)
    n              = len(clip_paths)
    clip_duration  = audio_duration / n
    print(f"  Assembling: {n} clips x {clip_duration:.1f}s = {audio_duration:.1f}s total")

    processed = []
    for i, raw_path in enumerate(clip_paths):
        out = str(OUTPUT_DIR / f"clip_{i}_processed.mp4")
        try:
            process_clip_to_portrait(raw_path, out, clip_duration)
            processed.append(out)
            print(f"  Clip {i+1}/{n} processed ({clip_duration:.1f}s)")
        except Exception as e:
            print(f"  Clip {i+1} failed ({e}) -- skipping")

    if not processed:
        raise RuntimeError("No clips processed successfully")

    if len(processed) < n:
        clip_duration = audio_duration / len(processed)
        print(f"  Re-processing {len(processed)} clips at {clip_duration:.1f}s each")
        reprocessed = []
        for i, raw_path in enumerate(clip_paths[:len(processed)]):
            out = str(OUTPUT_DIR / f"clip_{i}_adj.mp4")
            try:
                process_clip_to_portrait(raw_path, out, clip_duration)
                reprocessed.append(out)
            except Exception:
                pass
        processed = reprocessed

    concat_file = OUTPUT_DIR / "concat.txt"
    with open(concat_file, "w") as f:
        for p in processed:
            f.write(f"file '{Path(p).resolve()}'\n")

    concat_video = str(OUTPUT_DIR / "concat_video.mp4")
    cmd = [
        "ffmpeg", "-f", "concat", "-safe", "0",
        "-i", str(concat_file),
        "-c:v", "libx264", "-crf", "16", "-preset", "slow",
        "-t", str(audio_duration),
        "-y", concat_video
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Concat failed: {result.stderr[-500:]}")
    print(f"  Concat complete: {audio_duration:.1f}s")

    cmd = [
        "ffmpeg",
        "-i", concat_video,
        "-i", audio_path,
        "-map", "0:v:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-t", str(audio_duration),
        "-y", output_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Audio mix failed: {result.stderr[-500:]}")

    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    w, h    = get_video_dimensions(output_path)
    print(f"  Cinematic final: {output_path} ({w}x{h} | {size_mb:.1f} MB)")


def render_cinematic_video(script_text: str, pexels_queries: list) -> str:
    print("\n  [Cinematic] Generating voiceover via Fish Audio...")
    audio_path = str(OUTPUT_DIR / "voiceover.mp3")
    generate_fish_audio_tts(script_text, audio_path)

    print(f"\n  [Cinematic] Searching Pexels B-roll: {pexels_queries}")
    clips = search_pexels_clips(pexels_queries, num_clips=PEXELS_CLIPS_PER_VIDEO)
    if not clips:
        raise RuntimeError("No Pexels clips found")

    print(f"\n  [Cinematic] Downloading {len(clips)} clips...")
    clips_dir = OUTPUT_DIR / "clips"
    clips_dir.mkdir(exist_ok=True)
    raw_clip_paths = []
    for i, clip in enumerate(clips):
        clip_path = str(clips_dir / f"raw_{i}.mp4")
        try:
            download_clip(clip["url"], clip_path)
            raw_clip_paths.append(clip_path)
        except Exception as e:
            print(f"  Clip {i+1} download failed ({e}) -- skipping")

    if not raw_clip_paths:
        raise RuntimeError("All clip downloads failed")

    print(f"\n  [Cinematic] Assembling video ({len(raw_clip_paths)} clips)...")
    final_path = str(OUTPUT_DIR / "mindcore_ai_video.mp4")
    assemble_cinematic_video(raw_clip_paths, audio_path, final_path)
    return final_path


# ---------------------------------------------------------------------------
# Shared video utilities
# ---------------------------------------------------------------------------

def download_video(url: str, output_path: str):
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65_536):
            if chunk:
                f.write(chunk)
    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"  Downloaded: {output_path} ({size_mb:.1f} MB)")


def get_video_dimensions(path: str) -> tuple:
    cmd = ["ffprobe", "-v", "error", "-select_streams", "v:0",
           "-show_entries", "stream=width,height", "-of", "csv=p=0", path]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    parts  = result.stdout.strip().split(",")
    return int(parts[0]), int(parts[1])


def detect_content_crop(video_path: str) -> tuple:
    cmd = ["ffmpeg", "-i", video_path, "-vf", "cropdetect=limit=30:round=2:reset=0",
           "-frames:v", "90", "-f", "null", "-"]
    result  = subprocess.run(cmd, capture_output=True, text=True)
    matches = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", result.stderr)
    if not matches:
        return None
    cw, ch, cx, cy = map(int, matches[-1])
    print(f"  cropdetect: {cw}x{ch} at x={cx}, y={cy}")
    return cw, ch, cx, cy


def make_portrait_filter(cw, ch, cx, cy) -> str:
    return (
        f"crop={cw}:{ch}:{cx}:{cy},"
        f"scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop=1080:1920:(iw-1080)/2:(ih-1920)/2,"
        f"fps=30"
    )


def crop_to_portrait(raw_path: str, final_path: str):
    w, h = get_video_dimensions(raw_path)
    print(f"  Raw dimensions: {w}x{h}")
    crop_result = detect_content_crop(raw_path)
    filter_str  = (make_portrait_filter(*crop_result) if crop_result
                   else make_portrait_filter(w, h, 0, 0))
    cmd = ["ffmpeg", "-i", raw_path, "-vf", filter_str,
           "-c:v", "libx264", "-crf", "16", "-preset", "slow",
           "-b:v", "4M", "-maxrate", "6M", "-bufsize", "8M",
           "-c:a", "copy", "-y", final_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-1000:]}")
    size_mb = Path(final_path).stat().st_size / (1024 * 1024)
    w2, h2  = get_video_dimensions(final_path)
    print(f"  Final: {final_path} ({w2}x{h2} | {size_mb:.1f} MB)")


# ---------------------------------------------------------------------------
# Metadata Generation
# ---------------------------------------------------------------------------

def generate_upload_guide(script: dict, mode: str, render_fmt: str, client: anthropic.Anthropic) -> str:
    print("  Generating upload guide...")
    full_vo    = " ".join(script[scene]["voiceover"] for scene in SCENE_ORDER)
    topic      = script.get("topic", "")
    seo_kw     = script.get("seo_keyword", "")
    video_type = script.get("video_type", mode)
    prompt = f"""Social media expert for TikTok, Instagram Reels, Facebook Reels and YouTube Shorts,
men's mental health niche.

Generate upload guide for all 4 platforms.
VIDEO TYPE: {video_type.upper()} | FORMAT: {render_fmt.upper()}
TOPIC: {topic} | SEO KEYWORD: {seo_kw}
FULL VOICEOVER: \"\"\"{full_vo}\"\"\"

TIKTOK / INSTAGRAM: Caption (keyword-first hook + 8-12 hashtags, max 2200 chars). Include {REQUIRED_BRAND_HASHTAG}.
FACEBOOK: Title (max 255 chars) + Description (2-3 sentences + question + hashtags). Include {REQUIRED_BRAND_HASHTAG}.
YOUTUBE SHORTS: Title (max 100 chars) + Description (sentences + mindcoreai.eu link + hashtags + #Shorts) + Tags.
ON-SCREEN TEXT OVERLAY: 1 punchy line to add manually when posting (e.g. the hook in bold text).
ALSO: Thumbnail suggestion + A/B hook idea.
Plain text, clear labels, copy-paste ready."""
    for attempt in range(1, CLAUDE_MAX_RETRIES + 1):
        try:
            msg = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=1500,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text.strip()
        except anthropic.APIStatusError as e:
            if e.status_code == 529:
                time.sleep(CLAUDE_RETRY_BASE * attempt)
            else:
                raise
    raise RuntimeError("Could not generate upload guide")


def generate_upload_metadata(script: dict, mode: str, client: anthropic.Anthropic) -> dict:
    print("  Generating platform metadata...")
    full_vo    = " ".join(script[scene]["voiceover"] for scene in SCENE_ORDER)
    topic      = script.get("topic", "")
    seo_kw     = script.get("seo_keyword", "")
    video_type = script.get("video_type", mode).upper()
    prompt = f"""Social media expert for men's mental health on TikTok, Instagram, Facebook and YouTube Shorts.

VIDEO TYPE: {video_type} | TOPIC: {topic} | SEO KEYWORD: {seo_kw}
FULL VOICEOVER: {full_vo}

RULES:
- tiktok_caption: keyword-first sentence + 8-10 hashtags inline. Max 2200 chars.
  MUST include: {REQUIRED_BRAND_HASHTAG} #mensmentalhealth
- facebook_title: max 255 chars, keyword-first
- facebook_description: 2-3 sentences + question + 5-6 hashtags. MUST include {REQUIRED_BRAND_HASHTAG}
- youtube_title: max 100 chars, scroll-stopping, search-friendly
- youtube_description: 2-4 sentences + blank line + "Try MindCore AI: https://mindcoreai.eu"
  + blank line + 6-8 hashtags ending with #Shorts. MUST include {REQUIRED_BRAND_HASHTAG}
- youtube_tags: comma-separated 8-12 keywords (no # symbols)

Return ONLY valid JSON, no markdown:
{{
  "tiktok_caption": "{REQUIRED_BRAND_HASHTAG} keyword-first sentence #hashtag2 ...",
  "facebook_title": "...",
  "facebook_description": "... {REQUIRED_BRAND_HASHTAG} ...",
  "youtube_title": "...",
  "youtube_description": "sentences\\n\\nTry MindCore AI: https://mindcoreai.eu\\n\\n{REQUIRED_BRAND_HASHTAG} #mentalhealth #Shorts",
  "youtube_tags": "keyword1, keyword2, keyword3"
}}"""
    for attempt in range(1, CLAUDE_MAX_RETRIES + 1):
        try:
            msg = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=900,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = msg.content[0].text.strip()
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
            metadata = json.loads(raw)
            for key in ("tiktok_caption", "facebook_description", "youtube_description"):
                metadata[key] = ensure_brand_hashtag(metadata.get(key, ""))
            metadata["youtube_title"] = metadata.get("youtube_title", "")[:YOUTUBE_TITLE_LIMIT]
            print(f"  TikTok+IG: {metadata.get('tiktok_caption','')[:80]}...")
            print(f"  Facebook:  {metadata.get('facebook_title','')[:60]}...")
            print(f"  YouTube:   {metadata.get('youtube_title','')[:60]}...")
            return metadata
        except (anthropic.APIStatusError, json.JSONDecodeError) as e:
            if attempt == CLAUDE_MAX_RETRIES:
                raise RuntimeError(f"Could not generate metadata: {e}")
            time.sleep(10)
    raise RuntimeError("Unexpected exit from metadata generation")


# ---------------------------------------------------------------------------
# Upload
# ---------------------------------------------------------------------------

def upload_to_platforms(video_path: str, metadata: dict, cfg: dict) -> dict:
    if not UPLOAD_POST_API_KEY:
        return {"skipped": True, "reason": "no API key"}
    user = cfg.get("upload_post_user", "")
    if not user:
        return {"skipped": True, "reason": "no user configured"}

    caption              = metadata.get("tiktok_caption", "")[:TIKTOK_CAPTION_LIMIT]
    facebook_title       = metadata.get("facebook_title", "")[:255]
    facebook_description = metadata.get("facebook_description", "")
    youtube_title        = metadata.get("youtube_title", "")[:YOUTUBE_TITLE_LIMIT]
    youtube_description  = metadata.get("youtube_description", "")[:YOUTUBE_DESCRIPTION_LIMIT]
    youtube_tags         = metadata.get("youtube_tags", "")

    print(f"  Uploading to TikTok + Facebook + Instagram + YouTube as '{user}'...")
    headers = {"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"}
    data = [
        ("user",                 user),
        ("platform[]",           "tiktok"),
        ("platform[]",           "facebook"),
        ("platform[]",           "instagram"),
        ("platform[]",           "youtube"),
        ("title",                caption),
        ("facebook_title",       facebook_title),
        ("facebook_description", facebook_description),
        ("youtube_title",        youtube_title),
        ("youtube_description",  youtube_description),
        ("youtube_tags",         youtube_tags),
    ]
    try:
        with open(video_path, "rb") as f:
            files  = [("video", ("mindcore_ai_video.mp4", f, "video/mp4"))]
            resp   = requests.post(UPLOAD_POST_API_URL, headers=headers,
                                   files=files, data=data, timeout=180)
        result = (resp.json() if resp.headers.get("content-type", "").startswith("application/json")
                  else {"raw": resp.text})
        result["status_code"] = resp.status_code
        print(f"  Upload {'successful' if resp.ok else 'WARNING'}: {resp.status_code}")
        if not resp.ok:
            print(f"  {resp.text[:300]}")
        return result
    except Exception as e:
        print(f"  Upload failed: {e}")
        return {"error": str(e)}


def save_upload_guide(guide_text: str, script: dict, mode: str, run_number: int, render_fmt: str):
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    topic        = script.get("topic", "N/A")
    seo_kw       = script.get("seo_keyword", "N/A")
    video_type   = script.get("video_type", mode).upper()
    structure    = script.get("script_structure", "unknown")
    total_words  = sum(len(script[s]["voiceover"].split()) for s in SCENE_ORDER)
    est_duration = round(total_words / 130 * 60)
    header = f"""================================================================================
  MINDCORE AI -- VIDEO UPLOAD GUIDE
  Run #{run_number} | {generated_at}
================================================================================
  Video type      : {video_type}
  Format          : {render_fmt.upper()} ({'HeyGen Avatar' if render_fmt == 'avatar' else 'Fish Audio TTS + Pexels B-roll'})
  Script structure: {structure}
  Topic           : {topic}
  SEO keyword     : {seo_kw}
  Est. length     : ~{est_duration}s ({total_words} words @ ~130 wpm)
  Output          : 1080x1920 9:16 30fps
  Platforms       : TikTok + Facebook + Instagram Reels + YouTube Shorts
  Schedule        : Avatar: Tue/Wed/Thu + ad Sundays | Cinematic: Mon/Fri + content Sundays
================================================================================

FULL SCRIPT
-----------
"""
    for scene in SCENE_ORDER:
        wc = len(script[scene]["voiceover"].split())
        header += f"[{scene.upper()}]  ({wc} words)\n{script[scene]['voiceover']}\n\n"
    header += "================================================================================\n"
    header += "  PLATFORM UPLOAD DETAILS\n"
    header += "================================================================================\n\n"
    full = header + guide_text + "\n\n================================================================================\n"
    (OUTPUT_DIR / "upload_guide.txt").write_text(full, encoding="utf-8")
    print(f"  Upload guide saved")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "clips").mkdir(exist_ok=True)

    mode          = determine_mode()
    cfg           = load_config()
    client        = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    upload_enabled = cfg.get("upload_enabled", False) and bool(UPLOAD_POST_API_KEY)
    topic_history  = load_topic_history()

    print(f"\n  MindCore AI Video Pipeline v5.5")
    print(f"  Run #{GITHUB_RUN_NUMBER} -- Mode: {mode.upper()}")
    print(f"  Formats: Avatar (HeyGen) + Cinematic (Fish Audio + Pexels B-roll)")
    print(f"  Platforms: TikTok + Facebook + Instagram + YouTube")
    print(f"  Schedule: Avatar Tue/Wed/Thu + ad Sundays | Cinematic Mon/Fri + content Sundays")
    print(f"  Fish Audio voice: {FISH_AUDIO_VOICE_ID[:8]}...")
    print(f"  Auto-upload: {'ENABLED' if upload_enabled else 'DISABLED'}")
    if FORCE_FORMAT:
        print(f"  Format override: {FORCE_FORMAT.upper()}")
    print("=" * 60)

    print("\n  Generating script...")
    if mode == "ad":
        # Ad: informational content-first, soft CTA at the end
        script         = generate_ad_script(load_app_facts(), client)
        script         = sanitize_script(script)
        render_fmt     = "avatar"
        pexels_queries = []
    else:
        topic          = fetch_trending_topic(client)
        script         = generate_content_script(topic, client)
        script         = sanitize_script(script)
        render_fmt     = topic.get("format", "avatar")
        pexels_queries = topic.get("pexels_queries", ["man thinking", "empty road", "lonely man"])
        save_topic_history(topic_history, topic.get("keyword", topic.get("topic", "")))

    script["render_format"] = render_fmt
    (OUTPUT_DIR / "script.json").write_text(json.dumps(script, indent=2))

    total_words  = sum(len(script[s]["voiceover"].split()) for s in SCENE_ORDER)
    est_duration = round(total_words / 130 * 60)

    print(f"\n  Video type:       {script.get('video_type', mode)}")
    print(f"  Topic:            {script.get('topic', 'N/A')}")
    print(f"  SEO kw:           {script.get('seo_keyword', 'N/A')}")
    print(f"  Script structure: {script.get('script_structure', 'N/A')}")
    print(f"  Render format:    {render_fmt.upper()}")
    print(f"  Est. length:      ~{est_duration}s ({total_words} words)")
    if render_fmt == "cinematic":
        print(f"  Pexels queries: {pexels_queries}")
    if est_duration > 60:
        print(f"  NOTE: >{est_duration}s -- YouTube will post as regular video, not Short.")
    print()
    for scene in SCENE_ORDER:
        wc = len(script[scene]["voiceover"].split())
        print(f"  [{scene:15s}]  {wc:2d} words  |  {script[scene]['voiceover']}")

    full_script = build_full_script(script)
    print(f"\n  Full script:\n  {full_script}")

    final_path = None
    if render_fmt == "cinematic":
        print(f"\n  Rendering CINEMATIC video...")
        try:
            final_path = render_cinematic_video(full_script, pexels_queries)
        except Exception as e:
            print(f"\n  CINEMATIC RENDER FAILED: {e}")
            print(f"  Falling back to AVATAR render...")
            render_fmt = "avatar"
            script["render_format"] = "avatar"

    if render_fmt == "avatar" or final_path is None:
        print(f"\n  Rendering AVATAR video (HeyGen)...")
        final_path = render_avatar_video(full_script, cfg)

    print("\n  Generating upload guide...")
    guide_text = generate_upload_guide(script, mode, render_fmt, client)
    save_upload_guide(guide_text, script, mode, GITHUB_RUN_NUMBER, render_fmt)

    upload_metadata = generate_upload_metadata(script, mode, client)
    (OUTPUT_DIR / "upload_metadata.json").write_text(json.dumps(upload_metadata, indent=2))

    if upload_enabled:
        print("\n  Uploading to all platforms...")
        upload_result = upload_to_platforms(final_path, upload_metadata, cfg)
        (OUTPUT_DIR / "upload_result.json").write_text(json.dumps(upload_result, indent=2))
    else:
        print("\n  Auto-upload disabled -- video saved for manual review")
        (OUTPUT_DIR / "upload_result.json").write_text(json.dumps({"skipped": True}, indent=2))

    print(f"\n  DONE")
    print(f"  Format: {render_fmt.upper()} | ~{est_duration}s | Structure: {script.get('script_structure','?')}")
    print(f"  Video:  {final_path}")
    if upload_enabled:
        print("  Posted: TikTok + Facebook + Instagram + YouTube")
    print("\n  Pipeline complete!")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n  FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
