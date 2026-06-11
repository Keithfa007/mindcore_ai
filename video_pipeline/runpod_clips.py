"""
MindCore AI -- RunPod AI Video Clips v1.0
==========================================
Replaces pexels_clips.py when RunPod Serverless is active.
Sends prompts to RunPod endpoint, receives AI-generated video clips.

Requires: RUNPOD_ENDPOINT_ID and RUNPOD_API_KEY env vars.
"""

import os, base64, time, requests
from pathlib import Path

RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "")
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID", "")
RUNPOD_API_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}"

# Track used prompts within a run to avoid duplicates
_used_prompts = set()

# -----------------------------------------------
# DRONE JOURNEY THEMES -- one location per video
# -----------------------------------------------
DRONE_THEMES = {
    "ocean": [
        {"name": "approach", "prompt": "Cinematic FPV drone racing low over deep dark blue ocean waves at dawn, spray misting up from the surface, camera flying fast forward toward the distant horizon where golden light is appearing, dramatic moody atmosphere, photorealistic, 4K"},
        {"name": "waves", "prompt": "Breathtaking aerial drone shot flying smoothly above massive turquoise ocean waves rolling and crashing in slow motion, white foam patterns spreading across deep blue water, morning golden sunlight reflecting off the surface, birds eye view, photorealistic, 4K"},
        {"name": "coast", "prompt": "Epic cinematic drone sweeping along dramatic rocky ocean coastline, enormous waves crashing against dark volcanic cliffs sending white spray high into the air, helicopter tracking shot, golden hour warm light, photorealistic, 4K"},
        {"name": "calm", "prompt": "Stunning aerial drone gliding slowly over perfectly calm crystal clear shallow tropical ocean, turquoise and emerald green water revealing sandy bottom below, gentle ripples catching golden sunlight, paradise serenity, photorealistic, 4K"},
        {"name": "sunset", "prompt": "Breathtaking cinematic drone flying forward over endless open ocean at golden sunset, sun sitting low on the horizon creating a long golden reflection path on the water surface, warm orange and pink sky, peaceful and epic, photorealistic, 4K"},
    ],
    "mountain": [
        {"name": "valley", "prompt": "Cinematic aerial drone flying through a deep mountain valley at dawn, mist rising between dark peaks, first golden sunlight hitting the ridge tops, epic scale and atmosphere, photorealistic, 4K"},
        {"name": "ridgeline", "prompt": "Breathtaking FPV drone racing along a dramatic mountain ridgeline at golden hour, steep drops on both sides, snow capped peaks in the distance, clouds swirling below, adrenaline and majesty, photorealistic, 4K"},
        {"name": "lake", "prompt": "Stunning aerial drone gliding over a perfectly still alpine lake reflecting snow capped mountains and blue sky like a mirror, surrounded by dark pine forest, morning golden light, serene and peaceful, photorealistic, 4K"},
        {"name": "clouds", "prompt": "Epic cinematic drone rising through clouds to reveal majestic mountain peaks piercing above a sea of white clouds at sunrise, golden light painting the snow, breathtaking scale and beauty, photorealistic, 4K"},
        {"name": "summit", "prompt": "Breathtaking aerial drone slowly circling a dramatic mountain summit at golden sunset, 360 degree view of endless mountain ranges stretching to the horizon, warm golden pink light, feeling of accomplishment and freedom, photorealistic, 4K"},
    ],
    "forest": [
        {"name": "canopy", "prompt": "Cinematic aerial drone flying low over an endless lush green forest canopy at morning golden hour, mist rising between the trees, sunlight rays piercing through creating volumetric light beams, peaceful and magical, photorealistic, 4K"},
        {"name": "river", "prompt": "Breathtaking drone shot following a crystal clear river winding through dense ancient forest, sunlight sparkling on the water surface, moss covered rocks and fallen trees, nature at its purest, photorealistic, 4K"},
        {"name": "waterfall", "prompt": "Stunning cinematic drone slowly rising in front of a massive waterfall crashing down moss covered rocks in a deep forest canyon, mist and rainbow in the spray, epic power and beauty, photorealistic, 4K"},
        {"name": "clearing", "prompt": "Aerial drone gliding over a sunlit forest clearing with wildflowers, surrounded by tall ancient trees, golden hour light flooding through the canopy creating long shadows, butterflies and particles floating in the air, photorealistic, 4K"},
        {"name": "sunset_canopy", "prompt": "Breathtaking aerial drone rising above the forest canopy at golden sunset revealing an endless sea of green treetops stretching to the horizon, warm golden light painting everything, peaceful infinite nature, photorealistic, 4K"},
    ],
    "desert": [
        {"name": "dunes", "prompt": "Cinematic aerial drone flying low over endless golden sand dunes at sunrise, long dramatic shadows creating geometric patterns, wind blowing fine sand off the ridge tops, epic desolate beauty, photorealistic, 4K"},
        {"name": "canyon", "prompt": "Breathtaking FPV drone racing through a narrow red rock canyon, towering sandstone walls on both sides, golden sunlight streaming down from above creating dramatic contrast, epic scale and speed, photorealistic, 4K"},
        {"name": "mesa", "prompt": "Stunning aerial drone circling a dramatic desert mesa at golden hour, vast empty desert floor stretching to the horizon in every direction, warm orange and red tones, solitude and majesty, photorealistic, 4K"},
        {"name": "oasis", "prompt": "Cinematic drone discovering a hidden desert oasis with palm trees and turquoise water surrounded by golden sand dunes, contrast between harsh desert and lush life, aerial revealing shot, photorealistic, 4K"},
        {"name": "stars", "prompt": "Breathtaking aerial drone slowly rising above dark desert landscape revealing an incredible starry night sky with the Milky Way stretching across the entire frame, moonlight illuminating distant dunes, cosmic peace, photorealistic, 4K"},
    ],
    "coast": [
        {"name": "lighthouse", "prompt": "Cinematic aerial drone flying toward a dramatic lighthouse on rocky cliffs at golden sunrise, waves crashing below, warm light glowing from the beacon, epic atmosphere and scale, photorealistic, 4K"},
        {"name": "beach_flight", "prompt": "Breathtaking FPV drone racing low along a pristine sandy beach at golden hour, turquoise waves gently rolling in on one side, palm trees and tropical vegetation on the other, warm golden sunlight, paradise speed, photorealistic, 4K"},
        {"name": "tide_pools", "prompt": "Stunning aerial drone gliding slowly over beautiful rocky tide pools at low tide, crystal clear water revealing colorful marine life below, gentle waves lapping at the edges, morning golden light, serene detail, photorealistic, 4K"},
        {"name": "cliff_sunset", "prompt": "Epic cinematic drone sweeping along towering sea cliffs at golden sunset, dramatic light painting the cliff faces orange and gold, endless ocean stretching to the horizon, birds soaring below, photorealistic, 4K"},
        {"name": "aerial_rise", "prompt": "Breathtaking cinematic drone slowly rising high above a beautiful coastline at sunset revealing the perfect curve of the bay with golden sand beach, turquoise water, green hills, and warm sky, infinite beauty, photorealistic, 4K"},
    ],
}


def _submit_job(prompt, num_frames=81, height=832, width=480):
    """Submit a generation job to RunPod Serverless."""
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}", "Content-Type": "application/json"}
    payload = {
        "input": {
            "prompt": prompt,
            "num_frames": num_frames,
            "height": height,
            "width": width,
            "guidance_scale": 7.5,
            "fps": 16,
        }
    }
    resp = requests.post(f"{RUNPOD_API_URL}/run", headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json().get("id")


def _poll_result(job_id, timeout=600, interval=10):
    """Poll for job completion."""
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{RUNPOD_API_URL}/status/{job_id}", headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        if status == "COMPLETED":
            return data.get("output", {})
        elif status in ("FAILED", "CANCELLED"):
            raise RuntimeError(f"RunPod job {job_id} {status}: {data}")
        print(f"  [RunPod] {status}... ({int(deadline - time.time())}s remaining)")
        time.sleep(interval)
    raise TimeoutError(f"RunPod job {job_id} timed out after {timeout}s")


def fetch_runpod_clip(prompt, scene_idx, output_path, timeout=600):
    """Generate a single AI video clip via RunPod Serverless."""
    if not RUNPOD_API_KEY or not RUNPOD_ENDPOINT_ID:
        raise RuntimeError("RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID must be set")

    print(f"  [RunPod] Submitting: {prompt[:60]}...")
    job_id = _submit_job(prompt)
    print(f"  [RunPod] Job {job_id} submitted")

    result = _poll_result(job_id, timeout=timeout)
    video_b64 = result.get("video_base64", "")
    if not video_b64:
        raise RuntimeError(f"RunPod returned empty video for job {job_id}")

    with open(output_path, "wb") as f:
        f.write(base64.b64decode(video_b64))

    size_kb = Path(output_path).stat().st_size / 1024
    print(f"  [RunPod] Clip saved: {size_kb:.0f} KB")
    return output_path


def fetch_drone_journey_clips(theme_name, output_dir, github_run_number=1):
    """Generate all clips for a drone journey theme.
    
    Returns list of (clip_path, scene_name) tuples.
    """
    theme = DRONE_THEMES.get(theme_name)
    if not theme:
        # Random theme
        import random
        theme_name = random.choice(list(DRONE_THEMES.keys()))
        theme = DRONE_THEMES[theme_name]

    print(f"  [RunPod] Drone journey: {theme_name} ({len(theme)} scenes)")
    clips = []
    for i, scene in enumerate(theme):
        clip_path = os.path.join(output_dir, f"drone_{i}_{scene['name']}.mp4")
        try:
            fetch_runpod_clip(scene["prompt"], i, clip_path)
            clips.append((clip_path, scene["name"]))
        except Exception as e:
            print(f"  [RunPod] Scene {scene['name']} failed: {e}")
    return clips


def get_theme_for_run(github_run_number):
    """Rotate through themes based on run number."""
    themes = list(DRONE_THEMES.keys())
    return themes[github_run_number % len(themes)]


def reset_used_prompts():
    global _used_prompts
    _used_prompts = set()
