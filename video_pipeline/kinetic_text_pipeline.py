#!/usr/bin/env python3
"""
MindCore AI — Kinetic Text Video Pipeline v3.0
===============================================
Cinematic kinetic typography with AI-generated backgrounds.

v3.0 changes:
- fal.ai Flux Schnell background image with Ken Burns (slow zoom/pan)
- No-overlap transitions: outgoing line slides up + fades, incoming fades in after
- Emotional voiceover: lower stability, style parameter, natural pauses
- Stronger text styling: text shadow, amber glow, slight scale effect
- Progress bar + watermark retained

Flow:
1. Claude generates short raw script with natural pause markers
2. fal.ai generates moody background image matching content angle
3. ElevenLabs generates emotional voiceover
4. Whisper transcribes for word-level timestamps
5. Pillow renders frames: Ken Burns background + kinetic text
6. FFmpeg encodes video
7. Upload-Post publishes to TikTok + Facebook + YouTube
"""

import os, sys, json, random, subprocess, tempfile, datetime, time, math
from pathlib import Path
from anthropic import Anthropic
import requests

ANTHROPIC_API_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
ELEVENLABS_API_KEY  = os.environ.get("ELEVENLABS_API_KEY", "")
UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
UPLOAD_POST_USER    = os.environ.get("UPLOAD_POST_USER", "MindCoreAI")
FAL_KEY             = os.environ.get("FAL_KEY", "")
ELEVENLABS_VOICE_ID = "jfIS2w2yJi0grJZPyEsk"
ELEVENLABS_API_URL  = "https://api.elevenlabs.io/v1/text-to-speech"
ANTHROPIC_MODEL     = "claude-sonnet-4-6"
GITHUB_RUN_NUMBER   = int(os.environ.get("GITHUB_RUN_NUMBER", "1"))
POST_HOUR_UTC       = int(os.environ.get("POST_HOUR_UTC", "15"))

OUTPUT_DIR = Path("video_pipeline/output_kinetic")
WIDTH = 1080
HEIGHT = 1920

TK_HASHTAGS = "#mindcoreai #mentalhealth #mentalhealthmatters #fyp #recovery #healing #realtalk"
FB_HASHTAGS = "#mentalhealth #mentalhealthmatters #recovery #healing #mindcoreai"

CONTENT_ANGLES = [
    {
        "name": "3am_confession",
        "instruction": "A raw, honest confession that someone thinks at 3am. Written as if Keith is talking to himself in the dark. 4-5 short sentences. Each sentence should hit on its own. Not motivational. Just honest.",
        "bg_prompt": "dark moody bedroom at 3am, moonlight through curtains, shadows, lonely atmosphere, cinematic film grain, muted blue tones, melancholic, no people, no text",
    },
    {
        "name": "recovery_truth",
        "instruction": "A hard truth about recovery that nobody tells you. Written from 2 years of experience. 4-5 sentences. Each one should make someone in early recovery nod and think 'yeah, that's exactly it.'",
        "bg_prompt": "empty road at dawn, fog lifting, first light breaking through clouds, moody atmospheric landscape, cinematic, muted warm tones, no people, no text",
    },
    {
        "name": "the_mask",
        "instruction": "About hiding behind a performance of being okay. The exhaustion of pretending. Written for anyone who smiles at work and falls apart at home. 4-5 sentences. Raw and specific.",
        "bg_prompt": "cracked mirror reflecting dim light, dark room, broken glass fragments, moody shadows, cinematic lighting, melancholic atmosphere, no people, no text",
    },
    {
        "name": "what_healing_looks_like",
        "instruction": "What recovery and healing actually look like versus what people think it looks like. Not pretty. Not linear. Boring, uncomfortable, and real. 4-5 sentences.",
        "bg_prompt": "messy unmade bed in morning light, coffee cup on nightstand, rain on window, quiet solitude, warm muted tones, cinematic film grain, no people, no text",
    },
    {
        "name": "letter_to_the_hiding",
        "instruction": "Written directly to someone who is still hiding their struggle. Not preachy. Not 'you should get help.' More like 'I see you because I was you.' 4-5 sentences.",
        "bg_prompt": "dark forest path with distant light at the end, misty trees, atmospheric fog, moody green and blue tones, cinematic depth, no people, no text",
    },
    {
        "name": "the_first_honest_moment",
        "instruction": "About the moment of telling one person the truth for the first time. The terror, the relief, the aftermath. 4-5 sentences. Specific and visceral.",
        "bg_prompt": "two empty chairs facing each other in dim room, single warm lamp light, intimate setting, moody shadows, cinematic, emotional atmosphere, no people, no text",
    },
    {
        "name": "functioning_addict",
        "instruction": "About being the person nobody suspects. Showing up, performing, succeeding at work while self-destructing in private. 4-5 sentences. Written from lived experience.",
        "bg_prompt": "office building at night with one window lit, city lights in background, dark moody urban scene, loneliness, cinematic wide shot, no people, no text",
    },
]


def get_angle_for_run():
    idx = GITHUB_RUN_NUMBER % len(CONTENT_ANGLES)
    angle = CONTENT_ANGLES[idx]
    print(f"  Angle: {angle['name']} ({idx+1}/{len(CONTENT_ANGLES)})")
    return angle


def generate_script(client, angle):
    prompt = f"""You are Keith, founder of MindCore AI. 2 years clean after 15 years of hidden addiction.
Write a short voiceover script for a TikTok video.

ANGLE: {angle['name']}
INSTRUCTION: {angle['instruction']}

RULES:
- Exactly 4-5 sentences. Each sentence on its own line.
- Total length: 40-70 words. This will be spoken in 15-25 seconds.
- First person. Raw. Honest. No filter.
- Each sentence should work as a standalone line of text on screen.
- NO emojis, NO hashtags, NO "hey guys", NO motivational cliches.
- Do NOT start with "I" more than twice.
- Write with natural breathing points. Use short sentences mixed with longer ones.
- Put a blank line between sentences that need a dramatic pause.

WRITING STYLE (MANDATORY):
- NEVER use em dashes. Use commas, periods, or separate sentences instead.
- NEVER use these AI-tell words: "delve", "tapestry", "landscape", "realm", "navigate", "leverage", "foster", "cultivate", "embark", "comprehensive", "multifaceted", "ever-evolving", "game-changer", "unlock", "unleash", "empower", "supercharge", "revolutionize".
- Write like a real person. Vary sentence length. No corporate jargon.

Return ONLY the script lines. Nothing else."""

    for attempt in range(3):
        try:
            result = client.messages.create(
                model=ANTHROPIC_MODEL, max_tokens=200,
                messages=[{"role": "user", "content": prompt}]
            ).content[0].text.strip()
            lines = [l.strip() for l in result.split("\n") if l.strip()]
            print(f"  Script ({len(lines)} lines, {sum(len(l.split()) for l in lines)} words):")
            for l in lines:
                print(f"    > {l}")
            return lines
        except Exception as e:
            print(f"  Script generation attempt {attempt+1} failed: {e}")
            if attempt == 2:
                raise
    raise RuntimeError("Failed to generate script")


def generate_caption(client, script_lines, angle):
    script_text = " ".join(script_lines)
    prompt = f"""Write a SHORT TikTok caption for this mental health video.

SCRIPT: "{script_text}"
ANGLE: {angle['name']}

RULES:
- 1-2 short sentences. Complement the script, don't repeat it.
- Raw honest tone. Can ask a question to drive comments.
- NO emojis, NO hashtags, NO links.

Return ONLY the caption text."""

    try:
        return client.messages.create(
            model=ANTHROPIC_MODEL, max_tokens=150,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text.strip()
    except:
        return "Some things need to be said out loud."


# ── Background Image ─────────────────────────────────────────────────────

def generate_background_image(angle, output_path):
    """Generate a moody background image using fal.ai Flux Schnell."""
    if not FAL_KEY:
        print("  FAL_KEY not set, using gradient fallback")
        return None

    prompt = angle.get("bg_prompt", "dark moody atmospheric background, cinematic, no text")
    # Portrait 9:16 for TikTok
    payload = {
        "prompt": prompt,
        "image_size": {"width": 1080, "height": 1920},
        "num_images": 1,
        "num_inference_steps": 4,
        "enable_safety_checker": False,
    }

    try:
        resp = requests.post(
            "https://fal.run/fal-ai/flux/schnell",
            headers={"Authorization": f"Key {FAL_KEY}", "Content-Type": "application/json"},
            json=payload, timeout=120,
        )
        if not resp.ok:
            print(f"  fal.ai error {resp.status_code}: {resp.text[:200]}")
            return None

        data = resp.json()
        images = data.get("images", [])
        if not images:
            print("  fal.ai returned no images")
            return None

        img_url = images[0].get("url", "")
        if not img_url:
            print("  fal.ai image has no URL")
            return None

        img_resp = requests.get(img_url, timeout=60)
        if img_resp.ok:
            with open(output_path, "wb") as f:
                f.write(img_resp.content)
            size_kb = os.path.getsize(output_path) / 1024
            print(f"  Background image generated ({size_kb:.0f} KB)")
            return output_path
        else:
            print(f"  Failed to download image: {img_resp.status_code}")
            return None
    except Exception as e:
        print(f"  fal.ai failed: {e}")
        return None


# ── Voiceover ─────────────────────────────────────────────────────────────

def prepare_emotional_text(script_lines):
    """Add natural pauses between sentences for more emotional delivery."""
    # Join with ellipsis pauses to create natural breathing breaks
    parts = []
    for i, line in enumerate(script_lines):
        parts.append(line)
        if i < len(script_lines) - 1:
            parts.append("...")  # ElevenLabs interprets this as a natural pause
    return " ".join(parts)


def generate_voiceover(script_lines, output_path):
    if not ELEVENLABS_API_KEY:
        print("  ELEVENLABS_API_KEY not set")
        return False

    script_text = prepare_emotional_text(script_lines)
    url = f"{ELEVENLABS_API_URL}/{ELEVENLABS_VOICE_ID}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": script_text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.30,           # low = more expressive, emotional variation
            "similarity_boost": 0.65,     # moderate similarity to original voice
            "style": 0.60,               # emotional expressiveness (v2 only)
            "use_speaker_boost": True,    # clearer, more present sound
        },
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=120)
        if not resp.ok:
            print(f"  ElevenLabs error {resp.status_code}: {resp.text[:200]}")
            return False
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
        size_kb = os.path.getsize(output_path) / 1024
        print(f"  Voiceover generated ({size_kb:.0f} KB) [emotional mode]")
        return True
    except Exception as e:
        print(f"  ElevenLabs failed: {e}")
        return False


# ── Whisper ────────────────────────────────────────────────────────────────

def get_word_timestamps(audio_path):
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, word_timestamps=True)
        words = []
        for segment in result.get("segments", []):
            for word_data in segment.get("words", []):
                words.append({
                    "word": word_data["word"].strip(),
                    "start": word_data["start"],
                    "end": word_data["end"],
                })
        print(f"  Whisper: {len(words)} words transcribed")
        return words
    except Exception as e:
        print(f"  Whisper failed: {e}")
        return None


def get_audio_duration(audio_path):
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
         "-of", "csv=p=0", audio_path],
        capture_output=True, text=True
    )
    return float(result.stdout.strip())


def build_line_timestamps(script_lines, word_timestamps, audio_duration):
    if not word_timestamps:
        interval = audio_duration / len(script_lines)
        return [{"text": line, "start": i * interval, "end": (i + 1) * interval}
                for i, line in enumerate(script_lines)]

    line_times = []
    word_idx = 0
    total_words = len(word_timestamps)

    for line in script_lines:
        line_word_count = len(line.split())
        if word_idx >= total_words:
            break
        start_time = word_timestamps[word_idx]["start"]
        end_idx = min(word_idx + line_word_count - 1, total_words - 1)
        end_time = word_timestamps[end_idx]["end"]
        line_times.append({"text": line, "start": start_time, "end": end_time})
        word_idx = end_idx + 1

    return line_times


# ── Video Rendering ────────────────────────────────────────────────────────

def wrap_text_for_video(text, font, max_width):
    words = text.split()
    lines = []
    current = ""
    for word in words:
        test = f"{current} {word}".strip()
        bbox = font.getbbox(test)
        tw = bbox[2] - bbox[0]
        if tw <= max_width:
            current = test
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def ease_in_out(t):
    return t * t * (3 - 2 * t)


def create_kinetic_video(audio_path, line_timestamps, output_path, audio_duration, bg_image_path=None):
    """Render cinematic kinetic text video with AI background + Ken Burns."""
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    import tempfile, shutil

    FPS = 24
    total_frames = int((audio_duration + 0.5) * FPS)
    FADE_IN = 0.30     # seconds for new line to fade in
    FADE_OUT = 0.25    # seconds for old line to fade out (starts before new line)
    OVERLAP_GAP = 0.0  # old line fully fades before new one starts fading in

    # Brand colours
    AMBER = (212, 165, 116)
    WHITE = (255, 255, 255)

    # Load fonts
    font_main = None
    font_watermark = None
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        try:
            font_main = ImageFont.truetype(p, 56)
            break
        except:
            continue
    for p in ["/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]:
        try:
            font_watermark = ImageFont.truetype(p, 24)
            break
        except:
            continue
    if not font_main:
        font_main = ImageFont.load_default()
    if not font_watermark:
        font_watermark = ImageFont.load_default()

    max_text_width = int(WIDTH * 0.82)
    line_h = 68

    # Pre-wrap all lines
    wrapped_blocks = []
    for lt in line_timestamps:
        wrapped = wrap_text_for_video(lt["text"], font_main, max_text_width)
        wrapped_blocks.append({
            "lines": wrapped,
            "start": lt["start"],
            "end": lt.get("end", audio_duration),
        })

    # ── Background setup ──────────────────────────────────────────────
    bg_source = None
    if bg_image_path and os.path.exists(bg_image_path):
        try:
            bg_source = Image.open(bg_image_path).convert("RGB")
            # Make it 20% larger than frame for Ken Burns room
            kb_scale = 1.20
            bg_source = bg_source.resize(
                (int(WIDTH * kb_scale), int(HEIGHT * kb_scale)),
                Image.LANCZOS
            )
            # Darken the image for text readability
            enhancer = ImageEnhance.Brightness(bg_source)
            bg_source = enhancer.enhance(0.35)  # 35% brightness (very dark)
            print(f"  Background: AI image loaded ({bg_source.size[0]}x{bg_source.size[1]})")
        except Exception as e:
            print(f"  Background image load failed: {e}")
            bg_source = None

    # Fallback: dark gradient
    if bg_source is None:
        bg_fallback = Image.new("RGB", (WIDTH, HEIGHT))
        draw_bg = ImageDraw.Draw(bg_fallback)
        for y in range(HEIGHT):
            ratio = y / HEIGHT
            ease = ratio * ratio * (3 - 2 * ratio)
            r = int(12 + (6 - 12) * ease)
            g = int(16 + (6 - 16) * ease)
            bv = int(32 + (12 - 32) * ease)
            draw_bg.line([(0, y), (WIDTH, y)], fill=(r, g, bv))
        print("  Background: dark gradient fallback")

    # Dark overlay for vignette effect (applied on top of Ken Burns frames)
    vignette = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    vig_draw = ImageDraw.Draw(vignette)
    # Top and bottom darkening
    for y in range(300):
        alpha = int(180 * (1.0 - y / 300))
        vig_draw.line([(0, y), (WIDTH, y)], fill=(0, 0, 0, alpha))
    for y in range(HEIGHT - 300, HEIGHT):
        alpha = int(180 * ((y - (HEIGHT - 300)) / 300))
        vig_draw.line([(0, y), (WIDTH, y)], fill=(0, 0, 0, alpha))

    # Watermark position
    wt = "MindCore AI"
    wb = font_watermark.getbbox(wt)
    ww = wb[2] - wb[0]
    watermark_x = (WIDTH - ww) // 2
    watermark_y = HEIGHT - 90

    # Progress bar
    bar_y = HEIGHT - 40
    bar_h = 4
    bar_margin = 80

    frames_dir = tempfile.mkdtemp(prefix="kinetic_frames_")
    print(f"  Rendering {total_frames} frames at {FPS}fps...")

    for fn in range(total_frames):
        t = fn / FPS
        progress = t / audio_duration if audio_duration > 0 else 0

        # ── Ken Burns background ──────────────────────────────────
        if bg_source is not None:
            # Slow zoom: 1.0 to 1.15 over the video duration
            zoom = 1.0 + 0.15 * progress
            # Slow pan: drift from center-left to center-right
            pan_x = 0.5 + 0.1 * math.sin(progress * math.pi)
            pan_y = 0.5 + 0.05 * math.cos(progress * math.pi * 0.7)

            src_w = bg_source.width
            src_h = bg_source.height
            crop_w = int(WIDTH / zoom)
            crop_h = int(HEIGHT / zoom)

            # Center the crop with pan offset
            cx = int(pan_x * (src_w - crop_w))
            cy = int(pan_y * (src_h - crop_h))
            cx = max(0, min(cx, src_w - crop_w))
            cy = max(0, min(cy, src_h - crop_h))

            cropped = bg_source.crop((cx, cy, cx + crop_w, cy + crop_h))
            frame = cropped.resize((WIDTH, HEIGHT), Image.LANCZOS)

            # Apply vignette overlay
            frame_rgba = frame.convert("RGBA")
            frame_rgba = Image.alpha_composite(frame_rgba, vignette)
            frame = frame_rgba.convert("RGB")
        else:
            frame = bg_fallback.copy()

        draw = ImageDraw.Draw(frame)

        # ── Determine active line ─────────────────────────────────
        active_idx = -1
        for i, block in enumerate(wrapped_blocks):
            if t >= block["start"]:
                active_idx = i

        # ── Draw text: one line at a time, no overlap ─────────────
        for i, block in enumerate(wrapped_blocks):
            is_active = (i == active_idx)
            is_outgoing = (i == active_idx - 1) if active_idx > 0 else False

            if not is_active and not is_outgoing:
                continue

            block_lines = block["lines"]
            block_height = len(block_lines) * line_h
            base_y = (HEIGHT // 2) - (block_height // 2) - 20

            if is_outgoing:
                # Outgoing line: fade out + slide up
                next_start = wrapped_blocks[active_idx]["start"]
                fade_start = next_start - FADE_OUT
                if t < fade_start:
                    alpha = 1.0
                    y_offset = 0
                elif t < next_start:
                    raw = (t - fade_start) / FADE_OUT
                    alpha = 1.0 - ease_in_out(min(raw, 1.0))
                    y_offset = -int(40 * ease_in_out(min(raw, 1.0)))  # slide up 40px
                else:
                    continue  # fully gone

                if alpha < 0.03:
                    continue

                cy = base_y + y_offset
                for line in block_lines:
                    bbox = font_main.getbbox(line)
                    tw = bbox[2] - bbox[0]
                    x = (WIDTH - tw) // 2
                    r_val = int(AMBER[0] * alpha * 0.5)
                    g_val = int(AMBER[1] * alpha * 0.5)
                    b_val = int(AMBER[2] * alpha * 0.5)
                    draw.text((x, cy), line, font=font_main, fill=(r_val, g_val, b_val))
                    cy += line_h

            elif is_active:
                # Active line: fade in
                elapsed = t - block["start"]
                if elapsed < FADE_IN:
                    alpha = ease_in_out(min(elapsed / FADE_IN, 1.0))
                else:
                    alpha = 1.0

                # Text colour: bright white
                r_val = int(255 * alpha)
                g_val = int(255 * alpha)
                b_val = int(255 * alpha)
                text_col = (r_val, g_val, b_val)

                cy = base_y

                # Glow effect (amber blur behind text)
                if alpha > 0.4:
                    glow_layer = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
                    glow_draw = ImageDraw.Draw(glow_layer)
                    gy = cy
                    glow_alpha = int(80 * alpha)
                    for line in block_lines:
                        bbox = font_main.getbbox(line)
                        tw = bbox[2] - bbox[0]
                        x = (WIDTH - tw) // 2
                        glow_draw.text((x, gy), line, font=font_main,
                                       fill=(AMBER[0], AMBER[1], AMBER[2], glow_alpha))
                        gy += line_h
                    glow_layer = glow_layer.filter(ImageFilter.GaussianBlur(radius=16))
                    frame = Image.alpha_composite(
                        frame.convert("RGBA"), glow_layer
                    ).convert("RGB")
                    draw = ImageDraw.Draw(frame)

                # Main text with shadow
                for line in block_lines:
                    bbox = font_main.getbbox(line)
                    tw = bbox[2] - bbox[0]
                    x = (WIDTH - tw) // 2
                    # Shadow (dark, offset)
                    sh_a = int(80 * alpha)
                    draw.text((x + 3, cy + 3), line, font=font_main, fill=(0, 0, 0, ))
                    draw.text((x + 2, cy + 2), line, font=font_main, fill=(sh_a, sh_a, sh_a))
                    # Main text
                    draw.text((x, cy), line, font=font_main, fill=text_col)
                    cy += line_h

        # ── Watermark ─────────────────────────────────────────────
        draw.text((watermark_x, watermark_y), wt, font=font_watermark, fill=(180, 180, 200))

        # ── Progress bar ──────────────────────────────────────────
        if audio_duration > 0:
            bar_progress = min(t / audio_duration, 1.0)
            bar_left = bar_margin
            bar_right = WIDTH - bar_margin
            bar_total_width = bar_right - bar_left

            draw.rectangle([(bar_left, bar_y), (bar_right, bar_y + bar_h)], fill=(40, 40, 60))
            fill_w = int(bar_total_width * bar_progress)
            if fill_w > 0:
                draw.rectangle([(bar_left, bar_y), (bar_left + fill_w, bar_y + bar_h)], fill=AMBER)

        frame.save(os.path.join(frames_dir, f"frame_{fn:05d}.png"), "PNG")

        if fn % (FPS * 5) == 0:
            print(f"    Frame {fn}/{total_frames} ({t:.1f}s)")

    print(f"  All frames written. Encoding with FFmpeg...")

    cmd = [
        "ffmpeg", "-y",
        "-framerate", str(FPS),
        "-i", os.path.join(frames_dir, "frame_%05d.png"),
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    shutil.rmtree(frames_dir, ignore_errors=True)

    if result.returncode != 0:
        print(f"  FFmpeg error: {result.stderr[-500:]}")
        raise RuntimeError("FFmpeg encoding failed")

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  Video created ({size_mb:.1f} MB, {audio_duration:.1f}s)")


# ── Upload & Scheduling ──────────────────────────────────────────────────

def get_scheduled_time(hour_utc):
    now = datetime.datetime.utcnow()
    target = now.replace(hour=hour_utc, minute=0, second=0, microsecond=0)
    if now >= target:
        target += datetime.timedelta(days=1)
    return target.strftime("%Y-%m-%dT%H:%M:%SZ")


def upload_video(video_path, caption, scheduled_date=None):
    if not UPLOAD_POST_API_KEY:
        return {"skipped": True, "reason": "no API key"}

    tiktok_caption = f"{caption}\n\n{TK_HASHTAGS}"
    fb_description = f"{caption}\n\n{FB_HASHTAGS}"

    data = [
        ("user", UPLOAD_POST_USER),
        ("platform[]", "tiktok"),
        ("platform[]", "facebook"),
        ("platform[]", "youtube"),
        ("title", tiktok_caption[:2200]),
        ("facebook_title", caption[:255]),
        ("facebook_description", fb_description),
        ("youtube_title", caption[:100]),
        ("youtube_description", f"{caption}\n\n#mentalhealth #mindcoreai #recovery #Shorts"),
        ("youtube_tags", "mental health,recovery,addiction,sobriety,mindcore ai,healing"),
    ]
    if scheduled_date:
        data.append(("scheduled_date", scheduled_date))

    try:
        with open(video_path, "rb") as f:
            resp = requests.post(
                "https://api.upload-post.com/api/upload",
                headers={"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"},
                files=[("video", ("kinetic.mp4", f, "video/mp4"))],
                data=data, timeout=180,
            )
        result = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {"raw": resp.text}
        result["status_code"] = resp.status_code
        print(f"  Upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}")
        if not resp.ok:
            print(f"  {resp.text[:300]}")
        return result
    except Exception as e:
        print(f"  Upload failed: {e}")
        return {"error": str(e)}


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"== MindCore AI - Kinetic Text Pipeline v3.0 ==")
    print(f"  Run #{GITHUB_RUN_NUMBER} | Post: {POST_HOUR_UTC}:00 UTC")

    if not ANTHROPIC_API_KEY:
        sys.exit("ERROR: ANTHROPIC_API_KEY not set")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    scheduled_date = get_scheduled_time(POST_HOUR_UTC)

    with tempfile.TemporaryDirectory() as tmp:
        audio_path = os.path.join(tmp, "voiceover.mp3")
        video_path = os.path.join(tmp, "kinetic.mp4")
        bg_image_path = os.path.join(tmp, "background.png")

        print("\n1. Picking angle...")
        angle = get_angle_for_run()

        print("\n2. Generating script...")
        script_lines = generate_script(client, angle)

        print("\n3. Generating caption...")
        caption = generate_caption(client, script_lines, angle)
        print(f"  Caption: {caption}")

        print("\n4. Generating background image (fal.ai)...")
        bg_result = generate_background_image(angle, bg_image_path)

        print("\n5. Generating voiceover (emotional mode)...")
        has_voice = generate_voiceover(script_lines, audio_path)
        if not has_voice:
            sys.exit("ERROR: Voiceover generation failed")

        print("\n6. Getting word timestamps (Whisper)...")
        word_timestamps = get_word_timestamps(audio_path)
        audio_duration = get_audio_duration(audio_path)
        print(f"  Audio duration: {audio_duration:.1f}s")

        print("\n7. Building line timestamps...")
        line_timestamps = build_line_timestamps(script_lines, word_timestamps, audio_duration)
        for lt in line_timestamps:
            print(f"  [{lt['start']:.1f}s] {lt['text']}")

        print("\n8. Creating kinetic text video...")
        create_kinetic_video(audio_path, line_timestamps, video_path, audio_duration,
                            bg_image_path=bg_result)

        import shutil
        output_copy = OUTPUT_DIR / f"kinetic_{GITHUB_RUN_NUMBER}.mp4"
        shutil.copy2(video_path, output_copy)

        # Also save the background image for review
        if bg_result and os.path.exists(bg_result):
            shutil.copy2(bg_result, OUTPUT_DIR / f"bg_{GITHUB_RUN_NUMBER}.png")

        print("\n9. Uploading...")
        result = upload_video(video_path, caption, scheduled_date=scheduled_date)
        if result.get("status_code") in (200, 202):
            print(f"  Scheduled: {scheduled_date}")

    (OUTPUT_DIR / "kinetic_metadata.json").write_text(json.dumps({
        "run": GITHUB_RUN_NUMBER, "angle": angle["name"],
        "script": script_lines, "caption": caption,
        "scheduled": scheduled_date, "platform": "tiktok+facebook+youtube",
        "bg_image": bool(bg_result),
    }, indent=2))

    print("\n== Done ==")


if __name__ == "__main__":
    main()
