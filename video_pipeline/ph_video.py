#!/usr/bin/env python3
"""
Product Hunt video generator for MindCore AI.
Uses the same v3/videos endpoint + motion config as heygen_pipeline.py.
Outputs a download link to the logs and saves it as a text file artifact.
"""

import os, time, json, requests
from pathlib import Path

HEYGEN_API_KEY = os.environ["HEYGEN_API_KEY"]

AVATAR_ID = "7f98b80999e74f2dbd15b7585c972ca1"
VOICE_ID  = "6be73833ef9a4eb0aeee399b8fe9d62b"

HEYGEN_V3_URL     = "https://api.heygen.com/v3/videos"
HEYGEN_STATUS_URL = "https://api.heygen.com/v1/video_status.get"

OUTPUT_DIR  = Path("video_pipeline/output")
LINK_FILE   = OUTPUT_DIR / "ph_video_link.txt"

POLL_INTERVAL = 15
VIDEO_TIMEOUT = 1200

SCRIPT = (
    "My name is K.F. "
    "For a long time, I worked long hours, came home drained, "
    "and had nobody to really talk to. "
    "Not because I didn't have people around me. "
    "But because opening up felt impossible. "
    "So like a lot of people, I found other ways to cope. "
    "Alcohol. Substances. Anything to quiet the noise. "
    "The problem is those things don't actually help. "
    "They just delay the conversation you need to have with yourself. "
    "I built MindCore AI because I know that feeling. "
    "And I know I'm not the only one. "
    "MindCore AI is a private AI mental health companion. "
    "You hold a button and speak. It listens. "
    "It responds in a calm human voice. "
    "It remembers what you've shared. "
    "It tracks how you feel over time. "
    "No appointments. No judgment. No waiting rooms. "
    "Whether you're struggling with anxiety, addiction, low mood, "
    "or just the weight of everyday life, it's there. "
    "At three in the morning when everything feels heavy. "
    "On your lunch break when you need five minutes to breathe. "
    "I built this because nobody should feel like "
    "the only way through is a bottle or a substance. "
    "MindCore AI is live on Android now. Come and try it."
)

H = {"X-Api-Key": HEYGEN_API_KEY, "Content-Type": "application/json"}


def submit_video() -> str:
    print("Submitting to HeyGen v3/videos...")
    payload = {
        "type":               "avatar",
        "avatar_id":          AVATAR_ID,
        "voice_id":           VOICE_ID,
        "script":             SCRIPT,
        "motion_prompt":      (
            "Gesturing naturally with hands while presenting. "
            "Warm eye contact. Nodding gently on emotional points. "
            "Open palm gestures when sharing insights. "
            "Grounded upper body movement throughout."
        ),
        "expressiveness":     "high",
        "talking_style":      "expressive",
        "use_avatar_iv_model": True,
        "super_resolution":   True,
        "dimension":          {"width": 1080, "height": 1920},
        "aspect_ratio":       "9:16",
    }
    resp = requests.post(HEYGEN_V3_URL, headers=H, json=payload, timeout=30)
    print(f"Response [{resp.status_code}]: {resp.text[:300]}")
    if not resp.ok:
        raise RuntimeError(f"HeyGen v3/videos failed {resp.status_code}: {resp.text}")
    data = resp.json()
    video_id = (
        data.get("data", {}).get("video_id")
        or data.get("video_id")
        or data.get("data", {}).get("id")
        or data.get("id")
    )
    if not video_id:
        raise RuntimeError(f"No video_id in response: {data}")
    print(f"Submitted - video_id: {video_id}")
    return video_id


def poll_video(video_id: str) -> str:
    print(f"Polling every {POLL_INTERVAL}s (max {VIDEO_TIMEOUT}s)...")
    deadline = time.time() + VIDEO_TIMEOUT
    while time.time() < deadline:
        time.sleep(POLL_INTERVAL)
        resp = requests.get(
            HEYGEN_STATUS_URL,
            headers={"X-Api-Key": HEYGEN_API_KEY},
            params={"video_id": video_id},
            timeout=30,
        )
        resp.raise_for_status()
        data   = resp.json().get("data", {})
        status = data.get("status", "unknown")
        elapsed = int(time.time() - (deadline - VIDEO_TIMEOUT))
        print(f"  [{elapsed:>4}s] status={status}")
        if status == "completed":
            url = data.get("video_url")
            if not url:
                raise RuntimeError(f"Completed but no video_url: {data}")
            return url
        if status in ("failed", "error"):
            raise RuntimeError(f"HeyGen render failed: {data}")
    raise TimeoutError(f"Video not ready after {VIDEO_TIMEOUT}s")


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    vid_id  = submit_video()
    vid_url = poll_video(vid_id)

    # Save link to a tiny text file (the artifact to download)
    LINK_FILE.write_text(vid_url)

    # Print clearly in the logs too
    print()
    print("=" * 60)
    print("VIDEO DOWNLOAD LINK:")
    print(vid_url)
    print("=" * 60)
    print("Link also saved in the ph_video_link artifact.")
