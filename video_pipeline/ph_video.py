#!/usr/bin/env python3
import os, time, json, requests

HEYGEN_API_KEY = os.environ["HEYGEN_API_KEY"]
AVATAR_ID = "7f98b80999e74f2dbd15b7585c972ca1"
VOICE_ID  = "6be73833ef9a4eb0aeee399b8fe9d62b"
OUTPUT    = "video_pipeline/output/ph_video.mp4"

SCRIPT = (
    "My name is K.F. For a long time, I worked long hours, came home drained, "
    "and had nobody to really talk to. Not because I didn't have people around me. "
    "But because opening up felt impossible. So like a lot of people, I found other ways to cope. "
    "Alcohol. Substances. Anything to quiet the noise. "
    "The problem is those things don't actually help. "
    "They just delay the conversation you need to have with yourself. "
    "I built MindCore AI because I know that feeling. And I know I'm not the only one. "
    "MindCore AI is a private AI mental health companion. You hold a button and speak. "
    "It listens. It responds in a calm human voice. It remembers what you've shared. "
    "It tracks how you feel over time. No appointments. No judgment. No waiting rooms. "
    "Whether you're struggling with anxiety, addiction, low mood, or just the weight of everyday life, "
    "it's there. At three in the morning when everything feels heavy. "
    "On your lunch break when you need five minutes to breathe. "
    "I built this because nobody should feel like the only way through is a bottle or a substance. "
    "MindCore AI is live on Android now. Come and try it."
)

H = {"X-Api-Key": HEYGEN_API_KEY, "Content-Type": "application/json"}

def generate():
    print("Submitting to HeyGen...")
    r = requests.post("https://api.heygen.com/v2/video/generate", headers=H, json={
        "video_inputs": [{
            "character": {"type": "avatar", "avatar_id": AVATAR_ID, "avatar_style": "normal"},
            "voice":     {"type": "text", "input_text": SCRIPT, "voice_id": VOICE_ID, "speed": 1.0}
        }],
        "dimension": {"width": 1280, "height": 720}
    })
    d = r.json()
    print(json.dumps(d, indent=2))
    return d["data"]["video_id"]

def poll(video_id):
    print(f"Polling {video_id}...")
    for i in range(1, 61):
        time.sleep(30)
        r = requests.get(f"https://api.heygen.com/v1/video_status.get?video_id={video_id}", headers=H)
        d = r.json()
        status = d["data"]["status"]
        print(f"  [{i}] {status}")
        if status == "completed":
            return d["data"]["video_url"]
        if status == "failed":
            raise RuntimeError(json.dumps(d, indent=2))
    raise TimeoutError("Timed out")

def download(url):
    print("Downloading...")
    os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(OUTPUT, "wb") as f:
            for chunk in r.iter_content(65536):
                f.write(chunk)
    print(f"Saved: {OUTPUT} ({os.path.getsize(OUTPUT)/1024/1024:.1f} MB)")

if __name__ == "__main__":
    vid = generate()
    url = poll(vid)
    download(url)
    print("Done - ph_video.mp4 ready in Artifacts")
