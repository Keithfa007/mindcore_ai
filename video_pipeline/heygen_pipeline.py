#!/usr/bin/env python3
"""
MindCore AI Video Pipeline -- HeyGen Edition v1.0
===================================================
Clean avatar-based pipeline using KF (HeyGen AI avatar).

FLOW:
  1. Generate script (Claude) -- content or ad mode
  2. Validate word counts (max only -- short is always fine)
  3. Submit to HeyGen -- KF delivers the script as a talking avatar video
  4. Poll until complete
  5. Download MP4
  6. Generate upload guide (Claude)

No FFmpeg. No TTS. No audio sync issues.
HeyGen handles voice, lip sync, and video rendering.

MODES:
  content  (default, 9 out of 10 runs) -- emotional, audience-first
  ad       (every 10th run)            -- punchy, direct response

WORD LIMITS (max only -- short scenes are always valid):
  CONTENT: hook=12 | problem=18 | story=20 | cta=16
  AD:      hook=10 | problem=14 | story=16 | cta=14
"""

import json
import os
import random
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
VIDEO_TIMEOUT = 600

CLAUDE_MAX_RETRIES = 10
CLAUDE_RETRY_BASE  = 30

# Max word counts per scene per mode (upper bound only)
WORD_LIMITS_CONTENT = {
    "hook":         12,
    "problem":      18,
    "story":        20,
    "solution_cta": 16,
}

WORD_LIMITS_AD = {
    "hook":         10,
    "problem":      14,
    "story":        16,
    "solution_cta": 14,
}

SEO_KEYWORDS = [
    "AI mental health coach for men",
    "recovery support anxiety depression",
    "sobriety mental wellness app",
]


# -- Helpers ------------------------------------------------------------------

def determine_mode() -> str:
    return "ad" if GITHUB_RUN_NUMBER % 10 == 0 else "content"


def get_word_limits(mode: str) -> dict:
    return WORD_LIMITS_CONTENT if mode == "content" else WORD_LIMITS_AD


def load_config() -> dict:
    cfg_path = PIPELINE_DIR / "heygen_config.json"
    with open(cfg_path) as f:
        return json.load(f)


def load_app_facts() -> dict:
    path = PIPELINE_DIR / "app_facts.json"
    with open(path) as f:
        return json.load(f)


def load_niche_keywords() -> dict:
    path = PIPELINE_DIR / "niche_keywords.json"
    if not path.exists():
        return {"seed_queries": ["men mental health tips"], "content_angles": ["real talk"]}
    with open(path) as f:
        return json.load(f)


# -- CHECKPOINT -- Word count validation (max only) ---------------------------

def validate_word_counts(script: dict, word_limits: dict) -> tuple:
    errors = []
    for scene in SCENE_ORDER:
        vo = script[scene]["voiceover"]
        wc = len(vo.split())
        hi = word_limits[scene]
        if wc > hi:
            errors.append(f"  [{scene}] {wc} words -- TOO LONG (max {hi}): '{vo}'")
    return (len(errors) == 0), errors


def generate_script_with_validation(generate_fn, generate_args, word_limits, max_attempts=3):
    for attempt in range(1, max_attempts + 1):
        script = generate_fn(*generate_args)
        passed, errors = validate_word_counts(script, word_limits)
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
                f"Script exceeded word count limits after {max_attempts} attempts.\n"
                + "\n".join(errors)
            )
    raise RuntimeError("Unexpected exit from validation loop")


# -- Step 1a -- Trending Topic ------------------------------------------------

def fetch_trending_topic_serpapi(seed_query: str) -> dict:
    params = {
        "engine": "google", "q": seed_query,
        "api_key": SERP_API_KEY, "num": 10, "hl": "en", "gl": "us",
    }
    resp = requests.get(SERP_API_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    related = data.get("related_questions", [])
    if related:
        picked = random.choice(related[:6])
        q = picked.get("question", seed_query)
        return {"topic": q, "question": q, "keyword": seed_query, "source": "serpapi"}
    organic = data.get("organic_results", [])
    if organic:
        t = organic[0].get("title", seed_query)
        return {"topic": t, "question": t, "keyword": seed_query, "source": "serpapi_organic"}
    return {"topic": seed_query, "question": seed_query, "keyword": seed_query, "source": "seed"}


def fetch_trending_topic_claude(seed_queries: list, client) -> dict:
    seed = random.choice(seed_queries)
    prompt = f"""You are an SEO expert in men's mental health, recovery, and AI wellness.

Generate ONE high-demand, low-competition video topic for TikTok and Facebook Reels.
Related to this seed: "{seed}"

Criteria:
- Phrased as a real question or struggle that men search for
- High emotional resonance for men 35+ in recovery or struggling
- Not too broad, not too niche

Return ONLY valid JSON, no markdown:
{{
  "topic": "the specific topic or question",
  "question": "how it might be phrased as a Google search",
  "keyword": "primary SEO keyword",
  "source": "claude_generated"
}}"""
    return _call_claude_raw(prompt, client, max_tokens=300)


def fetch_trending_topic(client) -> dict:
    keywords = load_niche_keywords()
    seed = random.choice(keywords["seed_queries"])
    if SERP_API_KEY:
        print(f"  Fetching topic via SerpAPI: '{seed}'")
        try:
            topic = fetch_trending_topic_serpapi(seed)
            print(f"  Topic ({topic['source']}): {topic['topic']}")
            return topic
        except Exception as e:
            print(f"  SerpAPI failed ({e}) -- falling back to Claude")
    print("  Generating topic with Claude...")
    topic = fetch_trending_topic_claude(keywords["seed_queries"], client)
    print(f"  Topic ({topic['source']}): {topic['topic']}")
    return topic


# -- Step 1b -- Script Generation ---------------------------------------------

def generate_content_script(topic: dict, client) -> dict:
    print(f"  Generating CONTENT script: {topic['topic']}")
    keyword  = topic.get("keyword", topic["topic"])
    question = topic.get("question", topic["topic"])
    angles   = load_niche_keywords().get("content_angles", [])
    angle    = random.choice(angles) if angles else "real talk"

    prompt = f"""You are a top-performing TikTok and Facebook Reels creator in the men's
mental health and recovery space.

Create a 4-scene viral video script on this topic:
TOPIC: {topic['topic']}
SEARCH QUESTION: {question}
SEO KEYWORD: {keyword}
CONTENT ANGLE: {angle}

FORMAT: Hook -> Problem/Truth -> Insight/Story -> Takeaway

AUDIENCE: Men 35+, in recovery or struggling with anxiety, depression, isolation.
Speak like a trusted older brother who has been through it. Value-first, NOT an ad.

WORD COUNT (hard MAXIMUM -- shorter is always fine, do not exceed these):
- hook:         up to 12 words -- bold statement, stops the scroll
- problem:      up to 18 words -- name the pain with room to breathe
- story:        up to 20 words -- real insight, emotional depth
- solution_cta: up to 16 words -- warm hopeful close, may mention MindCore AI

SEO: Include '{keyword}' naturally. Second person only ("you", "your").

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
    return _call_claude_raw(prompt, client, max_tokens=1000)


def generate_ad_script(app_facts: dict, client) -> dict:
    print("  Generating APP AD script...")
    trial   = app_facts["trial"]
    premium = app_facts["plans"]["premium"]
    notes   = "\n".join(f"- {n}" for n in app_facts["important_notes"])

    prompt = f"""You are a performance marketing copywriter for MindCore AI.
Write a 4-scene video ad: Hook -> Problem -> Story -> Solution+CTA.

AUDIENCE: Men 35+, recovery, anxiety, depression, isolation.
TONE: Raw, honest, brotherly. Not salesy.

VERIFIED APP FACTS (use ONLY these):
- Trial: {trial['messages']} messages + {trial['voice_minutes']} voice minutes over {trial['duration_days']} days. {trial['description']}
- Premium: {premium['price']}. Features: {', '.join(premium['features'])}
- Platform: {app_facts['platform']}
- CTA: {app_facts['cta']}

CRITICAL RULES:
{notes}

SEO KEYWORDS: {', '.join(SEO_KEYWORDS)}

WORD COUNT (hard MAXIMUM -- shorter is always fine, do not exceed these):
- hook:         up to 10 words
- problem:      up to 14 words
- story:        up to 16 words
- solution_cta: up to 14 words -- include CTA + accurate trial info

Return ONLY valid JSON, no markdown:
{{
  "video_type": "ad",
  "topic": "MindCore AI -- your AI mental wellness companion",
  "seo_keyword": "AI mental health coach for men",
  "hook": {{"voiceover": "..."}},
  "problem": {{"voiceover": "..."}},
  "story": {{"voiceover": "..."}},
  "solution_cta": {{"voiceover": "..."}}
}}"""
    return _call_claude_raw(prompt, client, max_tokens=1000)


def _call_claude_raw(prompt: str, client, max_tokens: int = 1000) -> dict:
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


# -- Step 2 -- Build full script text -----------------------------------------

def build_full_script(script: dict) -> str:
    """
    Combine all 4 scenes into one continuous voiceover script.
    HeyGen speaks the whole thing as a single video -- no scene breaks needed.
    Natural pauses come from punctuation (full stops, ellipses).
    """
    parts = []
    for scene in SCENE_ORDER:
        vo = script[scene]["voiceover"].strip()
        # Ensure sentence ends with punctuation for natural pause
        if vo and vo[-1] not in ".!?":
            vo += "."
        parts.append(vo)
    return "  ".join(parts)  # double space = natural breath between scenes


# -- Step 3 -- Submit to HeyGen -----------------------------------------------

def submit_heygen_video(script_text: str, avatar_id: str, voice_id: str = "") -> str:
    """
    Submit a video generation request to HeyGen.
    KF speaks the full script in a single continuous video.
    Returns the video_id for polling.
    """
    headers = {
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json",
    }

    avatar_config = {
        "avatar_id": avatar_id,
        "type": "talking_photo",
    }

    voice_config = {"type": "text"}
    if voice_id:
        voice_config["voice_id"] = voice_id

    payload = {
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": avatar_id,
                    "avatar_style": "normal",
                },
                "voice": {
                    "type": "text",
                    "input_text": script_text,
                    **(  {"voice_id": voice_id} if voice_id else {} ),
                },
            }
        ],
        "dimension": {"width": 720, "height": 1280},  # 9:16 portrait
        "aspect_ratio": "9:16",
        "test": False,
    }

    resp = requests.post(HEYGEN_SUBMIT_URL, headers=headers, json=payload, timeout=30)
    if not resp.ok:
        raise RuntimeError(f"HeyGen submit failed {resp.status_code}: {resp.text}")

    data = resp.json()
    video_id = data.get("data", {}).get("video_id") or data.get("video_id")
    if not video_id:
        raise RuntimeError(f"No video_id in HeyGen response: {data}")

    print(f"  Submitted to HeyGen -- video_id: {video_id}")
    return video_id


# -- Step 4 -- Poll HeyGen ----------------------------------------------------

def poll_heygen_video(video_id: str) -> str:
    """
    Poll until HeyGen finishes rendering.
    Returns the download URL of the completed MP4.
    """
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

        print(f"    waiting... status={status}")
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


# -- Step 6 -- Upload Guide ---------------------------------------------------

def generate_upload_guide(script: dict, mode: str, client) -> str:
    print("  Generating upload guide...")
    full_vo    = " ".join(script[scene]["voiceover"] for scene in SCENE_ORDER)
    topic      = script.get("topic", "")
    seo_kw     = script.get("seo_keyword", "")
    video_type = script.get("video_type", mode)

    prompt = f"""You are a social media growth expert for TikTok and Facebook Reels
in the men's mental health and recovery niche.

Generate a complete upload guide for TikTok AND Facebook Reels.

VIDEO TYPE: {video_type.upper()}
TOPIC: {topic}
SEO KEYWORD: {seo_kw}
FULL VOICEOVER: \"\"\"{full_vo}\"\"\"

TIKTOK:
- Title: max 100 chars, keyword-first, scroll-stopper
- Description: max 150 chars -- hook + keyword + soft CTA
- Hashtags: 8-12, mix broad/mid/niche. Start each with #.
- Best posting times: top 3 (day + UTC time) for this niche
- On-screen text overlay suggestion: 1 punchy line

FACEBOOK REELS:
- Title: max 255 chars
- Description: 2-3 sentences, keyword-rich, ends with CTA or question
- Hashtags: 5-7
- Best posting times: top 3 (day + UTC time)

ALSO:
- Thumbnail suggestion
- A/B test hook idea

Plain text only. Clear labels (TIKTOK TITLE:, etc). Copy-paste ready."""

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


def save_upload_guide(guide_text: str, script: dict, mode: str, run_number: int):
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    topic        = script.get("topic", "N/A")
    seo_kw       = script.get("seo_keyword", "N/A")
    video_type   = script.get("video_type", mode).upper()

    header = f"""================================================================================
  MINDCORE AI -- VIDEO UPLOAD GUIDE
  Run #{run_number} | {generated_at} | Avatar: KF
================================================================================
  Video type : {video_type}
  Topic      : {topic}
  SEO keyword: {seo_kw}
  Format     : 9:16 vertical | HeyGen avatar | TikTok + Facebook Reels ready
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

    mode        = determine_mode()
    word_limits = get_word_limits(mode)
    cfg         = load_config()
    avatar_id   = cfg["avatar_id"]
    voice_id    = cfg.get("voice_id", "")

    print(f"\n  MindCore AI Video Pipeline -- HeyGen Edition v1.0")
    print(f"  Run #{GITHUB_RUN_NUMBER} -- Mode: {mode.upper()}")
    print(f"  Avatar: {cfg['avatar_name']} ({avatar_id})")
    print(f"  Format: 9:16 vertical -- TikTok + Facebook Reels")
    if mode == "content":
        print(f"  Word limits (CONTENT max): hook=12 | problem=18 | story=20 | cta=16")
    else:
        print(f"  Word limits (AD max): hook=10 | problem=14 | story=16 | cta=14")
    print("=" * 60)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # 1. Script + validation
    print("\n  Generating script...")
    if mode == "ad":
        app_facts = load_app_facts()
        script    = generate_script_with_validation(
            generate_ad_script, (app_facts, client), word_limits
        )
    else:
        topic  = fetch_trending_topic(client)
        script = generate_script_with_validation(
            generate_content_script, (topic, client), word_limits
        )

    (OUTPUT_DIR / "script.json").write_text(json.dumps(script, indent=2))
    print(f"\n  Video type: {script.get('video_type', mode)}")
    print(f"  Topic:      {script.get('topic', 'N/A')}")
    print(f"  SEO kw:     {script.get('seo_keyword', 'N/A')}")
    print()
    for scene in SCENE_ORDER:
        wc = len(script[scene]["voiceover"].split())
        hi = word_limits[scene]
        print(f"  [{scene:15s}]  {wc:2d} words (max {hi})  |  {script[scene]['voiceover']}")

    # 2. Build full script
    full_script = build_full_script(script)
    print(f"\n  Full script ({len(full_script.split())} words):")
    print(f"  {full_script}")

    # 3. Submit to HeyGen
    print(f"\n  Submitting to HeyGen (avatar: {cfg['avatar_name']})...")
    video_id = submit_heygen_video(full_script, avatar_id, voice_id)

    # 4. Poll
    print("\n  Waiting for HeyGen to render...")
    video_url = poll_heygen_video(video_id)

    # 5. Download
    print("\n  Downloading video...")
    final = str(OUTPUT_DIR / "mindcore_ai_video.mp4")
    download_video(video_url, final)

    # 6. Upload guide
    print("\n  Generating upload guide...")
    guide_text = generate_upload_guide(script, mode, client)
    save_upload_guide(guide_text, script, mode, GITHUB_RUN_NUMBER)

    print(f"\n  DONE")
    print(f"  Video:  {final}")
    print(f"  Guide:  video_pipeline/output/upload_guide.txt")
    print(f"  Mode:   {mode.upper()} | Avatar: {cfg['avatar_name']}")
    print("\n  Pipeline complete!")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n  FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
