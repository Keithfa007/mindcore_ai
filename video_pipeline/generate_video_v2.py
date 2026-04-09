#!/usr/bin/env python3
"""
MindCore AI Video Pipeline v2.2
=================================
FIXES:
  - 9:16 vertical format (720x1280) for TikTok + Facebook Reels
  - Robust concat: xfade with silent fallback to simple concat
  - Final MP4 is the ONLY artifact uploaded (no loose clips)
  - Retry on Anthropic 529 overload
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

import anthropic
import requests

# -- Config -------------------------------------------------------------------

ANTHROPIC_API_KEY  = os.environ["ANTHROPIC_API_KEY"]
FISH_AUDIO_API_KEY = os.environ["FISH_AUDIO_API_KEY"]
WAVESPEED_API_KEY  = os.environ["WAVESPEED_API_KEY"]
FISH_VOICE_ID      = os.environ.get("FISH_VOICE_ID", "eed26f2294d64177911af612473cca98")

# WAN 2.2 T2V 720p -- portrait 720x1280 = 9:16 for TikTok / Facebook Reels
WAVESPEED_SUBMIT_URL = "https://api.wavespeed.ai/api/v3/wavespeed-ai/wan-2.2/t2v-720p"
WAVESPEED_RESULT_URL = "https://api.wavespeed.ai/api/v3/predictions/{task_id}/result"
FISH_TTS_URL         = "https://api.fish.audio/v1/tts"

VIDEO_SIZE          = "720*1280"   # 9:16 portrait -- TikTok + Facebook Reels
OUTPUT_DIR          = Path("video_pipeline/output")
SCENE_ORDER         = ["hook", "problem", "story", "solution_cta"]
CROSSFADE_DUR       = 0.5
POLL_INTERVAL       = 15
VIDEO_TIMEOUT       = 600
SUPPORTED_DURATIONS = [5, 8]

SEO_KEYWORDS = [
    "AI mental health coach for men",
    "recovery support anxiety depression",
    "sobriety mental wellness app",
]


# -- Step 1 -- Script (with retry on overload) --------------------------------

def generate_script() -> dict:
    print("  Generating 4-scene script with Claude...")
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    prompt = f"""You are a viral performance marketing copywriter for MindCore AI --
an AI mental wellness companion targeting men in recovery or struggling with
anxiety, depression, and isolation.

Write a 4-scene vertical video ad script (9:16, TikTok / Facebook Reels):
Hook -> Problem -> Story -> Solution+CTA.

TARGET: Men 35+. Tone: raw, honest, brotherly. Not clinical.
SEO KEYWORDS to weave in naturally: {", ".join(SEO_KEYWORDS)}

STRICT WORD COUNT RULES (read at ~140 words/min):
- hook:         8-12 words   (~4-5 seconds spoken)
- problem:      12-16 words  (~5-7 seconds spoken)
- story:        14-18 words  (~6-8 seconds spoken)
- solution_cta: 12-16 words  (~5-7 seconds spoken)
Do NOT exceed these limits. Short = punchy = viral.

VISUAL PROMPT RULES (vertical 9:16 framing for mobile):
- 45-60 words each
- VERTICAL framing -- close-up faces, portrait compositions, mobile-first
- Cinematic realism, prestige drama quality
- Describe: subject, action, lighting, camera movement, mood
- Style: cinematic, shallow depth of field, film grain, golden/blue hour, dramatic
- No text, no logos, no UI elements

Return ONLY valid JSON with no markdown fences:
{{
  "hook": {{"voiceover": "...", "visual_prompt": "..."}},
  "problem": {{"voiceover": "...", "visual_prompt": "..."}},
  "story": {{"voiceover": "...", "visual_prompt": "..."}},
  "solution_cta": {{"voiceover": "...", "visual_prompt": "..."}}
}}"""

    max_retries = 5
    for attempt in range(1, max_retries + 1):
        try:
            message = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=1200,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = message.content[0].text.strip()
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
            script = json.loads(raw)
            print("  OK  Script generated")
            return script
        except anthropic.APIStatusError as e:
            if e.status_code == 529:
                wait = 20 * attempt
                print(f"  Anthropic overloaded -- attempt {attempt}/{max_retries}, retry in {wait}s...")
                time.sleep(wait)
            else:
                raise

    raise RuntimeError("Anthropic API still overloaded after all retries")


# -- Step 2 -- Fish Audio TTS -------------------------------------------------

def generate_tts(text: str, output_path: str) -> float:
    headers = {
        "Authorization": f"Bearer {FISH_AUDIO_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "text": text,
        "reference_id": FISH_VOICE_ID,
        "format": "mp3",
        "mp3_bitrate": 128,
        "latency": "normal",
        "normalize": True,
    }
    resp = requests.post(FISH_TTS_URL, headers=headers, json=payload, stream=True, timeout=60)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            if chunk:
                f.write(chunk)
    return get_media_duration(output_path)


def get_media_duration(path: str) -> float:
    result = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", path],
        capture_output=True, text=True, check=True,
    )
    return float(json.loads(result.stdout)["format"]["duration"])


# -- Step 3 -- Duration Matching ----------------------------------------------

def choose_video_duration(audio_duration: float) -> int:
    needed = audio_duration + 0.6
    for d in SUPPORTED_DURATIONS:
        if d >= needed:
            return d
    print(f"  WARNING: Audio ({audio_duration:.2f}s) > 8s cap -- clamping to 8s")
    return 8


# -- Step 4 -- WaveSpeed ------------------------------------------------------

def submit_video(visual_prompt: str, duration: int) -> str:
    headers = {
        "Authorization": f"Bearer {WAVESPEED_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "prompt": visual_prompt,
        "size": VIDEO_SIZE,       # 720*1280 = 9:16 portrait
        "duration": duration,
        "seed": -1,
        "enable_prompt_optimizer": True,
    }
    resp = requests.post(WAVESPEED_SUBMIT_URL, headers=headers, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    task_id = (
        data.get("data", {}).get("id")
        or data.get("id")
        or data.get("task_id")
    )
    if not task_id:
        raise RuntimeError(f"No task_id in response: {data}")
    return task_id


def poll_video(task_id: str) -> str:
    headers  = {"Authorization": f"Bearer {WAVESPEED_API_KEY}"}
    url      = WAVESPEED_RESULT_URL.format(task_id=task_id)
    deadline = time.time() + VIDEO_TIMEOUT
    while time.time() < deadline:
        resp   = requests.get(url, headers=headers, timeout=30)
        resp.raise_for_status()
        inner  = resp.json().get("data", resp.json())
        status = inner.get("status", "unknown")
        if status == "completed":
            outputs = inner.get("outputs", [])
            if outputs:
                return outputs[0]
            raise RuntimeError(f"Completed but no outputs: {inner}")
        if status in ("failed", "error", "cancelled"):
            raise RuntimeError(f"Generation failed [{status}]: {inner}")
        print(f"      waiting  {task_id[:8]}... {status}")
        time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"Timed out after {VIDEO_TIMEOUT}s  task={task_id}")


def download_file(url: str, output_path: str):
    resp = requests.get(url, stream=True, timeout=120)
    resp.raise_for_status()
    with open(output_path, "wb") as f:
        for chunk in resp.iter_content(chunk_size=65_536):
            if chunk:
                f.write(chunk)


# -- Step 5 -- Mux audio onto video (no looping) ------------------------------

def merge_audio_video(video_path: str, audio_path: str, output_path: str):
    """
    Mux VO onto video clip with no looping ever.
    Audio longer  -> freeze last video frame via tpad.
    Video longer  -> pad audio with silence via apad.
    Re-encode to h264/24fps so all clips are identical for concat.
    """
    v_dur = get_media_duration(video_path)
    a_dur = get_media_duration(audio_path)
    diff  = a_dur - v_dur

    if diff > 0:
        freeze_extra = diff + 0.2
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-filter_complex",
            f"[0:v]tpad=stop_mode=clone:stop_duration={freeze_extra:.3f}[vout]",
            "-map", "[vout]", "-map", "1:a:0",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-r", "24",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
            output_path,
        ]
    else:
        pad_dur = abs(diff) + 0.1
        cmd = [
            "ffmpeg", "-y",
            "-i", video_path,
            "-i", audio_path,
            "-filter_complex", f"[1:a]apad=pad_dur={pad_dur:.3f}[aout]",
            "-map", "0:v", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-r", "24",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k", "-ar", "44100", "-ac", "2",
            "-shortest",
            output_path,
        ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FFmpeg stderr:", result.stderr[-2000:])
        raise RuntimeError(f"merge_audio_video failed -> {output_path}")


# -- Step 6 -- Concat all clips into one final MP4 ----------------------------

def concat_clips(clip_paths: list, output_path: str):
    """
    Concatenate clips using xfade crossfade.
    Falls back to simple concat filter if xfade fails (e.g. codec mismatch).
    Final output: h264 / aac, yuv420p, 24fps, faststart -- ready for TikTok & Facebook.
    """
    n = len(clip_paths)

    if n == 1:
        import shutil
        shutil.copy(clip_paths[0], output_path)
        return

    durations = [get_media_duration(p) for p in clip_paths]
    print(f"  Clip durations: {[f'{d:.2f}s' for d in durations]}")

    # ── Try xfade crossfade ──────────────────────────────────────────────
    try:
        _xfade_concat(clip_paths, durations, output_path)
        print("  Concat method: xfade crossfade")
        return
    except Exception as e:
        print(f"  xfade failed ({e}) -- falling back to simple concat")

    # ── Fallback: concat filter (hard cut) ───────────────────────────────
    _simple_concat(clip_paths, output_path)
    print("  Concat method: simple concat (hard cuts)")


def _xfade_concat(clip_paths: list, durations: list, output_path: str):
    n = len(clip_paths)
    input_args = []
    for p in clip_paths:
        input_args += ["-i", p]

    vf, af = [], []
    offset = durations[0] - CROSSFADE_DUR
    vf.append(f"[0:v][1:v]xfade=transition=fade:duration={CROSSFADE_DUR}:offset={offset:.4f}[xv1]")
    af.append(f"[0:a][1:a]acrossfade=d={CROSSFADE_DUR}:c1=tri:c2=tri[xa1]")

    for i in range(2, n):
        offset += durations[i - 1] - CROSSFADE_DUR
        pv = f"[xv{i-1}]"
        pa = f"[xa{i-1}]"
        ov = "[vout]" if i == n - 1 else f"[xv{i}]"
        oa = "[aout]" if i == n - 1 else f"[xa{i}]"
        vf.append(f"{pv}[{i}:v]xfade=transition=fade:duration={CROSSFADE_DUR}:offset={offset:.4f}{ov}")
        af.append(f"{pa}[{i}:a]acrossfade=d={CROSSFADE_DUR}:c1=tri:c2=tri{oa}")

    if n == 2:
        vf[0] = vf[0].replace("[xv1]", "[vout]")
        af[0] = af[0].replace("[xa1]", "[aout]")

    cmd = (
        ["ffmpeg", "-y"]
        + input_args
        + [
            "-filter_complex", ";".join(vf + af),
            "-map", "[vout]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "18",
            "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "192k",
            "-movflags", "+faststart",
            output_path,
        ]
    )
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-1000:])


def _simple_concat(clip_paths: list, output_path: str):
    """Reliable hard-cut concat using FFmpeg concat demuxer."""
    list_file = str(OUTPUT_DIR / "concat_list.txt")
    with open(list_file, "w") as f:
        for p in clip_paths:
            abs_path = Path(p).resolve()
            f.write(f"file '{abs_path}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c:v", "libx264", "-preset", "fast", "-crf", "18",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        output_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FFmpeg stderr:", result.stderr[-2000:])
        raise RuntimeError("simple concat failed")


# -- Main ---------------------------------------------------------------------

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("\n  MindCore AI Video Pipeline v2.2")
    print("  Format: 9:16 vertical (720x1280) -- TikTok + Facebook Reels")
    print("=" * 60)

    # 1. Script
    script = generate_script()
    (OUTPUT_DIR / "script_v2.json").write_text(json.dumps(script, indent=2))
    print()
    for scene in SCENE_ORDER:
        wc = len(script[scene]["voiceover"].split())
        print(f"  [{scene:15s}]  {wc:2d} words  |  {script[scene]['voiceover']}")

    # 2. TTS first -- measure duration before requesting video
    print("\n  Generating voiceovers (Fish Audio Plus)...")
    audio_paths, audio_durations, video_durations = {}, {}, {}

    for scene in SCENE_ORDER:
        path  = str(OUTPUT_DIR / f"{scene}_vo.mp3")
        a_dur = generate_tts(script[scene]["voiceover"], path)
        v_dur = choose_video_duration(a_dur)
        audio_paths[scene]     = path
        audio_durations[scene] = a_dur
        video_durations[scene] = v_dur
        print(f"  [{scene}]  audio={a_dur:.2f}s  ->  requesting {v_dur}s video")

    # 3. Submit video jobs
    print("\n  Submitting video generation (WAN 2.2 T2V -- 9:16 vertical)...")
    task_ids = {}
    for scene in SCENE_ORDER:
        task_id = submit_video(script[scene]["visual_prompt"], video_durations[scene])
        task_ids[scene] = task_id
        print(f"  [{scene}]  task={task_id}  ({video_durations[scene]}s)")
        time.sleep(2)

    # 4. Poll + download raw clips
    print("\n  Polling WaveSpeed...")
    raw_video_paths = {}
    for scene in SCENE_ORDER:
        print(f"  [{scene}]  {task_ids[scene][:8]}...")
        video_url = poll_video(task_ids[scene])
        out = str(OUTPUT_DIR / f"{scene}_raw.mp4")
        download_file(video_url, out)
        raw_video_paths[scene] = out
        print(f"    OK  ({get_media_duration(out):.2f}s)")

    # 5. Mux audio onto each clip
    print("\n  Merging audio onto clips...")
    merged_paths = []
    for scene in SCENE_ORDER:
        out = str(OUTPUT_DIR / f"{scene}_merged.mp4")
        merge_audio_video(raw_video_paths[scene], audio_paths[scene], out)
        merged_paths.append(out)
        print(f"  [{scene}]  ({get_media_duration(out):.2f}s)")

    # 6. Concat all scenes into one final MP4
    print("\n  Concatenating all scenes into final video...")
    final = str(OUTPUT_DIR / "mindcore_ai_ad_v2.mp4")
    concat_clips(merged_paths, final)

    final_dur = get_media_duration(final)
    final_mb  = Path(final).stat().st_size / (1024 * 1024)
    print(f"\n  DONE")
    print(f"  File:     {final}")
    print(f"  Duration: {final_dur:.2f}s")
    print(f"  Size:     {final_mb:.1f} MB")
    print(f"  Format:   9:16 vertical / H.264 / AAC -- ready for TikTok + Facebook")
    print("\n  Pipeline complete!")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n  FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
