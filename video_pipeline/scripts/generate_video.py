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

# WaveSpeed API v3 — WAN 2.1 text-to-video 720p
# Budget friendly at ~$0.01/sec. Upgrade to wavespeed-ai/wan-2-1-t2v-1080p for higher quality.
MODEL_ID    = "wavespeed-ai/wan-2-1-t2v-720p"
SUBMIT_URL  = f"https://api.wavespeed.ai/api/v3/{MODEL_ID}"

payload = {
    "prompt": video_prompt,
    "negative_prompt": "text, watermark, logo, face, person, human, hands, words, letters, nsfw, blurry",
    "num_frames": 81,       # ~5 seconds at 16fps
    "aspect_ratio": "9:16", # TikTok / Reels vertical format
    "resolution": "720p",
}

print(f"[generate_video] Submitting to: {SUBMIT_URL}")
submit_response = requests.post(
    SUBMIT_URL,
    headers=headers,
    json=payload,
    timeout=60,
)

if submit_response.status_code != 200:
    print(f"[generate_video] ❌ Submission error {submit_response.status_code}: {submit_response.text}")
    raise Exception(f"WaveSpeed submission failed: {submit_response.status_code}")

submit_data = submit_response.json()
print(f"[generate_video] Response: {json.dumps(submit_data, indent=2)[:300]}")

request_id = submit_data.get("data", {}).get("id")
if not request_id:
    raise Exception(f"No request_id returned: {submit_data}")

print(f"[generate_video] ✅ Job submitted. ID: {request_id}")

# ── Poll for completion ────────────────────────────────────────────────────
poll_url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
max_wait = 300   # 5 minutes max
interval = 15    # poll every 15 seconds
elapsed  = 0

print(f"[generate_video] Polling: {poll_url}")

while elapsed < max_wait:
    time.sleep(interval)
    elapsed += interval

    poll_response = requests.get(poll_url, headers=headers, timeout=30)

    if poll_response.status_code != 200:
        print(f"[generate_video] Poll {poll_response.status_code} — retrying in {interval}s...")
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
