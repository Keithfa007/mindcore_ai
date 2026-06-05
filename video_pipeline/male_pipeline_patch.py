#!/usr/bin/env python3
"""
MindCore AI -- Male Pipeline Patch v1.0
=======================================
Injects Upload-Post scheduled_date into male_pipeline without
replacing the full 47KB file. Imported and run by GitHub Actions
instead of male_pipeline.py directly.

Slot detection (from current UTC hour at cron fire time):
  Cron 00:00 UTC -> hour 0 -> Slot A -> post 09:00 UTC = 11:00 Malta
  Cron 01:00 UTC -> hour 1 -> Slot B -> post 13:00 UTC = 15:00 Malta
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

import video_pipeline.male_pipeline as pipeline

# ---------------------------------------------------------------------------
# Slot-based scheduling
# ---------------------------------------------------------------------------
SLOT_SCHEDULE = {0: 9, 1: 13}   # run UTC hour -> post UTC hour

def get_scheduled_post_time():
    now = datetime.now(timezone.utc)
    post_hour = SLOT_SCHEDULE.get(now.hour, 9)
    target = now.replace(hour=post_hour, minute=0, second=0, microsecond=0)
    if now >= target:
        target += timedelta(days=1)
    scheduled = target.strftime("%Y-%m-%dT%H:%M:%SZ")
    slot = "MORNING (11am Malta)" if post_hour == 9 else "AFTERNOON (3pm Malta)"
    print(f"  [v8.0 patch] Slot: {slot} | Scheduled: {scheduled}")
    return scheduled

# ---------------------------------------------------------------------------
# Patched upload_to_platforms -- adds scheduled_date support
# ---------------------------------------------------------------------------
def _patched_upload(video_path, metadata, cfg, scheduled_date=None):
    if not pipeline.UPLOAD_POST_API_KEY:
        return {"skipped": True, "reason": "no API key"}
    user = cfg.get("upload_post_user", "")
    if not user:
        return {"skipped": True, "reason": "no user configured"}
    headers = {"Authorization": f"Apikey {pipeline.UPLOAD_POST_API_KEY}"}
    data = [
        ("user",                user),
        ("platform[]",          "tiktok"),
        ("platform[]",          "facebook"),
        ("platform[]",          "youtube"),
        ("title",               metadata.get("tiktok_caption","")[:pipeline.TIKTOK_CAPTION_LIMIT]),
        ("facebook_title",      metadata.get("facebook_title","")[:255]),
        ("facebook_description",metadata.get("facebook_description","")),
        ("youtube_title",       metadata.get("youtube_title","")[:pipeline.YOUTUBE_TITLE_LIMIT]),
        ("youtube_description", metadata.get("youtube_description","")[:pipeline.YOUTUBE_DESCRIPTION_LIMIT]),
        ("youtube_tags",        metadata.get("youtube_tags","")),
        ("first_comment",       metadata.get("first_comment","")),
    ]
    if scheduled_date:
        data.append(("scheduled_date", scheduled_date))
    try:
        with open(video_path, "rb") as f:
            files = [("video", ("mindcore_ai_video.mp4", f, "video/mp4"))]
            resp = requests.post(
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

# Apply patch to the module
pipeline.upload_to_platforms = _patched_upload

# ---------------------------------------------------------------------------
# Patched main -- calls get_scheduled_post_time() and passes it through
# ---------------------------------------------------------------------------
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
    music_tracks   = list(pipeline.MUSIC_DIR.glob("*.mp3")) if pipeline.MUSIC_DIR.exists() else []
    keywords_data  = pipeline.load_keywords_data()
    niche          = pipeline.get_niche_for_today(keywords_data)
    mood           = pipeline.pick_visual_mood(niche)

    print(f"\n  MindCore AI -- Male Cinematic Pipeline v8.0")
    print(f"  Run #{pipeline.GITHUB_RUN_NUMBER} | Mode: {mode.upper()} | Full fal.ai (~$1.25/video)")
    print(f"  Niche: {niche['name']} | Slot A->11am / Slot B->3pm Malta (scheduled)")
    print(f"  Upload: {'ENABLED' if upload_enabled else 'DISABLED'} | Music: {len(music_tracks)} tracks")
    print("=" * 60)

    print("\n  Generating script...")
    if mode == "ad":
        script = pipeline.generate_ad_script(pipeline.load_app_facts(), niche, client)
    else:
        topic  = pipeline.fetch_trending_topic(client, niche)
        script = pipeline.generate_content_script(topic, niche, client)
        topic_history = pipeline.load_topic_history()
        pipeline.save_topic_history(topic_history, topic.get("keyword", topic.get("topic", "")))

    script = pipeline.sanitize_script(script)
    (OUTPUT_DIR / "script.json").write_text(json.dumps(script, indent=2))

    total_words  = sum(len(script[s]["voiceover"].split()) for s in pipeline.SCENE_ORDER)
    est_duration = round(total_words / 130 * 60)
    print(f"\n  ~{est_duration}s | Hook formula: {script.get('hook_formula', '?')}")
    for scene in pipeline.SCENE_ORDER:
        print(f"  [{scene:15s}] {script[scene]['voiceover'][:85]}...")

    final_path    = pipeline.render_cinematic_video(pipeline.build_full_script(script), mood, niche, script=script)
    guide_text    = pipeline.generate_upload_guide(script, mode, niche, client)
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
            print(f"  Scheduled OK -- fires at {scheduled_date} (TikTok + Facebook + YouTube)")
    else:
        (OUTPUT_DIR / "upload_result.json").write_text(json.dumps({"skipped": True}, indent=2))

    print(f"\n  DONE | ~{est_duration}s | {niche['name']}")
    if upload_enabled:
        print("  Posted: TikTok + Facebook + YouTube (scheduled via Upload-Post)")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"\n  FAILED: {exc}", file=sys.stderr)
        raise SystemExit(1)
