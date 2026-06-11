"""
MindCore AI -- RunPod AI Video Clips v1.1
==========================================
v1.1: 12 drone journey themes for maximum visual variety.
v1.0: Initial 5 themes.

Replaces pexels_clips.py when RunPod Serverless is active.
Sends prompts to RunPod endpoint, receives AI-generated video clips.

Requires: RUNPOD_ENDPOINT_ID and RUNPOD_API_KEY env vars.
"""

import os, base64, time, requests
from pathlib import Path

RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "")
RUNPOD_ENDPOINT_ID = os.environ.get("RUNPOD_ENDPOINT_ID", "")
RUNPOD_API_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}"

_used_prompts = set()

# -----------------------------------------------
# 12 DRONE JOURNEY THEMES -- one location per video
# Each theme = 5 scenes = ~25 seconds with crossfades
# Themes rotate based on run number
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
    "volcano": [
        {"name": "crater", "prompt": "Cinematic aerial drone slowly approaching a massive volcanic crater at dawn, wisps of steam and smoke rising from vents, dramatic dark landscape with orange glow from below, raw elemental power, photorealistic, 4K"},
        {"name": "lava_flow", "prompt": "Breathtaking drone shot flying low over rivers of glowing orange lava flowing slowly down a dark volcanic slope at night, intense heat shimmer in the air, molten rock meeting ocean creating massive steam clouds, photorealistic, 4K"},
        {"name": "ash_fields", "prompt": "Stunning aerial drone gliding over vast black volcanic ash fields with dramatic cracks and textures, patches of bright green vegetation breaking through, contrast between destruction and rebirth, morning light, photorealistic, 4K"},
        {"name": "steam_vents", "prompt": "Cinematic drone circling geothermal steam vents erupting from dark volcanic rock, golden sunrise backlighting the steam creating dramatic silhouettes and god rays, raw earth energy, photorealistic, 4K"},
        {"name": "volcano_sunset", "prompt": "Breathtaking aerial drone slowly rising above a volcanic island at golden sunset, the entire landscape glowing orange and red, ocean surrounding the island catching fire from the light, epic scale and drama, photorealistic, 4K"},
    ],
    "northern_lights": [
        {"name": "first_glow", "prompt": "Cinematic aerial drone flying low over a frozen arctic landscape at twilight, faint green aurora borealis beginning to shimmer on the horizon, snow covered mountains and frozen lakes reflecting the first colors, magical atmosphere, photorealistic, 4K"},
        {"name": "full_display", "prompt": "Breathtaking drone shot slowly circling above a snow covered valley as vivid green and purple northern lights dance and swirl across the entire sky, ribbons of light reflecting off a frozen lake below, otherworldly beauty, photorealistic, 4K"},
        {"name": "mountains", "prompt": "Stunning aerial drone gliding between snow capped arctic mountain peaks as brilliant green and blue aurora borealis curtains wave overhead, stars visible through gaps in the lights, epic scale and wonder, photorealistic, 4K"},
        {"name": "reflection", "prompt": "Cinematic drone hovering over a perfectly still arctic fjord at night, vivid green and pink northern lights perfectly mirrored in the dark water surface creating a symmetrical dreamscape, silent and mesmerizing, photorealistic, 4K"},
        {"name": "fade", "prompt": "Breathtaking aerial drone slowly rising above the arctic landscape as the northern lights fade into pre-dawn blue, first golden sunlight touching distant mountain peaks, stars disappearing, peaceful transition from night to day, photorealistic, 4K"},
    ],
    "tropical_island": [
        {"name": "discovery", "prompt": "Cinematic aerial drone flying fast over deep blue ocean toward a lush tropical island appearing on the horizon, palm trees and white sand beaches becoming visible, crystal clear lagoon surrounding the island, excitement and discovery, photorealistic, 4K"},
        {"name": "lagoon", "prompt": "Breathtaking drone gliding slowly over a stunning turquoise tropical lagoon, water so clear you can see every detail of the coral reef and white sand below, small colorful fish visible, paradise perfection, photorealistic, 4K"},
        {"name": "palm_beach", "prompt": "Stunning FPV drone racing along a pristine white sand beach lined with tall coconut palm trees swaying in the breeze, crystal clear waves lapping at the shore, tropical flowers along the tree line, warm golden sunlight, photorealistic, 4K"},
        {"name": "jungle", "prompt": "Cinematic aerial drone flying low through lush tropical jungle canopy with exotic flowering trees, a hidden waterfall cascading into a natural emerald pool, mist and butterflies in the air, secret paradise, photorealistic, 4K"},
        {"name": "island_sunset", "prompt": "Breathtaking aerial drone slowly rising high above the tropical island at golden sunset, revealing the entire island surrounded by glowing turquoise water, palm trees silhouetted against blazing orange sky, ultimate peace and beauty, photorealistic, 4K"},
    ],
    "storm_clearing": [
        {"name": "dark_approach", "prompt": "Cinematic aerial drone flying toward massive dark storm clouds building on the horizon over open landscape, lightning flickering inside the clouds, wind bending tall grass below, tension and raw power, dramatic atmosphere, photorealistic, 4K"},
        {"name": "rain_wall", "prompt": "Breathtaking drone shot flying alongside a dramatic wall of heavy rain sweeping across green countryside, dark sky above, bright sunlit landscape ahead of the storm, contrast between darkness and light, epic scale, photorealistic, 4K"},
        {"name": "eye_of_storm", "prompt": "Stunning aerial drone rising through a break in massive storm clouds, dark towering clouds on all sides but a circle of blue sky and golden sunlight directly above, rays of light streaming down, hope emerging from chaos, photorealistic, 4K"},
        {"name": "rainbow", "prompt": "Cinematic drone flying toward a vivid double rainbow arcing across the sky as storm clouds clear, golden sunlight breaking through, rain still falling in the distance catching the light like diamonds, beauty after the storm, photorealistic, 4K"},
        {"name": "clear_sky", "prompt": "Breathtaking aerial drone slowly rising above freshly washed green landscape after a storm, everything glistening with raindrops in warm golden sunlight, blue sky expanding, white clouds retreating to the horizon, renewal and peace, photorealistic, 4K"},
    ],
    "lake_morning": [
        {"name": "mist", "prompt": "Cinematic aerial drone flying low over a glassy calm lake at dawn, thick morning mist hovering just above the water surface, dark pine trees emerging as silhouettes through the fog, mysterious and peaceful atmosphere, photorealistic, 4K"},
        {"name": "reflection", "prompt": "Breathtaking drone shot gliding over perfectly still lake water reflecting mountains and sky like a flawless mirror, not a single ripple, the world doubled in perfect symmetry, morning golden light, serene meditation, photorealistic, 4K"},
        {"name": "shoreline", "prompt": "Stunning aerial drone following a winding lake shoreline at golden hour, smooth river stones and crystal clear shallows, autumn colored trees lining the banks, a wooden dock extending into the calm water, peaceful solitude, photorealistic, 4K"},
        {"name": "birds", "prompt": "Cinematic drone capturing a flock of birds taking flight from a misty lake surface at sunrise, water droplets scattering in golden light, ripples spreading outward in perfect circles, life awakening, freedom and grace, photorealistic, 4K"},
        {"name": "sunrise_lake", "prompt": "Breathtaking aerial drone slowly rising above the lake as golden sunrise floods across the entire landscape, mist burning away to reveal pristine mountain scenery reflected in still water, complete peace and new beginning, photorealistic, 4K"},
    ],
    "waterfall_journey": [
        {"name": "source", "prompt": "Cinematic aerial drone following a mountain stream from its source high in misty peaks, crystal clear water tumbling over mossy rocks through ancient forest, morning light filtering through the canopy, the beginning of a journey, photorealistic, 4K"},
        {"name": "cascade", "prompt": "Breathtaking drone shot flying alongside a series of cascading waterfalls stepping down through lush green jungle, white water crashing over each tier, mist rising and catching rainbow light, raw natural power, photorealistic, 4K"},
        {"name": "main_fall", "prompt": "Stunning cinematic drone slowly rising in front of an enormous single-drop waterfall plunging hundreds of feet into a deep blue pool below, massive mist cloud at the base, surrounding cliffs covered in green vegetation, awe-inspiring scale, photorealistic, 4K"},
        {"name": "pool", "prompt": "Cinematic aerial drone gliding over the crystal clear turquoise pool at the base of a waterfall, sunlight penetrating deep into the water revealing the rocky bottom, fine mist creating a permanent rainbow, paradise hidden in nature, photorealistic, 4K"},
        {"name": "river_out", "prompt": "Breathtaking aerial drone following the river flowing away from the waterfall through a peaceful valley, water gradually calming from white rapids to smooth flow, golden sunset light flooding the valley, journey complete, serenity achieved, photorealistic, 4K"},
    ],
    "countryside": [
        {"name": "dawn_fields", "prompt": "Cinematic aerial drone flying low over endless golden wheat fields at dawn, morning mist hovering between the rows, long dramatic shadows stretching across the landscape, peaceful rural beauty, photorealistic, 4K"},
        {"name": "rolling_hills", "prompt": "Breathtaking drone shot sweeping over lush green rolling hills and patchwork farmland, stone walls and hedgerows dividing the landscape into beautiful patterns, scattered wildflowers, warm golden hour light, English countryside perfection, photorealistic, 4K"},
        {"name": "winding_road", "prompt": "Stunning aerial drone following a narrow winding country road cutting through emerald green hills and valleys, no cars, lined with ancient oak trees, dappled sunlight on the path, invitation to wander, photorealistic, 4K"},
        {"name": "village", "prompt": "Cinematic drone gliding over a picturesque countryside village with stone cottages and church steeple nestled in a green valley, smoke rising gently from chimneys, golden afternoon light, warmth and belonging, photorealistic, 4K"},
        {"name": "sunset_fields", "prompt": "Breathtaking aerial drone slowly rising above the countryside at golden sunset, entire landscape glowing warm orange, long shadows from ancient trees stretching across green fields, birds returning home, perfect peace and contentment, photorealistic, 4K"},
    ],
}


def _submit_job(prompt, num_frames=81, height=832, width=480):
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}", "Content-Type": "application/json"}
    payload = {"input": {"prompt": prompt, "num_frames": num_frames, "height": height, "width": width, "guidance_scale": 7.5, "fps": 16}}
    resp = requests.post(f"{RUNPOD_API_URL}/run", headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json().get("id")


def _poll_result(job_id, timeout=600, interval=10):
    headers = {"Authorization": f"Bearer {RUNPOD_API_KEY}"}
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = requests.get(f"{RUNPOD_API_URL}/status/{job_id}", headers=headers, timeout=30)
        resp.raise_for_status()
        data = resp.json()
        status = data.get("status")
        if status == "COMPLETED": return data.get("output", {})
        elif status in ("FAILED", "CANCELLED"): raise RuntimeError(f"RunPod job {job_id} {status}: {data}")
        print(f"  [RunPod] {status}... ({int(deadline - time.time())}s remaining)")
        time.sleep(interval)
    raise TimeoutError(f"RunPod job {job_id} timed out after {timeout}s")


def fetch_runpod_clip(prompt, scene_idx, output_path, timeout=600):
    if not RUNPOD_API_KEY or not RUNPOD_ENDPOINT_ID:
        raise RuntimeError("RUNPOD_API_KEY and RUNPOD_ENDPOINT_ID must be set")
    print(f"  [RunPod] Submitting: {prompt[:60]}...")
    job_id = _submit_job(prompt)
    print(f"  [RunPod] Job {job_id} submitted")
    result = _poll_result(job_id, timeout=timeout)
    video_b64 = result.get("video_base64", "")
    if not video_b64: raise RuntimeError(f"RunPod returned empty video for job {job_id}")
    with open(output_path, "wb") as f: f.write(base64.b64decode(video_b64))
    size_kb = Path(output_path).stat().st_size / 1024
    print(f"  [RunPod] Clip saved: {size_kb:.0f} KB")
    return output_path


def fetch_drone_journey_clips(theme_name, output_dir, github_run_number=1):
    theme = DRONE_THEMES.get(theme_name)
    if not theme:
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
    themes = list(DRONE_THEMES.keys())
    return themes[github_run_number % len(themes)]


def reset_used_prompts():
    global _used_prompts
    _used_prompts = set()
