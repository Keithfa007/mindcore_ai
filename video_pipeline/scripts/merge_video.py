"""
merge_video.py
MindCore AI Video Pipeline — Step 4
Uses FFmpeg to merge voiceover.mp3 + background_video.mp4
Loops background video to match full audio duration.
"""

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

# ── Find FFmpeg / FFprobe ──────────────────────────────────────────────────
def find_bin(name):
    b = shutil.which(name)
    if b:
        return b
    for p in [f"/usr/bin/{name}", f"/usr/local/bin/{name}"]:
        if Path(p).exists():
            return p
    raise FileNotFoundError(f"{name} not found. Run: sudo apt-get install -y ffmpeg")

ffmpeg_bin  = find_bin("ffmpeg")
ffprobe_bin = find_bin("ffprobe")
print(f"[merge_video] ffmpeg:  {ffmpeg_bin}")
print(f"[merge_video] ffprobe: {ffprobe_bin}")

# ── Load metadata ──────────────────────────────────────────────────────────
with open(SCRIPT_FILE, "r") as f:
    script_data = json.load(f)

print(f"[merge_video] Title: {script_data.get('title')}")

# ── Verify inputs ──────────────────────────────────────────────────────────
for f in [AUDIO_FILE, VIDEO_FILE]:
    if not f.exists():
        raise FileNotFoundError(f"Missing: {f}")
    print(f"[merge_video] ✅ {f.name} ({f.stat().st_size / 1024:.0f} KB)")

# ── Get exact audio duration via ffprobe ───────────────────────────────────
probe = subprocess.run(
    [
        ffprobe_bin, "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        str(AUDIO_FILE),
    ],
    capture_output=True, text=True, check=True
)
audio_duration = float(probe.stdout.strip())
fade_out_start = max(0.0, audio_duration - 0.5)
print(f"[merge_video] Audio duration: {audio_duration:.2f}s")
print(f"[merge_video] Fade out at:    {fade_out_start:.2f}s")

# ── FFmpeg merge ───────────────────────────────────────────────────────────
# -stream_loop -1  → loop the background video indefinitely
# -t audio_duration → stop exactly when the voiceover ends
# -map 0:v -map 1:a → explicit stream mapping
ffmpeg_cmd = [
    ffmpeg_bin, "-y",
    "-stream_loop", "-1",
    "-i", str(VIDEO_FILE),
    "-i", str(AUDIO_FILE),
    "-map", "0:v",
    "-map", "1:a",
    "-t", str(audio_duration),
    "-vf", (
        f"scale=1080:1920:force_original_aspect_ratio=increase,"
        f"crop=1080:1920,"
        f"fade=t=in:st=0:d=0.5,"
        f"fade=t=out:st={fade_out_start:.2f}:d=0.5"
    ),
    "-c:v", "libx264",
    "-preset", "fast",
    "-crf", "23",
    "-c:a", "aac",
    "-b:a", "128k",
    "-movflags", "+faststart",
    str(FINAL_FILE),
]

print("[merge_video] Running FFmpeg...")
result = subprocess.run(ffmpeg_cmd, capture_output=True, text=True)

if result.returncode != 0:
    print(f"[merge_video] ❌ FFmpeg error:\n{result.stderr[-2000:]}")
    raise Exception("FFmpeg merge failed")

size_mb = FINAL_FILE.stat().st_size / (1024 * 1024)
print(f"[merge_video] ✅ Video: {FINAL_FILE.name} ({size_mb:.1f} MB, {audio_duration:.1f}s)")

# ── Save caption file ──────────────────────────────────────────────────────
caption_file = OUTPUT_DIR / f"mindcore_caption_{timestamp}.txt"
with open(caption_file, "w") as f:
    f.write(f"TITLE:\n{script_data.get('title', '')}\n\n")
    f.write(f"HOOK:\n{script_data.get('hook', '')}\n\n")
    f.write(f"CAPTION:\n{script_data.get('caption', '')}\n\n")
    f.write(f"SEO TAGS:\n{', '.join(script_data.get('seo_tags', []))}\n\n")
    f.write(f"PRIMARY KEYWORD:\n{script_data.get('primary_keyword', '')}\n")

print(f"[merge_video] ✅ Caption: {caption_file.name}")
print(f"\n{'='*50}")
print(f"VIDEO READY TO POST")
print(f"File:    {FINAL_FILE.name}")
print(f"Caption: {script_data.get('caption', '')}")
print(f"{'='*50}")

with open(OUTPUT_DIR / "final_video_path.txt", "w") as f:
    f.write(str(FINAL_FILE))
