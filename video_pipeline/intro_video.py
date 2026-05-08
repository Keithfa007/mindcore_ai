#!/usr/bin/env python3
"""
MindCore AI -- Introduction Video (ONE-TIME / MANUAL RUN)
=========================================================
Fixed avatar, fixed script, triggered manually via GitHub Actions.
No name is used anywhere. Founder remains anonymous.

Avatar:  c25c06ac64c3480bba0f700c1864b7cb
Voice:   6be73833ef9a4eb0aeee399b8fe9d62b
API:     HeyGen v3 /v3/videos  (same as main pipeline)
Output:  video_pipeline/output/mindcore_intro.mp4

Script format: INTERVIEW RESPONSE
  Written as if the founder was just asked "Why did you build MindCore AI?"
  Conversational, mid-answer tone. No prepared speech feel.
  No name. No free trial.

Subtitles: Whisper (tiny, CPU) -> ASS word-by-word captions burned in.
Crop:      cropdetect limit=200 to strip white letterbox padding.
"""

import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

HEYGEN_API_KEY = os.environ["HEYGEN_API_KEY"]

HEYGEN_V3_URL     = "https://api.heygen.com/v3/videos"
HEYGEN_STATUS_URL = "https://api.heygen.com/v1/video_status.get"

OUTPUT_DIR    = Path("video_pipeline/output")
POLL_INTERVAL = 15
VIDEO_TIMEOUT = 1800   # 30 minutes

AVATAR_ID        = "c25c06ac64c3480bba0f700c1864b7cb"
VOICE_ID         = "6be73833ef9a4eb0aeee399b8fe9d62b"
BACKGROUND_COLOR = "#07071a"

# ---------------------------------------------------------------------------
# Subtitle config -- calibrated for 1080x1920
# ---------------------------------------------------------------------------
WHISPER_MODEL      = "tiny"
SUBTITLE_FONT      = "Arial"
SUBTITLE_FONT_SIZE = 75
SUBTITLE_MARGIN_V  = 500
SUBTITLE_CHUNK     = 3

# ---------------------------------------------------------------------------
# Introduction script -- interview format, no name, no free trial
#
# Written as a direct answer to: "Why did you build MindCore AI?"
# Sounds like someone caught mid-conversation, not delivering a speech.
#
# ~135 words / ~62 seconds
# ---------------------------------------------------------------------------

INTRO_SCRIPT = (
    "Yeah, honestly -- because I needed it and nothing like it existed.  "

    "For a long time I was completely alone with my own head. "
    "No judgment-free space. Nobody to talk to without it turning into advice, "
    "or worry, or 'you should see someone.' "
    "And I know I'm not alone in that. "
    "Millions of men go through the same thing every single day -- "
    "quietly, pretending everything's fine.  "

    "So I built something. "
    "A private AI companion, built specifically for men. "
    "Available any time, day or night, for whatever you're carrying. "
    "Anxiety. Stress. Recovery. "
    "The stuff you can't say out loud to anyone.  "

    "It's not therapy. It's not a hotline. "
    "It's just an honest conversation, whenever you need one. "
    "It's called MindCore AI. It's on Google Play. "
    "You don't have to keep carrying this alone."
)

# Motion prompt: interview-style -- as if responding to an off-camera question
MOTION_PROMPT = (
    "Relaxed, natural posture as if in a podcast interview. "
    "Warm, direct eye contact with camera -- like answering someone you trust. "
    "Genuine hand gestures when making a point. "
    "Slight pause and nod before the emotional moments. "
    "Unhurried. Real. Not rehearsed."
)


# ---------------------------------------------------------------------------
# HeyGen v3
# ---------------------------------------------------------------------------

def submit_video() -> str:
    headers = {"X-Api-Key": HEYGEN_API_KEY, "Content-Type": "application/json"}
    payload = {
        "type":                "avatar",
        "avatar_id":           AVATAR_ID,
        "voice_id":            VOICE_ID,
        "script":              INTRO_SCRIPT,
        "motion_prompt":       MOTION_PROMPT,
        "expressiveness":      "high",
        "dimension":           {"width": 1080, "height": 1920},
        "aspect_ratio":        "9:16",
        "use_avatar_iv_model": True,
        "super_resolution":    True,
        "talking_style":       "expressive",
    }

    print(f"  HeyGen: POST /v3/videos | avatar={AVATAR_ID[:8]}...")
    resp = requests.post(HEYGEN_V3_URL, headers=headers, json=payload, timeout=30)
    print(f"  Response [{resp.status_code}]: {resp.text[:200]}")
    if not resp.ok:
        raise RuntimeError(f"HeyGen submit failed {resp.status_code}: {resp.text}")

    data     = resp.json()
    video_id = (data.get("data", {}).get("video_id") or data.get("video_id")
                or data.get("data", {}).get("id")     or data.get("id"))
    if not video_id:
        raise RuntimeError(f"No video_id in response: {data}")

    print(f"  Submitted -- video_id: {video_id}")
    return video_id


def poll_video(video_id: str) -> str:
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
            print("  Render complete!")
            return url

        if status in ("failed", "error"):
            raise RuntimeError(f"HeyGen render failed: {data}")

        elapsed = int(time.time() - (deadline - VIDEO_TIMEOUT))
        print(f"    waiting... status={status} ({elapsed}s elapsed)")
        time.sleep(POLL_INTERVAL)

    raise TimeoutError(f"Timed out after {VIDEO_TIMEOUT}s")


def download_video(url: str, path: str):
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65_536):
            if chunk:
                f.write(chunk)
    size_mb = Path(path).stat().st_size / (1024 * 1024)
    print(f"  Downloaded: {path} ({size_mb:.1f} MB)")


# ---------------------------------------------------------------------------
# Subtitles -- Whisper + ASS
# ---------------------------------------------------------------------------

def transcribe_audio_whisper(video_path: str) -> list:
    try:
        import whisper
        print(f"  Whisper: loading '{WHISPER_MODEL}' model (CPU)...")
        model  = whisper.load_model(WHISPER_MODEL)
        result = model.transcribe(str(video_path), word_timestamps=True,
                                  language="en", fp16=False)
        words = []
        for seg in result.get("segments", []):
            for w in seg.get("words", []):
                word = w.get("word", "").strip()
                if word:
                    words.append({
                        "word":  word,
                        "start": float(w.get("start", 0)),
                        "end":   float(w.get("end",   0)),
                    })
        print(f"  Whisper: {len(words)} words transcribed")
        return words
    except Exception as e:
        print(f"  Whisper failed ({e}) -- continuing without subtitles")
        return []


def generate_ass_subtitles(words: list, output_path: str) -> bool:
    if not words:
        return False

    def ts(secs: float) -> str:
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        s = secs % 60
        return f"{h}:{m:02d}:{s:05.2f}"

    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "ScaledBorderAndShadow: yes\nWrapStyle: 1\n\n"
        "[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{SUBTITLE_FONT},{SUBTITLE_FONT_SIZE},"
        "&H00FFFFFF,&H000000FF,&H00000000,&H00000000,"
        f"-1,0,0,0,100,100,1,0,1,4,0,2,60,60,{SUBTITLE_MARGIN_V},1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, "
        "MarginL, MarginR, MarginV, Effect, Text\n"
    )

    chunks = []
    i = 0
    while i < len(words):
        chunk = words[i : i + SUBTITLE_CHUNK]
        text  = " ".join(w["word"].upper() for w in chunk)
        start = chunk[0]["start"]
        end   = chunk[-1]["end"]
        if chunks and start < chunks[-1]["end"]:
            start = chunks[-1]["end"]
        chunks.append({"text": text, "start": start, "end": end})
        i += SUBTITLE_CHUNK

    events = "".join(
        f"Dialogue: 0,{ts(c['start'])},{ts(c['end'])},Default,,0,0,0,,{c['text']}\n"
        for c in chunks
    )

    Path(output_path).write_text(header + events, encoding="utf-8")
    print(f"  Subtitles: {len(chunks)} groups | {SUBTITLE_FONT} {SUBTITLE_FONT_SIZE}px | MarginV {SUBTITLE_MARGIN_V}px")
    return True


# ---------------------------------------------------------------------------
# FFmpeg -- crop + subtitle burn
# ---------------------------------------------------------------------------

def get_dimensions(path: str) -> tuple:
    cmd    = ["ffprobe", "-v", "error", "-select_streams", "v:0",
              "-show_entries", "stream=width,height", "-of", "csv=p=0", path]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    w, h   = result.stdout.strip().split(",")
    return int(w), int(h)


def detect_crop(path: str) -> tuple:
    """
    limit=200 catches white/near-white letterbox padding from HeyGen.
    Looks that fill the frame natively are unaffected.
    """
    cmd     = ["ffmpeg", "-i", path, "-vf",
               "cropdetect=limit=200:round=2:reset=0",
               "-frames:v", "90", "-f", "null", "-"]
    result  = subprocess.run(cmd, capture_output=True, text=True)
    matches = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", result.stderr)
    if not matches:
        return None
    cw, ch, cx, cy = map(int, matches[-1])
    print(f"  cropdetect: {cw}x{ch} at x={cx}, y={cy}")
    return cw, ch, cx, cy


def make_portrait_filter(cw, ch, cx, cy) -> str:
    return (
        f"crop={cw}:{ch}:{cx}:{cy},"
        f"scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop=1080:1920:(iw-1080)/2:(ih-1920)/2,"
        f"fps=30"
    )


def to_portrait(raw: str, final: str, ass_path: str = None):
    w, h = get_dimensions(raw)
    print(f"  Raw dimensions: {w}x{h}")
    crop       = detect_crop(raw)
    filter_str = make_portrait_filter(*crop) if crop else make_portrait_filter(w, h, 0, 0)

    if ass_path and Path(ass_path).exists():
        safe_ass    = str(Path(ass_path).resolve()).replace("\\", "/")
        filter_str += f",ass='{safe_ass}'"
        print(f"  Burning subtitles: {Path(ass_path).name}")
    else:
        print("  No subtitle file -- rendering without captions")

    cmd    = ["ffmpeg", "-i", raw, "-vf", filter_str,
              "-c:v", "libx264", "-crf", "16", "-preset", "slow",
              "-b:v", "4M", "-maxrate", "6M", "-bufsize", "8M",
              "-c:a", "copy", "-y", final]
    result = subprocess.run(cmd, capture_output=True, text=True)

    if result.returncode != 0:
        if ass_path and Path(ass_path).exists():
            print("  WARNING: subtitle burn failed -- retrying without captions")
            to_portrait(raw, final, ass_path=None)
            return
        raise RuntimeError(f"ffmpeg failed:\n{result.stderr[-500:]}")

    w2, h2 = get_dimensions(final)
    size   = Path(final).stat().st_size / (1024 * 1024)
    sub    = " + captions" if (ass_path and Path(ass_path).exists()) else ""
    print(f"  Final: {final} ({w2}x{h2} | {size:.1f} MB{sub})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    raw      = str(OUTPUT_DIR / "mindcore_intro_raw.mp4")
    final    = str(OUTPUT_DIR / "mindcore_intro.mp4")
    ass_path = str(OUTPUT_DIR / "intro_subtitles.ass")

    word_count = len(INTRO_SCRIPT.split())
    est_secs   = round(word_count / 130 * 60)

    print("\n  MindCore AI -- Introduction Video")
    print(f"  Avatar:    {AVATAR_ID[:8]}...")
    print(f"  Voice:     {VOICE_ID[:8]}...")
    print(f"  Script:    {word_count} words (~{est_secs}s) -- INTERVIEW FORMAT")
    print(f"  Subtitles: Whisper '{WHISPER_MODEL}' -> {SUBTITLE_FONT_SIZE}px {SUBTITLE_FONT} bold")
    print(f"  Crop:      cropdetect limit=200 (strips white letterbox)")
    print(f"  Format:    1080x1920 9:16 portrait")
    print("=" * 50)

    print("\n  [Script preview]")
    print(f"  {INTRO_SCRIPT[:120]}...")

    print("\n  Submitting to HeyGen v3...")
    video_id = submit_video()

    print(f"\n  Rendering (up to {VIDEO_TIMEOUT // 60} min)...")
    video_url = poll_video(video_id)

    print("\n  Downloading...")
    download_video(video_url, raw)

    print("\n  Transcribing with Whisper...")
    words = transcribe_audio_whisper(raw)
    if not generate_ass_subtitles(words, ass_path):
        ass_path = None

    print("\n  Cropping to portrait + burning captions...")
    to_portrait(raw, final, ass_path=ass_path)

    print(f"\n  DONE -- download from Artifacts: mindcore_intro.mp4")
    print(f"  File: {final}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n  FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
