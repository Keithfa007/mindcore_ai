#!/usr/bin/env python3
"""
MindCore AI -- Male Pipeline Patch v2.1
=======================================
v2.1: No background music -- voice only.
      TikTok adds its own audio. FB/YouTube get raw authentic voice.
v2.0: Pexels restored, fal.ai removed.
v1.1: POST_HOUR_UTC from env.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests
import video_pipeline.male_pipeline as pipeline


def get_scheduled_post_time():
    env_hour = os.environ.get("POST_HOUR_UTC")
    if not env_hour:
        raise RuntimeError("POST_HOUR_UTC env variable not set.")
    post_hour  = int(env_hour)
    now        = datetime.now(timezone.utc)
    target     = now.replace(hour=post_hour, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    scheduled  = target.strftime("%Y-%m-%dT%H:%M:%SZ")
    malta_hour = post_hour + 2
    slot       = "A (11am Malta)" if post_hour == 9 else "B (3pm Malta)"
    print(f"  [v8.0] Slot {slot} | {post_hour:02d}:00 UTC = {malta_hour:02d}:00 Malta | Fires: {scheduled}")
    return scheduled


def _patched_render_cinematic_video(script_text, mood, niche, script=None):
    """Render video with Pexels B-roll, voice only (no background music)."""
    from video_pipeline.pexels_clips import fetch_pexels_clip_for_scene

    print("\n  [TTS] Generating voiceover...")
    audio_path = str(pipeline.OUTPUT_DIR / "voiceover.mp3")
    pipeline.generate_fish_audio_tts(script_text, audio_path)

    print("\n  [Subtitles] Transcribing with Whisper...")
    ass_path = str(pipeline.OUTPUT_DIR / "subtitles_cinematic.ass")
    words = pipeline.transcribe_audio_whisper(audio_path)
    if not pipeline.generate_ass_subtitles(words, ass_path):
        ass_path = None

    clips_dir = pipeline.OUTPUT_DIR / "clips"
    clips_dir.mkdir(exist_ok=True)
    raw_clip_paths = []
    scene_types    = []

    scene_plan = [("hook", 1), ("problem", 2), ("story", 1), ("solution_cta", 1)]
    clip_idx   = 0

    for scene_name, count in scene_plan:
        for j in range(count):
            clip_path  = str(clips_dir / f"raw_{clip_idx}.mp4")
            print(f"  [Pexels] {scene_name.upper()} {j+1}/{count}...")
            pexels_path = fetch_pexels_clip_for_scene(
                scene_name, clip_idx, clip_path,
                pipeline.GITHUB_RUN_NUMBER, gender="man"
            )
            if pexels_path:
                raw_clip_paths.append(pexels_path)
                scene_types.append(scene_name)
            else:
                print(f"  WARNING: {scene_name} clip {j+1} skipped")
            clip_idx += 1

    if not raw_clip_paths:
        raise RuntimeError("All Pexels fetches failed")

    print(f"\n  Fetched {len(raw_clip_paths)}/5 clips (Pexels -- free, real footage)")
    music_path = None  # Voice only -- no background music. TikTok adds its own.
    final_path = str(pipeline.OUTPUT_DIR / "mindcore_ai_video.mp4")
    pipeline.assemble_cinematic_video(
        raw_clip_paths, audio_path, final_path,
        music_path, ass_path, scene_types=scene_types
    )
    return final_path


def _patched_upload(video_path, metadata, cfg, scheduled_date=None):
    if not pipeline.UPLOAD_POST_API_KEY:
        return {"skipped": True, "reason": "no API key"}
    user = cfg.get("upload_post_user", "")
    if not user:
        return {"skipped": True, "reason": "no user configured"}
    headers = {"Authorization": f"Apikey {pipeline.UPLOAD_POST_API_KEY}"}
    data = [
        ("user",                 user),
        ("platform[]",           "tiktok"),
        ("platform[]",           "facebook"),
        ("platform[]",           "youtube"),
        ("title",                metadata.get("tiktok_caption", "")[:pipeline.TIKTOK_CAPTION_LIMIT]),
        ("facebook_title",       metadata.get("facebook_title", "")[:255]),
        ("facebook_description", metadata.get("facebook_description", "")),
        ("youtube_title",        metadata.get("youtube_title", "")[:pipeline.YOUTUBE_TITLE_LIMIT]),
        ("youtube_description",  metadata.get("youtube_description", "")[:pipeline.YOUTUBE_DESCRIPTION_LIMIT]),
        ("youtube_tags",         metadata.get("youtube_tags", "")),
        ("first_comment",        metadata.get("first_comment", "")),
    ]
    if scheduled_date:
        data.append(("scheduled_date", scheduled_date))
    try:
        with open(video_path, "rb") as f:
            files = [("video", ("mindcore_ai_video.mp4", f, "video/mp4"))]
            resp  = requests.post(
                pipeline.UPLOAD_POST_API_URL,
                headers=headers, files=files, data=data, timeout=180
            )
        result = (
            resp.json()
            if resp.headers.get("content-type", "").startswith("application/json")
            else {"raw": resp.text}
        )
        result["status_code"] = resp.status_code
        if scheduled_date:
            result["scheduled_date"] = scheduled_date
        print(f"  Upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}")
        if not resp.ok:
            print(f"  {resp.text[:300]}")
        return result
    except Exception as e:
        print(f"  Upload failed: {e}")
        return {"error": str(e)}


pipeline.render_cinematic_video = _patched_render_cinematic_video
pipeline.upload_to_platforms    = _patched_upload


def main():
    OUTPUT_DIR   = pipeline.OUTPUT_DIR
    PIPELINE_DIR = pipeline.PIPELINE_DIR

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "clips").mkdir(exist_ok=True)

    mode   = pipeline.determine_mode()
    import anthropic
    client = anthropic.Anthropic(api_key=pipeline.ANTHROPIC_API_KEY)

    cfg      = {}
    cfg_path = PIPELINE_DIR / "heygen_config.json"
    if cfg_path.exists():
        with open(cfg_path) as f:
            cfg = json.load(f)

    upload_enabled = cfg.get("upload_enabled", False) and bool(pipeline.UPLOAD_POST_API_KEY)
    keywords_data  = pipeline.load_keywords_data()
    niche          = pipeline.get_niche_for_today(keywords_data)
    mood           = pipeline.pick_visual_mood(niche)
    slot_label     = "A (11am Malta)" if os.environ.get("POST_HOUR_UTC") == "9" else "B (3pm Malta)"

    print(f"\n  MindCore AI -- Male Cinematic Pipeline v8.0")
    print(f"  Run #{pipeline.GITHUB_RUN_NUMBER} | Mode: {mode.upper()} | Slot {slot_label}")
    print(f"  Niche: {niche['name']} | Pexels B-roll | Voice only (no music)")
    print(f"  Upload: {'ENABLED' if upload_enabled else 'DISABLED'}")
    print("=" * 60)

    print("\n  Generating script...")
    if mode == "ad":
        script = pipeline.generate_ad_script(pipeline.load_app_facts(), niche, client)
    else:
        topic  = pipeline.fetch_trending_topic(client, niche)
        script = pipeline.generate_content_script(topic, niche, client)
        pipeline.save_topic_history(
            pipeline.load_topic_history(),
            topic.get("keyword", topic.get("topic", ""))
        )

    script = pipeline.sanitize_script(script)
    (OUTPUT_DIR / "script.json").write_text(json.dumps(script, indent=2))

    total_words  = sum(len(script[s]["voiceover"].split()) for s in pipeline.SCENE_ORDER)
    est_duration = round(total_words / 130 * 60)
    print(f"\n  ~{est_duration}s | Hook: {script.get('hook_formula', '?')}")
    for scene in pipeline.SCENE_ORDER:
        print(f"  [{scene:15s}] {script[scene]['voiceover'][:85]}...")

    final_path      = pipeline.render_cinematic_video(
        pipeline.build_full_script(script), mood, niche, script=script
    )
    guide_text      = pipeline.generate_upload_guide(script, mode, niche, client)
    pipeline.save_upload_guide(guide_text, script, mode, pipeline.GITHUB_RUN_NUMBER, niche)
    upload_metadata = pipeline.generate_upload_metadata(script, mode, niche, client)
    (OUTPUT_DIR / "upload_metadata.json").write_text(json.dumps(upload_metadata, indent=2))

    if upload_enabled:
        scheduled_date = get_scheduled_post_time()
        upload_result  = pipeline.upload_to_platforms(
            final_path, upload_metadata, cfg, scheduled_date=scheduled_date
        )
        (OUTPUT_DIR / "upload_result.json").write_text(json.dumps(upload_result, indent=2))
        if upload_result.get("status_code") == 200:
            print(f"  Scheduled OK -- fires at {scheduled_date}")
    else:
        (OUTPUT_DIR / "upload_result.json").write_text(json.dumps({"skipped": True}, indent=2))

    print(f"\n  DONE | ~{est_duration}s | {niche['name']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n  FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
