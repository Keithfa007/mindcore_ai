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

# ── Step 1: Query available models and print ALL IDs ──────────────────────
print("[generate_video] Querying WaveSpeed model list...")
models_response = requests.get(
    "https://api.wavespeed.ai/api/v3/models",
    headers=headers,
    params={"page": 1, "page_size": 200},
    timeout=30,
)

print(f"[generate_video] Models API: HTTP {models_response.status_code}")

if models_response.status_code == 200:
    raw = models_response.json()

    # data can be a list OR a dict with a models key — handle both
    data = raw.get("data", raw)
    if isinstance(data, dict):
        all_models = data.get("models", data.get("items", []))
    else:
        all_models = data  # it's already a list

    print(f"[generate_video] Total models: {len(all_models)}")
    print("[generate_video] === ALL MODEL IDs ===")
    for m in all_models:
        if isinstance(m, dict):
            mid = m.get("id", m.get("model_id", m.get("name", str(m))))
        else:
            mid = str(m)
        print(f"  {mid}")
    print("[generate_video] === END MODEL LIST ===")
else:
    print(f"[generate_video] Models list failed: {models_response.text[:300]}")

# ── Step 2: Try candidate model IDs until one works ───────────────────────
CANDIDATES = [
    # WAN text-to-video variants to try
    ("wavespeed-ai/wan-2.1-t2v",         {"prompt": video_prompt, "negative_prompt": "text, watermark, logo, face, person, human, hands, blurry", "size": "720*1280", "duration": 5}),
    ("wavespeed-ai/wan2.1-t2v-720p",     {"prompt": video_prompt, "negative_prompt": "text, watermark, logo, face, person, human, hands, blurry", "size": "720*1280", "duration": 5}),
    ("alibaba/wan-2.1-t2v-plus-720p",    {"prompt": video_prompt, "negative_prompt": "text, watermark, logo, face, person, human, hands, blurry", "size": "720*1280", "duration": 5}),
    ("alibaba/wan-2.2-t2v-plus-480p",    {"prompt": video_prompt, "negative_prompt": "text, watermark, logo, face, person, human, hands, blurry", "size": "480*848",  "duration": 5}),
    ("alibaba/wan-2.5-text-to-video",    {"prompt": video_prompt, "negative_prompt": "text, watermark, logo, face, person, human, hands, blurry", "size": "720*1280", "duration": 5}),
    # Pixverse fast t2v as reliable fallback
    ("pixverse/pixverse-v4.5-t2v-fast",  {"prompt": video_prompt, "negative_prompt": "text, watermark, logo, face, person, human, hands, blurry", "duration": 5, "aspect_ratio": "9:16"}),
    ("pixverse/pixverse-v5-t2v",         {"prompt": video_prompt, "negative_prompt": "text, watermark, logo, face, person, human, hands, blurry", "duration": 5, "aspect_ratio": "9:16"}),
]

working_model = None
request_id    = None

for model_id, payload in CANDIDATES:
    url = f"https://api.wavespeed.ai/api/v3/{model_id}"
    print(f"[generate_video] Trying: {model_id}")
    r = requests.post(url, headers=headers, json=payload, timeout=30)
    print(f"[generate_video]   → HTTP {r.status_code}: {r.text[:200]}")

    if r.status_code == 200:
        data = r.json()
        request_id = data.get("data", {}).get("id")
        if request_id:
            working_model = model_id
            print(f"[generate_video] ✅ Model works: {model_id} | Job: {request_id}")
            break

if not request_id:
    raise Exception(
        "No working WaveSpeed model found. "
        "Check the === ALL MODEL IDs === section above to find the correct text-to-video model ID."
    )

# ── Step 3: Poll for result ────────────────────────────────────────────────
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
        print(f"[generate_video] ✅ Done! Model: {working_model} | Size: {size_mb:.1f} MB")
        break

    elif status == "failed":
        error = poll_data.get("data", {}).get("error", "unknown")
        raise Exception(f"WaveSpeed generation failed: {error}")

else:
    raise TimeoutError(f"Timed out after {max_wait}s")
