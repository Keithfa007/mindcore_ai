#!/usr/bin/env python3
"""
MindCore AI Video Pipeline -- HeyGen Edition v3.4
===================================================

CHANGES (v3.4):
  Keyword research now finds BOTH short-tail AND long-tail low-competition
  keywords. Adds Google Autocomplete queries alongside PAA + Related Searches.
  Every candidate is tagged with word count and type so Claude can evaluate
  niche-specific short-tail (1-3 words, under big-brand radar) separately
  from long-tail specificity. Claude picks the best from either category.

CHANGES (v3.3):
  SERP-first keyword research -- PAA + Related Searches ranked by Claude.

CHANGES (v3.2):
  FFmpeg zoom-to-fill (cover mode) -- no black bars ever.

CHANGES (v3.1):
  Content scripts purely educational. Zero MindCore AI mentions.
  1-in-10 ad ratio handles all promotion.
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

# -- Config -------------------------------------------------------------------

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
HEYGEN_API_KEY    = os.environ["HEYGEN_API_KEY"]
SERP_API_KEY      = os.environ.get("SERP_API_KEY", "")

GITHUB_RUN_NUMBER = int(os.environ.get("GITHUB_RUN_NUMBER", "1"))

HEYGEN_SUBMIT_URL = "https://api.heygen.com/v2/video/generate"
HEYGEN_STATUS_URL = "https://api.heygen.com/v1/video_status.get"
SERP_API_URL      = "https://serpapi.com/search"

OUTPUT_DIR   = Path("video_pipeline/output")
PIPELINE_DIR = Path("video_pipeline")
SCENE_ORDER  = ["hook", "problem", "story", "solution_cta"]

POLL_INTERVAL = 15
VIDEO_TIMEOUT = 1200  # 20 minutes

CLAUDE_MAX_RETRIES = 10
CLAUDE_RETRY_BASE  = 30

# Seeds queried per run. 3 regular + 2 autocomplete = ~5 SerpAPI calls total
SERP_SEEDS_PER_RUN        = 3
AUTOCOMPLETE_SEEDS_PER_RUN = 2

WORD_LIMITS_AD = {
    "hook":         8,
    "problem":      12,
    "story":        14,
    "solution_cta": 14,
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

AD_CTA_POOL = [
    "Try it. Find MindCore AI on Google Play.",
    "Start your trial. Find us on Google Play.",
    "Give it a go. Search MindCore AI on Google Play.",
    "Try it today. MindCore AI on Google Play.",
    "It's waiting for you. Find MindCore AI on Google Play.",
    "Take the first step. MindCore AI on Google Play.",
    "You don't have to do this alone. Try MindCore AI on Google Play.",
    "Start when you're ready. MindCore AI on Google Play.",
]

BANNED_PHRASE_REPLACEMENTS = [
    (r"try\s+it\s+for\s+free",  "try it"),
    (r"download\s+now",         "find us on Google Play"),
    (r"free\s+trial",           "trial"),
]


# -- Helpers ------------------------------------------------------------------

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
        return {"seed_queries": ["men mental health tips"], "content_angles": ["real talk"]}
    with open(path) as f:
        return json.load(f)


# -- Script sanitizer ---------------------------------------------------------

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


# -- Ad validation ------------------------------------------------------------

def validate_ad_word_counts(script: dict) -> tuple:
    errors = []
    for scene in SCENE_ORDER:
        vo = script[scene]["voiceover"]
        wc = len(vo.split())
        hi = WORD_LIMITS_AD[scene]
        if wc > hi:
            errors.append(f"  [{scene}] {wc} words -- TOO LONG (max {hi}): '{vo}'")
    return (len(errors) == 0), errors


def generate_ad_with_validation(generate_fn, generate_args, max_attempts=3):
    for attempt in range(1, max_attempts + 1):
        script = generate_fn(*generate_args)
        script = sanitize_script(script)
        passed, errors = validate_ad_word_counts(script)
        if passed:
            print(f"  CHECKPOINT PASSED -- all word counts within limits")
            return script
        print(f"  CHECKPOINT FAILED (attempt {attempt}/{max_attempts}):")
        for e in errors:
            print(e)
        if attempt < max_attempts:
            print(f"  Regenerating script...")
        else:
            raise RuntimeError(
                f"Ad script exceeded word count limits after {max_attempts} attempts.\n"
                + "\n".join(errors)
            )
    raise RuntimeError("Unexpected exit from validation loop")


# -- Step 1a -- SERP Keyword Research (Short + Long Tail) ----------------------
#
# TWO RESEARCH PATHS run in parallel:
#
# PATH A -- Long-tail discovery (PAA + Related Searches)
#   Hit 3 seed queries via regular Google search.
#   Collect People Also Ask questions (4-10 words, real intent, lower
#   competition because they're specific) and Related Searches.
#
# PATH B -- Short-tail discovery (Google Autocomplete)
#   Hit 2 seed queries via Google Autocomplete endpoint.
#   Autocomplete returns 1-4 word suggestions -- what people are
#   actively typing RIGHT NOW. Short-tail can be low competition if
#   the niche is small enough that big health brands aren't targeting it.
#   Examples: "sobriety anger", "men crying", "emotional numbness men"
#
# Claude then ranks ALL candidates together, evaluating each on:
#   - Emotional resonance for men 35+
#   - Short-tail: is this niche-specific enough that WebMD/BetterHelp
#     aren't dominating it? (e.g. "sobriety anger" vs "anxiety")
#   - Long-tail: specificity as competition proxy
#   - Video potential in 30-45 seconds

def _serp_google_query(seed: str) -> dict:
    """Standard Google search via SerpAPI."""
    params = {
        "engine":  "google",
        "q":       seed,
        "api_key": SERP_API_KEY,
        "num":     10,
        "hl":      "en",
        "gl":      "us",
    }
    resp = requests.get(SERP_API_URL, params=params, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _serp_autocomplete_query(seed: str) -> list:
    """
    Google Autocomplete via SerpAPI.
    Returns a list of short suggestion strings (typically 1-5 words).
    These represent what people are actively typing -- great source of
    short-tail keywords with real search volume.
    """
    params = {
        "engine":  "google_autocomplete",
        "q":       seed,
        "api_key": SERP_API_KEY,
        "hl":      "en",
        "gl":      "us",
    }
    try:
        resp = requests.get(SERP_API_URL, params=params, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        return [s.get("value", "").strip() for s in data.get("suggestions", []) if s.get("value")]
    except Exception as e:
        print(f"  Autocomplete failed for '{seed}': {e}")
        return []


def _word_count(text: str) -> int:
    return len(text.split())


def _keyword_type(text: str) -> str:
    wc = _word_count(text)
    if wc <= 3:
        return "short_tail"
    elif wc <= 5:
        return "mid_tail"
    else:
        return "long_tail"


def research_keyword_candidates_from_serp(seeds: list) -> list:
    """
    Collect keyword candidates from two SerpAPI sources:

    1. Regular Google search (PAA + Related Searches + organic titles)
       -- strong for long-tail and mid-tail
    2. Google Autocomplete
       -- strong for short-tail (what people actually type)

    Each candidate is tagged with:
      - source: people_also_ask | related_search | autocomplete | organic_title
      - tail_type: short_tail | mid_tail | long_tail
      - word_count: integer
    """
    candidates = []
    seen       = set()

    # -- PATH A: Regular Google search (3 seeds) ------------------------------
    regular_seeds = random.sample(seeds, min(SERP_SEEDS_PER_RUN, len(seeds)))

    for seed in regular_seeds:
        try:
            data          = _serp_google_query(seed)
            total_results = int(
                str(data.get("search_information", {}).get("total_results", "0"))
                    .replace(",", "").replace(".", "") or "0"
            )

            # People Also Ask -- real questions, typically mid-to-long tail
            paa_count = 0
            for q in data.get("related_questions", []):
                text = q.get("question", "").strip()
                if text and text.lower() not in seen:
                    seen.add(text.lower())
                    candidates.append({
                        "text":          text,
                        "source":        "people_also_ask",
                        "tail_type":     _keyword_type(text),
                        "word_count":    _word_count(text),
                        "seed":          seed,
                        "total_results": total_results,
                    })
                    paa_count += 1

            # Related Searches -- mix of short and long tail
            rs_count = 0
            for r in data.get("related_searches", []):
                text = r.get("query", "").strip()
                if text and text.lower() not in seen:
                    seen.add(text.lower())
                    candidates.append({
                        "text":          text,
                        "source":        "related_search",
                        "tail_type":     _keyword_type(text),
                        "word_count":    _word_count(text),
                        "seed":          seed,
                        "total_results": 0,
                    })
                    rs_count += 1

            # Top 3 organic titles
            for org in data.get("organic_results", [])[:3]:
                title = org.get("title", "").strip()
                if title and title.lower() not in seen and len(title) < 120:
                    seen.add(title.lower())
                    candidates.append({
                        "text":          title,
                        "source":        "organic_title",
                        "tail_type":     _keyword_type(title),
                        "word_count":    _word_count(title),
                        "seed":          seed,
                        "total_results": total_results,
                    })

            print(f"  [GOOGLE] '{seed[:45]}': {paa_count} PAA | {rs_count} related | {total_results:,} results")
            time.sleep(0.5)

        except Exception as e:
            print(f"  Google search failed for '{seed}': {e}")

    # -- PATH B: Google Autocomplete (2 seeds) --------------------------------
    # Use shorter/broader seeds to get better short-tail suggestions
    # Extract the core 1-3 word concepts from seeds for autocomplete
    autocomplete_bases = []
    for seed in seeds:
        words = seed.split()
        # Take first 2-3 words as a shorter autocomplete base
        if len(words) >= 3:
            autocomplete_bases.append(" ".join(words[:2]))
            autocomplete_bases.append(" ".join(words[:3]))
        else:
            autocomplete_bases.append(seed)

    # Deduplicate and sample
    autocomplete_bases = list(set(autocomplete_bases))
    ac_seeds = random.sample(autocomplete_bases, min(AUTOCOMPLETE_SEEDS_PER_RUN, len(autocomplete_bases)))

    for ac_seed in ac_seeds:
        suggestions = _serp_autocomplete_query(ac_seed)
        ac_count    = 0
        for text in suggestions:
            if text and text.lower() not in seen and _word_count(text) <= 6:
                seen.add(text.lower())
                candidates.append({
                    "text":          text,
                    "source":        "autocomplete",
                    "tail_type":     _keyword_type(text),
                    "word_count":    _word_count(text),
                    "seed":          ac_seed,
                    "total_results": 0,  # unknown without separate lookup
                })
                ac_count += 1
        if ac_count:
            print(f"  [AUTOCOMPLETE] '{ac_seed}': {ac_count} suggestions")
        time.sleep(0.5)

    # Summary
    short = sum(1 for c in candidates if c["tail_type"] == "short_tail")
    mid   = sum(1 for c in candidates if c["tail_type"] == "mid_tail")
    long  = sum(1 for c in candidates if c["tail_type"] == "long_tail")
    print(f"  Total candidates: {len(candidates)} ({short} short | {mid} mid | {long} long tail)")

    return candidates


def rank_and_select_keyword_claude(candidates: list, client: anthropic.Anthropic) -> dict:
    """
    Send all SERP candidates to Claude -- both short-tail and long-tail.

    Claude evaluates each on:
    - Short-tail (1-3 words): Is this niche-specific enough that WebMD,
      BetterHelp, and Mayo Clinic are NOT dominating it? Niche emotional
      terms like "sobriety anger", "men crying", "emotional numbness" can
      be short AND low-competition because big brands don't bother.
    - Long-tail (4+ words): Specificity as competition proxy.
    - Emotional resonance for men 35+ regardless of tail type.

    Returns the single best candidate.
    """
    if not candidates:
        raise ValueError("No SERP candidates to rank")

    # Sort: short-tail first (new priority), then PAA, then rest
    type_order   = {"short_tail": 0, "mid_tail": 1, "long_tail": 2}
    source_order = {"autocomplete": 0, "people_also_ask": 1, "related_search": 2, "organic_title": 3}
    sorted_cands = sorted(
        candidates,
        key=lambda c: (type_order.get(c["tail_type"], 3), source_order.get(c["source"], 4))
    )

    # Build candidate list with tail type visible to Claude
    candidate_list = "\n".join([
        f"{i+1}. [{c['tail_type'].upper()} | {c['source'].upper()} | {c['word_count']}w] {c['text']}"
        for i, c in enumerate(sorted_cands[:50])
    ])

    prompt = f"""You are an expert in SEO and content strategy for men's mental health, recovery, sobriety, and anxiety on TikTok and Facebook Reels.

Below are REAL search queries collected from Google (Autocomplete, People Also Ask, Related Searches, organic results). Each is labelled with its tail type and word count.

YOUR TASK: Choose the SINGLE BEST keyword/topic to make a short video about today.

IMPORTANT -- THIS RUN SHOULD FAVOUR SHORT-TAIL IF POSSIBLE:
Short-tail keywords (1-3 words) are NOT always high competition. In niche emotional spaces like men's sobriety, grief, emotional numbness, or recovery -- short phrases can be LOW competition because big health brands (WebMD, NHS, BetterHelp, Mayo Clinic) don't create content for them. They go after clinical, broad terms. The raw emotional short-tail is often owned by individual creators.

LOW-COMPETITION SHORT-TAIL SIGNALS (prefer these):
- Emotionally raw and specific to men: "sobriety anger", "men crying", "numb after drinking", "emotional shutdown"
- Not clinical language: "anxiety attack" = high competition; "anxiety men" or "anxiety alone" = potentially low
- Not broad wellness: "mental health tips" = high; "men breaking down" = low
- Something a man would type into his phone at 2am, not something a doctor would write

SCORING (in order):
1. EMOTIONAL RESONANCE -- Would a man aged 35-55 struggling silently with anxiety, depression, isolation, or sobriety STOP scrolling for this?
2. COMPETITION REALITY -- For short-tail: is this niche enough to avoid big brand dominance? For long-tail: is it specific enough?
3. NICHE FIT -- Men's mental health, sobriety, recovery, emotional struggles, isolation.
4. VIDEO POTENTIAL -- Can this become a powerful 30-45 second spoken word video?

CANDIDATES (sorted short-tail first):
{candidate_list}

Return ONLY valid JSON, no markdown fences:
{{
  "topic": "the exact text of the chosen candidate",
  "question": "how a man would type this into Google naturally",
  "keyword": "the primary 1-5 word SEO keyword for the script",
  "tail_type": "short_tail|mid_tail|long_tail",
  "competition_signal": "low|medium|high",
  "why": "one sentence: why this beats the others for our specific audience",
  "source": "autocomplete|people_also_ask|related_search|organic_title"
}}"""

    result = _call_claude_raw(prompt, client, max_tokens=500)
    tail   = result.get("tail_type", "?")
    comp   = result.get("competition_signal", "?")
    kw     = result.get("keyword", "?")
    print(f"  Winner: '{kw}' [{tail} | {comp} competition]")
    print(f"  Reason: {result.get('why', '')}")
    return result


def fetch_trending_topic_claude_fallback(seeds: list, client: anthropic.Anthropic) -> dict:
    """Fallback when SERP unavailable -- Claude generates both short and long tail options."""
    seed = random.choice(seeds)
    prompt = f"""You are an SEO expert for men's mental health, recovery, anxiety, sobriety content.

Generate ONE keyword/topic for a short TikTok/Reels video.
Related to: "{seed}"

IMPORTANT: Consider BOTH short-tail (1-3 words, niche emotional terms big brands ignore)
AND long-tail (4+ words, specific questions). Pick whichever is stronger.

Low-competition short-tail examples: "sobriety anger", "men crying alone", "emotional numbness"
Low-competition long-tail examples: "why do I feel worse after stopping drinking"

Return ONLY valid JSON, no markdown:
{{
  "topic": "the keyword or question",
  "question": "how a man would type this into Google",
  "keyword": "primary 1-5 word SEO keyword",
  "tail_type": "short_tail|mid_tail|long_tail",
  "competition_signal": "low|medium|high",
  "why": "one sentence rationale",
  "source": "claude_generated"
}}"""
    return _call_claude_raw(prompt, client, max_tokens=300)


def fetch_trending_topic(client: anthropic.Anthropic) -> dict:
    """
    Main topic research function.
    Queries Google for both short-tail (autocomplete) and long-tail
    (PAA + related searches), then Claude picks the best from either.
    Falls back to Claude generation if SERP unavailable.
    """
    keywords = load_niche_keywords()
    seeds    = keywords["seed_queries"]

    if SERP_API_KEY:
        print(f"  Keyword research: {SERP_SEEDS_PER_RUN} Google searches + {AUTOCOMPLETE_SEEDS_PER_RUN} autocomplete queries...")
        try:
            candidates = research_keyword_candidates_from_serp(seeds)
            if candidates:
                topic = rank_and_select_keyword_claude(candidates, client)
                topic["source"] = f"serp_{topic.get('source', 'research')}"
                # Save research log
                log_path = OUTPUT_DIR / "keyword_research.json"
                log_path.write_text(json.dumps({
                    "run":        GITHUB_RUN_NUMBER,
                    "candidates": candidates,
                    "winner":     topic,
                }, indent=2))
                return topic
            else:
                print("  No SERP candidates found -- falling back to Claude")
        except Exception as e:
            print(f"  SERP research failed ({e}) -- falling back to Claude")

    print("  Generating topic with Claude (no SERP)...")
    topic = fetch_trending_topic_claude_fallback(seeds, client)
    print(f"  Topic: {topic.get('topic')} [{topic.get('tail_type','?')} | {topic.get('competition_signal', '?')}]")
    return topic


# -- Step 1b -- Script Generation ---------------------------------------------

def generate_content_script(topic: dict, client: anthropic.Anthropic) -> dict:
    print(f"  Generating CONTENT script for: {topic['topic']}")
    keyword   = topic.get("keyword", topic["topic"])
    question  = topic.get("question", topic["topic"])
    tail_type = topic.get("tail_type", "long_tail")
    angles    = load_niche_keywords().get("content_angles", [])
    angle     = random.choice(angles) if angles else "real talk"

    lo_hook,  hi_hook  = WORD_TARGETS_CONTENT["hook"]
    lo_prob,  hi_prob  = WORD_TARGETS_CONTENT["problem"]
    lo_story, hi_story = WORD_TARGETS_CONTENT["story"]
    lo_cta,   hi_cta   = WORD_TARGETS_CONTENT["solution_cta"]

    # Tailor script guidance based on keyword type
    if tail_type == "short_tail":
        kw_guidance = (
            f"This is a SHORT-TAIL keyword ('{keyword}'). The script must explore the full "
            f"emotional depth behind this short phrase. Don't just define it -- LIVE it. "
            f"Show what it feels like from the inside."
        )
    else:
        kw_guidance = (
            f"This is a SPECIFIC keyword ('{keyword}'). The script must answer the exact "
            f"question or struggle implied. Be precise and emotionally honest."
        )

    prompt = f"""You are a top-performing TikTok and Facebook Reels content creator in the men's
mental health and recovery space. Your content gets millions of views because it speaks
RAW TRUTH and shares REAL STORIES that men 35+ actually recognise from their own lives.

Create a 4-scene short video script on this topic:
TOPIC: {topic['topic']}
SEARCH QUESTION: {question}
PRIMARY SEO KEYWORD: {keyword}
KEYWORD TYPE: {tail_type}
CONTENT ANGLE: {angle}
COMPETITION LEVEL: {topic.get('competition_signal', 'unknown')}

KEYWORD GUIDANCE: {kw_guidance}

FORMAT: Hook -> Problem/Truth -> Real Story or Insight -> Genuine Takeaway

AUDIENCE: Men 35+, in recovery or struggling with anxiety, depression, isolation.
They feel alone. They don't ask for help. Speak like someone who has genuinely been through it.

THIS IS PURE VALUE CONTENT -- NOT AN AD:
- Do NOT mention MindCore AI, any app, any product, or any service.
- The last scene is a GENUINE HUMAN TAKEAWAY -- a real insight or honest truth.

WRITE FOR THE EAR, NOT THE EYE:
- Natural spoken language -- contractions, pauses, conversational connectors
- Use connectors: "And the thing is...", "Because here's what nobody tells you...",
  "The truth is...", "What actually helped was...", "And if that's you right now..."
- Each scene = one continuous thought, not bullet points.

TARGET word counts per scene:
- hook:         {lo_hook}-{hi_hook} words  -- One striking line that stops the scroll
- problem:      {lo_prob}-{hi_prob} words  -- Name the pain honestly, make them feel seen
- story:        {lo_story}-{hi_story} words -- Real story or insight, specific and human
- solution_cta: {lo_cta}-{hi_cta} words  -- A genuine takeaway or truth. No promotion.

Total: ~130-150 words. No generic openers. No "hey guys". No "in today's video".
Weave '{keyword}' naturally at least once.

Return ONLY valid JSON, no markdown fences:
{{
  "video_type": "content",
  "topic": "{topic['topic']}",
  "seo_keyword": "{keyword}",
  "hook": {{"voiceover": "..."}},
  "problem": {{"voiceover": "..."}},
  "story": {{"voiceover": "..."}},
  "solution_cta": {{"voiceover": "..."}}
}}"""

    return _call_claude_raw(prompt, client, max_tokens=1200)


def generate_ad_script(app_facts: dict, client: anthropic.Anthropic) -> dict:
    cta = random.choice(AD_CTA_POOL)
    print(f"  Generating APP AD script... CTA: \"{cta}\"")

    prompt = f"""You are a performance marketing copywriter for MindCore AI.
Write a 4-scene video ad: Hook -> Problem -> Story -> Solution+CTA.

AUDIENCE: Men 35+, in recovery or struggling with anxiety, depression, isolation.
TONE: Raw, honest, brotherly. Not salesy. Not clinical. Sounds like a real person talking.

TARGET LENGTH: ~20 seconds total. Short, punchy, every word earns its place.

BANNED PHRASES:
- "try it for free" -- say ONLY "try it"
- "free trial" -- say ONLY "trial"
- "download now" -- say "find us on Google Play"
- NEVER mention specific numbers like "50 messages" or "5 voice minutes"

ABOUT MINDCORE AI:
- AI mental wellness companion for men, on Google Play
- Free trial, no credit card required
- Real AI conversation, any time, no judgement

THE SOLUTION_CTA MUST END WITH EXACTLY THIS SENTENCE:
"{cta}"

SEO KEYWORDS: {', '.join(SEO_KEYWORDS)}

STRICT WORD COUNT:
- hook:         up to 8 words
- problem:      up to 12 words
- story:        up to 14 words
- solution_cta: up to 14 words

Return ONLY valid JSON, no markdown fences:
{{
  "video_type": "ad",
  "topic": "MindCore AI -- your AI mental wellness companion",
  "seo_keyword": "AI mental health coach for men",
  "hook": {{"voiceover": "..."}},
  "problem": {{"voiceover": "..."}},
  "story": {{"voiceover": "..."}},
  "solution_cta": {{"voiceover": "..."}}
}}"""

    return _call_claude_raw(prompt, client, max_tokens=800)


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


# -- Step 2 -- Build full script ----------------------------------------------

def build_full_script(script: dict) -> str:
    parts = []
    for scene in SCENE_ORDER:
        vo = script[scene]["voiceover"].strip()
        if vo and vo[-1] not in ".!?":
            vo += "."
        parts.append(vo)
    return "  ".join(parts)


# -- Step 3 -- Submit to HeyGen -----------------------------------------------

def submit_heygen_video(script_text: str, avatar_id: str, voice_id: str,
                        background_color: str, natural_gestures: bool) -> str:
    headers = {
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json",
    }

    voice_config = {"type": "text", "input_text": script_text}
    if voice_id:
        voice_config["voice_id"] = voice_id

    payload = {
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id,
                },
                "voice": voice_config,
                "background": {
                    "type": "color",
                    "value": background_color,
                },
            }
        ],
        "dimension":    {"width": 1080, "height": 1920},
        "aspect_ratio": "9:16",
        "test": False,
    }

    if not natural_gestures:
        MOTION_PROMPT = (
            "Deliver this as a grounded, emotionally present mental health speaker. "
            "Hands mostly still and relaxed at rest. Reserve hand movement for key moments only. "
            "Slow deliberate gestures -- open palms or hand on chest for personal experience. "
            "Nod gently on empathetic statements. Soft warm eye contact. "
            "Go completely still at profound statements. Trusted older brother tone."
        )
        payload["use_avatar_iv_model"]          = True
        payload["custom_motion_prompt"]         = MOTION_PROMPT
        payload["enhance_custom_motion_prompt"] = True
        print(f"  Motion: CUSTOM PROMPT")
    else:
        print(f"  Motion: NATURAL (avatar's own trained gestures)")

    resp = requests.post(HEYGEN_SUBMIT_URL, headers=headers, json=payload, timeout=30)
    if not resp.ok:
        raise RuntimeError(f"HeyGen submit failed {resp.status_code}: {resp.text}")

    data     = resp.json()
    video_id = data.get("data", {}).get("video_id") or data.get("video_id")
    if not video_id:
        raise RuntimeError(f"No video_id in HeyGen response: {data}")

    print(f"  Submitted -- video_id: {video_id}")
    return video_id


# -- Step 4 -- Poll -----------------------------------------------------------

def poll_heygen_video(video_id: str) -> str:
    headers  = {"X-Api-Key": HEYGEN_API_KEY}
    deadline = time.time() + VIDEO_TIMEOUT

    while time.time() < deadline:
        resp = requests.get(
            HEYGEN_STATUS_URL,
            headers=headers,
            params={"video_id": video_id},
            timeout=30,
        )
        resp.raise_for_status()
        data   = resp.json().get("data", {})
        status = data.get("status", "unknown")

        if status == "completed":
            url = data.get("video_url")
            if not url:
                raise RuntimeError(f"Completed but no video_url: {data}")
            print(f"  HeyGen render complete!")
            return url

        if status in ("failed", "error"):
            raise RuntimeError(f"HeyGen render failed: {data}")

        elapsed = int(time.time() - (deadline - VIDEO_TIMEOUT))
        print(f"    waiting... status={status} ({elapsed}s elapsed)")
        time.sleep(POLL_INTERVAL)

    raise TimeoutError(f"HeyGen timed out after {VIDEO_TIMEOUT}s")


# -- Step 5 -- Download -------------------------------------------------------

def download_video(url: str, output_path: str):
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65_536):
            if chunk:
                f.write(chunk)
    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"  Downloaded: {output_path} ({size_mb:.1f} MB)")


# -- Step 5b -- Force 9:16 portrait with zoom-to-fill ------------------------

def get_video_dimensions(path: str) -> tuple:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0",
        path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    parts  = result.stdout.strip().split(",")
    return int(parts[0]), int(parts[1])


def detect_content_crop(video_path: str) -> tuple:
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", "cropdetect=limit=30:round=2:reset=0",
        "-frames:v", "90",
        "-f", "null", "-"
    ]
    result  = subprocess.run(cmd, capture_output=True, text=True)
    matches = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", result.stderr)
    if not matches:
        return None
    cw, ch, cx, cy = map(int, matches[-1])
    print(f"  cropdetect: content area {cw}x{ch} at x={cx}, y={cy}")
    return cw, ch, cx, cy


def make_portrait_filter(cw: int, ch: int, cx: int, cy: int) -> str:
    """Cover mode: zoom to fill 1080x1920, center crop, no black bars."""
    return (
        f"crop={cw}:{ch}:{cx}:{cy},"
        f"scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop=1080:1920:(iw-1080)/2:(ih-1920)/2,"
        f"fps=30"
    )


def crop_to_portrait(raw_path: str, final_path: str):
    w, h = get_video_dimensions(raw_path)
    print(f"  Raw video dimensions: {w}x{h}")

    crop_result = detect_content_crop(raw_path)
    if crop_result:
        cw, ch, cx, cy = crop_result
        filter_str = make_portrait_filter(cw, ch, cx, cy)
    else:
        print(f"  cropdetect found no bars -- using full frame")
        filter_str = make_portrait_filter(w, h, 0, 0)

    print(f"  FFmpeg filter: {filter_str}")

    cmd = [
        "ffmpeg", "-i", raw_path,
        "-vf", filter_str,
        "-c:v", "libx264",
        "-crf", "16",
        "-preset", "slow",
        "-b:v", "4M",
        "-maxrate", "6M",
        "-bufsize", "8M",
        "-c:a", "copy",
        "-y", final_path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ffmpeg stderr:\n{result.stderr[-1000:]}")
        raise RuntimeError(f"ffmpeg failed with code {result.returncode}")

    size_mb = Path(final_path).stat().st_size / (1024 * 1024)
    w2, h2  = get_video_dimensions(final_path)
    print(f"  Final: {final_path} ({w2}x{h2} | {size_mb:.1f} MB)")


# -- Step 6 -- Upload Guide ---------------------------------------------------

def generate_upload_guide(script: dict, mode: str, client: anthropic.Anthropic) -> str:
    print("  Generating upload guide...")
    full_vo    = " ".join(script[scene]["voiceover"] for scene in SCENE_ORDER)
    topic      = script.get("topic", "")
    seo_kw     = script.get("seo_keyword", "")
    video_type = script.get("video_type", mode)

    prompt = f"""You are a social media growth expert for TikTok and Facebook Reels,
men's mental health and recovery niche.

Generate a complete upload guide for TikTok AND Facebook.

VIDEO TYPE: {video_type.upper()}
TOPIC: {topic}
SEO KEYWORD: {seo_kw}
FULL VOICEOVER:
\"\"\"{full_vo}\"\"\"

TIKTOK:
- Title: max 100 characters, front-load the keyword
- Description: max 150 characters
- Hashtags: 8-12
- Best posting times: top 3 (day + UTC time)
- On-screen text overlay suggestion: 1 punchy line

FACEBOOK REELS:
- Title: max 255 characters
- Description: 2-3 sentences, ends with CTA or question
- Hashtags: 5-7
- Best posting times: top 3 (day + UTC time)

ALSO INCLUDE:
- Thumbnail suggestion
- A/B test hook idea

Plain text only. Clear labels. Copy-paste ready."""

    for attempt in range(1, CLAUDE_MAX_RETRIES + 1):
        try:
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1200,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text.strip()
        except anthropic.APIStatusError as e:
            if e.status_code == 529:
                wait = CLAUDE_RETRY_BASE * attempt
                print(f"  Anthropic overloaded -- waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Could not generate upload guide")


def save_upload_guide(guide_text: str, script: dict, mode: str, run_number: int, avatar_id: str):
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    topic        = script.get("topic", "N/A")
    seo_kw       = script.get("seo_keyword", "N/A")
    video_type   = script.get("video_type", mode).upper()
    total_words  = sum(len(script[s]["voiceover"].split()) for s in SCENE_ORDER)
    est_duration = round(total_words / 130 * 60)

    header = f"""================================================================================
  MINDCORE AI -- VIDEO UPLOAD GUIDE
  Run #{run_number} | {generated_at}
================================================================================
  Video type  : {video_type}
  Topic       : {topic}
  SEO keyword : {seo_kw}
  Avatar look : {avatar_id}
  Est. length : ~{est_duration}s ({total_words} words @ ~130 wpm)
  Format      : 1080x1920 9:16 30fps | Zoom-to-fill | TikTok + Facebook
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
    out  = OUTPUT_DIR / "upload_guide.txt"
    out.write_text(full, encoding="utf-8")
    print(f"  Upload guide saved -> {out}")


# -- Main ---------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    mode             = determine_mode()
    cfg              = load_config()
    avatar_id        = pick_avatar_look(cfg)
    voice_id         = cfg.get("voice_id", "")
    background_color = cfg.get("background_color", "#07071a")
    natural_gestures = cfg.get("use_natural_gestures", True)

    print(f"\n  MindCore AI Video Pipeline -- HeyGen Edition v3.4")
    print(f"  Run #{GITHUB_RUN_NUMBER} -- Mode: {mode.upper()}")
    print(f"  Avatar: {cfg.get('avatar_name', 'Unknown')} | look: {avatar_id[:8]}... ({len(cfg['avatar_look_ids'])} looks)")
    print(f"  Motion: {'NATURAL (avatar gestures)' if natural_gestures else 'CUSTOM PROMPT'}")
    print(f"  Format: 1080x1920 9:16 30fps | zoom-to-fill (no black bars)")
    print(f"  Keywords: short+long tail SERP research {'active' if SERP_API_KEY else 'DISABLED -- add SERP_API_KEY secret'}")
    if mode == "content":
        print(f"  Content: educational + storytelling only -- zero promotion")
    else:
        print(f"  Ad: rotating CTA | ~20s")
    print("=" * 60)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    print("\n  Generating script...")
    if mode == "ad":
        app_facts = load_app_facts()
        script    = generate_ad_with_validation(generate_ad_script, (app_facts, client))
    else:
        topic  = fetch_trending_topic(client)
        script = generate_content_script(topic, client)
        script = sanitize_script(script)

    (OUTPUT_DIR / "script.json").write_text(json.dumps(script, indent=2))
    total_words  = sum(len(script[s]["voiceover"].split()) for s in SCENE_ORDER)
    est_duration = round(total_words / 130 * 60)
    print(f"\n  Video type: {script.get('video_type', mode)}")
    print(f"  Topic:      {script.get('topic', 'N/A')}")
    print(f"  SEO kw:     {script.get('seo_keyword', 'N/A')}")
    print(f"  Est. length: ~{est_duration}s ({total_words} words)")
    print()
    for scene in SCENE_ORDER:
        wc = len(script[scene]["voiceover"].split())
        print(f"  [{scene:15s}]  {wc:2d} words  |  {script[scene]['voiceover']}")

    full_script = build_full_script(script)
    print(f"\n  Full script:\n  {full_script}")

    print(f"\n  Submitting to HeyGen...")
    video_id = submit_heygen_video(
        full_script, avatar_id, voice_id, background_color, natural_gestures
    )

    print(f"\n  Waiting for HeyGen to render (up to {VIDEO_TIMEOUT//60} min)...")
    video_url = poll_heygen_video(video_id)

    print("\n  Downloading raw video from HeyGen...")
    raw_path   = str(OUTPUT_DIR / "mindcore_ai_raw.mp4")
    final_path = str(OUTPUT_DIR / "mindcore_ai_video.mp4")
    download_video(video_url, raw_path)

    print("\n  Converting to 9:16 portrait (zoom-to-fill)...")
    crop_to_portrait(raw_path, final_path)

    print("\n  Generating upload guide...")
    guide_text = generate_upload_guide(script, mode, client)
    save_upload_guide(guide_text, script, mode, GITHUB_RUN_NUMBER, avatar_id)

    print(f"\n  DONE")
    print(f"  Video:  {final_path}")
    print(f"  Guide:  video_pipeline/output/upload_guide.txt")
    print(f"  Mode:   {mode.upper()} | ~{est_duration}s | Look: {avatar_id[:8]}...")
    print("\n  Pipeline complete!")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n  FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
