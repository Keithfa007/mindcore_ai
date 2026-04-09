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

OUTPUT_DIR.mkdir(exist_ok=True)

# ── Config ─────────────────────────────────────────────────────────────────
WAVESPEED_API_KEY  = os.environ["WAVESPEED_API_KEY"]
SUBMIT_URL         = "https://api.wavespeed.ai/api/v3/wavespeed-ai/wan-2.1/t2v-720p"
RESULT_URL         = "https://api.wavespeed.ai/api/v3/predictions/{task_id}/result"
POLL_INTERVAL      = 15    # seconds between status checks
TIMEOUT            = 600   # max seconds to wait

# ── Load script output ─────────────────────────────────────────────────────
if not SCRIPT_FILE.exists():
    raise FileNotFoundError(f"Script output not found: {SCRIPT_FILE}")

with open(SCRIPT_FILE, "r") as f:
    script_data = json.load(f)

# Support both single prompt and multi-scene prompts array
if "video_prompts" in script_data:
    # Use the first prompt for single-clip v1 generation
    video_prompt = script_data["video_prompts"][0]
elif "video_prompt" in script_data:
    video_prompt = script_data["video_prompt"]
else:
    raise KeyError("No video_prompt or video_prompts found in script_output.json")

print(f"[generate_video] Video prompt: {video_prompt[:80]}...")

# ── Submit video generation task ───────────────────────────────────────────
headers = {
    "Authorization": f"Bearer {WAVESPEED_API_KEY}",
    "Content-Type": "application/json",
}

payload = {
    "prompt": video_prompt,
    "negative_prompt": "text, watermark, logo, blurry, low quality, distorted, cartoon, anime",
    "size": "1280*720",
    "num_inference_steps": 30,
    "duration": 5,
    "guidance_scale": 5,
    "flow_shift": 5,
    "seed": -1,
    "enable_prompt_optimizer": True,
    "enable_safety_checker": True,
}

print("[generate_video] Submitting video generation task to WaveSpeed...")

resp = requests.post(SUBMIT_URL, headers=headers, json=payload, timeout=30)

if resp.status_code != 200:
    print(f"[generate_video] ❌ WaveSpeed submit error {resp.status_code}: {resp.text}")
    raise Exception(f"WaveSpeed submit failed: {resp.status_code}")

data    = resp.json()
task_id = (
    data.get("data", {}).get("id")
    or data.get("id")
    or data.get("task_id")
)

if not task_id:
    raise Exception(f"No task_id returned: {data}")

print(f"[generate_video] Task submitted. ID: {task_id}")

# ── Poll for result ────────────────────────────────────────────────────────
print("[generate_video] Polling for completion...")

deadline = time.time() + TIMEOUT

while time.time() < deadline:
    time.sleep(POLL_INTERVAL)

    result_resp = requests.get(
        RESULT_URL.format(task_id=task_id),
        headers={"Authorization": f"Bearer {WAVESPEED_API_KEY}"},
        timeout=30,
    )
    result_resp.raise_for_status()
    result_data = result_resp.json()

    inner  = result_data.get("data", result_data)
    status = inner.get("status", "unknown")

    print(f"[generate_video] Status: {status}")

    if status == "completed":
        outputs = inner.get("outputs", [])
        if not outputs:
            raise Exception(f"Completed but no outputs in response: {result_data}")
        video_url = outputs[0]
        break

    if status in ("failed", "error", "cancelled"):
        raise Exception(f"Video generation failed with status '{status}': {result_data}")

else:
    raise TimeoutError(f"Video generation timed out after {TIMEOUT}s (task: {task_id})")

# ── Download video ─────────────────────────────────────────────────────────
print(f"[generate_video] Downloading video from {video_url}...")

download_resp = requests.get(video_url, stream=True, timeout=120)
download_resp.raise_for_status()

with open(VIDEO_FILE, "wb") as f:
    for chunk in download_resp.iter_content(chunk_size=65_536):
        if chunk:
            f.write(chunk)

size_mb = VIDEO_FILE.stat().st_size / (1024 * 1024)
print(f"[generate_video] ✅ Video saved: {VIDEO_FILE} ({size_mb:.2f} MB)")
