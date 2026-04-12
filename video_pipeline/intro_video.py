#!/usr/bin/env python3
"""
MindCore AI -- Introduction Video (ONE-TIME RUN)
================================================
Hardcoded avatar, hardcoded script, run once.
Avatar: d16b8465de694753967c8eb69591e0a4 (Avatar 3)
Output: video_pipeline/output/mindcore_intro.mp4
"""

import os
import re
import subprocess
import sys
import time
from pathlib import Path

import requests

# -- Config -------------------------------------------------------------------

HEYGEN_API_KEY    = os.environ["HEYGEN_API_KEY"]

HEYGEN_SUBMIT_URL = "https://api.heygen.com/v2/video/generate"
HEYGEN_STATUS_URL = "https://api.heygen.com/v1/video_status.get"

OUTPUT_DIR   = Path("video_pipeline/output")
POLL_INTERVAL = 15
VIDEO_TIMEOUT = 1800  # 30 minutes

AVATAR_ID        = "d16b8465de694753967c8eb69591e0a4"
VOICE_ID         = "6be73833ef9a4eb0aeee399b8fe9d62b"
BACKGROUND_COLOR = "#07071a"

# Full introduction script -- all scenes joined naturally
INTRO_SCRIPT = (
    "There was a time in my life when I was completely alone with my own head. "
    "And that is a dangerous place to be.  "

    "I spent years struggling -- and the hardest part wasn't the struggle itself. "
    "It was having nobody to talk to. No judgement-free space. No place to just... "
    "say what was actually going on inside. "
    "And I know I'm not the only one. Millions of men go through the same thing "
    "every single day -- quietly, alone, pretending everything is fine.  "

    "That's exactly why I built MindCore AI. "
    "It's an AI mental wellness companion -- available any time, day or night, "
    "for whatever you're going through. Whether that's anxiety, stress, recovery, "
    "or just needing someone to talk to without being judged. "
    "It's not therapy. It's not a hotline. It's a real conversation, whenever you need one.  "

    "If any part of what I just said speaks to you -- MindCore AI is on Google Play. "
    "Start your trial today. "
    "You don't have to keep doing this alone."
)


# -- HeyGen -------------------------------------------------------------------

def submit_video() -> str:
    headers = {
        "X-Api-Key": HEYGEN_API_KEY,
        "Content-Type": "application/json",
    }
    payload = {
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": AVATAR_ID,
                },
                "voice": {
                    "type": "text",
                    "input_text": INTRO_SCRIPT,
                    "voice_id": VOICE_ID,
                },
                "background": {
                    "type": "color",
                    "value": BACKGROUND_COLOR,
                },
            }
        ],
        "dimension":    {"width": 1080, "height": 1920},
        "aspect_ratio": "9:16",
        "test": False,
    }

    resp = requests.post(HEYGEN_SUBMIT_URL, headers=headers, json=payload, timeout=30)
    if not resp.ok:
        raise RuntimeError(f"HeyGen submit failed {resp.status_code}: {resp.text}")

    data     = resp.json()
    video_id = data.get("data", {}).get("video_id") or data.get("video_id")
    if not video_id:
        raise RuntimeError(f"No video_id in response: {data}")

    print(f"  Submitted -- video_id: {video_id}")
    return video_id


def poll_video(video_id: str) -> str:
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
            print(f"  Render complete!")
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


# -- ffmpeg crop --------------------------------------------------------------

def get_dimensions(path: str) -> tuple:
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "csv=p=0", path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    w, h = result.stdout.strip().split(",")
    return int(w), int(h)


def cropdetect(path: str) -> tuple:
    cmd = [
        "ffmpeg", "-i", path,
        "-vf", "cropdetect=limit=30:round=2:reset=0",
        "-frames:v", "90", "-f", "null", "-"
    ]
    result  = subprocess.run(cmd, capture_output=True, text=True)
    matches = re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)", result.stderr)
    if not matches:
        return None
    cw, ch, cx, cy = map(int, matches[-1])
    print(f"  cropdetect: {cw}x{ch} at x={cx}, y={cy}")
    return cw, ch, cx, cy


def make_filter(cw, ch, cx, cy) -> str:
    scale_h = 1920
    scale_w = round(cw * scale_h / ch)
    if scale_w % 2:
        scale_w += 1
    if scale_w >= 1080:
        x_off = (scale_w - 1080) // 2
        return f"crop={cw}:{ch}:{cx}:{cy},scale={scale_w}:{scale_h}:flags=lanczos,crop=1080:1920:{x_off}:0,fps=30"
    else:
        return f"crop={cw}:{ch}:{cx}:{cy},scale=1080:-2:flags=lanczos,pad=1080:1920:0:(1920-ih)/2:color=0x07071a,fps=30"


def to_portrait(raw: str, final: str):
    w, h = get_dimensions(raw)
    print(f"  Raw dimensions: {w}x{h}")
    crop = cropdetect(raw)
    filt = make_filter(*crop) if crop else make_filter(w, h, 0, 0)
    cmd  = [
        "ffmpeg", "-i", raw, "-vf", filt,
        "-c:v", "libx264", "-crf", "16", "-preset", "slow",
        "-b:v", "4M", "-maxrate", "6M", "-bufsize", "8M",
        "-c:a", "copy", "-y", final
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ffmpeg error:\n{result.stderr[-500:]}")
        raise RuntimeError("ffmpeg failed")
    w2, h2 = get_dimensions(final)
    size   = Path(final).stat().st_size / (1024 * 1024)
    print(f"  Final: {final} ({w2}x{h2} | {size:.1f} MB)")


# -- Main ---------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    raw   = str(OUTPUT_DIR / "mindcore_intro_raw.mp4")
    final = str(OUTPUT_DIR / "mindcore_intro.mp4")

    print("\n  MindCore AI -- Introduction Video")
    print(f"  Avatar:     {AVATAR_ID}")
    print(f"  Script:     {len(INTRO_SCRIPT.split())} words")
    print(f"  Format:     1080x1920 9:16 portrait")
    print("=" * 50)

    print("\n  Submitting to HeyGen...")
    video_id = submit_video()

    print(f"\n  Rendering (up to {VIDEO_TIMEOUT//60} min)...")
    video_url = poll_video(video_id)

    print("\n  Downloading...")
    download_video(video_url, raw)

    print("\n  Converting to portrait...")
    to_portrait(raw, final)

    print(f"\n  DONE -- download from Artifacts: mindcore_intro.mp4")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n  FAILED: {e}", file=sys.stderr)
        raise SystemExit(1)
