"""
MindCore AI -- RunPod AI Video Clips v1.8
==========================================
v1.8: Added urban_night, fog_weather, architecture themes (15 total). Color grading keywords.
v1.7: Real-ESRGAN upscaling -- clips generated at 832x480 then upscaled 2x to 1664x960.
v1.6: PARALLEL clip generation -- all 5 clips generated simultaneously.
v1.5: Increased poll timeout to 1800s (30min) for cold starts.
v1.3: All prompts rewritten for strong continuous flying movement.
v1.2: Built-in crossfade transitions between scenes.
v1.1: 12 drone journey themes.

Replaces pexels_clips.py when RunPod Serverless is active.
"""

import os, base64, time, subprocess, requests
from pathlib import Path

RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "")
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID", "")
RUNPOD_API_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}"

CROSSFADE_DURATION = 0.8
CLIP_DURATION = 5.06
UPSCALE_FACTOR = 2

_used_prompts = set()

DRONE_THEMES = {
    "ocean": [
        {"name": "approach", "prompt": "FPV drone flying fast forward low over dark blue ocean waves at dawn, camera racing toward the horizon, spray misting up from the surface, continuous forward motion never stopping, golden light appearing ahead, dramatic moody atmosphere, smooth tracking shot, cinematic warm golden tones, photorealistic, 4K"},
        {"name": "waves", "prompt": "Aerial drone flying forward steadily above massive turquoise ocean waves rolling and crashing below, camera moving continuously forward over the water, white foam patterns spreading, morning golden sunlight reflecting off the surface, smooth continuous forward tracking shot, cinematic color grading, photorealistic, 4K"},
        {"name": "coast", "prompt": "Cinematic drone flying sideways along dramatic rocky ocean coastline, camera tracking laterally along the cliffs, enormous waves crashing against volcanic rocks sending spray into the air, continuous lateral movement never stopping, golden hour warm light, cinematic orange and teal, photorealistic, 4K"},
        {"name": "calm", "prompt": "Aerial drone flying forward steadily over perfectly calm crystal clear tropical ocean, camera moving continuously forward, turquoise and emerald green water revealing sandy bottom below, gentle ripples catching golden sunlight, smooth forward tracking shot, vibrant tropical color grading, photorealistic, 4K"},
        {"name": "sunset", "prompt": "Cinematic drone flying forward over endless open ocean at golden sunset, camera racing toward the sun on the horizon, golden reflection path stretching ahead on the water surface, continuous forward motion, warm orange and pink sky, smooth tracking shot, cinematic warm golden tones, photorealistic, 4K"},
    ],
    "mountain": [
        {"name": "valley", "prompt": "Cinematic drone flying forward through a deep mountain valley at dawn, camera moving continuously through the valley between dark peaks, mist rising around the camera, first golden sunlight hitting ridge tops, smooth forward tracking shot, epic scale, cinematic orange and teal with enhanced contrast, photorealistic, 4K"},
        {"name": "ridgeline", "prompt": "FPV drone racing forward along a dramatic mountain ridgeline at golden hour, camera flying fast along the ridge, steep drops visible on both sides, snow capped peaks ahead, continuous forward motion along the ridge, adrenaline and majesty, cinematic warm golden tones, photorealistic, 4K"},
        {"name": "lake", "prompt": "Aerial drone flying forward steadily over a still alpine lake reflecting snow capped mountains, camera tracking forward across the mirror-like water surface, surrounded by dark pine forest, continuous forward motion, morning golden light, natural with enhanced blues and subtle vignetting, photorealistic, 4K"},
        {"name": "clouds", "prompt": "Cinematic drone flying upward through clouds and rising to reveal majestic mountain peaks piercing above a sea of white clouds at sunrise, camera moving continuously upward, golden light painting the snow, vertical tracking shot, cinematic warm highlights with cool shadows, photorealistic, 4K"},
        {"name": "summit", "prompt": "Aerial drone flying in a wide circle around a dramatic mountain summit at golden sunset, camera orbiting continuously around the peak, 360 degree view of endless mountain ranges, continuous orbital motion, warm golden pink light, cinematic orange and teal, photorealistic, 4K"},
    ],
    "forest": [
        {"name": "canopy", "prompt": "Cinematic drone flying forward low over an endless lush green forest canopy at morning golden hour, camera moving continuously forward over the treetops, mist rising between the trees, sunlight rays creating volumetric light beams, smooth forward tracking shot, rich greens with warm highlights, photorealistic, 4K"},
        {"name": "river", "prompt": "Aerial drone flying forward following a crystal clear river winding through dense ancient forest, camera tracking forward along the river below, sunlight sparkling on the water surface, continuous forward motion following the river, rich greens with enhanced water clarity, photorealistic, 4K"},
        {"name": "waterfall", "prompt": "Cinematic drone flying upward slowly in front of a massive waterfall crashing down moss covered rocks, camera rising continuously revealing the full scale of the falls, mist and rainbow in the spray, smooth vertical tracking shot, cool blues and whites with prismatic highlights, photorealistic, 4K"},
        {"name": "clearing", "prompt": "Aerial drone flying forward into a sunlit forest clearing with wildflowers, camera moving steadily forward through the gap in the trees, golden hour light flooding through the canopy, continuous forward discovery shot, warm earth tones with enhanced greens, photorealistic, 4K"},
        {"name": "sunset_canopy", "prompt": "Cinematic drone flying upward and rising above the forest canopy at golden sunset, camera climbing continuously to reveal an endless sea of green treetops stretching to the horizon, smooth upward tracking shot, warm golden light, cinematic warm golden tones, photorealistic, 4K"},
    ],
    "desert": [
        {"name": "dunes", "prompt": "FPV drone flying fast forward low over endless golden sand dunes at sunrise, camera racing forward over the ridges, long dramatic shadows below, wind blowing fine sand off the tops, continuous forward motion, smooth tracking shot, warm earth tones with enhanced texture detail, photorealistic, 4K"},
        {"name": "canyon", "prompt": "FPV drone fast forward through a narrow red rock canyon, camera racing between towering sandstone walls on both sides, golden sunlight streaming down from above, continuous forward motion through the canyon, epic speed, high contrast with enhanced rock textures, photorealistic, 4K"},
        {"name": "mesa", "prompt": "Aerial drone flying in a wide orbit around a dramatic desert mesa at golden hour, camera circling continuously around the formation, vast desert floor below stretching to the horizon, smooth continuous orbital motion, warm earth tones with long shadow detail, photorealistic, 4K"},
        {"name": "oasis", "prompt": "Cinematic drone flying forward and descending toward a hidden desert oasis with palm trees and turquoise water, camera moving forward and downward revealing the oasis, golden sand dunes surrounding, continuous approach shot, vibrant greens against warm sand tones, photorealistic, 4K"},
        {"name": "stars", "prompt": "Cinematic drone flying upward slowly above dark desert landscape at night, camera rising continuously to reveal an incredible starry sky with the Milky Way stretching across the frame, smooth vertical tracking shot upward, cosmic peace, deep cinematic blues and purples, photorealistic, 4K"},
    ],
    "coast": [
        {"name": "lighthouse", "prompt": "Cinematic drone flying forward toward a dramatic lighthouse on rocky cliffs at golden sunrise, camera approaching continuously, waves crashing below, warm light from the beacon growing larger, smooth forward approach shot, cinematic warm golden tones, photorealistic, 4K"},
        {"name": "beach_flight", "prompt": "FPV drone racing forward low along a pristine sandy beach at golden hour, camera flying fast along the shoreline, turquoise waves rolling in on one side, palm trees on the other, continuous forward motion along the coast, vibrant tropical color grading, photorealistic, 4K"},
        {"name": "tide_pools", "prompt": "Aerial drone flying forward steadily over beautiful rocky tide pools at low tide, camera tracking forward over the pools, crystal clear water below, gentle waves lapping at the edges, continuous forward motion, morning golden light, natural with enhanced blues, photorealistic, 4K"},
        {"name": "cliff_sunset", "prompt": "Cinematic drone flying sideways along towering sea cliffs at golden sunset, camera tracking laterally along the cliff face, dramatic light painting the rocks orange and gold, continuous lateral movement, birds soaring below, cinematic orange and teal, photorealistic, 4K"},
        {"name": "aerial_rise", "prompt": "Cinematic drone flying upward and rising high above a beautiful coastline at sunset, camera climbing continuously revealing the curve of the bay with golden sand beach and turquoise water below, smooth vertical tracking shot, warm highlights with cool ocean shadows, photorealistic, 4K"},
    ],
    "volcano": [
        {"name": "crater", "prompt": "Cinematic drone flying forward slowly toward a massive volcanic crater at dawn, camera approaching continuously, wisps of steam rising, dramatic dark landscape with orange glow growing ahead, smooth forward approach shot, dramatic orange and deep shadow contrast, photorealistic, 4K"},
        {"name": "lava_flow", "prompt": "Aerial drone flying forward low over rivers of glowing orange lava flowing down a dark volcanic slope at night, camera tracking forward along the lava river, intense heat shimmer, continuous forward motion following the flow, dramatic orange and deep shadow contrast, photorealistic, 4K"},
        {"name": "ash_fields", "prompt": "Aerial drone flying forward steadily over vast black volcanic ash fields, camera moving continuously forward over dramatic cracks and textures, patches of bright green vegetation breaking through, continuous forward tracking shot, desaturated with enhanced texture contrast, photorealistic, 4K"},
        {"name": "steam_vents", "prompt": "Cinematic drone flying in a circle around geothermal steam vents erupting from dark volcanic rock, camera orbiting continuously, golden sunrise backlighting the steam creating god rays, smooth continuous orbital motion, dramatic orange and deep shadow contrast, photorealistic, 4K"},
        {"name": "volcano_sunset", "prompt": "Cinematic drone flying upward and rising above a volcanic island at golden sunset, camera climbing continuously, the entire landscape glowing orange below, ocean surrounding the island catching fire, smooth vertical tracking shot, cinematic warm golden tones, photorealistic, 4K"},
    ],
    "northern_lights": [
        {"name": "first_glow", "prompt": "Cinematic drone flying forward low over a frozen arctic landscape at twilight, camera moving continuously forward over snow and ice, faint green aurora borealis shimmering on the horizon ahead, smooth forward tracking shot, magical atmosphere, deep cinematic blues and purples, photorealistic, 4K"},
        {"name": "full_display", "prompt": "Aerial drone flying in a slow orbit above a snow covered valley as vivid green and purple northern lights dance overhead, camera circling continuously, ribbons of light reflecting off a frozen lake below, smooth orbital motion, vibrant aurora greens with deep blue sky, photorealistic, 4K"},
        {"name": "mountains", "prompt": "Cinematic drone flying forward between snow capped arctic mountain peaks, camera moving continuously forward through the mountains, brilliant green and blue aurora borealis curtains waving overhead, smooth forward tracking shot, deep cinematic blues and purples, photorealistic, 4K"},
        {"name": "reflection", "prompt": "Aerial drone flying forward steadily over a perfectly still arctic fjord at night, camera tracking forward over the mirror water, vivid green and pink northern lights mirrored perfectly below, continuous forward motion, enhanced aurora colors with deep shadow contrast, photorealistic, 4K"},
        {"name": "fade", "prompt": "Cinematic drone flying upward slowly above the arctic landscape as northern lights fade into pre-dawn blue, camera rising continuously, first golden sunlight touching distant peaks, smooth vertical tracking shot, transitioning from cool blues to warm golden, photorealistic, 4K"},
    ],
    "tropical_island": [
        {"name": "discovery", "prompt": "FPV drone flying fast forward over deep blue ocean toward a lush tropical island on the horizon, camera racing toward the island growing larger, palm trees and white sand beaches becoming visible, continuous forward approach, vibrant tropical color grading, photorealistic, 4K"},
        {"name": "lagoon", "prompt": "Aerial drone flying forward steadily over a stunning turquoise tropical lagoon, camera moving continuously forward, water so clear revealing coral reef and white sand below, smooth forward tracking shot over paradise water, vibrant turquoise and emerald tones, photorealistic, 4K"},
        {"name": "palm_beach", "prompt": "FPV drone racing forward along a pristine white sand beach lined with coconut palm trees, camera flying fast along the shoreline, crystal clear waves on one side, tropical vegetation on the other, continuous forward motion, saturated tropical color palette, photorealistic, 4K"},
        {"name": "jungle", "prompt": "Cinematic drone flying forward low through lush tropical jungle canopy, camera moving continuously forward through the trees, exotic flowers passing by, a hidden waterfall visible ahead, smooth forward tracking shot, rich greens with warm dappled highlights, photorealistic, 4K"},
        {"name": "island_sunset", "prompt": "Cinematic drone flying upward and rising high above the tropical island at golden sunset, camera climbing continuously, revealing the entire island surrounded by glowing turquoise water below, smooth vertical tracking shot, cinematic warm golden tones, photorealistic, 4K"},
    ],
    "storm_clearing": [
        {"name": "dark_approach", "prompt": "Cinematic drone flying forward toward massive dark storm clouds on the horizon, camera moving continuously toward the storm, lightning flickering inside the clouds ahead, wind bending grass below, smooth forward approach shot, desaturated with dramatic contrast, photorealistic, 4K"},
        {"name": "rain_wall", "prompt": "Aerial drone flying forward alongside a dramatic wall of heavy rain sweeping across green countryside, camera tracking forward parallel to the rain, dark sky above, bright sunlit landscape ahead, continuous forward motion, desaturated with dramatic contrast, photorealistic, 4K"},
        {"name": "eye_of_storm", "prompt": "Cinematic drone flying upward through a break in massive storm clouds, camera rising continuously through the gap, dark clouds on all sides, blue sky and golden sunlight appearing above, smooth vertical tracking shot, dramatic contrast transitioning to warm light, photorealistic, 4K"},
        {"name": "rainbow", "prompt": "Aerial drone flying forward toward a vivid double rainbow arcing across the sky, camera moving continuously toward the rainbow, storm clouds clearing ahead, golden sunlight breaking through, smooth forward tracking shot, prismatic highlights with enhanced saturation, photorealistic, 4K"},
        {"name": "clear_sky", "prompt": "Cinematic drone flying upward and rising above freshly washed green landscape after a storm, camera climbing continuously, everything glistening with raindrops in warm golden sunlight, blue sky expanding, smooth vertical tracking shot, cinematic warm golden tones, photorealistic, 4K"},
    ],
    "lake_morning": [
        {"name": "mist", "prompt": "Cinematic drone flying forward low over a glassy calm lake at dawn, camera moving continuously forward through thick morning mist hovering above the water, pine tree silhouettes emerging ahead, smooth forward tracking shot, monochromatic with subtle warm shifts, photorealistic, 4K"},
        {"name": "reflection", "prompt": "Aerial drone flying forward steadily over perfectly still lake water reflecting mountains like a mirror, camera tracking continuously forward over the glass-like surface, morning golden light, smooth forward motion, natural with enhanced blues and subtle vignetting, photorealistic, 4K"},
        {"name": "shoreline", "prompt": "Aerial drone flying forward following a winding lake shoreline at golden hour, camera tracking along the shore, crystal clear shallows below, autumn colored trees passing alongside, continuous forward motion following the shore, warm autumn palette with enhanced reds and golds, photorealistic, 4K"},
        {"name": "birds", "prompt": "Cinematic drone flying forward over a misty lake as a flock of birds takes flight from the surface ahead, camera moving continuously forward through the rising birds, water droplets scattering in golden light, smooth forward tracking shot, cinematic warm golden tones, photorealistic, 4K"},
        {"name": "sunrise_lake", "prompt": "Cinematic drone flying upward and rising above the lake as golden sunrise floods across the landscape, camera climbing continuously, mist burning away to reveal mountain scenery reflected in still water, smooth vertical tracking shot, cinematic orange and teal, photorealistic, 4K"},
    ],
    "waterfall_journey": [
        {"name": "source", "prompt": "Aerial drone flying forward following a mountain stream from its source high in misty peaks, camera tracking forward along the stream, crystal clear water tumbling over mossy rocks, continuous forward motion downstream, cool blues and rich greens, photorealistic, 4K"},
        {"name": "cascade", "prompt": "Cinematic drone flying forward alongside a series of cascading waterfalls stepping down through lush jungle, camera tracking forward and downward following the water, white water crashing over each tier, continuous forward motion, rich greens with cool water highlights, photorealistic, 4K"},
        {"name": "main_fall", "prompt": "Cinematic drone flying upward slowly in front of an enormous waterfall plunging into a deep blue pool below, camera rising continuously revealing the full massive scale of the falls, mist and rainbow, smooth vertical tracking shot, cool blues and whites with prismatic highlights, photorealistic, 4K"},
        {"name": "pool", "prompt": "Aerial drone flying forward over the crystal clear turquoise pool at the base of a waterfall, camera moving continuously forward over the water, sunlight penetrating deep, fine mist creating a rainbow, smooth forward tracking shot, vibrant turquoise with prismatic highlights, photorealistic, 4K"},
        {"name": "river_out", "prompt": "Aerial drone flying forward following the river flowing away from the waterfall through a peaceful valley, camera tracking forward along the calming water, golden sunset light flooding the valley, continuous forward motion, journey complete, cinematic warm golden tones, photorealistic, 4K"},
    ],
    "countryside": [
        {"name": "dawn_fields", "prompt": "Cinematic drone flying forward low over endless golden wheat fields at dawn, camera moving continuously forward over the golden rows, morning mist below, long dramatic shadows stretching across the landscape, smooth forward tracking shot, warm earth tones with enhanced texture detail, photorealistic, 4K"},
        {"name": "rolling_hills", "prompt": "Aerial drone flying forward over lush green rolling hills and patchwork farmland, camera moving continuously forward over the landscape, stone walls and hedgerows below, warm golden hour light, smooth forward tracking shot, vibrant greens and golds with high contrast, photorealistic, 4K"},
        {"name": "winding_road", "prompt": "Aerial drone flying forward following a narrow winding country road through emerald green hills, camera tracking forward along the road below, lined with ancient oak trees, dappled sunlight, continuous forward motion following the path, rich greens with warm dappled highlights, photorealistic, 4K"},
        {"name": "village", "prompt": "Cinematic drone flying forward and descending toward a picturesque countryside village with stone cottages nestled in a green valley, camera approaching continuously, golden afternoon light, smooth forward approach shot, warm medieval palette with enhanced stone textures, photorealistic, 4K"},
        {"name": "sunset_fields", "prompt": "Cinematic drone flying upward and rising above the countryside at golden sunset, camera climbing continuously, entire landscape glowing warm orange below, long shadows stretching across green fields, smooth vertical tracking shot, cinematic warm golden tones, photorealistic, 4K"},
    ],
    "urban_night": [
        {"name": "skyline_approach", "prompt": "Cinematic drone flying forward toward a glowing city skyline at night, camera moving continuously toward the towers, millions of lights reflecting off glass facades, neon signs and street lights below, continuous forward approach, cinematic orange and teal color grading, photorealistic, 4K"},
        {"name": "highway_flow", "prompt": "Aerial drone flying forward steadily above a busy highway at night, camera tracking forward over flowing red and white light trails from cars below, city skyline glowing in the background, continuous forward motion, desaturated with enhanced light trails, photorealistic, 4K"},
        {"name": "neon_streets", "prompt": "FPV drone racing forward low through neon-lit city streets at night, camera flying fast between glowing signs and wet reflections on the road, rain-slicked streets catching colorful light, continuous forward motion, vibrant neon color palette, photorealistic, 4K"},
        {"name": "rooftop_orbit", "prompt": "Cinematic drone flying in a slow orbit around a rooftop at night, camera circling continuously, the entire city sprawling below with twinkling lights to the horizon, warm interior light from rooftop windows, smooth orbital motion, warm highlights with cool shadows, photorealistic, 4K"},
        {"name": "city_dawn", "prompt": "Cinematic drone flying upward and rising above the city as first light of dawn appears on the horizon, camera climbing continuously, city lights still glowing below while golden light floods across the skyline, smooth vertical tracking shot, cinematic orange and blue color grading, photorealistic, 4K"},
    ],
    "fog_weather": [
        {"name": "fog_rollin", "prompt": "Aerial drone flying forward steadily above a dense fog bank rolling over coastal hills, camera moving continuously forward over the white blanket of mist, treetops poking through like islands, diffused golden sunlight through fog creating ethereal glow, continuous forward motion, monochromatic with warm highlights, photorealistic, 4K"},
        {"name": "valley_mist", "prompt": "Cinematic drone flying forward through a misty mountain valley at dawn, camera moving continuously through layers of mist between dark ridges, visibility shifting from clear to obscured, golden light filtering through, smooth forward tracking shot, desaturated with subtle warm shifts, photorealistic, 4K"},
        {"name": "storm_approach", "prompt": "FPV drone flying fast forward toward massive dark storm clouds building on the horizon, camera racing toward the storm wall, green fields below bending in wind, lightning flickering inside distant clouds, continuous forward motion, high contrast dramatic sky, photorealistic, 4K"},
        {"name": "rain_clearing", "prompt": "Cinematic drone flying upward through a break in heavy rain clouds, camera rising continuously through the gap, dark storm clouds parting to reveal brilliant blue sky and golden sunlight above, water droplets catching light, smooth vertical tracking shot, prismatic highlights, photorealistic, 4K"},
        {"name": "mist_sunrise", "prompt": "Aerial drone flying forward over a landscape emerging from morning mist as golden sunrise burns it away, camera moving continuously forward, mist dissolving to reveal lush green valleys and sparkling rivers, continuous forward discovery shot, warm golden earth tones, photorealistic, 4K"},
    ],
    "architecture": [
        {"name": "castle_reveal", "prompt": "Cinematic drone flying forward toward a medieval castle on a hilltop revealed through lifting morning mist, camera approaching continuously, ancient stone walls and towers growing larger, golden hour with mist backlit by sunrise, smooth forward approach shot, warm medieval palette with enhanced stone textures, photorealistic, 4K"},
        {"name": "bridge_flyunder", "prompt": "FPV drone racing forward under a dramatic suspension bridge spanning a wide river, camera flying fast between the massive cables and steel structure, water rushing below, continuous forward motion through the bridge, cool metallic tones with enhanced structural detail, photorealistic, 4K"},
        {"name": "monument_spiral", "prompt": "Aerial drone flying in an ascending spiral around a grand historical monument or cathedral, camera orbiting continuously upward revealing intricate architectural details at every level, dramatic side lighting emphasizing carved stone, smooth continuous orbital and vertical motion, classic warm palette, photorealistic, 4K"},
        {"name": "ruins_discovery", "prompt": "Cinematic drone flying forward low over ancient stone ruins overgrown with vegetation in a jungle clearing, camera moving continuously forward over crumbling walls and moss-covered columns, golden shafts of light piercing the canopy above, smooth forward discovery shot, rich greens with warm golden highlights, photorealistic, 4K"},
        {"name": "lighthouse_orbit", "prompt": "Aerial drone flying in a wide circle around a dramatic lighthouse perched on rocky cliffs at golden sunset, camera orbiting continuously, enormous waves crashing against the rocks below, warm golden light painting everything orange, smooth continuous orbital motion, cinematic orange and teal, photorealistic, 4K"},
    ],
}


def assemble_drone_journey(clip_paths, output_path, crossfade_dur=None):
    if crossfade_dur is None: crossfade_dur = CROSSFADE_DURATION
    if not clip_paths: raise RuntimeError("No clips to assemble")
    if len(clip_paths) == 1:
        import shutil; shutil.copy2(clip_paths[0], output_path); return output_path
    durations = []
    for cp in clip_paths:
        dur = _get_duration(cp); durations.append(dur)
        print(f"  [Crossfade] Clip duration: {dur:.2f}s")
    inputs = []
    for p in clip_paths: inputs.extend(["-i", p])
    filters = []; offset = durations[0] - crossfade_dur; prev = "0:v"
    for i in range(1, len(clip_paths)):
        out_label = f"v{i}" if i < len(clip_paths) - 1 else "outv"
        filters.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={crossfade_dur}:offset={offset:.2f}[{out_label}]")
        prev = out_label
        if i < len(clip_paths) - 1: offset += durations[i] - crossfade_dur
    cmd = ["ffmpeg", "-y"] + inputs + ["-filter_complex", ";".join(filters), "-map", "[outv]", "-c:v", "libx264", "-crf", "16", "-preset", "slow", "-pix_fmt", "yuv420p", output_path]
    print(f"  [Crossfade] Assembling {len(clip_paths)} clips with {crossfade_dur}s crossfade...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  [Crossfade] FFmpeg error: {result.stderr[-500:]}"); return _simple_concat(clip_paths, output_path)
    size_mb = Path(output_path).stat().st_size / (1024 * 1024)
    total_dur = sum(durations) - crossfade_dur * (len(clip_paths) - 1)
    print(f"  [Crossfade] Done: {size_mb:.1f} MB | ~{total_dur:.0f}s"); return output_path

def _get_duration(video_path):
    result = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video_path], capture_output=True, text=True, check=True)
    return float(result.stdout.strip())

def _simple_concat(clip_paths, output_path):
    cf = str(Path(output_path).parent / "concat_fallback.txt")
    with open(cf, "w") as f:
        for p in clip_paths: f.write(f"file '{p}'\n")
    subprocess.run(["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", cf, "-c:v", "libx264", "-crf", "18", "-preset", "fast", "-pix_fmt", "yuv420p", output_path], check=True, capture_output=True)
    return output_path


def _submit_job(prompt, num_frames=81, height=832, width=480, upscale=None):
    if upscale is None: upscale = UPSCALE_FACTOR
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}", "Content-Type": "application/json"}
    payload = {"input": {"prompt": prompt, "num_frames": num_frames, "height": height, "width": width, "guidance_scale": 7.5, "fps": 16, "upscale": upscale}}
    resp = requests.post(f"{RUNPOD_API_URL}/run", headers=headers, json=payload, timeout=30)
    resp.raise_for_status(); return resp.json().get("id")

def _poll_result(job_id, timeout=1800, interval=10):
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{RUNPOD_API_URL}/status/{job_id}", headers=headers, timeout=30)
        resp.raise_for_status(); data = resp.json(); status = data.get("status")
        if status == "COMPLETED": return data.get("output", {})
        elif status in ("FAILED", "CANCELLED"): raise RuntimeError(f"RunPod job {job_id} {status}: {data}")
        print(f"  [RunPod] {status}... ({int(deadline - time.time())}s remaining)"); time.sleep(interval)
    raise TimeoutError(f"RunPod job {job_id} timed out after {timeout}s")

def fetch_runpod_clip(prompt, scene_idx, output_path, timeout=1800):
    if not RUNPOD_API_KEY or not RUNPOD_ENDPOINT_ID: raise RuntimeError("RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID must be set")
    print(f"  [RunPod] Submitting: {prompt[:60]}..."); job_id = _submit_job(prompt)
    print(f"  [RunPod] Job {job_id} submitted"); result = _poll_result(job_id, timeout=timeout)
    video_b64 = result.get("video_base64", "")
    if not video_b64: raise RuntimeError(f"RunPod returned empty video for job {job_id}")
    with open(output_path, "wb") as f: f.write(base64.b64decode(video_b64))
    print(f"  [RunPod] Clip saved: {Path(output_path).stat().st_size / 1024:.0f} KB"); return output_path

def fetch_drone_journey_clips(theme_name, output_dir, github_run_number=1):
    """Generate all clips IN PARALLEL -- submit all jobs at once, poll simultaneously."""
    theme = DRONE_THEMES.get(theme_name)
    if not theme:
        import random; theme_name = random.choice(list(DRONE_THEMES.keys())); theme = DRONE_THEMES[theme_name]
    print(f"  [RunPod] Drone journey: {theme_name} ({len(theme)} scenes) -- PARALLEL + {UPSCALE_FACTOR}x UPSCALE")

    jobs = []
    for i, scene in enumerate(theme):
        clip_path = os.path.join(output_dir, f"drone_{i}_{scene['name']}.mp4")
        try:
            print(f"  [RunPod] Submitting [{i+1}/{len(theme)}]: {scene['prompt'][:55]}...")
            job_id = _submit_job(scene["prompt"])
            jobs.append({"job_id": job_id, "scene": scene, "clip_path": clip_path, "index": i, "done": False, "result": None})
            print(f"  [RunPod] Job {job_id} submitted")
        except Exception as e:
            print(f"  [RunPod] Submit failed for {scene['name']}: {e}")
    if not jobs:
        return []
    print(f"  [RunPod] All {len(jobs)} jobs submitted -- polling in parallel...")

    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
    deadline = time.time() + 1800
    while time.time() < deadline:
        all_done = True
        for job in jobs:
            if job["done"]:
                continue
            all_done = False
            try:
                resp = requests.get(f"{RUNPOD_API_URL}/status/{job['job_id']}", headers=headers, timeout=30)
                resp.raise_for_status()
                data = resp.json()
                status = data.get("status")
                if status == "COMPLETED":
                    job["done"] = True
                    job["result"] = data.get("output", {})
                    print(f"  [RunPod] [{job['index']+1}/{len(jobs)}] {job['scene']['name']} COMPLETED")
                elif status in ("FAILED", "CANCELLED"):
                    job["done"] = True
                    print(f"  [RunPod] [{job['index']+1}/{len(jobs)}] {job['scene']['name']} {status}")
            except Exception as e:
                print(f"  [RunPod] Poll error for {job['scene']['name']}: {e}")
        if all_done:
            break
        pending = sum(1 for j in jobs if not j["done"])
        remaining = int(deadline - time.time())
        print(f"  [RunPod] {pending} clips generating... ({remaining}s remaining)")
        time.sleep(10)

    clips = []
    for job in jobs:
        if job["result"] and job["result"].get("video_base64"):
            with open(job["clip_path"], "wb") as f:
                f.write(base64.b64decode(job["result"]["video_base64"]))
            size_kb = Path(job["clip_path"]).stat().st_size / 1024
            print(f"  [RunPod] Saved {job['scene']['name']}: {size_kb:.0f} KB")
            clips.append((job["clip_path"], job["scene"]["name"]))
        elif not job["done"]:
            print(f"  [RunPod] {job['scene']['name']} timed out")
        else:
            print(f"  [RunPod] {job['scene']['name']} failed (no video)")
    print(f"  [RunPod] {len(clips)}/{len(jobs)} clips generated successfully")
    return clips

def render_drone_journey(theme_name, output_dir, output_path, github_run_number=1):
    clips = fetch_drone_journey_clips(theme_name, output_dir, github_run_number)
    if not clips: raise RuntimeError(f"No clips generated for theme '{theme_name}'")
    return assemble_drone_journey([cp for cp, _ in clips], output_path)

def get_theme_for_run(github_run_number):
    return list(DRONE_THEMES.keys())[github_run_number % len(DRONE_THEMES)]

def reset_used_prompts():
    global _used_prompts; _used_prompts = set()
