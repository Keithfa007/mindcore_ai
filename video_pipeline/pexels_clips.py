"""
MindCore AI -- Pexels B-roll Clip Fetcher v2.1
===============================================
Real human footage + dramatic cinematic atmosphere.
Scene-specific query pools designed for scroll-stopping visuals.

v2.1: Dramatic, inspirational, cinematic queries.
      Mix of human silhouettes + nature metaphors + atmospheric scenes.
      Designed for emotional resonance, not generic stock footage.

Key insight: best mental health B-roll isn't always people.
Storm clouds = inner turmoil. Sunrise = hope. Ocean = overwhelm.
The footage matches the FEELING, not the literal subject.
"""

import os
import random
from pathlib import Path

import requests

PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"
PEXELS_API_KEY   = os.environ.get("PEXELS_API_KEY", "")

# ---------------------------------------------------------------------------
# FEMALE -- dramatic, emotional, cinematic
# ---------------------------------------------------------------------------

FEMALE_SCENE_QUERIES = {
    # HOOK -- scroll-stopping, dramatic, raw
    "hook": [
        "woman silhouette sunset dramatic",
        "rain window close up night",
        "woman underwater swimming dark",
        "ocean waves storm dramatic",
        "woman walking rain city night",
        "crying face close up tears",
        "storm clouds dramatic sky timelapse",
        "woman rooftop city night wind",
        "dark ocean waves crashing rocks",
        "woman fog alone mysterious",
        "lightning storm night dramatic",
        "empty road fog morning dramatic",
        "woman hair wind dramatic portrait",
        "waterfall dramatic power nature",
        "woman standing cliff ocean",
    ],

    # PROBLEM -- weight, isolation, atmospheric tension
    "problem": [
        "woman alone window rain night",
        "dark room single candle flame",
        "empty street night rain reflections",
        "woman reflection dark mirror",
        "fog forest morning mysterious",
        "hands clasped tight close up",
        "rain drops glass close up slow",
        "shadows light wall dramatic",
        "woman phone dark bedroom night",
        "rain street lights city night bokeh",
        "smoke dark room atmospheric",
        "woman silhouette window dark",
        "clock ticking close up",
        "empty chair room sunlight dust",
        "person walking alone fog",
    ],

    # STORY -- transition, shift, hope beginning to emerge
    "story": [
        "sunrise dramatic clouds timelapse",
        "light breaking through storm clouds",
        "woman walking toward light",
        "birds flying freedom sky",
        "opening curtains morning sunlight",
        "forest sunlight rays trees",
        "calm water reflection morning",
        "clouds clearing blue sky timelapse",
        "woman deep breath eyes closed",
        "morning dew nature close up",
        "river flowing calm peaceful",
        "butterfly wings close up",
        "woman looking up sky hopeful",
        "candle lighting dark room",
        "dawn horizon ocean",
    ],

    # CTA -- resolution, warmth, inspiration, beauty
    "solution_cta": [
        "golden hour woman nature peaceful",
        "woman smiling sunrise morning",
        "ocean sunset calm peaceful beautiful",
        "flowers blooming timelapse spring",
        "mountain top view breathtaking",
        "peaceful nature morning golden light",
        "woman happy free outdoor wind",
        "sunrise beach golden waves",
        "garden morning sunlight beautiful",
        "woman laughing genuine happy outdoor",
        "mountain lake reflection calm",
        "cherry blossom spring beautiful",
        "woman arms open freedom sunset",
        "golden field wheat sunset",
        "stars night sky peaceful",
    ],
}

# ---------------------------------------------------------------------------
# MALE -- dramatic, powerful, raw
# ---------------------------------------------------------------------------

MALE_SCENE_QUERIES = {
    # HOOK -- powerful, dramatic, cinematic
    "hook": [
        "man silhouette sunset dramatic",
        "rain city night dramatic cinematic",
        "man walking alone empty road",
        "ocean storm waves crashing dramatic",
        "man rooftop city skyline night",
        "lightning storm night sky dramatic",
        "empty highway desert dramatic sky",
        "man face shadow dramatic portrait",
        "storm clouds building dramatic timelapse",
        "dark alley night rain atmospheric",
        "man standing cliff edge ocean",
        "fog mountain man alone",
        "waves crashing rocks dramatic power",
        "man rain standing still",
        "empty stadium alone dramatic",
    ],

    # PROBLEM -- weight, isolation, pressure
    "problem": [
        "man alone dark room shadow",
        "rain drops window close up",
        "empty office night dark",
        "man hands face stressed close",
        "fog highway morning dramatic",
        "abandoned building dark atmospheric",
        "dark clouds heavy rain",
        "man sitting alone bench park",
        "shadows dark room atmospheric",
        "night city walking alone rain",
        "man steering wheel car night",
        "smoke rising dark atmospheric",
        "clock hands moving close up",
        "man silhouette window night city",
        "empty hallway dark dramatic",
    ],

    # STORY -- shift, resolve forming, determination
    "story": [
        "sunrise dramatic clouds horizon",
        "light breaking through dark clouds",
        "man walking toward morning light",
        "ocean waves calming dawn",
        "forest morning mist sunlight rays",
        "dawn breaking horizon dramatic",
        "man deep breath outdoor",
        "mountains fog clearing sunrise",
        "sky clearing after storm timelapse",
        "eagle flying soaring mountains",
        "river flowing mountain calm",
        "man looking up sky clouds",
        "first light morning window",
        "road stretching forward sunrise",
        "campfire night flames close up",
    ],

    # CTA -- strength, resolution, earned peace
    "solution_cta": [
        "golden hour man nature mountain",
        "man confident sunrise outdoor",
        "mountain summit breathtaking view",
        "ocean sunset peaceful dramatic",
        "man happy outdoors nature",
        "warm sunshine morning golden",
        "nature mountain peaceful calm",
        "sunrise mountain peak dramatic",
        "man smiling genuine outdoor",
        "beach sunrise golden waves",
        "man walking forward confident road",
        "lake reflection mountain calm",
        "stars milky way night peaceful",
        "man arms spread mountain top",
        "golden field sunset dramatic",
    ],
}

# Fallback queries -- simple, reliable
FALLBACK_QUERIES = {
    "hook":         {"woman": "dramatic storm ocean", "man": "dramatic storm lightning"},
    "problem":      {"woman": "rain window night", "man": "dark room alone"},
    "story":        {"woman": "sunrise clouds hope", "man": "sunrise mountain morning"},
    "solution_cta": {"woman": "golden hour nature", "man": "mountain summit sunrise"},
}


def search_pexels_videos(query: str, orientation: str = "portrait", per_page: int = 15):
    """Search Pexels for videos. Returns list of video objects."""
    if not PEXELS_API_KEY:
        return []
    headers = {"Authorization": PEXELS_API_KEY}
    params  = {
        "query":       query,
        "orientation": orientation,
        "per_page":    per_page,
        "size":        "medium",
    }
    try:
        resp = requests.get(PEXELS_VIDEO_URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        videos = resp.json().get("videos", [])
        # If portrait returns nothing, try without orientation filter
        if not videos:
            params.pop("orientation", None)
            resp = requests.get(PEXELS_VIDEO_URL, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            videos = resp.json().get("videos", [])
        return videos
    except Exception as e:
        print(f"  Pexels search failed ({e})")
        return []


def get_best_video_file(video: dict):
    """Return the best quality video file, preferring portrait HD."""
    files = video.get("video_files", [])
    # Prefer portrait orientation
    portrait = [f for f in files if f.get("width", 1) < f.get("height", 1)]
    pool = portrait if portrait else files
    # Sort by resolution descending -- prefer HD
    pool.sort(key=lambda f: f.get("height", 0), reverse=True)
    return pool[0] if pool else None


def download_pexels_clip(video_url: str, output_path: str) -> str:
    """Download a Pexels video clip. Returns output_path."""
    resp = requests.get(video_url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65_536):
            if chunk:
                f.write(chunk)
    size_kb = Path(output_path).stat().st_size / 1024
    print(f"  Pexels: downloaded {size_kb:.0f} KB")
    return output_path


def fetch_pexels_clip_for_scene(
    scene_name: str,
    scene_idx:  int,
    output_path: str,
    github_run_number: int = 1,
    gender: str = "woman",
) -> str | None:
    """Fetch a dramatic Pexels clip for a specific scene.

    Selects query using (github_run_number + scene_idx) % pool_size.
    Falls back to simpler queries if primary returns nothing.
    """
    gender_key = "woman" if gender == "woman" else "man"
    queries    = FEMALE_SCENE_QUERIES if gender == "woman" else MALE_SCENE_QUERIES
    pool       = queries.get(scene_name, queries["problem"])
    query_idx  = (github_run_number + scene_idx) % len(pool)
    query      = pool[query_idx]

    print(f"  [Pexels] {scene_name.upper()} -- '{query}'")
    videos = search_pexels_videos(query)

    # Fallback if no results
    if not videos:
        fallback = FALLBACK_QUERIES.get(scene_name, {}).get(gender_key, "dramatic cinematic")
        print(f"  [Pexels] No results -- fallback: '{fallback}'")
        videos = search_pexels_videos(fallback)

    if not videos:
        print(f"  [Pexels] No results for {scene_name} -- skipping")
        return None

    # Pick clip -- rotate by run number + scene_idx for variety
    video     = videos[(github_run_number + scene_idx) % len(videos)]
    best_file = get_best_video_file(video)

    if not best_file:
        print(f"  [Pexels] No suitable file found for {scene_name}")
        return None

    try:
        return download_pexels_clip(best_file["link"], output_path)
    except Exception as e:
        print(f"  [Pexels] Download failed for {scene_name} ({e})")
        return None
