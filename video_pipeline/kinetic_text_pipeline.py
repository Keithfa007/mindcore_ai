#!/usr/bin/env python3
"""
MindCore AI — Kinetic Text Video Pipeline v3.1
===============================================
Cinematic word-by-word karaoke with AI backgrounds.

v3.1 changes:
- Word-by-word highlight synced to Whisper timestamps (karaoke style)
- Unspoken words: dim gray | Active word: amber glow | Spoken words: white
- Montserrat Extra Bold font (downloaded in workflow)
- Smoother sentence transitions (old sentence fades out before new appears)
- AI background + Ken Burns + emotional voice retained from v3.0
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
    if not FAL_KEY:
        print("  FAL_KEY not set, using gradient fallback")
        return None
    prompt = angle.get("bg_prompt", "dark moody atmospheric background, cinematic, no text")
    payload = {
        "prompt": prompt,
        "image_size": {"width": 1080, "height": 1920},
        "num_images": 1, "num_inference_steps": 4,
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
        if not images or not images[0].get("url"):
            print("  fal.ai returned no images")
            return None
        img_resp = requests.get(images[0]["url"], timeout=60)
        if img_resp.ok:
            with open(output_path, "wb") as f:
                f.write(img_resp.content)
            print(f"  Background generated ({os.path.getsize(output_path) // 1024} KB)")
            return output_path
        return None
    except Exception as e:
        print(f"  fal.ai failed: {e}")
        return None


# ── Voiceover ─────────────────────────────────────────────────────────────

def prepare_emotional_text(script_lines):
    parts = []
    for i, line in enumerate(script_lines):
        parts.append(line)
        if i < len(script_lines) - 1:
            parts.append("...")
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
            "stability": 0.30, "similarity_boost": 0.65,
            "style": 0.60, "use_speaker_boost": True,
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
        print(f"  Voiceover generated ({os.path.getsize(output_path) // 1024} KB) [emotional]")
        return True
    except Exception as e:
        print(f"  ElevenLabs failed: {e}")
        return False


# ── Whisper & Timestamps ──────────────────────────────────────────────────

def get_word_timestamps(audio_path):
    try:
        import whisper
        model = whisper.load_model("base")
        result = model.transcribe(audio_path, word_timestamps=True)
        words = []
        for seg in result.get("segments", []):
            for w in seg.get("words", []):
                words.append({"word": w["word"].strip(), "start": w["start"], "end": w["end"]})
        print(f"  Whisper: {len(words)} words")
        return words
    except Exception as e:
        print(f"  Whisper failed: {e}")
        return None


def get_audio_duration(audio_path):
    r = subprocess.run(
        ["ffprobe", "-v", "quiet", "-show_entries", "format=duration", "-of", "csv=p=0", audio_path],
        capture_output=True, text=True)
    return float(r.stdout.strip())


def build_sentence_word_data(script_lines, word_timestamps, audio_duration):
    """Build per-sentence, per-word timestamp data for karaoke rendering."""
    sentences = []
    w_idx = 0
    total_w = len(word_timestamps) if word_timestamps else 0

    for line in script_lines:
        words = line.split()
        sent = {"text": line, "words": []}
        for word in words:
            if w_idx < total_w:
                wt = word_timestamps[w_idx]
                sent["words"].append({"text": word, "start": wt["start"], "end": wt["end"]})
                w_idx += 1
            else:
                last_end = sent["words"][-1]["end"] if sent["words"] else 0
                sent["words"].append({"text": word, "start": last_end, "end": last_end + 0.3})
        if sent["words"]:
            sent["start"] = sent["words"][0]["start"]
            sent["end"] = sent["words"][-1]["end"]
        else:
            sent["start"] = 0
            sent["end"] = 0
        sentences.append(sent)

    return sentences


# ── Video Rendering ────────────────────────────────────────────────────────

def ease_in_out(t):
    return t * t * (3 - 2 * t)


def build_word_positions(words, font, max_width, center_x, base_y, line_h):
    """Calculate pixel (x, y) for each word, wrapping and centering lines."""
    space_w = font.getbbox("n")[2] - font.getbbox("n")[0]  # approximate space width

    # Pass 1: assign words to wrapped lines
    lines = []
    cur_line = []
    cur_w = 0
    for i, word in enumerate(words):
        bbox = font.getbbox(word["text"])
        ww = bbox[2] - bbox[0]
        test = cur_w + (space_w if cur_line else 0) + ww
        if test <= max_width or not cur_line:
            cur_line.append({"idx": i, "text": word["text"], "w": ww})
            cur_w = test
        else:
            lines.append((cur_line, cur_w))
            cur_line = [{"idx": i, "text": word["text"], "w": ww}]
            cur_w = ww
    if cur_line:
        lines.append((cur_line, cur_w))

    # Pass 2: compute centered positions
    positions = [None] * len(words)
    y = base_y
    for line_words, line_width in lines:
        x = center_x - line_width // 2
        for lw in line_words:
            positions[lw["idx"]] = {"x": x, "y": y, "w": lw["w"]}
            x += lw["w"] + space_w
        y += line_h

    return positions, len(lines)


def create_kinetic_video(audio_path, sentences, output_path, audio_duration, bg_image_path=None):
    """Render word-by-word karaoke video with AI background."""
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    import tempfile, shutil

    FPS = 24
    total_frames = int((audio_duration + 0.5) * FPS)
    SENT_FADE_IN = 0.25
    SENT_FADE_OUT = 0.20

    # Colours
    AMBER = (212, 165, 116)
    WHITE = (255, 255, 255)
    DIM = (90, 90, 110)
    BLACK = (0, 0, 0)

    # Load fonts — prefer Montserrat if available
    font_main = None
    for p in ["/tmp/fonts/Montserrat-ExtraBold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        try:
            font_main = ImageFont.truetype(p, 54)
            print(f"  Font: {os.path.basename(p)}")
            break
        except:
            continue
    if not font_main:
        font_main = ImageFont.load_default()

    font_wm = None
    for p in ["/tmp/fonts/Montserrat-Medium.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
              "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]:
        try:
            font_wm = ImageFont.truetype(p, 22)
            break
        except:
            continue
    if not font_wm:
        font_wm = ImageFont.load_default()

    max_text_w = int(WIDTH * 0.84)
    line_h = 72
    center_x = WIDTH // 2

    # Pre-compute word positions for each sentence
    for sent in sentences:
        block_lines_count_estimate = max(1, len(sent["words"]) // 4)
        block_h = block_lines_count_estimate * line_h
        base_y = (HEIGHT // 2) - (block_h // 2) - 20
        positions, n_lines = build_word_positions(
            sent["words"], font_main, max_text_w, center_x, base_y, line_h
        )
        # Recompute base_y with actual line count
        actual_h = n_lines * line_h
        base_y = (HEIGHT // 2) - (actual_h // 2) - 20
        positions, _ = build_word_positions(
            sent["words"], font_main, max_text_w, center_x, base_y, line_h
        )
        sent["positions"] = positions

    # ── Background ────────────────────────────────────────────────
    bg_source = None
    if bg_image_path and os.path.exists(bg_image_path):
        try:
            bg_source = Image.open(bg_image_path).convert("RGB")
            kb_scale = 1.20
            bg_source = bg_source.resize(
                (int(WIDTH * kb_scale), int(HEIGHT * kb_scale)), Image.LANCZOS)
            enhancer = ImageEnhance.Brightness(bg_source)
            bg_source = enhancer.enhance(0.32)
            print(f"  BG: AI image ({bg_source.size[0]}x{bg_source.size[1]})")
        except Exception as e:
            print(f"  BG load failed: {e}")
            bg_source = None

    if bg_source is None:
        bg_fallback = Image.new("RGB", (WIDTH, HEIGHT))
        d = ImageDraw.Draw(bg_fallback)
        for y in range(HEIGHT):
            r = y / HEIGHT
            e = r * r * (3 - 2 * r)
            d.line([(0, y), (WIDTH, y)],
                   fill=(int(12 + (6-12)*e), int(16 + (6-16)*e), int(32 + (12-32)*e)))
        print("  BG: gradient fallback")

    # Vignette overlay
    vignette = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
    vd = ImageDraw.Draw(vignette)
    for y in range(350):
        a = int(200 * (1.0 - y / 350))
        vd.line([(0, y), (WIDTH, y)], fill=(0, 0, 0, a))
    for y in range(HEIGHT - 350, HEIGHT):
        a = int(200 * ((y - (HEIGHT - 350)) / 350))
        vd.line([(0, y), (WIDTH, y)], fill=(0, 0, 0, a))

    # Watermark
    wt = "MindCore AI"
    wb = font_wm.getbbox(wt)
    wm_x = (WIDTH - (wb[2] - wb[0])) // 2
    wm_y = HEIGHT - 85

    bar_y = HEIGHT - 38
    bar_h = 4
    bar_m = 80

    frames_dir = tempfile.mkdtemp(prefix="kinetic_")
    print(f"  Rendering {total_frames} frames at {FPS}fps...")

    for fn in range(total_frames):
        t = fn / FPS
        progress = t / audio_duration if audio_duration > 0 else 0

        # ── Ken Burns BG ──────────────────────────────────────────
        if bg_source is not None:
            zoom = 1.0 + 0.15 * progress
            px = 0.5 + 0.1 * math.sin(progress * math.pi)
            py = 0.5 + 0.05 * math.cos(progress * math.pi * 0.7)
            sw, sh = bg_source.size
            cw, ch = int(WIDTH / zoom), int(HEIGHT / zoom)
            cx = max(0, min(int(px * (sw - cw)), sw - cw))
            cy = max(0, min(int(py * (sh - ch)), sh - ch))
            frame = bg_source.crop((cx, cy, cx + cw, cy + ch)).resize((WIDTH, HEIGHT), Image.LANCZOS)
            frame = Image.alpha_composite(frame.convert("RGBA"), vignette).convert("RGB")
        else:
            frame = bg_fallback.copy()

        draw = ImageDraw.Draw(frame)

        # ── Active sentence ───────────────────────────────────────
        active_idx = -1
        for i, s in enumerate(sentences):
            if t >= s["start"]:
                active_idx = i

        # ── Draw words ────────────────────────────────────────────
        for si, sent in enumerate(sentences):
            is_active = (si == active_idx)
            is_outgoing = (si == active_idx - 1) if active_idx > 0 else False

            if not is_active and not is_outgoing:
                continue

            positions = sent.get("positions", [])
            if not positions or any(p is None for p in positions):
                continue

            if is_outgoing:
                # Fade out old sentence
                next_s = sentences[active_idx]["start"]
                fade_begin = next_s - SENT_FADE_OUT
                if t >= next_s:
                    continue
                if t < fade_begin:
                    alpha = 1.0
                    y_off = 0
                else:
                    raw = (t - fade_begin) / SENT_FADE_OUT
                    alpha = 1.0 - ease_in_out(min(raw, 1.0))
                    y_off = -int(30 * ease_in_out(min(raw, 1.0)))

                if alpha < 0.03:
                    continue

                for wi, w in enumerate(sent["words"]):
                    pos = positions[wi]
                    c = (int(DIM[0] * alpha), int(DIM[1] * alpha), int(DIM[2] * alpha))
                    draw.text((pos["x"], pos["y"] + y_off), w["text"], font=font_main, fill=c)

            elif is_active:
                # Sentence fade-in alpha
                elapsed = t - sent["start"]
                sent_alpha = ease_in_out(min(elapsed / SENT_FADE_IN, 1.0)) if elapsed < SENT_FADE_IN else 1.0

                # Collect active-word indices for glow
                active_word_idx = -1
                for wi, w in enumerate(sent["words"]):
                    if w["start"] <= t < w["end"]:
                        active_word_idx = wi
                        break
                    elif t >= w["end"]:
                        active_word_idx = wi  # last finished word

                # Draw glow behind active word
                if active_word_idx >= 0 and sent_alpha > 0.5:
                    for wi, w in enumerate(sent["words"]):
                        if w["start"] <= t < w["end"]:
                            pos = positions[wi]
                            glow = Image.new("RGBA", (WIDTH, HEIGHT), (0, 0, 0, 0))
                            gd = ImageDraw.Draw(glow)
                            gd.text((pos["x"], pos["y"]), w["text"], font=font_main,
                                    fill=(AMBER[0], AMBER[1], AMBER[2], int(100 * sent_alpha)))
                            glow = glow.filter(ImageFilter.GaussianBlur(radius=14))
                            frame = Image.alpha_composite(frame.convert("RGBA"), glow).convert("RGB")
                            draw = ImageDraw.Draw(frame)
                            break

                # Draw each word
                for wi, w in enumerate(sent["words"]):
                    pos = positions[wi]
                    word_started = t >= w["start"]
                    word_active = w["start"] <= t < w["end"]

                    if word_active:
                        # Currently speaking: bright white
                        c = (int(255 * sent_alpha), int(255 * sent_alpha), int(255 * sent_alpha))
                    elif word_started:
                        # Already spoken: white
                        c = (int(240 * sent_alpha), int(240 * sent_alpha), int(240 * sent_alpha))
                    else:
                        # Not yet spoken: dim
                        c = (int(DIM[0] * sent_alpha), int(DIM[1] * sent_alpha), int(DIM[2] * sent_alpha))

                    # Text shadow
                    sh = (int(20 * sent_alpha), int(20 * sent_alpha), int(20 * sent_alpha))
                    draw.text((pos["x"] + 2, pos["y"] + 2), w["text"], font=font_main, fill=sh)
                    draw.text((pos["x"], pos["y"]), w["text"], font=font_main, fill=c)

        # ── Watermark + progress ──────────────────────────────────
        draw.text((wm_x, wm_y), wt, font=font_wm, fill=(180, 180, 200))
        if audio_duration > 0:
            bp = min(t / audio_duration, 1.0)
            bw = WIDTH - 2 * bar_m
            draw.rectangle([(bar_m, bar_y), (WIDTH - bar_m, bar_y + bar_h)], fill=(40, 40, 60))
            fw = int(bw * bp)
            if fw > 0:
                draw.rectangle([(bar_m, bar_y), (bar_m + fw, bar_y + bar_h)], fill=AMBER)

        frame.save(os.path.join(frames_dir, f"frame_{fn:05d}.png"), "PNG")
        if fn % (FPS * 5) == 0:
            print(f"    Frame {fn}/{total_frames} ({t:.1f}s)")

    print("  Encoding with FFmpeg...")
    cmd = [
        "ffmpeg", "-y", "-framerate", str(FPS),
        "-i", os.path.join(frames_dir, "frame_%05d.png"),
        "-i", audio_path,
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-c:a", "aac", "-b:a", "128k", "-pix_fmt", "yuv420p", "-shortest",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    shutil.rmtree(frames_dir, ignore_errors=True)
    if result.returncode != 0:
        print(f"  FFmpeg error: {result.stderr[-500:]}")
        raise RuntimeError("FFmpeg encoding failed")
    print(f"  Video: {os.path.getsize(output_path) / (1024*1024):.1f} MB, {audio_duration:.1f}s")


# ── Upload ────────────────────────────────────────────────────────────────

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
        ("platform[]", "tiktok"), ("platform[]", "facebook"), ("platform[]", "youtube"),
        ("title", tiktok_caption[:2200]),
        ("facebook_title", caption[:255]), ("facebook_description", fb_description),
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
                data=data, timeout=180)
        result = resp.json() if "json" in resp.headers.get("content-type", "") else {"raw": resp.text}
        result["status_code"] = resp.status_code
        print(f"  Upload {'OK' if resp.ok else 'WARN'}: {resp.status_code}")
        return result
    except Exception as e:
        print(f"  Upload failed: {e}")
        return {"error": str(e)}


# ── Main ──────────────────────────────────────────────────────────────────

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"== MindCore AI - Kinetic Text Pipeline v3.1 ==")
    print(f"  Run #{GITHUB_RUN_NUMBER} | Post: {POST_HOUR_UTC}:00 UTC")
    if not ANTHROPIC_API_KEY:
        sys.exit("ERROR: ANTHROPIC_API_KEY not set")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    scheduled_date = get_scheduled_time(POST_HOUR_UTC)

    with tempfile.TemporaryDirectory() as tmp:
        audio_path = os.path.join(tmp, "voiceover.mp3")
        video_path = os.path.join(tmp, "kinetic.mp4")
        bg_path = os.path.join(tmp, "background.png")

        print("\n1. Picking angle...")
        angle = get_angle_for_run()

        print("\n2. Generating script...")
        script_lines = generate_script(client, angle)

        print("\n3. Generating caption...")
        caption = generate_caption(client, script_lines, angle)
        print(f"  Caption: {caption}")

        print("\n4. Background image (fal.ai)...")
        bg_result = generate_background_image(angle, bg_path)

        print("\n5. Voiceover (emotional)...")
        if not generate_voiceover(script_lines, audio_path):
            sys.exit("ERROR: Voiceover generation failed")

        print("\n6. Word timestamps (Whisper)...")
        word_timestamps = get_word_timestamps(audio_path)
        audio_duration = get_audio_duration(audio_path)
        print(f"  Duration: {audio_duration:.1f}s")

        print("\n7. Building word-level data...")
        sentences = build_sentence_word_data(script_lines, word_timestamps, audio_duration)
        for s in sentences:
            print(f"  [{s['start']:.1f}-{s['end']:.1f}s] {s['text']} ({len(s['words'])} words)")

        print("\n8. Rendering video...")
        create_kinetic_video(audio_path, sentences, video_path, audio_duration,
                            bg_image_path=bg_result)

        import shutil
        shutil.copy2(video_path, OUTPUT_DIR / f"kinetic_{GITHUB_RUN_NUMBER}.mp4")
        if bg_result and os.path.exists(bg_result):
            shutil.copy2(bg_result, OUTPUT_DIR / f"bg_{GITHUB_RUN_NUMBER}.png")

        print("\n9. Uploading...")
        result = upload_video(video_path, caption, scheduled_date=scheduled_date)
        if result.get("status_code") in (200, 202):
            print(f"  Scheduled: {scheduled_date}")

    (OUTPUT_DIR / "kinetic_metadata.json").write_text(json.dumps({
        "run": GITHUB_RUN_NUMBER, "angle": angle["name"],
        "script": script_lines, "caption": caption,
        "scheduled": scheduled_date, "bg_image": bool(bg_result),
    }, indent=2))
    print("\n== Done ==")


if __name__ == "__main__":
    main()
