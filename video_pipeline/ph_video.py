#!/usr/bin/env python3
"""
Product Hunt video generator for MindCore AI.
Same pattern as heygen_pipeline.py — Python handles the API
so URL query params never touch bash.
"""

import os, time, json, requests

HEYGEN_API_KEY = os.environ["HEYGEN_API_KEY"]
AVATAR_ID      = "7f98b80999e74f2dbd15b7585c972ca1"
VOICE_ID       = "6be73833ef9a4eb0aeee399b8fe9d62b"
OUTPUT_PATH    = "video_pipeline/output/ph_video.mp4"

SCRIPT = (
    "My name is K.F. "
    "For a long time, I worked long hours, came home drained, and had nobody to really talk to. "
    "Not because I didn't have people around me. "
    "But because opening up felt impossible. "
    "So like a lot of people, I found other ways to cope. "
    "Alcohol. Substances. Anything to quiet the noise. "
    "The problem is those things don't actually help. "
    "They just delay the conversation you need to have with yourself. "
    "I built MindCore AI because I know that feeling. And I know I'm not the only one. "
    "MindCore AI is a private AI mental health companion. "
    "You hold a button and speak. It listens. "
    "It responds in a calm human voice. "
    "It remembers what you've shared. It tracks how you feel over time. "
    "No appointments. No judgment. No waiting rooms. "
    "Whether you're struggling with anxiety, addiction, low mood, "
    "or just the weight of everyday life, it's there. "
    "At three in the morning when everything feels heavy. "
    "On your lunch break when you need five minutes to breathe. "
    "I built this because nobody should feel like "
    "the only way through is a bottle or a substance. "
    "MindCore AI is live on Android now. Come and try it."
)

HEADERS = {
    "X-Api-Key": HEYGEN_API_KEY,
    "Content-Type": "application/json",
}


def generate_video():
    print("\U0001f3ac Submitting video to HeyGen...")
    resp = requests.post(
        "https://api.heygen.com/v2/video/generate",
        headers=HEADERS,
        json={
            "video_inputs": [{
                "character": {
                    "type": "avatar",
                    "avatar_id": AVATAR_ID,
                    "avatar_style": "normal",
                },
                "voice": {
                    "type": "text",
                    "input_text": SCRIPT,
                    "voice_id": VOICE_ID,
                    "speed": 1.0,
                },
            }],
            "dimension": {"width": 1280, "height": 720},
        },
    )
    data = resp.json()
    print(json.dumps(data, indent=2))
    video_id = data["data"]["video_id"]
    print(f"Video ID: {video_id}")
    return video_id


def poll_video(video_id, max_attempts=60, interval=30):
    print(f"\u23f3 Polling every {interval}s (max {max_attempts} attempts)...")
    for attempt in range(1, max_attempts + 1):
        time.sleep(interval)
        resp = requests.get(
            f"https://api.heygen.com/v1/video_status.get?video_id={video_id}",
            headers=HEADERS,
        )
        data  = resp.json()
        status = data["data"]["status"]
        print(f"  Attempt {attempt:>2}: {status}")
        if status == "completed":
            url = data["data"]["video_url"]
            print(f"\n\u2705 Video ready")
            return url
        if status == "failed":
            raise RuntimeError(f"HeyGen reported failure: {json.dumps(data, indent=2)}")
    raise TimeoutError("Video not ready after maximum polling attempts")


def download_video(url):
    print("\u2b07\ufe0f  Downloading...")
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(OUTPUT_PATH, "wb") as f:
            for chunk in r.iter_content(chunk_size=65536):
                f.write(chunk)
    mb = os.path.getsize(OUTPUT_PATH) / 1024 / 1024
    print(f"\u2705 Saved: {OUTPUT_PATH} ({mb:.1f} MB)")


if __name__ == "__main__":
    vid_id  = generate_video()
    vid_url = poll_video(vid_id)
    download_video(vid_url)
    print("\n\U0001f3a5 Product Hunt video is ready in video_pipeline/output/ph_video.mp4")
