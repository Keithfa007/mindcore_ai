"""MindCore AI -- WaveSpeed AI Video Clips v1.2
==========================================
v1.2: Single-scene mode -- generates 1 continuous clip per video (no choppy transitions).
v1.1: Fixed API URL and model slug.
v1.0: Initial WaveSpeed integration.

Uses Wan 2.2 T2V Ultra Fast ($0.01/second).
"""
import os, time, random, requests
from pathlib import Path

WAVESPEED_API_KEY = os.environ.get("WAVESPEED_API_KEY", "")
WAVESPEED_BASE = "https://api.wavespeed.ai/api/v3"
WAVESPEED_MODEL = "wavespeed-ai/wan-2.2/t2v-480p-ultra-fast"

from video_pipeline.runpod_clips import DRONE_THEMES, get_theme_for_run


def _submit(prompt, duration=5):
    """Submit a video generation job. Returns request ID."""
    headers = {"Authorization": f"Bearer {WAVESPEED_API_KEY}", "Content-Type": "application/json"}
    url = f"{WAVESPEED_BASE}/{WAVESPEED_MODEL}"
    payload = {"prompt": prompt, "size": "832*480", "duration": duration, "seed": -1}
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    req_id = data.get("data", {}).get("id") or data.get("id")
    if not req_id:
        raise RuntimeError(f"WaveSpeed no request ID: {data}")
    return req_id


def _poll(req_id, timeout=300):
    """Poll for completion. Returns output URL."""
    headers = {"Authorization": f"Bearer {WAVESPEED_API_KEY}"}
    url = f"{WAVESPEED_BASE}/predictions/{req_id}/result"
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        result = resp.json()
        d = result.get("data", result)
        status = d.get("status", "")
        if status == "completed":
            outputs = d.get("outputs") or d.get("output", [])
            if outputs:
                return outputs[0] if isinstance(outputs[0], str) else outputs[0].get("url", "")
            raise RuntimeError(f"WaveSpeed completed but no output: {result}")
        elif status in ("failed", "cancelled"):
            raise RuntimeError(f"WaveSpeed {status}: {d.get('error', result)}")
        remaining = int(deadline - time.time())
        print(f"  [WaveSpeed] {status}... ({remaining}s remaining)")
        time.sleep(5)
    raise TimeoutError(f"WaveSpeed job {req_id} timed out after {timeout}s")


def _download(video_url, output_path):
    """Download video from URL."""
    vid_resp = requests.get(video_url, timeout=120)
    vid_resp.raise_for_status()
    with open(output_path, "wb") as f:
        f.write(vid_resp.content)
    size_kb = Path(output_path).stat().st_size / 1024
    print(f"  [WaveSpeed] Clip saved: {size_kb:.0f} KB")
    return output_path


def fetch_drone_journey_clips(theme_name, output_dir, github_run_number=1):
    """Generate a SINGLE continuous drone clip for the entire video.
    Picks one scene from the theme and generates one clip.
    Returns list with single clip for compatibility with assembly pipeline.
    """
    theme = DRONE_THEMES.get(theme_name)
    if not theme:
        theme_name = random.choice(list(DRONE_THEMES.keys()))
        theme = DRONE_THEMES[theme_name]

    # Pick 1 scene from the theme (rotate based on run number)
    scene_idx = github_run_number % len(theme)
    scene = theme[scene_idx]
    print(f"  [WaveSpeed] Single scene: {theme_name} / {scene['name']}")
    print(f"  [WaveSpeed] Prompt: {scene['prompt'][:80]}...")

    clip_path = os.path.join(output_dir, f"drone_0_{scene['name']}.mp4")

    try:
        print(f"  [WaveSpeed] Submitting...")
        req_id = _submit(scene["prompt"], duration=5)
        print(f"  [WaveSpeed] Job {req_id} submitted")
        video_url = _poll(req_id, timeout=300)
        if video_url:
            _download(video_url, clip_path)
            return [(clip_path, scene["name"])]
    except Exception as e:
        print(f"  [WaveSpeed] Failed: {e}")

    return []


def fetch_wavespeed_clip(prompt, scene_idx, output_path, timeout=300):
    """Generate a single clip (for direct use)."""
    if not WAVESPEED_API_KEY:
        raise RuntimeError("WAVESPEED_API_KEY not set")
    print(f"  [WaveSpeed] Submitting: {prompt[:60]}...")
    req_id = _submit(prompt)
    print(f"  [WaveSpeed] Job {req_id} submitted")
    video_url = _poll(req_id, timeout=timeout)
    if video_url:
        return _download(video_url, output_path)
    raise RuntimeError("No video URL returned")
