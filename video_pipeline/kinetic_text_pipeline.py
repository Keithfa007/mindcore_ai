#!/usr/bin/env python3
"""
MindCore AI — Kinetic Text Video Pipeline v1.0
===============================================
Combines kinetic typography + voiceover subtitles.
No stock video needed — pure text + voice on dark background.

Flow:
1. Claude generates short raw script (15-25 seconds)
2. ElevenLabs generates voiceover
3. Whisper transcribes for word-level timestamps
4. FFmpeg renders kinetic text video synced to audio
5. Upload-Post publishes to TikTok + Facebook + YouTube
"""

import os, sys, json, random, subprocess, tempfile, datetime, time, math
from pathlib import Path
from anthropic import Anthropic
import requests

ANTHROPIC_API_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
ELEVENLABS_API_KEY  = os.environ.get("ELEVENLABS_API_KEY", "")
UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
UPLOAD_POST_USER    = os.environ.get("UPLOAD_POST_USER", "MindCoreAI")
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
    },
    {
        "name": "recovery_truth",
        "instruction": "A hard truth about recovery that nobody tells you. Written from 2 years of experience. 4-5 sentences. Each one should make someone in early recovery nod and think 'yeah, that's exactly it.'",
    },
    {
        "name": "the_mask",
        "instruction": "About hiding behind a performance of being okay. The exhaustion of pretending. Written for anyone who smiles at work and falls apart at home. 4-5 sentences. Raw and specific.",
    },
    {
        "name": "what_healing_looks_like",
        "instruction": "What recovery and healing actually look like versus what people think it looks like. Not pretty. Not linear. Boring, uncomfortable, and real. 4-5 sentences.",
    },
    {
        "name": "letter_to_the_hiding",
        "instruction": "Written directly to someone who is still hiding their struggle. Not preachy. Not 'you should get help.' More like 'I see you because I was you.' 4-5 sentences.",
    },
    {
        "name": "the_first_honest_moment",
        "instruction": "About the moment of telling one person the truth for the first time. The terror, the relief, the aftermath. 4-5 sentences. Specific and visceral.",
    },
    {
        "name": "functioning_addict",
        "instruction": "About being the person nobody suspects. Showing up, performing, succeeding at work while self-destructing in private. 4-5 sentences. Written from lived experience.",
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


def generate_voiceover(script_text, output_path):
    if not ELEVENLABS_API_KEY:
        print("  ELEVENLABS_API_KEY not set")
        return False
    url = f"{ELEVENLABS_API_URL}/{ELEVENLABS_VOICE_ID}"
    headers = {"xi-api-key": ELEVENLABS_API_KEY, "Content-Type": "application/json"}
    payload = {
        "text": script_text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {"stability": 0.55, "similarity_boost": 0.70},
    }
    try:
        resp = requests.post(url, headers=headers, json=payload, stream=True, timeout=120)
        if not resp.ok:
            print(f"  ElevenLabs error {resp.status_code}")
            return False
        with open(output_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk:
                    f.write(chunk)
        size_kb = os.path.getsize(output_path) / 1024
        print(f"  Voiceover generated ({size_kb:.0f} KB)")
        return True
    except Exception as e:
        print(f"  ElevenLabs failed: {e}")
        return False


def get_word_timestamps(audio_path):
    """Use Whisper to get word-level timestamps."""
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
    """Map script lines to start times using word timestamps."""
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


def escape_ffmpeg_text(text):
    """Escape special characters for FFmpeg drawtext."""
    return text.replace("\\", "\\\\").replace("'", "\u2019").replace(":", "\\:").replace("%", "%%").replace('"', '\\"')


def create_kinetic_video(audio_path, line_timestamps, output_path, audio_duration):
    """Create video with kinetic text synced to audio."""
    bg_filter = f"color=c=0x0c1020:s={WIDTH}x{HEIGHT}:d={audio_duration + 1}"

    drawtext_filters = []
    font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_path_light = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    total_lines = len(line_timestamps)
    line_height = 70
    total_text_height = total_lines * line_height
    start_y = (HEIGHT // 2) - (total_text_height // 2)

    for i, lt in enumerate(line_timestamps):
        text = escape_ffmpeg_text(lt["text"])
        y_pos = start_y + (i * line_height)
        appear_time = lt["start"]
        fade_duration = 0.3

        alpha_expr = f"if(lt(t\\,{appear_time:.2f})\\,0\\,if(lt(t\\,{appear_time + fade_duration:.2f})\\,({1}/{fade_duration:.2f})*(t-{appear_time:.2f})\\,1))"

        if i < total_lines - 1:
            next_appear = line_timestamps[i + 1]["start"]
            color_expr = f"if(lt(t\\,{next_appear:.2f})\\,0xFFFFFF\\,0x888888)"
        else:
            color_expr = "0xFFFFFF"

        drawtext_filters.append(
            f"drawtext=fontfile={font_path}:text='{text}'"
            f":fontsize=42:fontcolor_expr='{color_expr}'"
            f":x=(w-text_w)/2:y={y_pos}"
            f":alpha='{alpha_expr}'"
            f":shadowcolor=black:shadowx=2:shadowy=2"
        )

    drawtext_filters.append(
        f"drawtext=fontfile={font_path_light}:text='MindCore AI'"
        f":fontsize=28:fontcolor=0x8888aa:x=(w-text_w)/2:y={HEIGHT - 100}"
        f":alpha=0.6"
    )

    filter_chain = ",".join(drawtext_filters)

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", bg_filter,
        "-i", audio_path,
        "-vf", filter_chain,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-c:a", "aac", "-b:a", "128k",
        "-pix_fmt", "yuv420p",
        "-shortest",
        output_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  FFmpeg error: {result.stderr[-500:]}")
        raise RuntimeError("FFmpeg failed")

    size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"  Video created ({size_mb:.1f} MB, {audio_duration:.1f}s)")


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


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"== MindCore AI - Kinetic Text Pipeline v1.0 ==")
    print(f"  Run #{GITHUB_RUN_NUMBER} | Post: {POST_HOUR_UTC}:00 UTC")

    if not ANTHROPIC_API_KEY:
        sys.exit("ERROR: ANTHROPIC_API_KEY not set")

    client = Anthropic(api_key=ANTHROPIC_API_KEY)
    scheduled_date = get_scheduled_time(POST_HOUR_UTC)

    with tempfile.TemporaryDirectory() as tmp:
        audio_path = os.path.join(tmp, "voiceover.mp3")
        video_path = os.path.join(tmp, "kinetic.mp4")

        print("\n1. Picking angle...")
        angle = get_angle_for_run()

        print("\n2. Generating script...")
        script_lines = generate_script(client, angle)
        script_text = " ".join(script_lines)

        print("\n3. Generating caption...")
        caption = generate_caption(client, script_lines, angle)
        print(f"  Caption: {caption}")

        print("\n4. Generating voiceover...")
        has_voice = generate_voiceover(script_text, audio_path)
        if not has_voice:
            sys.exit("ERROR: Voiceover generation failed")

        print("\n5. Getting word timestamps (Whisper)...")
        word_timestamps = get_word_timestamps(audio_path)
        audio_duration = get_audio_duration(audio_path)
        print(f"  Audio duration: {audio_duration:.1f}s")

        print("\n6. Building line timestamps...")
        line_timestamps = build_line_timestamps(script_lines, word_timestamps, audio_duration)
        for lt in line_timestamps:
            print(f"  [{lt['start']:.1f}s] {lt['text']}")

        print("\n7. Creating kinetic text video...")
        create_kinetic_video(audio_path, line_timestamps, video_path, audio_duration)

        import shutil
        output_copy = OUTPUT_DIR / f"kinetic_{GITHUB_RUN_NUMBER}.mp4"
        shutil.copy2(video_path, output_copy)

        print("\n8. Uploading...")
        result = upload_video(video_path, caption, scheduled_date=scheduled_date)
        if result.get("status_code") in (200, 202):
            print(f"  Scheduled: {scheduled_date}")

    (OUTPUT_DIR / "kinetic_metadata.json").write_text(json.dumps({
        "run": GITHUB_RUN_NUMBER, "angle": angle["name"],
        "script": script_lines, "caption": caption,
        "scheduled": scheduled_date, "platform": "tiktok+facebook+youtube",
    }, indent=2))

    print("\n== Done ==")


if __name__ == "__main__":
    main()
