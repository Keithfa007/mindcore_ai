#!/usr/bin/env python3
"""
MindCore AI Video Pipeline v3.9
=================================
Smart content/ad rotation pipeline.

WORD LIMITS (v3.9):
  Content and ad modes now have SEPARATE word limits.

  CONTENT -- longer, more emotional, audience-first:
    hook:         8-12 words  -- bold statement, stops the scroll
    problem:      14-18 words -- name the pain with room to breathe
    story:        16-20 words -- emotional depth, perspective shift
    solution_cta: 12-16 words -- warm close, soft mention of MindCore AI
    Target video length: ~30-35 seconds

  AD -- short, punchy, direct response:
    hook:         6-10 words
    problem:      10-14 words
    story:        12-16 words
    solution_cta: 10-14 words
    Target video length: ~20-28 seconds

  Both modes share the same two-checkpoint validation:
    CHECKPOINT 1: word count (auto-retry Claude if exceeded)
    CHECKPOINT 2: actual audio duration (fail before WaveSpeed if over 7.0s)

  Hard ceiling: WaveSpeed supports max 8s clips. With 0.8s tail + 0.2s margin
  the max audio per scene is 7.0s. The checkpoint catches any overruns.
"""

import json
import os
import random
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import requests

# -- Config -------------------------------------------------------------------

ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
FISH_AUDIO_API_KEY = os.environ["FISH_AUDIO_API_KEY"]
WAVESPEED_API_KEY  = os.environ["WAVESPEED_API_KEY"]
FISH_VOICE_ID      = os.environ.get("FISH_VOICE_ID", "eed26f2294d64177911af612473cca98")
SERP_API_KEY       = os.environ.get("SERP_API_KEY", "")

GITHUB_RUN_NUMBER  = int(os.environ.get("GITHUB_RUN_NUMBER", "1"))

WAVESPEED_SUBMIT_URL = "https://api.wavespeed.ai/api/v3/wavespeed-ai/wan-2.2/t2v-720p"
WAVESPEED_RESULT_URL = "https://api.wavespeed.ai/api/v3/predictions/{task_id}/result"
FISH_TTS_URL         = "https://api.fish.audio/v1/tts"
SERP_API_URL         = "https://serpapi.com/search"

VIDEO_SIZE          = "720*1280"
OUTPUT_DIR          = Path("video_pipeline/output")
PIPELINE_DIR        = Path("video_pipeline")
SCENE_ORDER         = ["hook", "problem", "story", "solution_cta"]
POLL_INTERVAL       = 15
VIDEO_TIMEOUT       = 600
SUPPORTED_DURATIONS = [5, 8]

AUDIO_BUFFER_SECS   = 1.5   # buffer when requesting WaveSpeed clip
SCENE_TAIL_SECS     = 0.8   # silence after VO ends before next scene
TTS_SPEED           = 0.85  # slightly slower, warmer delivery

CLAUDE_MAX_RETRIES  = 10
CLAUDE_RETRY_BASE   = 30

# Word count limits per scene, per mode
# CONTENT: longer scenes for emotional depth and audience connection
# AD: short and punchy for direct response
WORD_LIMITS_CONTENT = {
    "hook":         (8, 12),   # bold opener, slightly longer than ad
    "problem":      (14, 18),  # name the pain with room to breathe
    "story":        (16, 20),  # emotional depth, real perspective shift
    "solution_cta": (12, 16),  # warm hopeful close
}

WORD_LIMITS_AD = {
    "hook":         (6, 10),   # ultra short scroll-stopper
    "problem":      (10, 14),  # quick pain point
    "story":        (12, 16),  # brief turning point
    "solution_cta": (10, 14),  # direct CTA with trial info
}

# Max audio per scene before we refuse to call WaveSpeed
# = largest clip (8s) - tail (0.8s) - safety margin (0.2s) = 7.0s
MAX_AUDIO_SECS = max(SUPPORTED_DURATIONS) - SCENE_TAIL_SECS - 0.2

SEO_KEYWORDS = [
    "AI mental health coach for men",
    "recovery support anxiety depression",
    "sobriety mental wellness app",
]


# -- Mode Detection -----------------------------------------------------------

def determine_mode() -> str:
    if GITHUB_RUN_NUMBER % 10 == 0:
        return "ad"
    return "content"


def get_word_limits(mode: str) -> dict:
    return WORD_LIMITS_CONTENT if mode == "content" else WORD_LIMITS_AD


# -- Loaders ------------------------------------------------------------------

def load_app_facts() -> dict:
    facts_path = PIPELINE_DIR / "app_facts.json"
    if not facts_path.exists():
        raise FileNotFoundError(f"app_facts.json not found at {facts_path}")
    with open(facts_path) as f:
        return json.load(f)


def load_niche_keywords() -> dict:
    kw_path = PIPELINE_DIR / "niche_keywords.json"
    if not kw_path.exists():
        return {"seed_queries": ["men mental health tips"], "content_angles": ["real talk"]}
    with open(kw_path) as f:
        return json.load(f)


# -- CHECKPOINT 1 -- Word count validation ------------------------------------

def validate_word_counts(script: dict, word_limits: dict) -> tuple:
    """Returns (passed: bool, errors: list[str])."""
    errors = []
    for scene in SCENE_ORDER:
        vo     = script[scene]["voiceover"]
        wc     = len(vo.split())
        lo, hi = word_limits[scene]
        if wc < lo:
            errors.append(f"  [{scene}] {wc} words -- too short (min {lo}): '{vo}'")
        elif wc > hi:
            errors.append(f"  [{scene}] {wc} words -- TOO LONG (max {hi}): '{vo}'")
    return (len(errors) == 0), errors


def generate_script_with_validation(generate_fn, generate_args, word_limits, max_attempts=3):
    """
    Call generate_fn, validate word counts against mode-specific limits,
    auto-retry if invalid. Fails fast before any TTS or WaveSpeed calls.
    """
    for attempt in range(1, max_attempts + 1):
        script = generate_fn(*generate_args)
        passed, errors = validate_word_counts(script, word_limits)

        if passed:
            print(f"  CHECKPOINT 1 PASSED -- all word counts within limits")
            return script

        print(f"  CHECKPOINT 1 FAILED (attempt {attempt}/{max_attempts}):")
        for e in errors:
            print(e)

        if attempt < max_attempts:
            print(f"  Regenerating script...")
        else:
            raise RuntimeError(
                f"Script failed word count validation after {max_attempts} attempts.\n"
                + "\n".join(errors)
            )

    raise RuntimeError("Unexpected exit from validation loop")


# -- CHECKPOINT 2 -- Audio duration validation --------------------------------

def validate_audio_durations(audio_durations: dict) -> None:
    """
    Verify every scene audio fits inside the max clip duration.
    Raises RuntimeError BEFORE any WaveSpeed calls if validation fails.
    No credits wasted on a video that would be broken.
    """
    errors = []
    for scene in SCENE_ORDER:
        a_dur = audio_durations[scene]
        if a_dur > MAX_AUDIO_SECS:
            errors.append(
                f"  [{scene}] audio={a_dur:.2f}s exceeds max {MAX_AUDIO_SECS:.1f}s "
                f"(8s clip - {SCENE_TAIL_SECS}s tail - 0.2s margin)"
            )

    if errors:
        raise RuntimeError(
            "CHECKPOINT 2 FAILED -- audio too long, aborting before WaveSpeed:\n"
            + "\n".join(errors)
            + "\nRe-run -- script will be regenerated with shorter voiceovers."
        )

    print(f"  CHECKPOINT 2 PASSED -- all audio within {MAX_AUDIO_SECS:.1f}s limit")


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
Speak directly, emotionally, like a trusted older brother who has been through it.

STRICT WORD COUNT RULES -- enforced by automated validator. Rejected and regenerated if exceeded.
- hook:         8-12 words   -- Bold statement or question. Stops the scroll immediately.
- problem:      14-18 words  -- Name the pain. Make them feel completely seen. Take your time.
- story:        16-20 words  -- Real insight, perspective shift, or truth they haven't heard.
                                This is where emotional connection happens. Don't rush it.
- solution_cta: 12-16 words  -- Warm, hopeful close. May naturally mention MindCore AI if it fits.

COUNT YOUR WORDS carefully before outputting. Exceeding limits causes auto-rejection.

SEO: Weave '{keyword}' naturally at least once. Second person only ("you", "your").
The hook must make someone stop mid-scroll. No generic openers.

VISUAL PROMPT RULES (vertical 9:16 portrait for mobile):
- 45-60 words each, cinematic realism, prestige drama quality
- Close-up portrait shots, authentic emotions, no posed looks
- No text, no logos, no UI, no phones in frame
- Describe: subject, action, lighting, camera movement, mood
- Style: shallow depth of field, film grain, golden/blue hour, dramatic

Return ONLY valid JSON, no markdown fences:
{{
  "video_type": "content",
  "topic": "{topic['topic']}",
  "seo_keyword": "{keyword}",
  "hook": {{"voiceover": "...", "visual_prompt": "..."}},
  "problem": {{"voiceover": "...", "visual_prompt": "..."}},
  "story": {{"voiceover": "...", "visual_prompt": "..."}},
  "solution_cta": {{"voiceover": "...", "visual_prompt": "..."}}
}}"""

    return _call_claude_raw(prompt, client, max_tokens=1600)


def generate_ad_script(app_facts: dict, client: anthropic.Anthropic) -> dict:
    print("  Generating APP AD script (using verified app_facts.json)...")
    trial   = app_facts["trial"]
    premium = app_facts["plans"]["premium"]
    notes   = "\n".join(f"- {n}" for n in app_facts["important_notes"])

    prompt = f"""You are a performance marketing copywriter for MindCore AI.
Write a 4-scene video ad: Hook -> Problem -> Story -> Solution+CTA.

AUDIENCE: Men 35+, in recovery or struggling with anxiety, depression, isolation.
TONE: Raw, honest, brotherly. Not salesy. Not clinical.

VERIFIED APP FACTS (use ONLY these):
- Trial: {trial['messages']} messages + {trial['voice_minutes']} voice minutes over {trial['duration_days']} days. {trial['description']}
- Premium plan: {premium['price']}. Features: {', '.join(premium['features'])}
- Platform: {app_facts['platform']}
- CTA: {app_facts['cta']}

CRITICAL RULES:
{notes}

SEO KEYWORDS: {', '.join(SEO_KEYWORDS)}

STRICT WORD COUNT RULES -- enforced by automated validator. Rejected and regenerated if exceeded.
- hook:         6-10 words   -- ultra-short scroll-stopper
- problem:      10-14 words  -- quick pain point
- story:        12-16 words  -- brief turning point
- solution_cta: 10-14 words  -- direct CTA with accurate trial info

COUNT YOUR WORDS carefully. Exceeding limits causes auto-rejection.

VISUAL PROMPT RULES (vertical 9:16 portrait):
- 45-60 words, cinematic realism, portrait framing
- No text, no logos, no UI elements
- Style: shallow depth of field, film grain, dramatic lighting

Return ONLY valid JSON, no markdown fences:
{{
  "video_type": "ad",
  "topic": "MindCore AI -- your AI mental wellness companion",
  "seo_keyword": "AI mental health coach for men",
  "hook": {{"voiceover": "...", "visual_prompt": "..."}},
  "problem": {{"voiceover": "...", "visual_prompt": "..."}},
  "story": {{"voiceover": "...", "visual_prompt": "..."}},
  "solution_cta": {{"voiceover": "...", "visual_prompt": "..."}}
}}"""

    return _call_claude_raw(prompt, client, max_tokens=1400)


def _call_claude_raw(prompt: str, client: anthropic.Anthropic, max_tokens: int = 1400) -> dict:
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
                    raise RuntimeError(
                        f"Anthropic API overloaded after {CLAUDE_MAX_RETRIES} attempts. "
                        "Try re-running the workflow in a few minutes."
                    )
                wait = CLAUDE_RETRY_BASE * attempt
                print(f"  Anthropic overloaded -- attempt {attempt}/{CLAUDE_MAX_RETRIES}, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise

        except json.JSONDecodeError:
            if attempt == CLAUDE_MAX_RETRIES:
                raise RuntimeError("Claude returned invalid JSON after all retries")
            print(f"  JSON parse error -- attempt {attempt}/{CLAUDE_MAX_RETRIES}, retrying in 10s...")
            time.sleep(10)

    raise RuntimeError("Unexpected exit from retry loop")


# -- Step 2 -- Fish Audio TTS -------------------------------------------------

def generate_tts(text: str, output_path: str) -> float:
    headers = {
        "Authorization": f"Bearer {FISH_AUDIO_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "reference_id": FISH_VOICE_ID,
        "format": "mp3",
        "mp3_bitrate": 128,
        "latency": "normal",
        "normalize": True,
        "speed": TTS_SPEED,
    }
    resp = requests.post(FISH_TTS_URL, headers=headers, json=payload, stream=True, timeout=60)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return get_media_duration(output_path)


def get_media_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


# -- Step 3 -- Duration Matching ----------------------------------------------

def choose_video_duration(audio_duration: float) -> int:
    needed = audio_duration + AUDIO_BUFFER_SECS
    for d in SUPPORTED_DURATIONS:
        if d >= needed:
            return d
    return max(SUPPORTED_DURATIONS)


# -- Step 4 -- WaveSpeed Video ------------------------------------------------

def submit_video(visual_prompt: str, duration: int) -> str:
    headers = {
        "Authorization": f"Bearer {WAVESPEED_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": visual_prompt,
        "size": VIDEO_SIZE,
        "duration": duration,
        "seed": -1,
        "enable_prompt_optimizer": True,
    }
    resp = requests.post(WAVESPEED_SUBMIT_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    task_id = (
        data.get("data", {}).get("id")
        or data.get("id")
        or data.get("task_id")
    )
    if not task_id:
        raise RuntimeError(f"No task_id in response: {data}")
    return task_id


def poll_video(task_id: str) -> str:
    headers  = {"Authorization": f"Bearer {WAVESPEED_API_KEY}"}
    url      = WAVESPEED_RESULT_URL.format(task_id=task_id)
    deadline = time.time() + VIDEO_TIMEOUT
    while time.time() < deadline:
        resp   = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        inner  = resp.json().get("data", resp.json())
        status = inner.get("status", "unknown")
        if status == "completed":
            outputs = inner.get("outputs", [])
            if outputs:
                return outputs[0]
            raise RuntimeError(f"Completed but no outputs: {inner}")
        if status in ("failed", "error", "cancelled"):
            raise RuntimeError(f"Generation failed [{status}]: {inner}")
        print(f"      waiting  {task_id[:8]}... {status}")
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Timed out after {VIDEO_TIMEOUT}s  task={task_id}")


def download_file(url: str, output_path: str):
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65_536):
            if chunk:
                f.write(chunk)


# -- Step 5 -- Mux audio onto video -------------------------------------------

def merge_audio_video(video_path: str, audio_path: str, output_path: str):
    v_dur      = get_media_duration(video_path)
    a_dur      = get_media_duration(audio_path)
    target_dur = a_dur + SCENE_TAIL_SECS

    print(f"    video={v_dur:.2f}s  audio={a_dur:.2f}s  -> clip={target_dur:.2f}s")

    if a_dur > v_dur:
        freeze_extra = (a_dur - v_dur) + SCENE_TAIL_SECS + 0.2
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path, "-i", audio_path,
            "-filter_complex",
            f"[0:v]tpad=stop_mode=clone:stop_duration={freeze_extra:.3f}[vout]",
            "-map", "[vout]", "-map", "1:a:0",
            "-t", f"{target_dur:.3f}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-r", "24",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
            output_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path, "-i", audio_path,
            "-map", "0:v", "-map", "1:a:0",
            "-t", f"{target_dur:.3f}",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-r", "24",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
            output_path,
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FFmpeg stderr:", result.stderr[-2000:])
        raise RuntimeError(f"merge_audio_video failed -> {output_path}")

    print(f"    merged: {get_media_duration(output_path):.2f}s")


# -- Step 6 -- Concat all scenes (hard cuts, perfect sync) --------------------

def concat_clips(clip_paths: list, output_path: str):
    n = len(clip_paths)
    if n == 1:
        import shutil
        shutil.copy(clip_paths[0], output_path)
        return

    durations = [get_media_duration(p) for p in clip_paths]
    total     = sum(durations)
    print(f"  Clip durations: {[f'{d:.2f}s' for d in durations]}  total={total:.2f}s")

    list_file = str(OUTPUT_DIR / "concat_list.txt")
    with open(list_file, "w") as f:
        for p in clip_paths:
            f.write(f"file '{Path(p).resolve()}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0", "-i", list_file,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FFmpeg stderr:", result.stderr[-2000:])
        raise RuntimeError("concat_clips failed")

    print(f"  Concat done -> {get_media_duration(output_path):.2f}s total")


# -- Step 7 -- Upload Guide ---------------------------------------------------

def generate_upload_guide(script: dict, mode: str, duration: float, client: anthropic.Anthropic) -> str:
    print("  Generating upload guide (TikTok + Facebook)...")

    full_voiceover = " ".join(script[scene]["voiceover"] for scene in SCENE_ORDER)
    topic      = script.get("topic", "")
    seo_kw     = script.get("seo_keyword", "")
    video_type = script.get("video_type", mode)

    prompt = f"""You are a social media growth expert specialising in TikTok and Facebook Reels
for the men's mental health and recovery niche.

Based on this video script, generate a complete upload guide for TikTok AND Facebook.

VIDEO TYPE: {video_type.upper()}
TOPIC: {topic}
SEO KEYWORD: {seo_kw}
DURATION: {duration:.1f} seconds
FULL VOICEOVER:
\"\"\"{full_voiceover}\"\"\"

Generate the following for EACH platform (TikTok and Facebook):

TIKTOK:
- Title: max 100 characters, front-load the keyword, scroll-stopper
- Description: max 150 characters (before "more") -- hook + keyword + soft CTA
- Hashtags: 8-12 hashtags. Mix broad, mid-tier, niche low-competition. Start each with #.
- Best posting times: top 3 times for this niche (day + time in UTC)
- Suggested on-screen text overlay: 1 punchy line for the hook moment

FACEBOOK REELS:
- Title: max 255 characters
- Description: 2-3 sentences, keyword-rich, ends with question or CTA
- Hashtags: 5-7 hashtags
- Best posting times: top 3 times for this niche (day + time in UTC)

ALSO INCLUDE:
- Thumbnail suggestion: ideal frame + any text overlay
- A/B test idea: one alternative hook line to test

Return plain text only -- no JSON, no markdown # headers.
Use clear labels: TIKTOK TITLE:, FACEBOOK DESCRIPTION:, etc.
Copy-paste ready."""

    for attempt in range(1, CLAUDE_MAX_RETRIES + 1):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1200,
                messages=[{"role": "user", "content": prompt}],
            )
            return message.content[0].text.strip()
        except anthropic.APIStatusError as e:
            if e.status_code == 529:
                wait = CLAUDE_RETRY_BASE * attempt
                print(f"  Anthropic overloaded -- upload guide attempt {attempt}/{CLAUDE_MAX_RETRIES}, waiting {wait}s...")
                time.sleep(wait)
            else:
                raise
    raise RuntimeError("Could not generate upload guide -- API overloaded")


def save_upload_guide(guide_text: str, script: dict, mode: str, duration: float, run_number: int):
    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    topic        = script.get("topic", "N/A")
    seo_kw       = script.get("seo_keyword", "N/A")
    video_type   = script.get("video_type", mode).upper()

    header = f"""================================================================================
  MINDCORE AI -- VIDEO UPLOAD GUIDE
  Run #{run_number} | {generated_at}
================================================================================
  Video type : {video_type}
  Topic      : {topic}
  SEO keyword: {seo_kw}
  Duration   : {duration:.1f}s
  Format     : 9:16 vertical | H.264 | AAC | TikTok + Facebook Reels ready
================================================================================

FULL SCRIPT (for reference)
----------------------------
"""
    for scene in SCENE_ORDER:
        wc = len(script[scene]["voiceover"].split())
        header += f"[{scene.upper()}]  ({wc} words)\n{script[scene]['voiceover']}\n\n"

    header += "================================================================================\n"
    header += "  PLATFORM UPLOAD DETAILS\n"
    header += "================================================================================\n\n"

    full_content = header + guide_text + "\n\n================================================================================\n"
    output_path  = OUTPUT_DIR / "upload_guide.txt"
    output_path.write_text(full_content, encoding="utf-8")
    print(f"  Upload guide saved -> {output_path}")
    return str(output_path)


# -- Main ---------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    mode        = determine_mode()
    word_limits = get_word_limits(mode)

    print(f"\n  MindCore AI Video Pipeline v3.9")
    print(f"  Run #{GITHUB_RUN_NUMBER} -- Mode: {mode.upper()}")
    print(f"  Format: 9:16 vertical (720x1280) -- TikTok + Facebook Reels")
    print(f"  TTS speed: {TTS_SPEED}x | Tail: {SCENE_TAIL_SECS}s | Max audio/scene: {MAX_AUDIO_SECS:.1f}s")
    if mode == "content":
        print(f"  Word limits (CONTENT): hook=8-12 | problem=14-18 | story=16-20 | cta=12-16")
    else:
        print(f"  Word limits (AD): hook=6-10 | problem=10-14 | story=12-16 | cta=10-14")
    print("=" * 60)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # 1. Script + CHECKPOINT 1 (mode-specific word count, auto-retry up to 3x)
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

    (OUTPUT_DIR / "script_v2.json").write_text(json.dumps(script, indent=2))
    print(f"\n  Video type: {script.get('video_type', mode)}")
    print(f"  Topic:      {script.get('topic', 'N/A')}")
    print(f"  SEO kw:     {script.get('seo_keyword', 'N/A')}")
    print()
    for scene in SCENE_ORDER:
        wc     = len(script[scene]["voiceover"].split())
        lo, hi = word_limits[scene]
        status = "OK" if lo <= wc <= hi else "!!"
        print(f"  [{scene:15s}]  {wc:2d} words [{status}]  |  {script[scene]['voiceover']}")

    # 2. TTS -- generate audio before any video calls
    print(f"\n  Generating voiceovers (Fish Audio | speed={TTS_SPEED}x)...")
    audio_paths, audio_durations, video_durations = {}, {}, {}
    for scene in SCENE_ORDER:
        path  = str(OUTPUT_DIR / f"{scene}_vo.mp3")
        a_dur = generate_tts(script[scene]["voiceover"], path)
        v_dur = choose_video_duration(a_dur)
        audio_paths[scene]     = path
        audio_durations[scene] = a_dur
        video_durations[scene] = v_dur
        print(f"  [{scene}]  audio={a_dur:.2f}s  -> {v_dur}s clip")

    # CHECKPOINT 2 -- audio duration before any WaveSpeed credits spent
    print("\n  Running CHECKPOINT 2 -- audio duration validation...")
    validate_audio_durations(audio_durations)

    # 3. Submit video jobs (only reached if both checkpoints passed)
    print("\n  Submitting video generation (WAN 2.2 T2V 9:16)...")
    task_ids = {}
    for scene in SCENE_ORDER:
        task_id = submit_video(script[scene]["visual_prompt"], video_durations[scene])
        task_ids[scene] = task_id
        print(f"  [{scene}]  task={task_id}  ({video_durations[scene]}s)")
        time.sleep(2)

    # 4. Poll + download
    print("\n  Polling WaveSpeed...")
    raw_video_paths = {}
    for scene in SCENE_ORDER:
        print(f"  [{scene}]  {task_ids[scene][:8]}...")
        video_url = poll_video(task_ids[scene])
        out = str(OUTPUT_DIR / f"{scene}_raw.mp4")
        download_file(video_url, out)
        raw_video_paths[scene] = out
        print(f"    raw: {get_media_duration(out):.2f}s")

    # 5. Mux audio + trim
    print(f"\n  Merging audio + trimming to audio + {SCENE_TAIL_SECS}s tail...")
    merged_paths = []
    for scene in SCENE_ORDER:
        out = str(OUTPUT_DIR / f"{scene}_merged.mp4")
        merge_audio_video(raw_video_paths[scene], audio_paths[scene], out)
        merged_paths.append(out)

    # 6. Concat (hard cuts, perfect sync)
    print("\n  Concatenating all scenes...")
    final = str(OUTPUT_DIR / "mindcore_ai_ad_v2.mp4")
    concat_clips(merged_paths, final)
    final_dur = get_media_duration(final)
    final_mb  = Path(final).stat().st_size / (1024 * 1024)

    # 7. Upload guide
    print("\n  Generating social media upload guide...")
    guide_text = generate_upload_guide(script, mode, final_dur, client)
    save_upload_guide(guide_text, script, mode, final_dur, GITHUB_RUN_NUMBER)

    print(f"\n  DONE")
    print(f"  Video:    {final}  ({final_dur:.2f}s | {final_mb:.1f} MB)")
    print(f"  Guide:    video_pipeline/output/upload_guide.txt")
    print(f"  Mode:     {mode.upper()}")
    print(f"  Format:   9:16 / H.264 / AAC -- ready for TikTok + Facebook")
    print("\n  Pipeline complete!")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n  FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
