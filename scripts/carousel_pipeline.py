#!/usr/bin/env python3
"""
MindCore AI -- Carousel Image Post Pipeline v1.3
=================================================
Generates a 50-second TikTok slideshow video from 5 cinematic images.
Partner-directed scripts drive saves and shares.

Format:
  - 5 cinematic images (gpt-image-1 HIGH, 1080x1920)
  - Bold text overlay per slide (PIL)
  - ffmpeg assembles 50s slideshow video (10s per slide)
  - Ambient music from video_pipeline/music folder
  - Full prose script as caption
  - Uploaded as video via Upload-Post to TikTok

Cost: ~$0.40/post (5 x gpt-image-1 high @ ~$0.08)
Schedule: daily 07:00 UTC (9am Malta --> ~2pm Malta landing)

v1.3: Convert images to slideshow video for Upload-Post compatibility
v1.2: gpt-image-1 high quality
v1.1: TikTok only
"""

import base64
import io
import json
import os
import random
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import requests
from PIL import Image, ImageDraw, ImageFont
from openai import OpenAI

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
ANTHROPIC_API_KEY   = os.environ["ANTHROPIC_API_KEY"]
OPENAI_API_KEY      = os.environ["OPENAI_API_KEY"]
UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
GITHUB_RUN_NUMBER   = int(os.environ.get("GITHUB_RUN_NUMBER", "1"))

UPLOAD_POST_API_URL = "https://api.upload-post.com/api/upload"

OUTPUT_DIR   = Path("scripts/output_carousel")
PIPELINE_DIR = Path("scripts")
MUSIC_DIR    = Path("video_pipeline/music")
HISTORY_PATH = PIPELINE_DIR / "carousel_history.json"

REQUIRED_BRAND_HASHTAG = "#mindcoreai"
HASHTAGS = (
    "#mindcoreai #mentalhealth #fyp #foryou "
    "#mentalhealthawareness #anxiety #healing #selfcare"
)

IMAGE_WIDTH   = 1080
IMAGE_HEIGHT  = 1920
SECONDS_PER_SLIDE = 10  # 5 slides x 10s = 50s total
MUSIC_VOLUME  = 0.08

CLAUDE_MAX_RETRIES = 8
CLAUDE_RETRY_BASE  = 30

# ---------------------------------------------------------------------------
# Partner-directed topic seeds
# ---------------------------------------------------------------------------
PARTNER_SEEDS = [
    "loving someone with anxiety",
    "supporting someone with depression",
    "loving someone in recovery from addiction",
    "what someone with burnout needs from you",
    "loving someone who carries everything alone",
    "what your anxious partner needs you to know",
    "supporting a partner with mental health struggles",
    "what loving someone with high-functioning anxiety looks like",
    "how to love someone who doesn't know how to ask for help",
    "what men in recovery need their partners to understand",
    "loving someone who can't switch their mind off",
    "what it means to love someone with depression",
    "how to support someone who overthinks everything",
    "what someone with trauma needs from the people they love",
    "loving someone who has never felt like enough",
]

# ---------------------------------------------------------------------------
# Slide image prompts
# ---------------------------------------------------------------------------
SLIDE_IMAGE_PROMPTS = {
    "slide_1": (
        "Cinematic portrait photography, 9:16 vertical format. "
        "A person floating peacefully on their back in warm golden-hour water, "
        "face serene and eyes closed, hair fanned out around their head. "
        "Soft pink and lavender sunset reflections shimmering on the water. "
        "Warm aspirational wellness aesthetic, safe and beautiful. "
        "High-key warm grade, photorealistic, no text, no logos."
    ),
    "slide_2": (
        "Cinematic portrait photography, 9:16 vertical format. "
        "A person sitting alone near a rain-streaked window at dusk, "
        "warm soft ambient interior light casting a gentle glow, "
        "peaceful contemplative expression, hands in lap. "
        "Intimate quiet mood, slightly warm dim interior. "
        "Photorealistic, no text, no logos."
    ),
    "slide_3": (
        "Cinematic portrait photography, 9:16 vertical format. "
        "Two hands gently holding each other on a warm wooden table, "
        "soft golden afternoon light, simple and tender connection. "
        "Warm amber colour grade, quiet intimacy. "
        "Photorealistic, no text, no logos."
    ),
    "slide_4": (
        "Cinematic portrait photography, 9:16 vertical format. "
        "A person looking upward toward soft warm natural light "
        "streaming through a window, face peaceful and hopeful, "
        "golden light touching skin gently. "
        "Warm transitional mood, beginning of resolution. "
        "Photorealistic, no text, no logos."
    ),
    "slide_5": (
        "Cinematic portrait photography, 9:16 vertical format. "
        "Soft golden sunrise light filtering through sheer white curtains, "
        "peaceful bedroom scene, warm amber and ivory tones, "
        "a sense of safety, serenity, and gentle hope. "
        "Full warm golden resolution mood. "
        "Photorealistic, no text, no logos."
    ),
}

SLIDE_FONT_SIZES = {
    "slide_1": 62,
    "slide_2": 48,
    "slide_3": 48,
    "slide_4": 66,
    "slide_5": 54,
}

SLIDE_TEXT_POSITIONS = {
    "slide_1": 0.70,
    "slide_2": 0.55,
    "slide_3": 0.60,
    "slide_4": 0.65,
    "slide_5": 0.72,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def load_history():
    if HISTORY_PATH.exists():
        try: return json.loads(HISTORY_PATH.read_text())
        except: return []
    return []

def save_history(history, new_entry):
    history.append(new_entry)
    HISTORY_PATH.write_text(json.dumps(history[-30:], indent=2))
    print(f"  History: {len(history)} carousel posts")

def _call_claude(prompt, client, max_tokens=1500):
    for attempt in range(1, CLAUDE_MAX_RETRIES+1):
        try:
            msg = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=max_tokens,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = msg.content[0].text.strip()
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
            return json.loads(raw)
        except anthropic.APIStatusError as e:
            if e.status_code == 529:
                wait = CLAUDE_RETRY_BASE * attempt
                print(f"  Overloaded -- waiting {wait}s..."); time.sleep(wait)
            else: raise
        except json.JSONDecodeError:
            if attempt == CLAUDE_MAX_RETRIES: raise
            time.sleep(10)
    raise RuntimeError("Claude failed after all retries")

def pick_music_track():
    if not MUSIC_DIR.exists(): return None
    tracks = [t for t in MUSIC_DIR.glob("*.mp3") if t.stem != ".gitkeep"]
    if not tracks: return None
    chosen = random.choice(tracks)
    print(f"  Music: {chosen.name} @ {int(MUSIC_VOLUME*100)}%")
    return str(chosen)


# ---------------------------------------------------------------------------
# Step 1: Generate script
# ---------------------------------------------------------------------------
def generate_carousel_script(client, history):
    used_topics = [e.get("topic", "") for e in history]
    seed = random.choice(PARTNER_SEEDS)
    avoid = ", ".join(used_topics[-10:]) if used_topics else "none"

    prompt = f"""You are a senior mental wellness content writer specialising in TikTok carousel posts.

Write a 5-slide carousel post in the partner-directed style.
This content speaks TO the person who loves someone with a mental health struggle --
not to the person who is struggling. This doubles the audience because:
  - The struggling person shares it to their partner ("this is me")
  - The partner saves it ("I need to remember this")

SEED TOPIC: "{seed}"
AVOID (already used): {avoid}

TONE: Warm, empathetic, validating. Like advice from a wise friend who has been there.
Never preachy. Never clinical. No lists. Pure flowing prose.

FORMAT RULES:
  - headline_line1: First line. Ends mid-sentence for cliffhanger.
    Example: "Loving someone with anxiety"
  - headline_line2: Second line. MUST end with "..." for read-more impulse.
    Example: "means remembering this..."
  - slide_2_text: 3-4 sentences naming the invisible reality of their struggle.
  - slide_3_text: 3-4 sentences with the deeper truth. Begin to shift the frame.
  - slide_4_text: 1-2 sentences MAXIMUM. The screenshot-worthy payoff reframe.
    Example: "You don't have to fix their thoughts. Just stand beside them while they face them."
  - slide_5_text: 2-3 sentences warm resolution. Reader feels seen and capable.
  - full_prose_caption: 200-280 word flowing prose. No bullets. No headers.
    Start with the headline concept. End with soft save trigger like
    "Save this for the moments when you need a reminder."
  - topic: 4-7 word description
  - hashtag_topic: single hashtag without # (e.g. anxietysupport)

Return ONLY valid JSON:
{{
  "topic": "...",
  "headline_line1": "...",
  "headline_line2": "...\u2026",
  "slide_2_text": "...",
  "slide_3_text": "...",
  "slide_4_text": "...",
  "slide_5_text": "...",
  "full_prose_caption": "...",
  "hashtag_topic": "..."
}}"""

    result = _call_claude(prompt, client, max_tokens=1500)
    print(f"  Topic: {result.get('topic')}")
    print(f"  Headline: {result.get('headline_line1')} / {result.get('headline_line2')}")
    return result


# ---------------------------------------------------------------------------
# Step 2: Generate images via gpt-image-1 HIGH
# ---------------------------------------------------------------------------
def generate_slide_image(openai_client, slide_key, script):
    base_prompt = SLIDE_IMAGE_PROMPTS[slide_key]
    prompt = f"{base_prompt} Theme: {script.get('topic', '')}" if slide_key == "slide_1" else base_prompt
    print(f"  [gpt-image-1 HIGH] {slide_key} generating...")
    response = openai_client.images.generate(
        model="gpt-image-1", prompt=prompt,
        size="1024x1536", quality="high", n=1,
    )
    data = response.data[0]
    img_bytes = requests.get(data.url, timeout=30).content if getattr(data, "url", None) else base64.b64decode(data.b64_json)
    print(f"  [gpt-image-1 HIGH] {slide_key} ready ({len(img_bytes)//1024:.0f} KB)")
    return img_bytes


# ---------------------------------------------------------------------------
# Step 3: Resize to 1080x1920
# ---------------------------------------------------------------------------
def resize_to_tiktok(img_bytes):
    img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    scale = IMAGE_WIDTH / img.width
    new_h = int(img.height * scale)
    img = img.resize((IMAGE_WIDTH, new_h), Image.LANCZOS)
    if img.height >= IMAGE_HEIGHT:
        top = (img.height - IMAGE_HEIGHT) // 2
        img = img.crop((0, top, IMAGE_WIDTH, top + IMAGE_HEIGHT))
    else:
        padded = Image.new("RGB", (IMAGE_WIDTH, IMAGE_HEIGHT), (0, 0, 0))
        padded.paste(img, (0, (IMAGE_HEIGHT - img.height) // 2))
        img = padded
    return img


# ---------------------------------------------------------------------------
# Step 4: Text overlay
# ---------------------------------------------------------------------------
def wrap_text(text, font, max_width):
    words = text.split(); lines = []; current = []
    for word in words:
        test = " ".join(current + [word])
        try: w = font.getbbox(test)[2] - font.getbbox(test)[0]
        except: w = len(test) * 30
        if w <= max_width: current.append(word)
        else:
            if current: lines.append(" ".join(current))
            current = [word]
    if current: lines.append(" ".join(current))
    return lines

def load_font(size):
    for path in [
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/ubuntu/Ubuntu-Bold.ttf",
    ]:
        if Path(path).exists():
            try: return ImageFont.truetype(path, size)
            except: pass
    return ImageFont.load_default()

def add_text_overlay(img, text_lines, slide_key):
    draw = ImageDraw.Draw(img)
    font_size = SLIDE_FONT_SIZES[slide_key]
    font = load_font(font_size)
    max_w = int(IMAGE_WIDTH * 0.85)
    stroke = max(3, font_size // 18)
    spacing = int(font_size * 1.35)
    wrapped = []
    for line in text_lines:
        wrapped.extend(wrap_text(line, font, max_w))
    start_y = int(IMAGE_HEIGHT * SLIDE_TEXT_POSITIONS[slide_key]) - (len(wrapped) * spacing) // 2
    cx = IMAGE_WIDTH // 2
    for i, line in enumerate(wrapped):
        y = start_y + i * spacing
        for dx in range(-stroke, stroke+1):
            for dy in range(-stroke, stroke+1):
                if dx or dy:
                    draw.text((cx+dx, y+dy), line, font=font, fill=(0,0,0), anchor="mm")
        draw.text((cx, y), line, font=font, fill=(255,255,255), anchor="mm")
    return img

def build_slide_texts(script):
    return {
        "slide_1": [script["headline_line1"], script["headline_line2"]],
        "slide_2": [script["slide_2_text"]],
        "slide_3": [script["slide_3_text"]],
        "slide_4": [script["slide_4_text"]],
        "slide_5": [script["slide_5_text"]],
    }


# ---------------------------------------------------------------------------
# Step 5: Build slideshow video from images via ffmpeg
# ---------------------------------------------------------------------------
def build_slideshow_video(image_paths, music_path=None):
    """Assemble 5 images into a 50-second slideshow video with optional ambient music."""
    total_duration = len(image_paths) * SECONDS_PER_SLIDE
    concat_path = str(OUTPUT_DIR / "concat_images.txt")
    silent_video = str(OUTPUT_DIR / "slideshow_silent.mp4")
    final_video  = str(OUTPUT_DIR / "carousel_slideshow.mp4")

    # Write concat file -- each image shown for SECONDS_PER_SLIDE
    with open(concat_path, "w") as f:
        for path in image_paths:
            f.write(f"file '{Path(path).resolve()}'\n")
            f.write(f"duration {SECONDS_PER_SLIDE}\n")
        # ffmpeg concat needs the last file repeated without duration
        f.write(f"file '{Path(image_paths[-1]).resolve()}'\n")

    # Build silent slideshow video
    cmd = [
        "ffmpeg", "-f", "concat", "-safe", "0", "-i", concat_path,
        "-vf", "scale=1080:1920:force_original_aspect_ratio=decrease,"
               "pad=1080:1920:(ow-iw)/2:(oh-ih)/2,setsar=1",
        "-c:v", "libx264", "-crf", "18", "-preset", "fast",
        "-pix_fmt", "yuv420p", "-r", "30",
        "-t", str(total_duration), "-y", silent_video
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg slideshow failed: {result.stderr[-300:]}")
    print(f"  Slideshow: {total_duration}s video assembled")

    # Add ambient music if available
    if music_path and Path(music_path).exists():
        cmd = [
            "ffmpeg", "-i", silent_video,
            "-stream_loop", "-1", "-i", music_path,
            "-filter_complex", f"[1:a]volume={MUSIC_VOLUME}[music];[music]atrim=0:{total_duration}[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k",
            "-t", str(total_duration), "-y", final_video
        ]
        result = subprocess.run(cmd, capture_output=True, text=True)
        if result.returncode != 0:
            print(f"  Music mix failed -- using silent video")
            Path(silent_video).replace(Path(final_video))
        else:
            print(f"  Music added: {Path(music_path).name}")
    else:
        Path(silent_video).replace(Path(final_video))
        print("  No music track found -- silent video")

    size_mb = Path(final_video).stat().st_size / (1024*1024)
    print(f"  Final video: {size_mb:.1f} MB")
    return final_video


# ---------------------------------------------------------------------------
# Step 6: Caption
# ---------------------------------------------------------------------------
def build_caption(script):
    prose = script.get("full_prose_caption", "")
    topic_tag = f"#{script.get('hashtag_topic', 'mentalwellness')}"
    caption = f"{prose}\n\n{topic_tag} {HASHTAGS}"
    if REQUIRED_BRAND_HASHTAG.lower() not in caption.lower():
        caption += f" {REQUIRED_BRAND_HASHTAG}"
    return caption


# ---------------------------------------------------------------------------
# Step 7: Upload video to TikTok via Upload-Post
# ---------------------------------------------------------------------------
def upload_slideshow(video_path, caption, cfg):
    if not UPLOAD_POST_API_KEY:
        return {"skipped": True, "reason": "no API key"}
    user = cfg.get("upload_post_user", "")
    if not user:
        return {"skipped": True, "reason": "no user configured"}

    headers = {"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"}
    data = [
        ("user",       user),
        ("platform[]", "tiktok"),
        ("title",      caption[:2200]),
    ]
    try:
        with open(video_path, "rb") as f:
            files = [("video", ("carousel_slideshow.mp4", f, "video/mp4"))]
            resp = requests.post(
                UPLOAD_POST_API_URL, headers=headers,
                files=files, data=data, timeout=180
            )
        result = (
            resp.json()
            if resp.headers.get("content-type", "").startswith("application/json")
            else {"raw": resp.text}
        )
        result["status_code"] = resp.status_code
        print(f"  Upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}")
        if not resp.ok: print(f"  {resp.text[:300]}")
        return result
    except Exception as e:
        print(f"  Upload failed: {e}")
        return {"error": str(e)}


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    client        = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    openai_client = OpenAI(api_key=OPENAI_API_KEY)

    cfg = {}
    cfg_path = Path("video_pipeline/heygen_config.json")
    if cfg_path.exists():
        with open(cfg_path) as f: cfg = json.load(f)
    upload_enabled = cfg.get("upload_enabled", False) and bool(UPLOAD_POST_API_KEY)

    history = load_history()
    total_duration = 5 * SECONDS_PER_SLIDE

    print(f"\n  MindCore AI -- Carousel Image Post Pipeline v1.3")
    print(f"  Run #{GITHUB_RUN_NUMBER} | 5 slides x {SECONDS_PER_SLIDE}s = {total_duration}s | gpt-image-1 HIGH | ~$0.40")
    print(f"  Upload: {'ENABLED' if upload_enabled else 'DISABLED'} | TikTok only")
    print("=" * 60)

    # Script
    print("\n  Generating partner-directed script...")
    script = generate_carousel_script(client, history)
    (OUTPUT_DIR / "carousel_script.json").write_text(json.dumps(script, indent=2), encoding="utf-8")

    # Images
    slide_keys  = ["slide_1", "slide_2", "slide_3", "slide_4", "slide_5"]
    slide_texts = build_slide_texts(script)
    image_paths = []

    for slide_key in slide_keys:
        print(f"\n  [{slide_key.upper()}]")
        img_bytes = generate_slide_image(openai_client, slide_key, script)
        img = resize_to_tiktok(img_bytes)
        img = add_text_overlay(img, slide_texts[slide_key], slide_key)
        out_path = str(OUTPUT_DIR / f"{slide_key}.jpg")
        img.save(out_path, format="JPEG", quality=92)
        image_paths.append(out_path)
        print(f"  Saved: {Path(out_path).stat().st_size // 1024:.0f} KB")
        time.sleep(1)

    # Build slideshow video
    print("\n  Building slideshow video...")
    music_path  = pick_music_track()
    video_path  = build_slideshow_video(image_paths, music_path)

    # Caption
    caption = build_caption(script)
    (OUTPUT_DIR / "carousel_caption.txt").write_text(caption, encoding="utf-8")
    print(f"\n  Caption ({len(caption)} chars): {caption[:80]}...")

    # Upload
    if upload_enabled:
        print("\n  Uploading slideshow to TikTok...")
        result = upload_slideshow(video_path, caption, cfg)
        (OUTPUT_DIR / "carousel_upload_result.json").write_text(json.dumps(result, indent=2))
    else:
        print("\n  Upload DISABLED -- video saved to output_carousel/")
        (OUTPUT_DIR / "carousel_upload_result.json").write_text(json.dumps({"skipped": True}))

    save_history(history, {
        "date":     datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "topic":    script.get("topic", ""),
        "headline": f"{script.get('headline_line1')} / {script.get('headline_line2')}",
        "run":      GITHUB_RUN_NUMBER,
    })

    print(f"\n  DONE | {script.get('topic')} | {total_duration}s slideshow | ~$0.40")
    if upload_enabled: print("  Posted: TikTok")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        import sys
        print(f"\n  FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
