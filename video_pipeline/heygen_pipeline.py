#!/usr/bin/env python3
"""
MindCore AI Video Pipeline -- HeyGen Edition v4.7
===================================================

CHANGES (v4.7):
  Add YouTube Shorts as a 4th auto-upload platform.
  YouTube-specific metadata: youtube_title, youtube_description, youtube_tags.
  YouTube auto-detects 9:16 videos under 60s as Shorts (no special flag needed).
  Brand hashtag enforced in YouTube description too.

CHANGES (v4.6):
  Enforce #mindcoreai brand hashtag in all captions (TikTok, IG, Facebook).
  Belt-and-braces post-check guarantees inclusion even if Claude omits it.

CHANGES (v4.5):
  Add Instagram Reels to auto-upload platforms.

CHANGES (v4.4):
  Fix Upload-Post field mapping. TikTok caption = title + hashtags merged.
  Facebook gets full description. Schedule: Tue/Wed/Thu 17:00 UTC.

CHANGES (v4.3):
  Add type: "avatar" discriminator field to /v3/videos payload.

CHANGES (v4.2):
  Switch to POST /v3/videos per HeyGen support.

CHANGES (v4.1):
  Added super_resolution: true and talking_style: "expressive".

CHANGES (v4.0):
  Full body motion: pose=full_body, motion_prompt, expressiveness=high.

CHANGES (v3.5):
  Auto-upload to TikTok + Facebook via Upload-Post API.

CHANGES (v3.4):
  Short-tail + long-tail keyword research via SERP + Autocomplete.

CHANGES (v3.3):
  SERP-first keyword research before every content video.

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

ANTHROPIC_API_KEY   = os.environ["ANTHROPIC_API_KEY"]
HEYGEN_API_KEY      = os.environ["HEYGEN_API_KEY"]
SERP_API_KEY        = os.environ.get("SERP_API_KEY", "")
UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")

GITHUB_RUN_NUMBER = int(os.environ.get("GITHUB_RUN_NUMBER", "1"))

HEYGEN_V3_URL       = "https://api.heygen.com/v3/videos"
HEYGEN_STATUS_URL   = "https://api.heygen.com/v1/video_status.get"
SERP_API_URL        = "https://serpapi.com/search"
UPLOAD_POST_API_URL = "https://api.upload-post.com/api/upload"

OUTPUT_DIR   = Path("video_pipeline/output")
PIPELINE_DIR = Path("video_pipeline")
SCENE_ORDER  = ["hook", "problem", "story", "solution_cta"]

POLL_INTERVAL = 15
VIDEO_TIMEOUT = 1200  # 20 minutes

CLAUDE_MAX_RETRIES = 10
CLAUDE_RETRY_BASE  = 30

SERP_SEEDS_PER_RUN         = 3
AUTOCOMPLETE_SEEDS_PER_RUN = 2

TIKTOK_CAPTION_LIMIT      = 2200  # TikTok caption max chars
YOUTUBE_TITLE_LIMIT       = 100   # YouTube title max chars
YOUTUBE_DESCRIPTION_LIMIT = 5000  # YouTube description max chars (we'll keep ours much shorter)

# Brand hashtag enforced across all captions and descriptions
REQUIRED_BRAND_HASHTAG = "#mindcoreai"

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


# -- Brand hashtag enforcement ------------------------------------------------

def ensure_brand_hashtag(text: str) -> str:
    """
    Belt-and-braces: guarantee #mindcoreai is in the text. If Claude omits it,
    append to the last hashtag-bearing line, or add a new line if none exist.
    """
    if not text:
        return f"{REQUIRED_BRAND_HASHTAG}"
    if REQUIRED_BRAND_HASHTAG.lower() in text.lower():
        return text
    # Find the last line containing a hashtag and append the brand tag
    lines = text.rstrip().split("\n")
    for i in range(len(lines) - 1, -1, -1):
        if "#" in lines[i]:
            # Append to the last hashtag in that line, respecting the existing format
            lines[i] = lines[i].rstrip() + f" {REQUIRED_BRAND_HASHTAG}"
            return "\n".join(lines)
    # No hashtags at all -- append on a new line
    return text.rstrip() + f"\n{REQUIRED_BRAND_HASHTAG}"


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


# -- Step 1a -- SERP Keyword Research -----------------------------------------

def _serp_google_query(seed: str) -> dict:
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
    if wc <= 3:   return "short_tail"
    elif wc <= 5: return "mid_tail"
    else:         return "long_tail"


def research_keyword_candidates_from_serp(seeds: list) -> list:
    candidates = []
    seen       = set()

    regular_seeds = random.sample(seeds, min(SERP_SEEDS_PER_RUN, len(seeds)))
    for seed in regular_seeds:
        try:
            data          = _serp_google_query(seed)
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
                                       "tail_type": _keyword_type(text),
                                       "word_count": _word_count(text),
                                       "seed": seed, "total_results": total_results})
                    paa_count += 1
            rs_count = 0
            for r in data.get("related_searches", []):
                text = r.get("query", "").strip()
                if text and text.lower() not in seen:
                    seen.add(text.lower())
                    candidates.append({"text": text, "source": "related_search",
                                       "tail_type": _keyword_type(text),
                                       "word_count": _word_count(text),
                                       "seed": seed, "total_results": 0})
                    rs_count += 1
            for org in data.get("organic_results", [])[:3]:
                title = org.get("title", "").strip()
                if title and title.lower() not in seen and len(title) < 120:
                    seen.add(title.lower())
                    candidates.append({"text": title, "source": "organic_title",
                                       "tail_type": _keyword_type(title),
                                       "word_count": _word_count(title),
                                       "seed": seed, "total_results": total_results})
            print(f"  [GOOGLE] '{seed[:45]}': {paa_count} PAA | {rs_count} related | {total_results:,} results")
            time.sleep(0.5)
        except Exception as e:
            print(f"  Google search failed for '{seed}': {e}")

    autocomplete_bases = []
    for seed in seeds:
        words = seed.split()
        if len(words) >= 3:
            autocomplete_bases.append(" ".join(words[:2]))
            autocomplete_bases.append(" ".join(words[:3]))
        else:
            autocomplete_bases.append(seed)
    autocomplete_bases = list(set(autocomplete_bases))
    ac_seeds = random.sample(autocomplete_bases, min(AUTOCOMPLETE_SEEDS_PER_RUN, len(autocomplete_bases)))
    for ac_seed in ac_seeds:
        suggestions = _serp_autocomplete_query(ac_seed)
        ac_count = 0
        for text in suggestions:
            if text and text.lower() not in seen and _word_count(text) <= 6:
                seen.add(text.lower())
                candidates.append({"text": text, "source": "autocomplete",
                                   "tail_type": _keyword_type(text),
                                   "word_count": _word_count(text),
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


def rank_and_select_keyword_claude(candidates: list, client: anthropic.Anthropic) -> dict:
    if not candidates:
        raise ValueError("No SERP candidates to rank")

    type_order   = {"short_tail": 0, "mid_tail": 1, "long_tail": 2}
    source_order = {"autocomplete": 0, "people_also_ask": 1, "related_search": 2, "organic_title": 3}
    sorted_cands = sorted(
        candidates,
        key=lambda c: (type_order.get(c["tail_type"], 3), source_order.get(c["source"], 4))
    )

    candidate_list = "\n".join([
        f"{i+1}. [{c['tail_type'].upper()} | {c['source'].upper()} | {c['word_count']}w] {c['text']}"
        for i, c in enumerate(sorted_cands[:50])
    ])

    prompt = f"""You are an expert in SEO for men's mental health, recovery, sobriety, anxiety on TikTok and Facebook Reels.

Below are REAL search queries from Google (Autocomplete, PAA, Related Searches, organic).
Each is labelled with tail type and word count.

CHOOSE THE SINGLE BEST keyword/topic for a short video today.

FAVOUR SHORT-TAIL IF it's niche-emotional and under big-brand radar:
- "sobriety anger", "men crying", "emotional numbness", "sober anxiety" = short but LOW competition
- Big health brands (WebMD, NHS, BetterHelp) ignore raw emotional short phrases
- Individual creators own this space

SCORING:
1. Emotional resonance for men 35-55 struggling silently
2. Competition reality: niche enough to avoid big brand dominance?
3. Niche fit: men's mental health, sobriety, recovery, emotional struggles
4. Video potential: powerful in 30-45 seconds spoken word?

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
  "source": "autocomplete|people_also_ask|related_search|organic_title"
}}"""

    result = _call_claude_raw(prompt, client, max_tokens=500)
    print(f"  Winner: '{result.get('keyword')}' [{result.get('tail_type','?')} | {result.get('competition_signal','?')} competition]")
    print(f"  Reason: {result.get('why', '')}")
    return result


def fetch_trending_topic_claude_fallback(seeds: list, client: anthropic.Anthropic) -> dict:
    seed = random.choice(seeds)
    prompt = f"""SEO expert for men's mental health, recovery, anxiety, sobriety.

Generate ONE keyword/topic for a TikTok/Reels video. Related to: "{seed}"

Consider BOTH short-tail (1-3 words, niche emotional) AND long-tail (4+ words, specific).

Return ONLY valid JSON:
{{
  "topic": "the keyword or question",
  "question": "how a man types this into Google",
  "keyword": "primary 1-5 word SEO keyword",
  "tail_type": "short_tail|mid_tail|long_tail",
  "competition_signal": "low|medium|high",
  "why": "one sentence rationale",
  "source": "claude_generated"
}}"""
    return _call_claude_raw(prompt, client, max_tokens=300)


def fetch_trending_topic(client: anthropic.Anthropic) -> dict:
    keywords = load_niche_keywords()
    seeds    = keywords["seed_queries"]

    if SERP_API_KEY:
        print(f"  Keyword research: {SERP_SEEDS_PER_RUN} Google + {AUTOCOMPLETE_SEEDS_PER_RUN} autocomplete...")
        try:
            candidates = research_keyword_candidates_from_serp(seeds)
            if candidates:
                topic = rank_and_select_keyword_claude(candidates, client)
                topic["source"] = f"serp_{topic.get('source', 'research')}"
                log_path = OUTPUT_DIR / "keyword_research.json"
                log_path.write_text(json.dumps({
                    "run": GITHUB_RUN_NUMBER, "candidates": candidates, "winner": topic
                }, indent=2))
                return topic
            print("  No candidates found -- falling back to Claude")
        except Exception as e:
            print(f"  SERP research failed ({e}) -- falling back to Claude")

    print("  Generating topic with Claude (no SERP)...")
    topic = fetch_trending_topic_claude_fallback(seeds, client)
    print(f"  Topic: {topic.get('topic')} [{topic.get('tail_type','?')} | {topic.get('competition_signal','?')}]")
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

    if tail_type == "short_tail":
        kw_guidance = f"SHORT-TAIL keyword '{keyword}'. Explore the full emotional depth. LIVE it from the inside."
    else:
        kw_guidance = f"SPECIFIC keyword '{keyword}'. Answer the exact question implied. Be precise and emotionally honest."

    prompt = f"""Top-performing TikTok/Reels creator, men's mental health + recovery space.
Content gets millions of views -- RAW TRUTH, REAL STORIES men 35+ recognise.

Create a 4-scene script:
TOPIC: {topic['topic']}
SEARCH QUESTION: {question}
PRIMARY SEO KEYWORD: {keyword}
KEYWORD GUIDANCE: {kw_guidance}
CONTENT ANGLE: {angle}
COMPETITION: {topic.get('competition_signal', 'unknown')}

FORMAT: Hook -> Problem/Truth -> Real Story or Insight -> Genuine Takeaway
AUDIENCE: Men 35+, struggling silently with anxiety, depression, isolation, recovery.

PURE VALUE -- NOT AN AD:
- No MindCore AI mentions. No download CTA. No product plugs.
- Last scene = genuine human takeaway, not promotion.

WRITE FOR THE EAR:
- Natural spoken language, contractions, conversational connectors
- "And the thing is...", "Because here's what nobody tells you...", "The truth is..."
- Each scene = one continuous thought.

WORD COUNTS:
- hook: {lo_hook}-{hi_hook} words -- stops the scroll
- problem: {lo_prob}-{hi_prob} words -- names the pain
- story: {lo_story}-{hi_story} words -- real and specific
- solution_cta: {lo_cta}-{hi_cta} words -- genuine takeaway

Total ~130-150 words. No "hey guys". No "in today's video".
Weave '{keyword}' naturally at least once.

Return ONLY valid JSON, no markdown:
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
    prompt = f"""Performance marketing copywriter for MindCore AI.
4-scene video ad: Hook -> Problem -> Story -> Solution+CTA.

AUDIENCE: Men 35+, recovery/anxiety/depression/isolation.
TONE: Raw, honest, brotherly. Not salesy.
TARGET: ~20 seconds. Every word earns its place.

BANNED: "try it for free" -> "try it", "free trial" -> "trial", "download now" -> "find us on Google Play"
ABOUT MINDCORE AI: AI mental wellness companion for men, Google Play, free trial, no credit card.
SOLUTION_CTA MUST END WITH: "{cta}"
SEO KEYWORDS: {', '.join(SEO_KEYWORDS)}
STRICT WORD COUNT: hook<=8, problem<=12, story<=14, solution_cta<=14

Return ONLY valid JSON:
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


# -- Step 3 -- Submit to HeyGen via /v3/videos --------------------------------

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

    print(f"  Endpoint: POST /v3/videos | type=avatar | expressiveness=high")
    print(f"  Avatar: {avatar_id[:8]}... | voice: {voice_id[:8]}...")

    resp = requests.post(HEYGEN_V3_URL, headers=headers, json=payload, timeout=30)
    print(f"  v3/videos response [{resp.status_code}]: {resp.text[:300]}")

    if not resp.ok:
        raise RuntimeError(f"HeyGen v3/videos failed {resp.status_code}: {resp.text}")

    data     = resp.json()
    video_id = (
        data.get("data", {}).get("video_id")
        or data.get("video_id")
        or data.get("data", {}).get("id")
        or data.get("id")
    )
    if not video_id:
        raise RuntimeError(f"No video_id in v3/videos response: {data}")

    print(f"  Submitted -- video_id: {video_id}")
    return video_id


# -- Step 4 -- Poll -----------------------------------------------------------

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
    print(f"  cropdetect: content area {cw}x{ch} at x={cx}, y={cy}")
    return cw, ch, cx, cy


def make_portrait_filter(cw: int, ch: int, cx: int, cy: int) -> str:
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
        print("  cropdetect found no bars -- using full frame")
        filter_str = make_portrait_filter(w, h, 0, 0)
    print(f"  FFmpeg filter: {filter_str}")
    cmd = ["ffmpeg", "-i", raw_path, "-vf", filter_str,
           "-c:v", "libx264", "-crf", "16", "-preset", "slow",
           "-b:v", "4M", "-maxrate", "6M", "-bufsize", "8M",
           "-c:a", "copy", "-y", final_path]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ffmpeg stderr:\n{result.stderr[-1000:]}")
        raise RuntimeError(f"ffmpeg failed with code {result.returncode}")
    size_mb = Path(final_path).stat().st_size / (1024 * 1024)
    w2, h2  = get_video_dimensions(final_path)
    print(f"  Final: {final_path} ({w2}x{h2} | {size_mb:.1f} MB)")


# -- Step 6 -- Upload Guide + Metadata ----------------------------------------

def generate_upload_guide(script: dict, mode: str, client: anthropic.Anthropic) -> str:
    print("  Generating upload guide...")
    full_vo    = " ".join(script[scene]["voiceover"] for scene in SCENE_ORDER)
    topic      = script.get("topic", "")
    seo_kw     = script.get("seo_keyword", "")
    video_type = script.get("video_type", mode)

    prompt = f"""Social media growth expert for TikTok, Instagram Reels, Facebook Reels and YouTube Shorts,
men's mental health and recovery niche.

Generate a complete upload guide for TikTok, Instagram, Facebook AND YouTube Shorts.

VIDEO TYPE: {video_type.upper()}
TOPIC: {topic}
SEO KEYWORD: {seo_kw}
FULL VOICEOVER: \"\"\"{full_vo}\"\"\"

TIKTOK / INSTAGRAM REELS:
- Caption (keyword-first hook + 8-12 hashtags inline, max 2200 chars)
- ALWAYS INCLUDE the brand hashtag {REQUIRED_BRAND_HASHTAG} in the hashtag set (non-negotiable)
- On-screen text overlay suggestion: 1 punchy line

FACEBOOK REELS:
- Title: max 255 characters, keyword-first
- Description: 2-3 sentences, emotionally engaging, ends with a question + 5-7 hashtags
- ALWAYS INCLUDE the brand hashtag {REQUIRED_BRAND_HASHTAG} in the Facebook hashtag set (non-negotiable)

YOUTUBE SHORTS:
- Title: max 100 chars, keyword-first, scroll-stopping
- Description: 2-4 sentences (longer than IG caption since YouTube viewers read more) +
  link to mindcoreai.eu + 5-8 hashtags ending with #Shorts to ensure Shorts placement
- ALWAYS INCLUDE the brand hashtag {REQUIRED_BRAND_HASHTAG} in the YouTube hashtag set (non-negotiable)
- Tags (comma-separated keywords for YouTube SEO, separate from hashtags): 8-12 keywords

ALSO INCLUDE:
- Thumbnail suggestion
- A/B test hook idea

Plain text only. Clear labels. Copy-paste ready."""

    for attempt in range(1, CLAUDE_MAX_RETRIES + 1):
        try:
            msg = client.messages.create(
                model="claude-sonnet-4-6", max_tokens=1500,
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


def generate_upload_metadata(script: dict, mode: str, client: anthropic.Anthropic) -> dict:
    print("  Generating platform metadata for upload...")
    full_vo    = " ".join(script[scene]["voiceover"] for scene in SCENE_ORDER)
    topic      = script.get("topic", "")
    seo_kw     = script.get("seo_keyword", "")
    video_type = script.get("video_type", mode).upper()

    prompt = f"""Social media expert for men's mental health content on TikTok, Instagram Reels, Facebook Reels and YouTube Shorts.

Generate optimised upload metadata for this video. Each platform needs DIFFERENT optimisation.

VIDEO TYPE: {video_type}
TOPIC: {topic}
SEO KEYWORD: {seo_kw}
FULL VOICEOVER: {full_vo}

RULES:

TIKTOK + INSTAGRAM (shared caption, hashtags inline):
- tiktok_caption: keyword-first sentence (max 100 chars) + space + 8-10 hashtags inline.
  Used for BOTH TikTok and Instagram Reels captions.
  ALWAYS INCLUDE these brand hashtags (non-negotiable): {REQUIRED_BRAND_HASHTAG} #mensmentalhealth
  Example: "Male loneliness is an epidemic. {REQUIRED_BRAND_HASHTAG} #menloneliness #mensmentalhealth ..."
  Max 2200 chars total.

FACEBOOK (separate title and description):
- facebook_title: max 255 chars, keyword-first
- facebook_description: 2-3 emotionally engaging sentences + question at end + 5-6 hashtags
  ALWAYS INCLUDE the brand hashtag {REQUIRED_BRAND_HASHTAG} in the Facebook hashtag set (non-negotiable)

YOUTUBE SHORTS (separate title, description, and tags):
- youtube_title: max 100 chars, keyword-first, scroll-stopping question or statement.
  YouTube titles are punchier than Facebook titles. Make it search-friendly.
  Example: "Why You Wake Up at 3am With Anxiety" (good — searchable, emotional)
- youtube_description: 2-4 sentences expanding the topic + a line break + the link
  "Try MindCore AI: https://mindcoreai.eu" + a line break + 6-8 hashtags ending with #Shorts.
  ALWAYS INCLUDE the brand hashtag {REQUIRED_BRAND_HASHTAG} in the YouTube hashtag set (non-negotiable).
  ALWAYS END the hashtag line with #Shorts to ensure YouTube treats this as a Short.
- youtube_tags: comma-separated string of 8-12 keywords (NO hashtags here, just keywords).
  These are YouTube's metadata tags for SEO (different from hashtags in the description).
  Include the SEO keyword + variations + niche terms.
  Example: "men mental health, anxiety men 35, sober anxiety, AI mental health coach, recovery support"

Return ONLY valid JSON, no markdown:
{{
  "tiktok_caption": "keyword-first hook sentence {REQUIRED_BRAND_HASHTAG} #hashtag2 #hashtag3 ...",
  "facebook_title": "...",
  "facebook_description": "... {REQUIRED_BRAND_HASHTAG} #tag2 ...",
  "youtube_title": "scroll-stopping title with keyword",
  "youtube_description": "2-4 sentences\\n\\nTry MindCore AI: https://mindcoreai.eu\\n\\n{REQUIRED_BRAND_HASHTAG} #mentalhealth #mensmentalhealth #Shorts",
  "youtube_tags": "keyword1, keyword2, keyword3, keyword4, keyword5, keyword6, keyword7, keyword8"
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

            # Belt-and-braces: ensure brand hashtag in all caption/description fields
            metadata["tiktok_caption"]       = ensure_brand_hashtag(metadata.get("tiktok_caption", ""))
            metadata["facebook_description"] = ensure_brand_hashtag(metadata.get("facebook_description", ""))
            metadata["youtube_description"]  = ensure_brand_hashtag(metadata.get("youtube_description", ""))

            # Enforce field length limits
            metadata["youtube_title"] = metadata.get("youtube_title", "")[:YOUTUBE_TITLE_LIMIT]

            print(f"  Caption (TikTok+IG)  : {metadata.get('tiktok_caption', '')[:80]}...")
            print(f"  Facebook title       : {metadata.get('facebook_title', '')[:60]}...")
            print(f"  YouTube title        : {metadata.get('youtube_title', '')[:60]}...")
            print(f"  YouTube tags         : {metadata.get('youtube_tags', '')[:80]}...")
            return metadata
        except (anthropic.APIStatusError, json.JSONDecodeError) as e:
            if attempt == CLAUDE_MAX_RETRIES:
                raise RuntimeError(f"Could not generate upload metadata: {e}")
            time.sleep(10)
    raise RuntimeError("Unexpected exit from metadata generation")


# -- Step 7 -- Auto-upload to TikTok + Facebook + Instagram + YouTube --------
#
# Platform field mapping:
#   TikTok:    "title" = caption (hashtags inline). description ignored.
#   Instagram: "title" = caption (hashtags inline). description ignored.
#   Facebook:  "facebook_title" + "facebook_description" (separate fields).
#   YouTube:   "youtube_title" + "youtube_description" + "youtube_tags" (separate fields).
#              YouTube auto-detects 9:16 videos under 60s as Shorts.

def upload_to_platforms(video_path: str, metadata: dict, cfg: dict) -> dict:
    if not UPLOAD_POST_API_KEY:
        print("  UPLOAD_POST_API_KEY not set -- skipping upload")
        return {"skipped": True, "reason": "no API key"}

    user = cfg.get("upload_post_user", "")
    if not user:
        print("  upload_post_user not set in config -- skipping upload")
        return {"skipped": True, "reason": "no user configured"}

    # Shared caption for TikTok + Instagram (hashtags inline)
    caption = metadata.get("tiktok_caption", "")[:TIKTOK_CAPTION_LIMIT]

    # Facebook separate fields
    facebook_title       = metadata.get("facebook_title", "")[:255]
    facebook_description = metadata.get("facebook_description", "")

    # YouTube separate fields
    youtube_title       = metadata.get("youtube_title", "")[:YOUTUBE_TITLE_LIMIT]
    youtube_description = metadata.get("youtube_description", "")[:YOUTUBE_DESCRIPTION_LIMIT]
    youtube_tags        = metadata.get("youtube_tags", "")

    print(f"  Uploading to TikTok + Facebook + Instagram + YouTube as '{user}'...")
    print(f"  Caption ({len(caption)} chars)        : {caption[:80]}...")
    print(f"  Facebook title                  : {facebook_title[:60]}...")
    print(f"  YouTube title                   : {youtube_title[:60]}...")

    headers = {"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"}

    data = [
        ("user",                 user),
        # All four platforms
        ("platform[]",           "tiktok"),
        ("platform[]",           "facebook"),
        ("platform[]",           "instagram"),
        ("platform[]",           "youtube"),
        # Caption for TikTok + Instagram (hashtags inline)
        ("title",                caption),
        # Facebook separate fields
        ("facebook_title",       facebook_title),
        ("facebook_description", facebook_description),
        # YouTube separate fields
        ("youtube_title",        youtube_title),
        ("youtube_description",  youtube_description),
        ("youtube_tags",         youtube_tags),
    ]

    try:
        with open(video_path, "rb") as f:
            files = [("video", ("mindcore_ai_video.mp4", f, "video/mp4"))]
            resp  = requests.post(
                UPLOAD_POST_API_URL,
                headers=headers,
                files=files,
                data=data,
                timeout=180,
            )

        result = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
        result["status_code"] = resp.status_code

        if resp.ok:
            print(f"  Upload successful! Status: {resp.status_code}")
        else:
            print(f"  Upload WARNING -- status {resp.status_code}: {resp.text[:300]}")

        return result

    except Exception as e:
        print(f"  Upload failed: {e}")
        return {"error": str(e), "skipped": False}


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
  Format      : 1080x1920 9:16 30fps | Zoom-to-fill | Full body motion
  Platforms   : TikTok + Facebook + Instagram Reels + YouTube Shorts
  Schedule    : Tue/Wed/Thu 17:00 UTC
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
    upload_enabled   = cfg.get("upload_enabled", False) and bool(UPLOAD_POST_API_KEY)

    print(f"\n  MindCore AI Video Pipeline -- HeyGen Edition v4.7")
    print(f"  Run #{GITHUB_RUN_NUMBER} -- Mode: {mode.upper()}")
    print(f"  Avatar: {cfg.get('avatar_name', 'Unknown')} | look: {avatar_id[:8]}... ({len(cfg['avatar_look_ids'])} looks)")
    print(f"  Endpoint: POST /v3/videos | type=avatar | expressiveness=high | motion_prompt active")
    print(f"  Format: 1080x1920 9:16 30fps | zoom-to-fill")
    print(f"  Platforms: TikTok + Facebook + Instagram Reels + YouTube Shorts")
    print(f"  Schedule: Tue/Wed/Thu 17:00 UTC")
    print(f"  Keywords: SERP short+long tail {'active' if SERP_API_KEY else 'DISABLED'}")
    print(f"  Auto-upload: {'TikTok + Facebook + Instagram + YouTube' if upload_enabled else 'DISABLED'}")
    if mode == "content":
        print("  Content: educational + storytelling only -- zero promotion")
    else:
        print("  Ad: rotating CTA | ~20s")
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
    if est_duration > 60:
        print(f"  WARNING: Video is {est_duration}s -- YouTube treats >60s as regular video, not Shorts.")
        print(f"           TikTok/IG/FB unaffected. Consider tightening word counts if you want all-Shorts placement.")
    print()
    for scene in SCENE_ORDER:
        wc = len(script[scene]["voiceover"].split())
        print(f"  [{scene:15s}]  {wc:2d} words  |  {script[scene]['voiceover']}")

    full_script = build_full_script(script)
    print(f"\n  Full script:\n  {full_script}")

    print("\n  Submitting to HeyGen v3/videos...")
    video_id = submit_heygen_video(full_script, avatar_id, voice_id, background_color, natural_gestures)

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

    upload_metadata = generate_upload_metadata(script, mode, client)
    (OUTPUT_DIR / "upload_metadata.json").write_text(json.dumps(upload_metadata, indent=2))

    if upload_enabled:
        print("\n  Uploading to TikTok + Facebook + Instagram + YouTube...")
        upload_result = upload_to_platforms(final_path, upload_metadata, cfg)
        (OUTPUT_DIR / "upload_result.json").write_text(json.dumps(upload_result, indent=2))
    else:
        print("\n  Auto-upload disabled -- video saved for manual review")
        (OUTPUT_DIR / "upload_result.json").write_text(json.dumps({"skipped": True}, indent=2))

    print(f"\n  DONE")
    print(f"  Video:  {final_path}")
    print(f"  Guide:  video_pipeline/output/upload_guide.txt")
    print(f"  Mode:   {mode.upper()} | ~{est_duration}s | Look: {avatar_id[:8]}...")
    if upload_enabled:
        print("  Posted: TikTok + Facebook + Instagram Reels + YouTube Shorts")
    print("\n  Pipeline complete!")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n  FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
