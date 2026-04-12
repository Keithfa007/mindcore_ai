#!/usr/bin/env python3
"""
MindCore AI Video Pipeline -- HeyGen Edition v2.9.1
=====================================================

CHANGE (v2.9.1):
  solution_cta word limit raised from 12 → 14.
  "Try it -- 50 messages, 5 voice minutes. Find us on Google Play." = 13 words.
  12 was too tight for a CTA that includes both a trial fact and a platform CTA.
  14 gives one word of breathing room. Total ad is still ~20 seconds.
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

WORD_LIMITS_AD = {
    "hook":         8,
    "problem":      12,
    "story":        14,
    "solution_cta": 14,   # raised from 12 -- 13 words is natural for CTA + platform
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

# Banned phrases -- hard-replaced by sanitize_script() after generation
BANNED_PHRASE_REPLACEMENTS = [
    (r"try\s+it\s+for\s+free",  "try it"),
    (r"download\s+now",         "find us on Google Play"),
    (r"free\s+trial",           "trial"),
]

# Motion prompt v2.6 -- restrained natural hands, stillness as default
MOTION_PROMPT = (
    "Deliver this as a grounded, emotionally present mental health speaker -- not a performer. "

    "POSTURE: Stand with feet hip-width apart, upright but relaxed. Shoulders down and loose, "
    "never rigid. Open chest, torso forward. Project calm stability throughout. "

    "HANDS: Hands are mostly still and relaxed at rest -- this is the default state. "
    "Do NOT gesture continuously. Reserve hand movement for only the most important moments: "
    "a single open palm when making a key honest point, or one hand briefly touching the chest "
    "when speaking from deep personal experience. Between these rare gestures, hands return "
    "immediately to a relaxed resting position. Never touch the neck, rub the arms, or fidget "
    "with clothing. Less is more -- restraint feels trustworthy. "

    "HEAD AND FACE: Nod slowly and gently when making empathetic statements. "
    "A slight head tilt (10-15 degrees) when showing empathy or listening. "
    "Smile warmly and genuinely when offering hope -- not a fixed presenter smile. "
    "Soft, compassionate expression throughout -- earnest, not intense. "

    "EYE CONTACT: Soft, warm, intermittent eye contact with the camera. "
    "Compassionate and safe, not staring. The gaze of someone who genuinely cares. "

    "STILLNESS: When delivering a profound or difficult statement, go completely still -- "
    "stop all movement including hands -- and let the words land. Stillness is powerful. "
    "Lean forward slightly toward camera only during the most sensitive emotional points. "
    "Do not pace or shift weight nervously. "

    "OVERALL: A trusted older brother having a quiet, honest conversation. "
    "Grounded. Present. Still. Every movement is earned, never performed."
)


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
            print(f"  SANITIZED [{scene}]: '{original}' → '{cleaned}'")
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


# -- Step 1a -- Fetch Trending Topic ------------------------------------------

def fetch_trending_topic_serpapi(seed_query: str) -> dict:
    params = {
        "engine": "google",
        "q": seed_query,
        "api_key": SERP_API_KEY,
        "num": 10,
        "hl": "en",
        "gl": "us",
    }
    resp = requests.get(SERP_API_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    related_questions = data.get("related_questions", [])
    if related_questions:
        picked   = random.choice(related_questions[:6])
        question = picked.get("question", seed_query)
        return {"topic": question, "question": question, "keyword": seed_query, "source": "serpapi_people_also_ask"}

    organic = data.get("organic_results", [])
    if organic:
        title = organic[0].get("title", seed_query)
        return {"topic": title, "question": title, "keyword": seed_query, "source": "serpapi_organic"}

    return {"topic": seed_query, "question": seed_query, "keyword": seed_query, "source": "seed_fallback"}


def fetch_trending_topic_claude(seed_queries: list, client: anthropic.Anthropic) -> dict:
    seed   = random.choice(seed_queries)
    prompt = f"""You are an SEO and content strategy expert specialising in men's mental health,
recovery, anxiety, depression, and AI wellness.

Generate ONE high-demand, low-competition video topic for TikTok and Facebook Reels.
The topic must be related to this seed: "{seed}"

Criteria:
- Phrased as a real question or struggle that men search for
- High emotional resonance for men 35+ in recovery or struggling
- Not too broad ("mental health tips") and not too niche
- Something with genuine search volume but not dominated by big brands

Return ONLY valid JSON, no markdown:
{{
  "topic": "the specific topic or question",
  "question": "how it might be phrased as a Google search",
  "keyword": "primary SEO keyword for this topic",
  "source": "claude_generated"
}}"""
    return _call_claude_raw(prompt, client, max_tokens=300)


def fetch_trending_topic(client: anthropic.Anthropic) -> dict:
    keywords = load_niche_keywords()
    seed     = random.choice(keywords["seed_queries"])

    if SERP_API_KEY:
        print(f"  Fetching trending topic via SerpAPI: '{seed}'")
        try:
            topic = fetch_trending_topic_serpapi(seed)
            print(f"  Topic found ({topic['source']}): {topic['topic']}")
            return topic
        except Exception as e:
            print(f"  SerpAPI failed ({e}) -- falling back to Claude")

    print("  Generating topic with Claude...")
    topic = fetch_trending_topic_claude(keywords["seed_queries"], client)
    print(f"  Topic ({topic['source']}): {topic['topic']}")
    return topic


# -- Step 1b -- Script Generation ---------------------------------------------

def generate_content_script(topic: dict, client: anthropic.Anthropic) -> dict:
    print(f"  Generating CONTENT script: {topic['topic']}")
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
RAW TRUTH to men who are quietly struggling.

Create a 4-scene viral short video script on this topic:
TOPIC: {topic['topic']}
SEARCH QUESTION: {question}
SEO KEYWORD: {keyword}
CONTENT ANGLE: {angle}

FORMAT: Hook -> Problem/Truth -> Insight/Story -> Takeaway

AUDIENCE: Men 35+, in recovery or struggling with anxiety, depression, isolation.
They feel alone. They don't ask for help. This is value-first content -- NOT an ad.
Speak like a real person who has been through it -- a trusted older brother, not a presenter.

CRITICAL -- WRITE FOR THE EAR, NOT THE EYE:
This script will be spoken aloud by an avatar. It must sound like a real human talking.
- Use natural spoken language -- contractions, pauses, conversational connectors
- Sentences must FLOW. No choppy fragments. No isolated bursts.
- Use connectors like: "And the thing is...", "Because here's what nobody tells you...",
  "The truth is...", "What changed everything was...", "And if that's you right now..."
- Write how people actually talk when they're being honest with a friend
- Each scene = one continuous thought. Not bullet points dressed up as sentences.
- Read it aloud in your head. If it sounds robotic or stiff, rewrite it.

TARGET: ~60-70 seconds total. Aim for these word counts per scene:
- hook:         {lo_hook}-{hi_hook} words  -- One striking line that stops the scroll cold
- problem:      {lo_prob}-{hi_prob} words  -- Name the pain in flowing natural sentences.
                                              Make them feel completely seen.
- story:        {lo_story}-{hi_story} words -- Real insight, conversational sentences.
                                              Build to a moment of truth with specific detail.
- solution_cta: {lo_cta}-{hi_cta} words  -- Warm hopeful close. May mention MindCore AI.

Total target: ~130-150 words. Stick close to this -- TikTok videos should be 60-75 seconds.

SEO: Weave '{keyword}' naturally at least once. Second person only ("you", "your").
Hook must stop the scroll. No generic openers. No "hey guys". No "in today's video".

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
    print("  Generating APP AD script...")
    trial   = app_facts["trial"]
    premium = app_facts["plans"]["premium"]
    notes   = "\n".join(f"- {n}" for n in app_facts["important_notes"])

    prompt = f"""You are a performance marketing copywriter for MindCore AI.
Write a 4-scene video ad: Hook -> Problem -> Story -> Solution+CTA.

AUDIENCE: Men 35+, in recovery or struggling with anxiety, depression, isolation.
TONE: Raw, honest, brotherly. Not salesy. Not clinical. Sounds like a real person talking.

TARGET LENGTH: ~20 seconds total. Short, punchy, every word earns its place.

CRITICAL -- WRITE FOR THE EAR, NOT THE EYE:
- Use natural spoken language and contractions
- Sentences must flow -- no choppy fragments, no isolated word bursts
- Read it aloud in your head -- if it sounds stiff, rewrite it

BANNED PHRASES -- NEVER use these:
- "try it for free" -- say ONLY "try it" instead (NOT "try it for free")
- "free trial" -- say ONLY "trial" instead
- "download now" -- say "find us on Google Play"

VERIFIED APP FACTS (use ONLY these):
- Trial: {trial['messages']} messages + {trial['voice_minutes']} voice minutes over {trial['duration_days']} days. {trial['description']}
- Premium plan: {premium['price']}. Features: {', '.join(premium['features'])}
- Platform: {app_facts['platform']}
- CTA: {app_facts['cta']}

CRITICAL RULES:
{notes}

SEO KEYWORDS: {', '.join(SEO_KEYWORDS)}

STRICT WORD COUNT (enforced):
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

def submit_heygen_video(script_text: str, avatar_id: str, voice_id: str, background_color: str) -> str:
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
        "use_avatar_iv_model":          True,
        "custom_motion_prompt":         MOTION_PROMPT,
        "enhance_custom_motion_prompt": True,
        "test": False,
    }

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


# -- Step 5b -- Crop to proper 9:16 portrait ----------------------------------

def get_video_dimensions(path: str) -> tuple:
    """Use ffprobe to get actual video width and height."""
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
    """
    Run ffmpeg cropdetect to find the actual content area, ignoring dark bars.
    Background color #07071a has luma ~9; limit=30 catches it reliably.
    Returns (crop_w, crop_h, crop_x, crop_y) or None if detection fails.
    """
    cmd = [
        "ffmpeg", "-i", video_path,
        "-vf", "cropdetect=limit=30:round=2:reset=0",
        "-frames:v", "90",
        "-f", "null", "-"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    matches = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", result.stderr)
    if not matches:
        return None
    cw, ch, cx, cy = map(int, matches[-1])
    print(f"  cropdetect found content: {cw}x{ch} at x={cx}, y={cy}")
    return cw, ch, cx, cy


def make_portrait_filter(cw: int, ch: int, cx: int, cy: int) -> str:
    """
    Build ffmpeg filter to convert any content rect to 1080x1920 portrait.
    Scale so HEIGHT = 1920 (no stretch), then crop center 1080 wide.
    """
    scale_h = 1920
    scale_w = round(cw * scale_h / ch)
    if scale_w % 2 != 0:
        scale_w += 1

    if scale_w >= 1080:
        x_offset = (scale_w - 1080) // 2
        return (
            f"crop={cw}:{ch}:{cx}:{cy},"
            f"scale={scale_w}:{scale_h}:flags=lanczos,"
            f"crop=1080:1920:{x_offset}:0,"
            f"fps=30"
        )
    else:
        return (
            f"crop={cw}:{ch}:{cx}:{cy},"
            f"scale=1080:-2:flags=lanczos,"
            f"pad=1080:1920:0:(1920-ih)/2:color=0x07071a,"
            f"fps=30"
        )


def crop_to_portrait(raw_path: str, final_path: str):
    """Convert HeyGen output to proper 9:16 portrait using cropdetect."""
    w, h = get_video_dimensions(raw_path)
    print(f"  Raw video dimensions: {w}x{h}")

    crop_result = detect_content_crop(raw_path)

    if crop_result:
        cw, ch, cx, cy = crop_result
        filter_str = make_portrait_filter(cw, ch, cx, cy)
        print(f"  Filter: {filter_str}")
    else:
        print(f"  cropdetect found no bars -- treating full frame as content")
        filter_str = make_portrait_filter(w, h, 0, 0)

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
    print(f"  Final portrait: {final_path} ({w2}x{h2} | {size_mb:.1f} MB)")


# -- Step 6 -- Upload Guide ---------------------------------------------------

def generate_upload_guide(script: dict, mode: str, client: anthropic.Anthropic) -> str:
    print("  Generating upload guide...")
    full_vo    = " ".join(script[scene]["voiceover"] for scene in SCENE_ORDER)
    topic      = script.get("topic", "")
    seo_kw     = script.get("seo_keyword", "")
    video_type = script.get("video_type", mode)

    prompt = f"""You are a social media growth expert specialising in TikTok and Facebook Reels
for the men's mental health and recovery niche.

Generate a complete upload guide for TikTok AND Facebook.

VIDEO TYPE: {video_type.upper()}
TOPIC: {topic}
SEO KEYWORD: {seo_kw}
FULL VOICEOVER:
\"\"\"{full_vo}\"\"\"

TIKTOK:
- Title: max 100 characters, front-load the keyword, scroll-stopper
- Description: max 150 characters -- hook + keyword + soft CTA
- Hashtags: 8-12. Mix broad/mid/niche. Start each with #.
- Best posting times: top 3 (day + UTC time) for this niche
- On-screen text overlay suggestion: 1 punchy line

FACEBOOK REELS:
- Title: max 255 characters
- Description: 2-3 sentences, keyword-rich, ends with CTA or question
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
  Format      : 1080x1920 9:16 30fps | Avatar IV + motion | TikTok + Facebook
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

    print(f"\n  MindCore AI Video Pipeline -- HeyGen Edition v2.9.1")
    print(f"  Run #{GITHUB_RUN_NUMBER} -- Mode: {mode.upper()}")
    print(f"  Avatar look: {avatar_id[:8]}... (1 of {len(cfg['avatar_look_ids'])}) | bg: {background_color}")
    print(f"  Format: 1080x1920 9:16 30fps | scale-to-height crop | script sanitizer")
    if mode == "content":
        print(f"  Target: ~60-70s | hook=10-15 | problem=30-40 | story=50-65 | cta=25-35")
    else:
        print(f"  Target: ~20s | hook=8 | problem=12 | story=14 | cta=14")
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

    print(f"\n  Submitting to HeyGen (Avatar IV + motion | look: {avatar_id[:8]}...)...")
    video_id = submit_heygen_video(full_script, avatar_id, voice_id, background_color)

    print(f"\n  Waiting for HeyGen to render (up to {VIDEO_TIMEOUT//60} min)...")
    video_url = poll_heygen_video(video_id)

    print("\n  Downloading raw video from HeyGen...")
    raw_path   = str(OUTPUT_DIR / "mindcore_ai_raw.mp4")
    final_path = str(OUTPUT_DIR / "mindcore_ai_video.mp4")
    download_video(video_url, raw_path)

    print("\n  Converting to 9:16 portrait (scale-to-height, center crop)...")
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
