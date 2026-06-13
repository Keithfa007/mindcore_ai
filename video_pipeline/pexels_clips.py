"""
MindCore AI -- Pexels B-roll Clip Fetcher v3.0
===============================================
v3.0: Queries rewritten for emotional specificity. More intimate human
      footage, less generic landscape. Queries designed to mirror the
      viewer's internal state (hook/problem) then open up (story/cta).
v2.2: Deduplication -- tracks used video IDs within a run.
v2.1: Dramatic cinematic queries, nature metaphors.
"""

import os
import random
from pathlib import Path
import requests

PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"
PEXELS_API_KEY   = os.environ.get("PEXELS_API_KEY", "")

_used_video_ids = set()

FEMALE_SCENE_QUERIES = {
    "hook": [
        "woman alone dark room phone glow",
        "rain window night close up drops",
        "woman silhouette window grey sky",
        "hands gripping coffee cup close dark",
        "woman staring mirror reflection tired",
        "empty unmade bed morning light alone",
        "woman eyes closed tight breathing",
        "candle flame dark room single light",
        "rain streaking glass blurred city night",
        "woman sitting floor back against wall",
        "shadow face half lit dramatic dark",
        "clock ticking night close up insomnia",
        "woman head in hands sitting alone",
        "dark hallway single doorway light",
        "tears close up face emotional woman",
    ],
    "problem": [
        "woman alone window rain grey watching",
        "empty chair sunlight dust quiet room",
        "woman phone scrolling bed night blue",
        "fog morning person walking alone path",
        "woman reflection glass dark moody",
        "rain drops puddle grey street alone",
        "hands clasped lap nervous close up",
        "woman staring out car window rain",
        "single lamp dark room shadows wall",
        "empty kitchen morning coffee alone still",
        "grey sky bare trees winter mood",
        "woman leaning wall eyes closed tired",
        "rain street night city lights blurred",
        "smoke wisps dark atmospheric moody",
        "person sitting alone bench park grey",
    ],
    "story": [
        "sunrise clouds first light breaking",
        "woman deep breath eyes closed calm",
        "light through curtains morning soft",
        "hands opening palms upward releasing",
        "woman walking toward sunlight path",
        "morning dew nature close up fresh",
        "clouds parting sunlight rays through",
        "woman looking up sky peaceful hope",
        "calm water reflection morning still",
        "opening window morning fresh air light",
        "birds flying dawn sky freedom",
        "forest sunlight rays through trees mist",
        "woman smiling softly alone genuine",
        "flower blooming close up timelapse",
        "gentle river flowing calm peaceful",
    ],
    "solution_cta": [
        "golden hour woman peaceful nature warm",
        "woman smiling sunrise morning genuine",
        "ocean sunset calm golden beautiful",
        "woman walking beach golden light free",
        "warm sunlight face peaceful eyes closed",
        "flowers garden morning golden soft",
        "woman laughing genuine happy sunlight",
        "mountain view sunrise breathtaking vast",
        "peaceful lake morning golden reflection",
        "woman arms open wind sunset freedom",
        "cherry blossom spring soft beautiful",
        "golden field sunset warm peaceful",
        "stars night sky peaceful vast calm",
        "woman journaling morning light peaceful",
        "sunrise beach waves golden warm sand",
    ],
}

MALE_SCENE_QUERIES = {
    "hook": [
        "man alone dark room sitting shadow",
        "rain window night close up moody",
        "man standing still city night alone",
        "hands gripping steering wheel night close",
        "man silhouette window city lights dark",
        "empty office chair night screen glow",
        "man face shadow half lit dramatic",
        "dark alley rain night atmospheric",
        "man looking down floor shadow weight",
        "storm clouds building heavy dark sky",
        "man rooftop city night wind alone",
        "whiskey glass bar dark alone close",
        "man bed awake phone glow night",
        "fog road car headlights alone dark",
        "man rain standing still not moving",
    ],
    "problem": [
        "man alone park bench grey sky",
        "empty room single chair sunlight dust",
        "man hands face stressed exhausted close",
        "rain highway driving alone night dark",
        "man reflection dark window staring",
        "abandoned building dark shadows lonely",
        "heavy coat man dark rain street",
        "man sitting car parked alone night",
        "clock ticking office night working late",
        "dark clouds heavy rain approaching",
        "man walking alone empty street fog",
        "gym bag floor untouched dark room",
        "man phone dark bedroom scrolling night",
        "shadows wall dark room single light",
        "empty hallway dark office night alone",
    ],
    "story": [
        "sunrise dramatic horizon light breaking",
        "man walking toward morning light path",
        "ocean waves calming dawn peaceful shore",
        "forest morning mist sunlight rays trees",
        "man deep breath outdoor eyes closed",
        "mountains fog clearing sunrise revealing",
        "sky clearing after storm clouds parting",
        "road stretching forward sunrise ahead",
        "man looking up sky clouds opening",
        "first light morning through window warm",
        "river flowing calm mountain peaceful",
        "eagle soaring mountains freedom scale",
        "dawn horizon ocean golden first light",
        "campfire flames night warm close calm",
        "man running morning road determined",
    ],
    "solution_cta": [
        "golden hour man nature mountain warm",
        "man confident sunrise outdoor forward",
        "mountain summit view breathtaking vast",
        "ocean sunset peaceful golden dramatic",
        "man walking forward road sunrise ahead",
        "warm sunshine morning golden light face",
        "man smiling genuine outdoor relaxed",
        "sunrise mountain peak dramatic golden",
        "lake reflection mountain calm still dawn",
        "stars milky way night peaceful vast",
        "man running sunrise beach determined",
        "golden field wheat sunset warm vast",
        "man looking horizon sunset confident",
        "beach sunrise golden waves warm sand",
        "man arms spread mountain top freedom",
    ],
}

FALLBACK_QUERIES = {
    "hook":         {"woman": "woman alone dark room", "man": "man alone dark room shadow"},
    "problem":      {"woman": "rain window night lonely", "man": "man sitting alone night"},
    "story":        {"woman": "sunrise clouds morning hope", "man": "sunrise mountain morning light"},
    "solution_cta": {"woman": "golden hour woman nature", "man": "mountain summit sunrise golden"},
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

    Deduplication -- tracks used video IDs across all scenes in a run.
    Tries up to 3 different queries before falling back.
    Never reuses a clip unless absolutely no alternatives exist.
    """
    global _used_video_ids

    gender_key = "woman" if gender == "woman" else "man"
    queries = FEMALE_SCENE_QUERIES if gender == "woman" else MALE_SCENE_QUERIES
    pool = queries.get(scene_name, queries["problem"])

    for attempt in range(3):
        query_idx = (github_run_number + scene_idx + attempt) % len(pool)
        query = pool[query_idx]

        label = f" (retry {attempt+1})" if attempt else ""
        print(f"  [Pexels] {scene_name.upper()} -- '{query}'{label}")
        videos = search_pexels_videos(query)
        if not videos: continue

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

    fallback = FALLBACK_QUERIES.get(scene_name, {}).get(gender_key, "dramatic cinematic")
    print(f"  [Pexels] Primary queries exhausted -- fallback: '{fallback}'")
    videos = search_pexels_videos(fallback)
    if not videos:
        print(f"  [Pexels] No results for {scene_name} -- skipping"); return None

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
