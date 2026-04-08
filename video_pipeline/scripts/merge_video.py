"""
merge_video.py
MindCore AI Video Pipeline — Step 4
Uses FFmpeg to merge voiceover.mp3 + background_video.mp4
into a final finished video at outputs/final_video.mp4
"""

import os
import json
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent
OUTPUT_DIR  = BASE_DIR / "outputs"
SCRIPT_FILE = OUTPUT_DIR / "script_output.json"
AUDIO_FILE  = OUTPUT_DIR / "voiceover.mp3"
VIDEO_FILE  = OUTPUT_DIR / "background_video.mp4"

timestamp  = datetime.utcnow().strftime("%Y%m%d_%H%M")
FINAL_FILE = OUTPUT_DIR / f"mindcore_video_{timestamp}.mp4"

# ── Find FFmpeg binary ─────────────────────────────────────────────────────
ffmpeg_bin = shutil.which("ffmpeg")
if not ffmpeg_bin:
    # Common fallback paths
    for candidate in ["/usr/bin/ffmpeg", "/usr/local/bin/ffmpeg", "/opt/homebrew/bin/ffmpeg"]:
        if Path(candidate).exists():
            ffmpeg_bin = candidate
            break

if not ffmpeg_bin:
    raise FileNotFoundError(
        "FFmpeg not found. Install it with: sudo apt-get install -y ffmpeg"
    )

print(f"[merge_video] FFmpeg: {ffmpeg_bin}")

# ── Load metadata ──────────────────────────────────────────────────────────
with open(SCRIPT_FILE, "r") as f:
    script_data = json.load(f)

print(f"[merge_video] Title:  {script_data.get('title')}")
print(f"[merge_video] Audio:  {AUDIO_FILE}")
print(f"[merge_video] Video:  {VIDEO_FILE}")
print(f"[merge_video] Output: {FINAL_FILE}")

# ── Verify input files exist ───────────────────────────────────────────────
for f in [AUDIO_FILE, VIDEO_FILE]:
    if not f.exists():
        raise FileNotFoundError(f"Input file missing: {f}")
    print(f"[merge_video] ✅ Found: {f} ({f.stat().st_size / 1024:.0f} KB)")

# ── FFmpeg merge ───────────────────────────────────────────────────────────
# - Loops background video if shorter than audio
# - Trims to audio length
# - Scales to 1080x1920 (9:16 vertical)
# - Adds fade in/out
ffmpeg_cmd = [
    ffmpeg_bin, "-y",
    "-stream_loop", "-1",
    "-i", str(VIDEO_FILE),
    "-i", str(AUDIO_FILE),
    "-vf", (
        "scale=1080:1920:force_original_aspect_ratio=increase,"
        "crop=1080:1920,"
        "fade=t=in:st=0:d=0.5,"
        "fade=t=out:st=4.5:d=0.5"
    ),
    "-c:v", "libx264",
    "-preset", "fast",
    "-crf", "23",
    "-c:a", "aac",
    "-b:a", "128k",
    "-shortest",
    "-movflags", "+faststart",
    str(FINAL_FILE),
]

print("[merge_video] Running FFmpeg...")
result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

if result.returncode != 0:
    print(f"[merge_video] ❌ FFmpeg stderr:\n{result.stderr[-2000:]}")
    raise Exception("FFmpeg merge failed")

size_mb = FINAL_FILE.stat().st_size / (1024 * 1024)
print(f"[merge_video] ✅ Final video saved: {FINAL_FILE} ({size_mb:.1f} MB)")

# ── Save caption alongside video ───────────────────────────────────────────
caption_file = OUTPUT_DIR / f"mindcore_caption_{timestamp}.txt"
with open(caption_file, "w") as f:
    f.write(f"TITLE:\n{script_data.get('title', '')}\n\n")
    f.write(f"HOOK:\n{script_data.get('hook', '')}\n\n")
    f.write(f"CAPTION:\n{script_data.get('caption', '')}\n\n")
    f.write(f"SEO TAGS:\n{', '.join(script_data.get('seo_tags', []))}\n\n")
    f.write(f"PRIMARY KEYWORD:\n{script_data.get('primary_keyword', '')}\n")

print(f"[merge_video] ✅ Caption saved: {caption_file}")
print(f"\n{'='*50}")
print(f"VIDEO READY TO POST")
print(f"File:    {FINAL_FILE.name}")
print(f"Caption: {script_data.get('caption', '')}")
print(f"{'='*50}")

# Write path for potential upload step
with open(OUTPUT_DIR / "final_video_path.txt", "w") as f:
    f.write(str(FINAL_FILE))
