#!/usr/bin/env python3
"""
MindCore AI Video Pipeline -- Akool Cinematic Edition v1.0
==========================================================

Replaces HeyGen with Akool Image-to-Video (Seedance 1.5 Pro).
Generates cinematic 9:16 1080p videos with a consistent character
across all scenes, assembled via FFmpeg with Akool TTS voiceover.

ARCHITECTURE:
  1. Claude generates voiceover script (content or ad mode)
  2. Claude generates 6 cinematic scene prompts from the script
  3. Akool Image-to-Video API generates each scene (Seedance 1.5 Pro)
  4. Akool TTS API generates the voiceover audio
  5. FFmpeg assembles: scenes + voiceover -> 9:16 1080p final video
  6. Claude generates upload guide (TikTok + Facebook Reels)

NOTE on model_name: The exact Akool API model string for Seedance 1.5 Pro
  may differ from what is in akool_config.json. If you get a 400 error,
  check https://docs.akool.com for the current model_name values.
  Common formats: 'seedance-1-5-pro-i2v', 'seedance-1-5-pro-i2v-250428'
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
from concurrent.futures import ThreadPoolExecutor, as_completed

import anthropic
import requests

# -- Config -------------------------------------------------------------------

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
AKOOL_API_KEY     = os.environ["AKOOL_API_KEY"]
SERP_API_KEY      = os.environ.get("SERP_API_KEY", "")

GITHUB_RUN_NUMBER = int(os.environ.get("GITHUB_RUN_NUMBER", "1"))

AKOOL_BASE_URL   = "https://openapi.akool.com/api/open/v4"
AKOOL_I2V_URL    = f"{AKOOL_BASE_URL}/image2Video/createBySourcePrompt/batch"
AKOOL_TTS_URL    = f"{AKOOL_BASE_URL}/voice/tts"
AKOOL_I2V_STATUS = f"{AKOOL_BASE_URL}/image2Video/info"
AKOOL_TTS_STATUS = f"{AKOOL_BASE_URL}/voice/resource/detail"
SERP_API_URL     = "https://serpapi.com/search"

OUTPUT_DIR   = Path("video_pipeline/output")
PIPELINE_DIR = Path("video_pipeline")
SCENE_ORDER  = ["hook", "problem", "story", "solution_cta"]

# Polling
POLL_INTERVAL_I2V = 20   # seconds between I2V status checks
POLL_INTERVAL_TTS = 10   # seconds between TTS status checks
VIDEO_TIMEOUT     = 1800  # 30 minutes total
TTS_TIMEOUT       = 300   # 5 minutes

# Claude retry config
CLAUDE_MAX_RETRIES = 10
CLAUDE_RETRY_BASE  = 30

# Word count targets (same as HeyGen pipeline)
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

# Akool status codes
STATUS_PROCESSING = 1
STATUS_SUCCESS    = 2
STATUS_FAILED     = 3


# -- Helpers ------------------------------------------------------------------

def determine_mode() -> str:
    return "ad" if GITHUB_RUN_NUMBER % 10 == 0 else "content"


def load_config() -> dict:
    with open(PIPELINE_DIR / "akool_config.json") as f:
        return json.load(f)


def load_app_facts() -> dict:
    with open(PIPELINE_DIR / "app_facts.json") as f:
        return json.load(f)


def load_niche_keywords() -> dict:
    path = PIPELINE_DIR / "niche_keywords.json"
    if not path.exists():
        return {"seed_queries": ["men mental health tips"], "content_angles": ["real talk"]}
    with open(path) as f:
        return json.load(f)


def akool_headers() -> dict:
    return {
        "x-api-key": AKOOL_API_KEY,
        "Content-Type": "application/json",
    }


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
RAW TRUTH and shares REAL STORIES that men 35+ actually recognise from their own lives.

Create a 4-scene short video script on this topic:
TOPIC: {topic['topic']}
SEARCH QUESTION: {question}
SEO KEYWORD: {keyword}
CONTENT ANGLE: {angle}

FORMAT: Hook -> Problem/Truth -> Real Story or Insight -> Genuine Takeaway

AUDIENCE: Men 35+, in recovery or struggling with anxiety, depression, isolation.
They feel alone. They don't ask for help. Speak like someone who has genuinely been through it.

THIS IS PURE VALUE CONTENT -- NOT AN AD:
- Do NOT mention MindCore AI, any app, any product, or any service.
- Do NOT end with a download CTA or any promotional message.
- The last scene is a GENUINE HUMAN TAKEAWAY -- a real insight or honest truth.

WRITE FOR THE EAR, NOT THE EYE:
- Natural spoken language -- contractions, pauses, conversational connectors
- Use connectors: "And the thing is...", "Because here's what nobody tells you..."
- Each scene = one continuous thought, not bullet points

TARGET word counts per scene:
- hook:         {lo_hook}-{hi_hook} words
- problem:      {lo_prob}-{hi_prob} words
- story:        {lo_story}-{hi_story} words
- solution_cta: {lo_cta}-{hi_cta} words

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


# -- Step 2 -- Build full voiceover script ------------------------------------

def build_full_script(script: dict) -> str:
    parts = []
    for scene in SCENE_ORDER:
        vo = script[scene]["voiceover"].strip()
        if vo and vo[-1] not in ".!?":
            vo += "."
        parts.append(vo)
    return "  ".join(parts)


# -- Step 3 -- Generate cinematic scene prompts from Claude -------------------

def generate_scene_prompts(full_script: str, cfg: dict, client: anthropic.Anthropic) -> list:
    """Generate 6 cinematic visual prompts (one per scene clip) from the voiceover."""
    print("  Generating cinematic scene prompts...")

    char_desc   = cfg.get("character_description", "a middle-aged man, strong jaw, slight grey at temples")
    camera_style = cfg.get("camera_style", "subtle slow push-in, close-up portrait")
    lighting     = cfg.get("lighting_style", "cinematic moody lighting")
    neg_prompt   = cfg.get("negative_prompt", "blurry, distorted, low quality")
    num_scenes   = cfg.get("num_scenes", 6)

    prompt = f"""You are a cinematic AI video director. Based on the voiceover below, create {num_scenes} visual scene prompts
for an AI image-to-video generator (Seedance 1.5 Pro).

VOICEOVER:
\"\"\"
{full_script}
\"\"\"

CHARACTER (must appear in every scene for consistency):
{char_desc}

CINEMATIC STYLE:
- Format: 9:16 vertical portrait (mobile-first)
- Camera: {camera_style}
- Lighting: {lighting}
- Feel: cinematic, moody, emotionally honest -- like a mental health documentary
- NO text overlays, NO graphics, NO logos

RULES:
1. EVERY scene must start with a clear description of the character: "{char_desc}"
2. Each scene is 5 seconds long -- describe ONLY subtle motion (breathing, eye movement, light shift)
3. Vary the environment across scenes (kitchen at night, window at dawn, outdoor bench, empty room, etc.)
4. The character's emotional state should reflect the voiceover content for that section
5. Include the camera movement in each prompt
6. Use natural, cinematic photography language
7. Each prompt should be 40-60 words

SCENE MAPPING (distribute the voiceover emotionally across the {num_scenes} scenes):
- Scene 1: The hook moment -- catching the viewer
- Scene 2: The dark/heavy moment -- isolation or pain
- Scene 3: The turn -- something subtle shifts
- Scene 4: The insight -- quiet realisation
- Scene 5: Small hope -- morning light, a breath
- Scene 6: Resolution -- calm, grounded, present

Return ONLY valid JSON, no markdown:
{{
  "scenes": [
    {{"scene": 1, "prompt": "...", "negative_prompt": "{neg_prompt}"}},
    {{"scene": 2, "prompt": "...", "negative_prompt": "{neg_prompt}"}},
    {{"scene": 3, "prompt": "...", "negative_prompt": "{neg_prompt}"}},
    {{"scene": 4, "prompt": "...", "negative_prompt": "{neg_prompt}"}},
    {{"scene": 5, "prompt": "...", "negative_prompt": "{neg_prompt}"}},
    {{"scene": 6, "prompt": "...", "negative_prompt": "{neg_prompt}"}}
  ]
}}"""

    result = _call_claude_raw(prompt, client, max_tokens=2000)
    scenes = result.get("scenes", [])
    print(f"  Generated {len(scenes)} scene prompts")
    for s in scenes:
        print(f"  Scene {s['scene']}: {s['prompt'][:80]}...")
    return scenes


# -- Step 4 -- Submit to Akool Image-to-Video ---------------------------------

def submit_akool_scenes(scenes: list, cfg: dict) -> list:
    """Submit all scenes as a batch to Akool I2V API. Returns list of job _ids."""
    print(f"  Submitting {len(scenes)} scenes to Akool I2V...")

    model_name    = cfg.get("model_name", "seedance-1-5-pro-i2v")
    resolution    = cfg.get("resolution", "1080p")
    aspect_ratio  = cfg.get("aspect_ratio", "9:16")
    duration      = cfg.get("scene_duration_seconds", 5)
    image_url     = cfg["character_image_url"]

    # Akool batch endpoint accepts one image + one prompt per call.
    # We submit each scene individually but in parallel later.
    # First: submit all as a batch using the batch endpoint (count param)
    # Actually: the batch endpoint generates N variations of the SAME prompt.
    # For different prompts per scene, we need separate calls.
    job_ids = []
    for scene in scenes:
        payload = {
            "image_url":       image_url,
            "prompt":          scene["prompt"],
            "model_name":      model_name,
            "negative_prompt": scene.get("negative_prompt", ""),
            "extend_prompt":   True,
            "resolution":      resolution,
            "aspect_ratio":    aspect_ratio,
            "video_length":    duration,
            "count":           1,
        }
        resp = requests.post(AKOOL_I2V_URL, headers=akool_headers(), json=payload, timeout=30)
        if not resp.ok:
            raise RuntimeError(f"Akool I2V submit failed {resp.status_code}: {resp.text}")
        data = resp.json()
        success_list = data.get("data", {}).get("successList", [])
        if not success_list:
            raise RuntimeError(f"Akool I2V returned no jobs: {data}")
        job_id = success_list[0]["_id"]
        job_ids.append(job_id)
        print(f"  Scene {scene['scene']} submitted: {job_id}")
        time.sleep(1)  # slight delay between submissions

    return job_ids


# -- Step 5 -- Submit TTS to Akool --------------------------------------------

def submit_akool_tts(script_text: str, cfg: dict) -> str:
    """Submit TTS job to Akool. Returns job _id."""
    print("  Submitting TTS to Akool...")

    payload = {
        "input_text":        script_text,
        "voice_id":          cfg["voice_id"],
        "voice_model_name":  cfg.get("voice_model_name", "Akool Multilingual 3"),
        "audio_setting": {
            "sample_rate": 44100,
            "bitrate":     192000,
            "format":      "mp3",
            "channel":     2,
        },
    }

    resp = requests.post(AKOOL_TTS_URL, headers=akool_headers(), json=payload, timeout=30)
    if not resp.ok:
        raise RuntimeError(f"Akool TTS submit failed {resp.status_code}: {resp.text}")

    data   = resp.json()
    job_id = data.get("data", {}).get("_id")
    if not job_id:
        raise RuntimeError(f"Akool TTS returned no job _id: {data}")

    print(f"  TTS submitted: {job_id}")
    return job_id


# -- Step 6 -- Poll for completion --------------------------------------------

def poll_i2v_job(job_id: str, scene_num: int) -> str:
    """Poll a single I2V job until complete. Returns video URL."""
    deadline = time.time() + VIDEO_TIMEOUT
    while time.time() < deadline:
        resp = requests.get(
            f"{AKOOL_I2V_STATUS}/{job_id}",
            headers=akool_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        data   = resp.json().get("data", {})
        status = data.get("status", 0)

        if status == STATUS_SUCCESS:
            url = data.get("video_url") or data.get("url")
            if not url:
                raise RuntimeError(f"Scene {scene_num} completed but no video_url: {data}")
            print(f"  Scene {scene_num} ready: {url[:60]}...")
            return url

        if status == STATUS_FAILED:
            raise RuntimeError(f"Scene {scene_num} failed: {data}")

        elapsed = int(time.time() - (deadline - VIDEO_TIMEOUT))
        print(f"    Scene {scene_num} -- status={status} ({elapsed}s elapsed)")
        time.sleep(POLL_INTERVAL_I2V)

    raise TimeoutError(f"Scene {scene_num} timed out after {VIDEO_TIMEOUT}s")


def poll_tts_job(job_id: str) -> str:
    """Poll TTS job until complete. Returns audio URL."""
    deadline = time.time() + TTS_TIMEOUT
    while time.time() < deadline:
        resp = requests.get(
            f"{AKOOL_TTS_STATUS}/{job_id}",
            headers=akool_headers(),
            timeout=30,
        )
        resp.raise_for_status()
        data   = resp.json().get("data", {})
        status = data.get("status", 0)

        if status == STATUS_SUCCESS:
            url = data.get("audio_url") or data.get("preview") or data.get("url")
            if not url:
                raise RuntimeError(f"TTS completed but no audio_url: {data}")
            print(f"  TTS ready: {url[:60]}...")
            return url

        if status == STATUS_FAILED:
            raise RuntimeError(f"TTS generation failed: {data}")

        elapsed = int(time.time() - (deadline - TTS_TIMEOUT))
        print(f"    TTS -- status={status} ({elapsed}s elapsed)")
        time.sleep(POLL_INTERVAL_TTS)

    raise TimeoutError(f"TTS timed out after {TTS_TIMEOUT}s")


def poll_all_jobs(job_ids: list, tts_job_id: str) -> tuple:
    """Poll all I2V jobs and TTS in parallel using threads. Returns (video_urls, audio_url)."""
    print(f"  Polling {len(job_ids)} video scenes + TTS in parallel...")
    video_urls = [None] * len(job_ids)
    audio_url  = None

    with ThreadPoolExecutor(max_workers=len(job_ids) + 1) as ex:
        # Submit I2V futures
        i2v_futures = {
            ex.submit(poll_i2v_job, job_id, i + 1): i
            for i, job_id in enumerate(job_ids)
        }
        # Submit TTS future
        tts_future = ex.submit(poll_tts_job, tts_job_id)

        for future in as_completed({**i2v_futures, tts_future: "tts"}):
            if future is tts_future:
                audio_url = future.result()
            else:
                idx = i2v_futures[future]
                video_urls[idx] = future.result()

    return video_urls, audio_url


# -- Step 7 -- Download assets ------------------------------------------------

def download_file(url: str, output_path: str, label: str):
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65_536):
            if chunk:
                f.write(chunk)
    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"  Downloaded {label}: {output_path} ({size_mb:.1f} MB)")


# -- Step 8 -- FFmpeg assembly ------------------------------------------------

def assemble_video(scene_paths: list, audio_path: str, output_path: str):
    """Concat scene clips, add voiceover, ensure 9:16 1080p output."""
    print(f"  Assembling {len(scene_paths)} scenes with FFmpeg...")

    # Write concat list
    concat_file = str(OUTPUT_DIR / "concat_list.txt")
    with open(concat_file, "w") as f:
        for path in scene_paths:
            f.write(f"file '{Path(path).absolute()}'\n")

    # Step 1: Concat all scenes
    raw_concat = str(OUTPUT_DIR / "concat_raw.mp4")
    cmd_concat = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_file,
        "-c", "copy",
        raw_concat
    ]
    result = subprocess.run(cmd_concat, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FFmpeg concat stderr:\n{result.stderr[-500:]}")
        raise RuntimeError(f"FFmpeg concat failed: {result.returncode}")

    # Step 2: Merge with audio, scale to 1080x1920 9:16, 30fps
    cmd_merge = [
        "ffmpeg", "-y",
        "-i", raw_concat,
        "-i", audio_path,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,pad=1080:1920:(ow-iw)/2:(oh-ih)/2:color=black,fps=30",
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "slow",
        "-b:v", "4M",
        "-maxrate", "6M",
        "-bufsize", "8M",
        "-c:a", "aac",
        "-b:a", "192k",
        "-ar", "44100",
        "-shortest",  # trim to shortest stream
        output_path
    ]
    result = subprocess.run(cmd_merge, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FFmpeg merge stderr:\n{result.stderr[-500:]}")
        raise RuntimeError(f"FFmpeg merge failed: {result.returncode}")

    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    print(f"  Final video: {output_path} ({size_mb:.1f} MB)")


# -- Step 9 -- Upload Guide ---------------------------------------------------

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


def save_upload_guide(guide_text: str, script: dict, mode: str, run_number: int, cfg: dict):
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
  Character   : {cfg.get('character_name', 'Marcus')}
  Model       : {cfg.get('model_name', 'seedance-1-5-pro-i2v')}
  Est. length : ~{est_duration}s ({total_words} words @ ~130 wpm)
  Format      : 1080x1920 9:16 30fps | Cinematic | TikTok + Facebook
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

    mode = determine_mode()
    cfg  = load_config()

    print(f"\n  MindCore AI Video Pipeline -- Akool Cinematic Edition v1.0")
    print(f"  Run #{GITHUB_RUN_NUMBER} -- Mode: {mode.upper()}")
    print(f"  Character: {cfg.get('character_name', 'Marcus')} | Model: {cfg.get('model_name')}")
    print(f"  Format: 1080x1920 9:16 30fps | {cfg.get('num_scenes', 6)} scenes x {cfg.get('scene_duration_seconds', 5)}s")
    if mode == "content":
        print(f"  Content: educational + storytelling only -- zero promotion")
    else:
        print(f"  Ad: rotating CTA | ~20s")
    print("=" * 60)

    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    # -- Generate voiceover script
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
    for scene in SCENE_ORDER:
        wc = len(script[scene]["voiceover"].split())
        print(f"  [{scene:15s}]  {wc:2d} words  |  {script[scene]['voiceover']}")

    full_script = build_full_script(script)
    print(f"\n  Full script:\n  {full_script}")

    # -- Generate cinematic scene prompts
    print("\n  Generating visual scene prompts...")
    scenes = generate_scene_prompts(full_script, cfg, client)
    (OUTPUT_DIR / "scene_prompts.json").write_text(json.dumps(scenes, indent=2))

    # -- Submit to Akool (I2V + TTS in parallel)
    print("\n  Submitting to Akool...")
    i2v_job_ids = submit_akool_scenes(scenes, cfg)
    tts_job_id  = submit_akool_tts(full_script, cfg)

    # -- Poll until all complete
    print(f"\n  Waiting for {len(i2v_job_ids)} video scenes + TTS (up to {VIDEO_TIMEOUT//60} min)...")
    video_urls, audio_url = poll_all_jobs(i2v_job_ids, tts_job_id)

    # -- Download all assets
    print("\n  Downloading video scenes and audio...")
    scene_paths = []
    for i, url in enumerate(video_urls):
        path = str(OUTPUT_DIR / f"scene_{i+1:02d}.mp4")
        download_file(url, path, f"scene {i+1}")
        scene_paths.append(path)

    audio_path = str(OUTPUT_DIR / "voiceover.mp3")
    download_file(audio_url, audio_path, "voiceover")

    # -- Assemble final video
    print("\n  Assembling final video...")
    final_path = str(OUTPUT_DIR / "mindcore_ai_video.mp4")
    assemble_video(scene_paths, audio_path, final_path)

    # -- Generate upload guide
    print("\n  Generating upload guide...")
    guide_text = generate_upload_guide(script, mode, client)
    save_upload_guide(guide_text, script, mode, GITHUB_RUN_NUMBER, cfg)

    print(f"\n  DONE")
    print(f"  Video:  {final_path}")
    print(f"  Guide:  video_pipeline/output/upload_guide.txt")
    print(f"  Mode:   {mode.upper()} | ~{est_duration}s | {len(scenes)} scenes")
    print("\n  Pipeline complete!")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n  FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
