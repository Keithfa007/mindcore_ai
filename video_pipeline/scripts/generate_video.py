"""
generate_video.py
MindCore AI Video Pipeline — Step 3
Reads video_prompt from outputs/script_output.json
Calls WaveSpeed AI API to generate background video
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
print(f"[generate_video] Prompt: {video_prompt[:100]}...")

# ── WaveSpeed AI API ───────────────────────────────────────────────────────
WAVESPEED_API_KEY = os.environ["WAVESPEED_API_KEY"]

headers = {
    "Authorization": f"Bearer {WAVESPEED_API_KEY}",
    "Content-Type": "application/json",
}

# Using WAN 2.1 text-to-video — budget friendly at $0.01/sec
# Swap model for "wavespeed-ai/kling-v2/text-to-video" for higher quality
payload = {
    "prompt": video_prompt,
    "negative_prompt": "text, watermark, logo, face, person, human, hands, words, letters, nsfw, blurry",
    "duration": 5,
    "aspect_ratio": "9:16",        # TikTok / Reels vertical format
    "resolution": "720p",
    "quality": "normal",
}

print("[generate_video] Submitting job to WaveSpeed AI...")
submit_response = requests.post(
    "https://api.wavespeed.ai/api/v2/wavespeed-ai/wan-v2.1/text-to-video",
    headers=headers,
    json=payload,
    timeout=60,
)

if submit_response.status_code != 200:
    print(f"[generate_video] ❌ Submission error {submit_response.status_code}: {submit_response.text}")
    raise Exception(f"WaveSpeed submission failed: {submit_response.status_code}")

submit_data = submit_response.json()
request_id = submit_data.get("data", {}).get("id")

if not request_id:
    raise Exception(f"No request_id returned: {submit_data}")

print(f"[generate_video] Job submitted. Request ID: {request_id}")

# ── Poll for completion ────────────────────────────────────────────────────
poll_url = f"https://api.wavespeed.ai/api/v2/predictions/{request_id}/result"
max_wait  = 300   # 5 minutes max
interval  = 10    # poll every 10 seconds
elapsed   = 0

while elapsed < max_wait:
    time.sleep(interval)
    elapsed += interval

    poll_response = requests.get(poll_url, headers=headers, timeout=30)

    if poll_response.status_code != 200:
        print(f"[generate_video] Poll error {poll_response.status_code} — retrying...")
        continue

    poll_data   = poll_response.json()
    status      = poll_data.get("data", {}).get("status")
    print(f"[generate_video] Status: {status} ({elapsed}s elapsed)")

    if status == "completed":
        outputs = poll_data.get("data", {}).get("outputs", [])
        if not outputs:
            raise Exception("Completed but no outputs returned")

        video_url = outputs[0]
        print(f"[generate_video] Downloading from: {video_url}")

        video_response = requests.get(video_url, timeout=120)
        with open(VIDEO_FILE, "wb") as f:
            f.write(video_response.content)

        size_mb = VIDEO_FILE.stat().st_size / (1024 * 1024)
        print(f"[generate_video] ✅ Video saved: {VIDEO_FILE} ({size_mb:.1f} MB)")
        break

    elif status == "failed":
        error = poll_data.get("data", {}).get("error", "Unknown error")
        raise Exception(f"WaveSpeed generation failed: {error}")

else:
    raise TimeoutError(f"Video generation timed out after {max_wait}s")
