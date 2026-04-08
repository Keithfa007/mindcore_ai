"""
generate_video.py
MindCore AI Video Pipeline — Step 3
Reads video_prompt from outputs/script_output.json
Calls WaveSpeed AI API (v3) to generate background video
Saves to outputs/background_video.mp4
"""

import os
import json
import time
import requests
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent
OUTPUT_DIR  = BASE_DIR / "outputs"
SCRIPT_FILE = OUTPUT_DIR / "script_output.json"
VIDEO_FILE  = OUTPUT_DIR / "background_video.mp4"

# ── Load video prompt ──────────────────────────────────────────────────────
with open(SCRIPT_FILE, "r") as f:
    script_data = json.load(f)

video_prompt = script_data["video_prompt"]
print(f"[generate_video] Prompt: {video_prompt[:120]}...")

# ── WaveSpeed AI API ───────────────────────────────────────────────────────
WAVESPEED_API_KEY = os.environ["WAVESPEED_API_KEY"]

headers = {
    "Authorization": f"Bearer {WAVESPEED_API_KEY}",
    "Content-Type": "application/json",
}

# Correct model ID — Alibaba WAN 2.1 Text-to-Video 720p
# Budget: ~$0.01/sec. To upgrade swap for: alibaba/wan-2.2-t2v-plus-1080p
MODEL_ID   = "alibaba/wan-2.1-t2v-plus-720p"
SUBMIT_URL = f"https://api.wavespeed.ai/api/v3/{MODEL_ID}"

payload = {
    "prompt": video_prompt,
    "negative_prompt": "text, watermark, logo, face, person, human, hands, words, letters, nsfw, blurry",
    "size": "720*1280",   # 9:16 vertical — TikTok / Reels format
    "duration": 5,
}

print(f"[generate_video] Model:    {MODEL_ID}")
print(f"[generate_video] Endpoint: {SUBMIT_URL}")
print(f"[generate_video] Submitting job...")

submit_response = requests.post(
    SUBMIT_URL,
    headers=headers,
    json=payload,
    timeout=60,
)

print(f"[generate_video] HTTP {submit_response.status_code}: {submit_response.text[:300]}")

if submit_response.status_code != 200:
    raise Exception(f"WaveSpeed submission failed: {submit_response.status_code}")

submit_data = submit_response.json()
request_id  = submit_data.get("data", {}).get("id")

if not request_id:
    raise Exception(f"No request_id returned: {submit_data}")

print(f"[generate_video] ✅ Job submitted. ID: {request_id}")

# ── Poll for completion ────────────────────────────────────────────────────
poll_url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
max_wait  = 300   # 5 minutes max
interval  = 15    # poll every 15 seconds
elapsed   = 0

while elapsed < max_wait:
    time.sleep(interval)
    elapsed += interval

    poll_response = requests.get(poll_url, headers=headers, timeout=30)

    if poll_response.status_code != 200:
        print(f"[generate_video] Poll {poll_response.status_code} — retrying...")
        continue

    poll_data = poll_response.json()
    status    = poll_data.get("data", {}).get("status", "unknown")
    print(f"[generate_video] Status: {status} ({elapsed}s elapsed)")

    if status == "completed":
        outputs = poll_data.get("data", {}).get("outputs", [])
        if not outputs:
            raise Exception(f"Completed but no outputs: {poll_data}")

        video_url = outputs[0]
        print(f"[generate_video] Downloading from: {video_url}")

        video_response = requests.get(video_url, timeout=120)
        with open(VIDEO_FILE, "wb") as f:
            f.write(video_response.content)

        size_mb = VIDEO_FILE.stat().st_size / (1024 * 1024)
        print(f"[generate_video] ✅ Video saved: {VIDEO_FILE} ({size_mb:.1f} MB)")
        break

    elif status == "failed":
        error = poll_data.get("data", {}).get("error", "unknown")
        raise Exception(f"WaveSpeed generation failed: {error}")

else:
    raise TimeoutError(f"Video generation timed out after {max_wait}s")
