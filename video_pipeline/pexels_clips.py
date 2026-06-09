"""
MindCore AI -- Pexels B-roll Clip Fetcher v2.2
===============================================
v2.2: Deduplication -- tracks used video IDs within a run.
      No clip repeats within the same video. Tries up to 3 different
      queries per scene before falling back. Logs unique clip count.
v2.1: Dramatic cinematic queries, nature metaphors.
"""

import os
import random
from pathlib import Path
import requests

PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"
PEXELS_API_KEY   = os.environ.get("PEXELS_API_KEY", "")

# Track used video IDs within a single pipeline run -- prevents duplicate clips
_used_video_ids = set()

FEMALE_SCENE_QUERIES = {
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

MALE_SCENE_QUERIES = {
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

FALLBACK_QUERIES = {
    "hook":         {"woman": "dramatic storm ocean", "man": "dramatic storm lightning"},
    "problem":      {"woman": "rain window night", "man": "dark room alone"},
    "story":        {"woman": "sunrise clouds hope", "man": "sunrise mountain morning"},
    "solution_cta": {"woman": "golden hour nature", "man": "mountain summit sunrise"},
}


def search_pexels_videos(query, orientation="portrait", per_page=15):
    if not PEXELS_API_KEY: return []
    headers = {"Authorization": PEXELS_API_KEY}
    params = {"query": query, "orientation": orientation, "per_page": per_page, "size": "medium"}
    try:
        resp = requests.get(PEXELS_VIDEO_URL, headers=headers, params=params, timeout=30)
        resp.raise_for_status()
        videos = resp.json().get("videos", [])
        if not videos:
            params.pop("orientation", None)
            resp = requests.get(PEXELS_VIDEO_URL, headers=headers, params=params, timeout=30)
            resp.raise_for_status()
            videos = resp.json().get("videos", [])
        return videos
    except Exception as e:
        print(f"  Pexels search failed ({e})"); return []


def get_best_video_file(video):
    files = video.get("video_files", [])
    portrait = [f for f in files if f.get("width", 1) < f.get("height", 1)]
    pool = portrait if portrait else files
    pool.sort(key=lambda f: f.get("height", 0), reverse=True)
    return pool[0] if pool else None


def download_pexels_clip(video_url, output_path):
    resp = requests.get(video_url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65_536):
            if chunk: f.write(chunk)
    print(f"  Pexels: downloaded {Path(output_path).stat().st_size / 1024:.0f} KB")
    return output_path


def fetch_pexels_clip_for_scene(scene_name, scene_idx, output_path, github_run_number=1, gender="woman"):
    """Fetch a UNIQUE Pexels clip for a scene.

    v2.2: Deduplication -- tracks used video IDs across all scenes in a run.
    Tries up to 3 different queries before falling back.
    Never reuses a clip unless absolutely no alternatives exist.
    """
    global _used_video_ids

    gender_key = "woman" if gender == "woman" else "man"
    queries = FEMALE_SCENE_QUERIES if gender == "woman" else MALE_SCENE_QUERIES
    pool = queries.get(scene_name, queries["problem"])

    # Try up to 3 different queries to find a unique clip
    for attempt in range(3):
        query_idx = (github_run_number + scene_idx + attempt) % len(pool)
        query = pool[query_idx]

        label = f" (retry {attempt+1})" if attempt else ""
        print(f"  [Pexels] {scene_name.upper()} -- '{query}'{label}")
        videos = search_pexels_videos(query)
        if not videos: continue

        # Filter out already-used videos
        unique = [v for v in videos if v.get("id") not in _used_video_ids]
        if not unique: continue

        video = unique[(github_run_number + scene_idx) % len(unique)]
        best = get_best_video_file(video)
        if not best: continue

        try:
            result = download_pexels_clip(best["link"], output_path)
            _used_video_ids.add(video["id"])
            print(f"  [Pexels] Video ID {video['id']} -- unique ({len(_used_video_ids)} clips total)")
            return result
        except Exception as e:
            print(f"  [Pexels] Download failed ({e})"); continue

    # Fallback: try a completely different query
    fallback = FALLBACK_QUERIES.get(scene_name, {}).get(gender_key, "dramatic cinematic")
    print(f"  [Pexels] Primary queries exhausted -- fallback: '{fallback}'")
    videos = search_pexels_videos(fallback)
    if not videos:
        print(f"  [Pexels] No results for {scene_name} -- skipping"); return None

    # Prefer unique, accept duplicate only as last resort
    unique = [v for v in videos if v.get("id") not in _used_video_ids]
    pick = unique if unique else videos
    video = pick[(github_run_number + scene_idx) % len(pick)]
    best = get_best_video_file(video)
    if not best: return None

    try:
        result = download_pexels_clip(best["link"], output_path)
        _used_video_ids.add(video["id"])
        if not unique: print(f"  [Pexels] WARNING: duplicate clip (no unique alternatives)")
        return result
    except Exception as e:
        print(f"  [Pexels] Fallback failed ({e})"); return None


def reset_used_videos():
    """Call at the start of a new pipeline run to clear the dedup tracker."""
    global _used_video_ids
    _used_video_ids = set()
