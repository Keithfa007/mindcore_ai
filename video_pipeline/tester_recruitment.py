#!/usr/bin/env python3
"""
MindCore AI -- Google Play Tester Recruitment Video
====================================================
Standalone one-time script.

FLOW:
  1. Submit hardcoded script to HeyGen (avatar d28c74da0f674f309ecce684f42d4387)
  2. Poll until complete
  3. Download raw avatar video
  4. Crop to 9:16 portrait (cropdetect)
  5. Overlay app screen recording during 0:28-0:45 (app showcase section)
  6. Output: tester_recruitment.mp4

APP OVERLAY:
  Place your app screen recording at:
  video_pipeline/assets/app_demo.mp4
  before running this workflow.

SKIP_HEYGEN=1 env var: skip HeyGen render and reuse existing portrait file.
"""

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

import requests

# -- Config -------------------------------------------------------------------

HEYGEN_API_KEY    = os.environ.get("HEYGEN_API_KEY", "")
HEYGEN_SUBMIT_URL = "https://api.heygen.com/v2/video/generate"
HEYGEN_STATUS_URL = "https://api.heygen.com/v1/video_status.get"

OUTPUT_DIR   = Path("video_pipeline/output")
ASSETS_DIR   = Path("video_pipeline/assets")
APP_DEMO     = str(ASSETS_DIR / "app_demo.mp4")

POLL_INTERVAL = 15
VIDEO_TIMEOUT = 1800  # 30 minutes

AVATAR_ID        = "d28c74da0f674f309ecce684f42d4387"
VOICE_ID         = "6be73833ef9a4eb0aeee399b8fe9d62b"
BACKGROUND_COLOR = "#07071a"

# App showcase overlay window (seconds)
OVERLAY_START = 28
OVERLAY_END   = 45

# Full script -- avatar speaks the entire video
SCRIPT = (
    "I built a mental health app completely alone -- "
    "no team, no money, no investors. "
    "And I almost didn't make it to this point. "

    "Two years ago I was at my lowest. "
    "Anxiety, depression, dependency -- I had lost myself completely. "
    "I made a decision to climb back. Not one drop since. "
    "I built MindCore AI because when I was at my worst, "
    "I needed someone to talk to at 2am without shame or judgment. "
    "So I built it myself. "

    "The app has AI chat that genuinely listens -- not robotic, actually warm. "
    "Breathing tools that keep your screen on so you can just close your eyes. "
    "A one-tap SOS button with voice guidance for when things get really tough. "
    "And mood tracking that actually builds a picture of how you're doing over time. "

    "Before I can go live on Google Play, I need 12 people with an Android phone "
    "to test it for 14 days. You don't need to do anything -- "
    "just click a link and install it. That's it. "
    "If you want to help me get this off the ground -- "
    "drop the word TEST in the comments or DM me. Thank you."
)


# -- HeyGen -------------------------------------------------------------------

def submit_video() -> str:
    print(f"  Avatar:  {AVATAR_ID}")
    print(f"  Script:  {len(SCRIPT.split())} words")

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
                    "input_text": SCRIPT,
                    "voice_id": VOICE_ID,
                    "speed": 0.9,  # slightly slower -- emotional delivery
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
                raise RuntimeError("Completed but no video_url")
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


# -- ffmpeg helpers -----------------------------------------------------------

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


def get_duration(path: str) -> float:
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0", path
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())


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
    print(f"  cropdetect: content {cw}x{ch} at x={cx}, y={cy}")
    return cw, ch, cx, cy


def run_ffmpeg(cmd: list):
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ffmpeg error:\n{result.stderr[-800:]}")
        raise RuntimeError("ffmpeg failed")


# -- Portrait crop ------------------------------------------------------------

def crop_to_portrait(raw: str, portrait: str):
    """Crop HeyGen output to clean 1080x1920 portrait."""
    w, h   = get_dimensions(raw)
    crop   = cropdetect(raw)
    cw, ch, cx, cy = crop if crop else (w, h, 0, 0)

    scale_h = 1920
    scale_w = round(cw * scale_h / ch)
    if scale_w % 2:
        scale_w += 1

    if scale_w >= 1080:
        x_off   = (scale_w - 1080) // 2
        vfilter = (
            f"crop={cw}:{ch}:{cx}:{cy},"
            f"scale={scale_w}:{scale_h}:flags=lanczos,"
            f"crop=1080:1920:{x_off}:0,"
            f"fps=30"
        )
    else:
        vfilter = (
            f"crop={cw}:{ch}:{cx}:{cy},"
            f"scale=1080:-2:flags=lanczos,"
            f"pad=1080:1920:0:(1920-ih)/2:color=0x07071a,"
            f"fps=30"
        )

    print(f"  Cropping to portrait...")
    run_ffmpeg([
        "ffmpeg", "-i", raw,
        "-vf", vfilter,
        "-c:v", "libx264", "-crf", "16", "-preset", "slow",
        "-b:v", "4M", "-maxrate", "6M", "-bufsize", "8M",
        "-c:a", "copy", "-y", portrait
    ])
    w2, h2 = get_dimensions(portrait)
    size   = Path(portrait).stat().st_size / (1024 * 1024)
    print(f"  Portrait ready: {portrait} ({w2}x{h2} | {size:.1f} MB)")


# -- App overlay --------------------------------------------------------------

def scale_app_to_portrait(app_w: int, app_h: int) -> str:
    """
    Build ffmpeg scale+crop filter to fit any app recording into 1080x1920.

    Strategy: always scale so the SMALLER dimension fills the output,
    then crop the excess from the center. No padding, no bars.

    Cases:
      Wide app (w > h):  scale height to 1920 → width > 1080 → crop sides
      Tall app (h > w):  scale width to 1080  → height > 1920 → crop top/bottom
      Square:            scale height to 1920 → crop sides
    """
    # Target output
    out_w, out_h = 1080, 1920
    target_ratio = out_w / out_h        # 0.5625
    source_ratio = app_w / app_h

    if source_ratio >= target_ratio:
        # App is wider than 9:16 -- scale to height, crop width
        scale_h = out_h
        scale_w = round(app_w * scale_h / app_h)
        if scale_w % 2:
            scale_w += 1
        x_off = (scale_w - out_w) // 2
        return f"scale={scale_w}:{scale_h}:flags=lanczos,crop={out_w}:{out_h}:{x_off}:0"
    else:
        # App is taller than 9:16 (e.g. 1080x2340) -- scale to width, crop height
        scale_w = out_w
        scale_h = round(app_h * scale_w / app_w)
        if scale_h % 2:
            scale_h += 1
        y_off = (scale_h - out_h) // 2
        return f"scale={scale_w}:{scale_h}:flags=lanczos,crop={out_w}:{out_h}:0:{y_off}"


def overlay_app_demo(portrait: str, app_demo: str, final: str):
    """
    Overlay the app screen recording during the app showcase section.
    App fills the full frame (full takeover) during OVERLAY_START to OVERLAY_END.
    Avatar audio plays throughout.
    """
    app_w, app_h = get_dimensions(app_demo)
    app_dur      = get_duration(app_demo)
    print(f"  App demo: {app_w}x{app_h} | {app_dur:.1f}s")
    print(f"  Overlay window: {OVERLAY_START}s -- {OVERLAY_END}s")

    app_scale = scale_app_to_portrait(app_w, app_h)
    print(f"  App scale filter: {app_scale}")

    filter_complex = (
        f"[1:v]{app_scale}[app];"
        f"[0:v][app]overlay=0:0:"
        f"enable='between(t,{OVERLAY_START},{OVERLAY_END})'[out]"
    )

    print(f"  Applying app overlay...")
    run_ffmpeg([
        "ffmpeg",
        "-i", portrait,
        "-i", app_demo,
        "-filter_complex", filter_complex,
        "-map", "[out]",
        "-map", "0:a",
        "-c:v", "libx264", "-crf", "16", "-preset", "slow",
        "-b:v", "4M", "-maxrate", "6M", "-bufsize", "8M",
        "-c:a", "aac", "-b:a", "192k",
        "-y", final
    ])

    w2, h2 = get_dimensions(final)
    size   = Path(final).stat().st_size / (1024 * 1024)
    dur    = get_duration(final)
    print(f"  Final video: {final} ({w2}x{h2} | {size:.1f} MB | {dur:.1f}s)")


# -- Main ---------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)

    raw      = str(OUTPUT_DIR / "tester_raw.mp4")
    portrait = str(OUTPUT_DIR / "tester_portrait.mp4")
    final    = str(OUTPUT_DIR / "tester_recruitment.mp4")

    skip_heygen = os.environ.get("SKIP_HEYGEN", "").lower() in ("1", "true", "yes")

    print("\n  MindCore AI -- Tester Recruitment Video")
    print(f"  Avatar:   {AVATAR_ID}")
    print(f"  Overlay:  {OVERLAY_START}s -- {OVERLAY_END}s (app showcase)")
    print(f"  App demo: {APP_DEMO}")
    if skip_heygen:
        print(f"  SKIP_HEYGEN=1 -- reusing existing portrait file")
    print("=" * 52)

    app_demo_exists = Path(APP_DEMO).exists()
    if not app_demo_exists:
        print(f"  WARNING: {APP_DEMO} not found -- will skip overlay")

    if not skip_heygen:
        print("\n  Submitting to HeyGen...")
        video_id  = submit_video()

        print(f"\n  Rendering (up to {VIDEO_TIMEOUT // 60} min)...")
        video_url = poll_video(video_id)

        print("\n  Downloading raw video...")
        download_video(video_url, raw)

        print("\n  Cropping to 9:16 portrait...")
        crop_to_portrait(raw, portrait)
    else:
        if not Path(portrait).exists():
            raise RuntimeError(f"SKIP_HEYGEN set but portrait not found: {portrait}")
        print(f"\n  Reusing existing portrait: {portrait}")

    if app_demo_exists:
        print("\n  Overlaying app screen recording (0:28 -- 0:45)...")
        overlay_app_demo(portrait, APP_DEMO, final)
    else:
        print("\n  No app demo -- using portrait-only output")
        shutil.copy(portrait, final)
        print(f"  Output: {final}")

    dur = get_duration(final)
    print(f"\n  DONE -- download tester_recruitment.mp4 from Artifacts")
    print(f"  Duration: {dur:.1f}s | Format: 1080x1920 9:16 portrait")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"\n  FAILED: {e}", file=sys.stderr)
        raise SystemExit(1)
