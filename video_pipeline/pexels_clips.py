"""
MindCore AI -- Pexels B-roll Clip Fetcher v2.0
===============================================
Replaces fal.ai for video clip generation.
Real human footage = better engagement, zero cost vs $1.25/video.

v2.0: Scene-specific query pools (10 per scene per gender).
      Rotates using GITHUB_RUN_NUMBER for variety across runs.
      Portrait-first filtering, HD quality preference.
"""

import os
import random
from pathlib import Path

import requests

PEXELS_VIDEO_URL = "https://api.pexels.com/videos/search"
PEXELS_API_KEY   = os.environ.get("PEXELS_API_KEY", "")

# ---------------------------------------------------------------------------
# Scene query pools -- 10 per scene per gender
# Rotates via (GITHUB_RUN_NUMBER + scene_idx) % 10
# Short, specific queries that reliably return portrait Pexels results
# ---------------------------------------------------------------------------

FEMALE_SCENE_QUERIES = {
    "hook": [
        "woman sad alone night",
        "woman crying emotional close",
        "woman window night alone",
        "woman tired depressed bedroom",
        "woman lonely dark room",
        "woman emotional tears face",
        "woman overwhelmed stressed",
        "woman anxious worried home",
        "woman exhausted sitting",
        "woman alone thinking night",
    ],
    "problem": [
        "woman sitting floor sad",
        "woman crying bedroom alone",
        "woman sad window rain",
        "woman stressed anxious home",
        "woman alone dark thinking",
        "woman depression lonely",
        "woman tired night city",
        "woman sad face close",
        "woman alone night",
        "woman emotional breakdown",
    ],
    "story": [
        "woman thinking window light",
        "woman calm reflection quiet",
        "woman introspective moment",
        "woman peaceful quiet sitting",
        "woman breathing calm",
        "woman thoughtful expression",
        "woman quiet morning light",
        "woman contemplating window",
        "woman mindful peaceful",
        "woman hopeful looking",
    ],
    "solution_cta": [
        "woman happy morning light",
        "woman sunrise hope outdoor",
        "woman smiling natural light",
        "woman peaceful morning coffee",
        "woman calm joy",
        "woman positive morning",
        "woman confident empowered",
        "woman relief outdoor",
        "woman joyful laughing",
        "woman morning nature calm",
    ],
}

MALE_SCENE_QUERIES = {
    "hook": [
        "man alone night thinking",
        "man sad sitting window",
        "man tired stressed face",
        "man lonely dark room",
        "man emotional serious",
        "man exhausted alone",
        "man worried anxious",
        "man sitting alone dark",
        "man night city alone",
        "man depressed thinking",
    ],
    "problem": [
        "man sitting alone bedroom",
        "man stressed work night",
        "man sad night window",
        "man alone thinking dark",
        "man depression lonely",
        "man tired face close",
        "man anxious worried home",
        "man alone park bench",
        "man emotional face",
        "man night alone city",
    ],
    "story": [
        "man thinking window light",
        "man calm reflection quiet",
        "man introspective quiet",
        "man peaceful sitting",
        "man breathing calm",
        "man thoughtful expression",
        "man hopeful looking forward",
        "man contemplating morning",
        "man mindful quiet",
        "man sunrise outdoor",
    ],
    "solution_cta": [
        "man happy morning outdoor",
        "man confident sunrise",
        "man peaceful morning",
        "man positive outdoor",
        "man calm joy morning",
        "man successful confident",
        "man relief outdoor",
        "man joyful nature",
        "man morning light calm",
        "man empowered walking",
    ],
}

# Fallback queries if main query returns no results
FALLBACK_QUERIES = {
    "hook":         {"woman": "woman sad", "man": "man sad"},
    "problem":      {"woman": "woman alone", "man": "man alone"},
    "story":        {"woman": "woman thinking", "man": "man thinking"},
    "solution_cta": {"woman": "woman happy", "man": "man happy"},
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
        return resp.json().get("videos", [])
    except Exception as e:
        print(f"  Pexels search failed ({e})")
        return []


def get_best_video_file(video: dict):
    """Return the best quality portrait video file from a Pexels video object."""
    files = video.get("video_files", [])
    # Prefer portrait orientation
    portrait = [f for f in files if f.get("width", 1) < f.get("height", 1)]
    pool = portrait if portrait else files
    # Sort by resolution descending -- prefer HD
    pool.sort(key=lambda f: f.get("height", 0), reverse=True)
    return pool[0] if pool else None


def download_pexels_clip(video_url: str, output_path: str) -> str:
    """Download a Pexels video clip to output_path. Returns output_path."""
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
    """Fetch a Pexels clip for a specific scene. Returns output_path or None.

    Selects query using (github_run_number + scene_idx) % 10 for variety.
    Falls back to simpler queries if primary returns no results.
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
        fallback = FALLBACK_QUERIES.get(scene_name, {}).get(gender_key, gender_key)
        print(f"  [Pexels] No results -- fallback: '{fallback}'")
        videos = search_pexels_videos(fallback)

    if not videos:
        print(f"  [Pexels] No results for {scene_name} -- skipping")
        return None

    # Pick clip -- rotate by run number for variety within results
    video     = videos[github_run_number % len(videos)]
    best_file = get_best_video_file(video)

    if not best_file:
        print(f"  [Pexels] No suitable file found for {scene_name}")
        return None

    try:
        return download_pexels_clip(best_file["link"], output_path)
    except Exception as e:
        print(f"  [Pexels] Download failed for {scene_name} ({e})")
        return None
