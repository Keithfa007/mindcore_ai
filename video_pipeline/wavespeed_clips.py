"""MindCore AI -- WaveSpeed AI Video Clips v2.0
==========================================
v2.0: Wan 2.2 negative prompt support -- critical for eliminating morphing,
      flickering, face deformation, and text artifacts. Based on Wan 2.2
      prompting guide best practices (PixelDojo, MimicPC).
v1.3: Single-scene mode, full-length clip matching voiceover duration.
v1.2: Single-scene mode.
v1.1: Fixed API URL and model slug.
v1.0: Initial WaveSpeed integration.

Uses Wan 2.2 T2V Ultra Fast ($0.01/second).
Wan 2.2 max duration is 5 seconds per clip.
Pipeline generates 5 clips and assembles with crossfade transitions.
"""
import os, time, random, requests
from pathlib import Path

WAVESPEED_API_KEY = os.environ.get("WAVESPEED_API_KEY", "")
WAVESPEED_BASE = "https://api.wavespeed.ai/api/v3"
WAVESPEED_MODEL = "wavespeed-ai/wan-2.2/t2v-480p-ultra-fast"
MAX_CLIP_DURATION = 5  # Wan 2.2 model limit

# ── Wan 2.2 negative prompt -- critical for output quality ───────────────
WAN_NEGATIVE_PROMPT = (
    "static, still picture, blurred details, overexposed, bright colors, "
    "overall gray, worst quality, low quality, JPEG compression residue, "
    "ugly, incomplete, extra fingers, poorly drawn hands, poorly drawn faces, "
    "deformed, disfigured, malformed limbs, fused fingers, text, subtitles, "
    "watermark, logo, cluttered background, three legs, walking backwards, "
    "morphing, warping, flickering, face deformation"
)

from video_pipeline.runpod_clips import DRONE_THEMES, get_theme_for_run


def _submit(prompt, duration=5):
    """Submit a video generation job with Wan 2.2 negative prompt. Returns request ID."""
    headers = {"Authorization": f"Bearer {WAVESPEED_API_KEY}", "Content-Type": "application/json"}
    url = f"{WAVESPEED_BASE}/{WAVESPEED_MODEL}"
    payload = {
        "prompt": prompt,
        "negative_prompt": WAN_NEGATIVE_PROMPT,
        "size": "832*480",
        "duration": min(duration, MAX_CLIP_DURATION),
        "seed": -1,
    }
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
        vid_resp.content and f.write(vid_resp.content)
    size_kb = Path(output_path).stat().st_size / 1024
    print(f"  [WaveSpeed] Clip saved: {size_kb:.0f} KB")
    return output_path


def fetch_drone_journey_clips(theme_name, output_dir, github_run_number=1, duration=5):
    """Generate ALL 5 clips from a theme IN PARALLEL via WaveSpeed.
    Each clip is 5 seconds. Assembled with crossfade transitions by the pipeline.
    Cost: 5 clips x 5s x $0.01/s = $0.25 per video.
    """
    theme = DRONE_THEMES.get(theme_name)
    if not theme:
        theme_name = random.choice(list(DRONE_THEMES.keys()))
        theme = DRONE_THEMES[theme_name]
    print(f"  [WaveSpeed] Drone journey: {theme_name} ({len(theme)} scenes) -- PARALLEL")
    print(f"  [WaveSpeed] Cost: ~${len(theme) * MAX_CLIP_DURATION * 0.01:.2f}")

    headers = {"Authorization": f"Bearer {WAVESPEED_API_KEY}", "Content-Type": "application/json"}
    submit_url = f"{WAVESPEED_BASE}/{WAVESPEED_MODEL}"

    # Step 1: Submit ALL jobs at once (with negative prompt)
    jobs = []
    for i, scene in enumerate(theme):
        clip_path = os.path.join(output_dir, f"drone_{i}_{scene['name']}.mp4")
        try:
            print(f"  [WaveSpeed] Submitting [{i+1}/{len(theme)}]: {scene['prompt'][:55]}...")
            payload = {
                "prompt": scene["prompt"],
                "negative_prompt": WAN_NEGATIVE_PROMPT,
                "size": "832*480",
                "duration": MAX_CLIP_DURATION,
                "seed": -1,
            }
            resp = requests.post(submit_url, headers=headers, json=payload, timeout=30)
            resp.raise_for_status()
            data = resp.json()
            req_id = data.get("data", {}).get("id") or data.get("id")
            if req_id:
                jobs.append({"id": req_id, "scene": scene, "clip_path": clip_path, "index": i, "done": False, "output_url": None})
                print(f"  [WaveSpeed] Job {req_id} submitted")
        except Exception as e:
            print(f"  [WaveSpeed] Submit failed for {scene['name']}: {e}")
    if not jobs:
        return []
    print(f"  [WaveSpeed] All {len(jobs)} jobs submitted -- polling in parallel...")

    # Step 2: Poll ALL jobs simultaneously
    headers_poll = {"Authorization": f"Bearer {WAVESPEED_API_KEY}"}
    deadline = time.time() + 600
    while time.time() < deadline:
        all_done = True
        for job in jobs:
            if job["done"]:
                continue
            all_done = False
            try:
                poll_url = f"{WAVESPEED_BASE}/predictions/{job['id']}/result"
                resp = requests.get(poll_url, headers=headers_poll, timeout=30)
                resp.raise_for_status()
                result = resp.json()
                d = result.get("data", result)
                status = d.get("status", "")
                if status == "completed":
                    job["done"] = True
                    outputs = d.get("outputs") or d.get("output", [])
                    if outputs:
                        job["output_url"] = outputs[0] if isinstance(outputs[0], str) else outputs[0].get("url", "")
                    print(f"  [WaveSpeed] [{job['index']+1}/{len(jobs)}] {job['scene']['name']} COMPLETED")
                elif status in ("failed", "cancelled"):
                    job["done"] = True
                    print(f"  [WaveSpeed] [{job['index']+1}/{len(jobs)}] {job['scene']['name']} {status}")
            except Exception as e:
                print(f"  [WaveSpeed] Poll error for {job['scene']['name']}: {e}")
        if all_done:
            break
        pending = sum(1 for j in jobs if not j["done"])
        remaining = int(deadline - time.time())
        print(f"  [WaveSpeed] {pending} clips generating... ({remaining}s remaining)")
        time.sleep(5)

    # Step 3: Download completed clips
    clips = []
    for job in jobs:
        if job["output_url"]:
            try:
                vid_resp = requests.get(job["output_url"], timeout=120)
                vid_resp.raise_for_status()
                with open(job["clip_path"], "wb") as f:
                    f.write(vid_resp.content)
                size_kb = Path(job["clip_path"]).stat().st_size / 1024
                print(f"  [WaveSpeed] Saved {job['scene']['name']}: {size_kb:.0f} KB")
                clips.append((job["clip_path"], job["scene"]["name"]))
            except Exception as e:
                print(f"  [WaveSpeed] Download failed for {job['scene']['name']}: {e}")
        elif not job["done"]:
            print(f"  [WaveSpeed] {job['scene']['name']} timed out")
        else:
            print(f"  [WaveSpeed] {job['scene']['name']} failed")
    print(f"  [WaveSpeed] {len(clips)}/{len(jobs)} clips generated successfully")
    return clips


def fetch_wavespeed_clip(prompt, scene_idx, output_path, timeout=300, duration=5):
    """Generate a single clip (for direct use)."""
    if not WAVESPEED_API_KEY:
        raise RuntimeError("WAVESPEED_API_KEY not set")
    print(f"  [WaveSpeed] Submitting: {prompt[:60]}...")
    req_id = _submit(prompt, duration=min(duration, MAX_CLIP_DURATION))
    print(f"  [WaveSpeed] Job {req_id} submitted")
    video_url = _poll(req_id, timeout=timeout)
    if video_url:
        return _download(video_url, output_path)
    raise RuntimeError("No video URL returned")
