"""
generate_video.py
MindCore AI Video Pipeline — Step 3
Queries WaveSpeed model list to find correct t2v model,
then generates background video and saves to outputs/background_video.mp4
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

# ── Step 1: Query available models to find correct t2v model ID ────────────
print("[generate_video] Querying WaveSpeed model list...")
models_response = requests.get(
    "https://api.wavespeed.ai/api/v3/models",
    headers=headers,
    params={"page": 1, "page_size": 100},
    timeout=30,
)

print(f"[generate_video] Models API: HTTP {models_response.status_code}")

if models_response.status_code == 200:
    models_data = models_response.json()
    # Print all models containing "wan" and "t2v" or "text-to-video"
    all_models = models_data.get("data", {}).get("models", [])
    if not all_models:
        # Try flat list
        all_models = models_data.get("data", [])

    print(f"[generate_video] Total models returned: {len(all_models)}")
    print("[generate_video] === Video models (t2v / text-to-video) ===")
    for m in all_models:
        model_id = m.get("id", "") or m.get("model_id", "") or str(m)
        if any(k in model_id.lower() for k in ["t2v", "text-to-video", "text_to_video"]):
            print(f"  {model_id}")
    print("[generate_video] === All WAN models ===")
    for m in all_models:
        model_id = m.get("id", "") or m.get("model_id", "") or str(m)
        if "wan" in model_id.lower():
            print(f"  {model_id}")
    print("[generate_video] ===================")
else:
    print(f"[generate_video] Models list response: {models_response.text[:500]}")

# ── Step 2: Try known model IDs in order until one works ──────────────────
CANDIDATE_MODELS = [
    "wavespeed-ai/wan-2.1-t2v",
    "wavespeed-ai/wan2.1-t2v-720p",
    "wavespeed-ai/wan-2-1-t2v",
    "alibaba/wan-2.1-t2v-plus-720p",
    "alibaba-wan-2.1-t2v-plus-720p",
    "wan-2.1-t2v-plus-720p",
    "pixverse/pixverse-v4.5-t2v-fast",  # fallback: Pixverse fast t2v
]

payload_base = {
    "prompt": video_prompt,
    "negative_prompt": "text, watermark, logo, face, person, human, hands, words, letters, nsfw, blurry",
}

working_model = None
request_id    = None

for model_id in CANDIDATE_MODELS:
    url = f"https://api.wavespeed.ai/api/v3/{model_id}"
    print(f"[generate_video] Trying: {url}")

    # Build payload — try different param names per model
    payload = {**payload_base}
    if "pixverse" in model_id:
        payload["duration"] = 5
        payload["aspect_ratio"] = "9:16"
    else:
        payload["size"]     = "720*1280"
        payload["duration"] = 5

    r = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"[generate_video]   → HTTP {r.status_code}: {r.text[:150]}")

    if r.status_code == 200:
        data = r.json()
        request_id = data.get("data", {}).get("id")
        if request_id:
            working_model = model_id
            print(f"[generate_video] ✅ Model works: {model_id} | Job ID: {request_id}")
            break

if not request_id:
    raise Exception("No working WaveSpeed model found. Check logs above for available models.")

# ── Step 3: Poll for completion ────────────────────────────────────────────
poll_url = f"https://api.wavespeed.ai/api/v3/predictions/{request_id}/result"
max_wait = 300
interval = 15
elapsed  = 0

print(f"[generate_video] Polling for result...")

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
        print(f"[generate_video] Downloading: {video_url}")

        video_response = requests.get(video_url, timeout=120)
        with open(VIDEO_FILE, "wb") as f:
            f.write(video_response.content)

        size_mb = VIDEO_FILE.stat().st_size / (1024 * 1024)
        print(f"[generate_video] ✅ Video saved: {VIDEO_FILE} ({size_mb:.1f} MB)")
        print(f"[generate_video] ✅ Working model: {working_model}")
        break

    elif status == "failed":
        error = poll_data.get("data", {}).get("error", "unknown")
        raise Exception(f"WaveSpeed generation failed: {error}")

else:
    raise TimeoutError(f"Timed out after {max_wait}s")
