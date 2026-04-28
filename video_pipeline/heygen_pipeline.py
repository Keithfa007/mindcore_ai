#!/usr/bin/env python3
"""
MindCore AI Video Pipeline -- HeyGen Edition v3.3
===================================================

CHANGES (v3.3):
  SERP-first keyword research before every content video.
  Queries 3 seed topics against Google via SerpAPI, collects real
  People Also Ask questions and Related Searches, then Claude ranks
  all candidates by emotional resonance + specificity (competition proxy).
  Result: every video targets a real high-demand, low-competition keyword.

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

# Number of seed queries to hit in SERP per run (3 = ~3 API credits)
SERP_SEEDS_PER_RUN = 3

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


# -- Step 1a -- SERP Keyword Research -----------------------------------------
#
# NEW IN v3.3: Before writing any script, we hit SerpAPI across multiple
# seed queries and collect real search data. People Also Ask questions
# and Related Searches are gold -- they represent actual things people
# type into Google, and specific/long-tail queries have lower competition.
# Claude then ranks all candidates to pick the best one for this run.

def _serp_query(seed: str) -> dict:
    """Single SerpAPI call. Returns raw JSON response."""
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


def research_keyword_candidates_from_serp(seeds: list) -> list:
    """
    Query SerpAPI for SERP_SEEDS_PER_RUN random seeds.
    Collect:
      - People Also Ask (real questions people search -- highest quality)
      - Related Searches (long-tail, typically lower competition)
      - Top 3 organic titles (shows what's already ranking)
    Returns a deduplicated flat list of candidate dicts.
    """
    sampled   = random.sample(seeds, min(SERP_SEEDS_PER_RUN, len(seeds)))
    candidates = []
    seen       = set()

    for seed in sampled:
        try:
            data         = _serp_query(seed)
            total_results = int(
                data.get("search_information", {})
                    .get("total_results", "0")
                    .replace(",", "")
                    .replace(".", "")
                or 0
            )

            # People Also Ask -- highest priority, shows direct search intent
            paa_count = 0
            for q in data.get("related_questions", []):
                text = q.get("question", "").strip()
                if text and text.lower() not in seen:
                    seen.add(text.lower())
                    candidates.append({
                        "text":          text,
                        "source":        "people_also_ask",
                        "seed":          seed,
                        "total_results": total_results,
                    })
                    paa_count += 1

            # Related Searches -- long-tail, lower competition
            rs_count = 0
            for r in data.get("related_searches", []):
                text = r.get("query", "").strip()
                if text and text.lower() not in seen:
                    seen.add(text.lower())
                    candidates.append({
                        "text":          text,
                        "source":        "related_search",
                        "seed":          seed,
                        "total_results": 0,  # separate lookup needed
                    })
                    rs_count += 1

            # Top 3 organic titles -- what currently ranks (shows competition)
            for org in data.get("organic_results", [])[:3]:
                title = org.get("title", "").strip()
                if title and title.lower() not in seen and len(title) < 120:
                    seen.add(title.lower())
                    candidates.append({
                        "text":          title,
                        "source":        "organic_title",
                        "seed":          seed,
                        "total_results": total_results,
                    })

            print(f"  SERP '{seed[:45]}': {paa_count} PAA | {rs_count} related | {total_results:,} results")
            time.sleep(0.5)  # rate-limit courtesy

        except Exception as e:
            print(f"  SERP failed for '{seed}': {e}")

    return candidates


def rank_and_select_keyword_claude(candidates: list, client: anthropic.Anthropic) -> dict:
    """
    Send all SERP candidates to Claude.
    Claude scores each by emotional resonance, niche fit, and specificity
    (longer/more specific = lower competition proxy).
    Returns the single best candidate as a topic dict.
    """
    if not candidates:
        raise ValueError("No SERP candidates to rank")

    # Prioritise PAA questions, then related searches, then organic
    priority_order = {"people_also_ask": 0, "related_search": 1, "organic_title": 2}
    sorted_candidates = sorted(candidates, key=lambda c: priority_order.get(c["source"], 3))

    # Build numbered list for Claude (cap at 40 to keep prompt tight)
    candidate_list = "\n".join([
        f"{i+1}. [{c['source'].upper()}] {c['text']}"
        for i, c in enumerate(sorted_candidates[:40])
    ])

    prompt = f"""You are an expert in SEO and content strategy for men's mental health, recovery, sobriety, and anxiety on TikTok and Facebook Reels.

Below are REAL search queries and topics pulled from Google (People Also Ask, Related Searches, and organic results) in the men's mental health niche.

YOUR TASK: Choose the SINGLE BEST topic to make a short video about today.

SCORING CRITERIA (in order of importance):
1. EMOTIONAL RESONANCE -- Would a man aged 35-55 struggling silently with anxiety, depression, isolation, or sobriety STOP scrolling for this? Does it name something he feels but never says out loud?
2. SEARCH SPECIFICITY -- More specific, longer-tail phrases tend to have lower competition. Prefer "why do I feel numb after stopping drinking" over "depression tips".
3. NICHE FIT -- Must directly relate to: men's mental health, emotional struggles, recovery/sobriety, anxiety, depression, loneliness, asking for help, emotional numbness, burnout.
4. VIDEO POTENTIAL -- Can this be explored emotionally and powerfully in 30-45 seconds of spoken word?

AVOID picking: Generic broad topics, anything requiring clinical credentials, topics already oversaturated by big brands.

COMPETITION NOTE: "People Also Ask" questions are typically lower competition than seed keywords. Prefer them. Related searches with 4+ words are usually long-tail and lower competition.

CANDIDATES (from real Google data):
{candidate_list}

Return ONLY valid JSON, no markdown fences:
{{
  "topic": "the exact text of the chosen candidate",
  "question": "how a man would type this into Google naturally",
  "keyword": "the primary 2-5 word SEO keyword to weave into the script",
  "competition_signal": "low|medium|high -- your estimate based on specificity",
  "why": "one sentence: why this beats the others for our specific audience",
  "source": "people_also_ask|related_search|organic_title"
}}"""

    result = _call_claude_raw(prompt, client, max_tokens=500)
    print(f"  Winner: '{result.get('keyword')}' [{result.get('competition_signal','?')} competition]")
    print(f"  Reason: {result.get('why', '')}")
    return result


def fetch_trending_topic_claude_fallback(seeds: list, client: anthropic.Anthropic) -> dict:
    """Fallback when SERP is unavailable -- Claude generates a topic from seeds."""
    seed   = random.choice(seeds)
    prompt = f"""You are an SEO and content strategy expert for men's mental health, recovery, anxiety, depression.

Generate ONE high-demand, low-competition video topic for TikTok and Facebook Reels.
Related to this seed: "{seed}"

Criteria:
- Phrased as a real question or struggle men actually search for
- High emotional resonance for men 35+ in recovery or struggling
- Specific enough to suggest low competition (avoid broad topics)
- Men's mental health / sobriety / emotional struggles niche only

Return ONLY valid JSON, no markdown:
{{
  "topic": "the specific topic or question",
  "question": "how it would be typed into Google",
  "keyword": "primary 2-5 word SEO keyword",
  "competition_signal": "low|medium|high",
  "why": "one sentence rationale",
  "source": "claude_generated"
}}"""
    return _call_claude_raw(prompt, client, max_tokens=300)


def fetch_trending_topic(client: anthropic.Anthropic) -> dict:
    """
    Main topic research function.
    If SERP_API_KEY is set: query Google across 3 seeds, collect PAA +
    related searches, rank with Claude, return the best keyword.
    Fallback: Claude generates a topic directly from seed list.
    """
    keywords = load_niche_keywords()
    seeds    = keywords["seed_queries"]

    if SERP_API_KEY:
        print(f"  Researching keywords via SerpAPI ({SERP_SEEDS_PER_RUN} seeds)...")
        try:
            candidates = research_keyword_candidates_from_serp(seeds)
            print(f"  Collected {len(candidates)} keyword candidates from SERP")
            if candidates:
                topic = rank_and_select_keyword_claude(candidates, client)
                topic["source"] = f"serp_{topic.get('source', 'research')}"
                # Save research log for reference
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
    print(f"  Topic: {topic.get('topic')} [{topic.get('competition_signal', '?')}]")
    return topic


# -- Step 1b -- Script Generation ---------------------------------------------

def generate_content_script(topic: dict, client: anthropic.Anthropic) -> dict:
    print(f"  Generating CONTENT script for: {topic['topic']}")
    keyword  = topic.get("keyword", topic["topic"])
    question = topic.get("question", topic["topic"])
    angles   = load_niche_keywords().get("content_angles", [])
    angle    = random.choice(angles) if angles else "real talk"

    lo_hook,  hi_hook  = WORD_TARGETS_CONTENT["hook"]
    lo_prob,  hi_prob  = WORD_TARGETS_CONTENT["problem"]
    lo_story, hi_story = WORD_TARGETS_CONTENT["story"]
    lo_cta,   hi_cta   = WORD_TARGETS_CONTENT["solution_cta"]

    prompt = f"""You are a top-performing TikTok and Facebook Reels content creator in the men's
mental health and recovery space. Your content gets millions of views because it speaks
RAW TRUTH and shares REAL STORIES that men 35+ actually recognise from their own lives.

Create a 4-scene short video script on this topic:
TOPIC: {topic['topic']}
SEARCH QUESTION: {question}
PRIMARY SEO KEYWORD: {keyword}
CONTENT ANGLE: {angle}
COMPETITION LEVEL: {topic.get('competition_signal', 'unknown')} -- lean into specificity

FORMAT: Hook -> Problem/Truth -> Real Story or Insight -> Genuine Takeaway

AUDIENCE: Men 35+, in recovery or struggling with anxiety, depression, isolation.
They feel alone. They don't ask for help. Speak like someone who has genuinely been through it.

THIS IS PURE VALUE CONTENT -- NOT AN AD:
- Do NOT mention MindCore AI, any app, any product, or any service. Not even subtly.
- Do NOT end with a download CTA or any promotional message whatsoever.
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
#
# COVER mode: always zoom in to fill the full 1080x1920 frame.
# No black bars. Center-crop any overflow.

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
    """
    1. Crop to detected content area (remove black bars HeyGen added)
    2. Scale COVER mode -- zoom until BOTH width>=1080 AND height>=1920
    3. Center-crop to exactly 1080x1920
    4. 30fps
    No black bars, ever.
    """
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

    print(f"\n  MindCore AI Video Pipeline -- HeyGen Edition v3.3")
    print(f"  Run #{GITHUB_RUN_NUMBER} -- Mode: {mode.upper()}")
    print(f"  Avatar: {cfg.get('avatar_name', 'Unknown')} | look: {avatar_id[:8]}... ({len(cfg['avatar_look_ids'])} looks)")
    print(f"  Motion: {'NATURAL (avatar gestures)' if natural_gestures else 'CUSTOM PROMPT'}")
    print(f"  Format: 1080x1920 9:16 30fps | zoom-to-fill (no black bars)")
    print(f"  Keywords: SERP-first research ({SERP_SEEDS_PER_RUN} seeds) {'active' if SERP_API_KEY else 'DISABLED -- add SERP_API_KEY secret'}")
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
