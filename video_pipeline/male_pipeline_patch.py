#!/usr/bin/env python3
"""
MindCore AI -- Male Pipeline Patch v2.2
=======================================
v2.2: Fixed power word flashes + softened ad CTA.
      - Apostrophe bug fixed (ISN'T now matches stopword 'isnt')
      - Expanded stopwords (no more flashing ACTUALLY, SAID, STOPPED)
      - Expanded power words (DISMISSED, FLINCH, HEARD now flash)
      - Ad CTA moved off-screen -- ends on emotional resolution
v2.1: No background music.
v2.0: Pexels restored.
v1.1: POST_HOUR_UTC from env.
"""
import json, os, sys, random
from datetime import datetime, timedelta, timezone
import requests
import video_pipeline.male_pipeline as pipeline
from video_pipeline.word_flash import pick_power_word as fixed_pick_power_word
from video_pipeline.word_flash import WORD_FLASH_STOPWORDS as FIXED_STOPWORDS
from video_pipeline.word_flash import POWER_WORDS as FIXED_POWER_WORDS

# Patch word flash into the pipeline module
pipeline.pick_power_word = fixed_pick_power_word
pipeline.WORD_FLASH_STOPWORDS = FIXED_STOPWORDS
pipeline.POWER_WORDS = FIXED_POWER_WORDS


def get_scheduled_post_time():
    env_hour = os.environ.get("POST_HOUR_UTC")
    if not env_hour: raise RuntimeError("POST_HOUR_UTC env variable not set.")
    post_hour = int(env_hour); now = datetime.now(timezone.utc)
    target = now.replace(hour=post_hour, minute=0, second=0, microsecond=0)
    if now >= target: target += timedelta(days=1)
    scheduled = target.strftime("%Y-%m-%dT%H:%M:%SZ")
    slot = "A (11am Malta)" if post_hour == 9 else "B (3pm Malta)"
    print(f"  [v8.0] Slot {slot} | {post_hour:02d}:00 UTC = {post_hour+2:02d}:00 Malta | Fires: {scheduled}")
    return scheduled


def _patched_render_cinematic_video(script_text, mood, niche, script=None):
    from video_pipeline.pexels_clips import fetch_pexels_clip_for_scene
    print("\n  [TTS] Generating voiceover...")
    audio_path = str(pipeline.OUTPUT_DIR / "voiceover.mp3")
    pipeline.generate_fish_audio_tts(script_text, audio_path)
    print("\n  [Subtitles] Transcribing with Whisper...")
    ass_path = str(pipeline.OUTPUT_DIR / "subtitles_cinematic.ass")
    words = pipeline.transcribe_audio_whisper(audio_path)
    if not pipeline.generate_ass_subtitles(words, ass_path): ass_path = None
    clips_dir = pipeline.OUTPUT_DIR / "clips"; clips_dir.mkdir(exist_ok=True)
    raw_clip_paths = []; scene_types = []
    for scene_name, count in [("hook",1),("problem",2),("story",1),("solution_cta",1)]:
        for j in range(count):
            clip_path = str(clips_dir / f"raw_{len(raw_clip_paths)}.mp4")
            pexels_path = fetch_pexels_clip_for_scene(scene_name, len(raw_clip_paths), clip_path, pipeline.GITHUB_RUN_NUMBER, gender="man")
            if pexels_path: raw_clip_paths.append(pexels_path); scene_types.append(scene_name)
            else: print(f"  WARNING: {scene_name} clip skipped")
    if not raw_clip_paths: raise RuntimeError("All Pexels fetches failed")
    print(f"\n  Fetched {len(raw_clip_paths)}/5 clips (Pexels -- free)")
    final_path = str(pipeline.OUTPUT_DIR / "mindcore_ai_video.mp4")
    pipeline.assemble_cinematic_video(raw_clip_paths, audio_path, final_path, None, ass_path, scene_types=scene_types)
    return final_path


def _patched_generate_ad_script(app_facts, niche, client):
    """Ad script with softened CTA -- emotional resolution on screen, app CTA in caption only."""
    ad_topic = random.choice(pipeline.AD_TOPICS)
    formula = random.choice(pipeline.HOOK_FORMULAS)
    hook_block = pipeline._build_hook_block(formula)
    print(f"  AD: {ad_topic['pain_point'][:65]}...")
    lp,hp = pipeline.WORD_TARGETS_AD["problem"]
    ls,hs = pipeline.WORD_TARGETS_AD["story"]
    lc,hc = pipeline.WORD_TARGETS_AD["solution_cta"]
    prompt = f"""You are writing a punchy cinematic voiceover ad script for MindCore AI. Target: 25-35 seconds.

VIEWER: {niche['viewer_persona']}
PAIN POINT: {ad_topic['pain_point']}
INSIGHT: {ad_topic['insight']}
FEATURE: {ad_topic['feature']}

{hook_block}

SCENES (KEEP TIGHT):
hook -> problem ({lp}-{hp} words) -> story ({ls}-{hs} words -- mention MindCore AI ONCE, naturally, as "a space that listens" or "somewhere that doesn't judge" or "a place that takes you seriously". NEVER say download, play, Google Play.) -> solution_cta ({lc}-{hc} words -- end on PURE EMOTIONAL RESOLUTION. The last sentence must be emotional and saveable, NOT transactional. Examples: "You deserve to be heard." / "That space exists now." / "You don't have to carry this alone anymore." NEVER say "Play now" or "Download now" or "Google Play" -- the app CTA goes in the caption, not the voiceover.)
BANNED IN VOICEOVER: "free trial", "first week free", "download now", "play now", "Google Play", "on Google Play"

Return ONLY valid JSON:
{{"video_type":"ad","topic":"{ad_topic['pain_point'][:55]}","seo_keyword":"AI mental health companion for men","render_format":"cinematic","hook_formula":"{formula['name']}","hook":{{"voiceover":"..."}},"problem":{{"voiceover":"..."}},"story":{{"voiceover":"..."}},"solution_cta":{{"voiceover":"..."}}}}"""
    return pipeline._call_claude_raw(prompt, client, max_tokens=800)


def _patched_upload(video_path, metadata, cfg, scheduled_date=None):
    if not pipeline.UPLOAD_POST_API_KEY: return {"skipped":True,"reason":"no API key"}
    user = cfg.get("upload_post_user","")
    if not user: return {"skipped":True,"reason":"no user configured"}
    headers = {"Authorization": f"Apikey {pipeline.UPLOAD_POST_API_KEY}"}
    data = [
        ("user",user),("platform[]","tiktok"),("platform[]","facebook"),("platform[]","youtube"),
        ("title",metadata.get("tiktok_caption","")[:pipeline.TIKTOK_CAPTION_LIMIT]),
        ("facebook_title",metadata.get("facebook_title","")[:255]),
        ("facebook_description",metadata.get("facebook_description","")),
        ("youtube_title",metadata.get("youtube_title","")[:pipeline.YOUTUBE_TITLE_LIMIT]),
        ("youtube_description",metadata.get("youtube_description","")[:pipeline.YOUTUBE_DESCRIPTION_LIMIT]),
        ("youtube_tags",metadata.get("youtube_tags","")),
        ("first_comment",metadata.get("first_comment","")),
    ]
    if scheduled_date: data.append(("scheduled_date",scheduled_date))
    try:
        with open(video_path,"rb") as f:
            resp = requests.post(pipeline.UPLOAD_POST_API_URL,headers=headers,files=[("video",("mindcore_ai_video.mp4",f,"video/mp4"))],data=data,timeout=180)
        result = resp.json() if resp.headers.get("content-type","").startswith("application/json") else {"raw":resp.text}
        result["status_code"] = resp.status_code
        if scheduled_date: result["scheduled_date"] = scheduled_date
        print(f"  Upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}")
        if not resp.ok: print(f"  {resp.text[:300]}")
        return result
    except Exception as e: print(f"  Upload failed: {e}"); return {"error":str(e)}


pipeline.render_cinematic_video = _patched_render_cinematic_video
pipeline.upload_to_platforms = _patched_upload
pipeline.generate_ad_script = _patched_generate_ad_script


def main():
    import anthropic
    OUTPUT_DIR = pipeline.OUTPUT_DIR; PIPELINE_DIR = pipeline.PIPELINE_DIR
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True); (OUTPUT_DIR/"clips").mkdir(exist_ok=True)
    mode = pipeline.determine_mode()
    client = anthropic.Anthropic(api_key=pipeline.ANTHROPIC_API_KEY)
    cfg = {}; cp = PIPELINE_DIR/"heygen_config.json"
    if cp.exists():
        with open(cp) as f: cfg = json.load(f)
    upload_enabled = cfg.get("upload_enabled",False) and bool(pipeline.UPLOAD_POST_API_KEY)
    keywords_data = pipeline.load_keywords_data(); niche = pipeline.get_niche_for_today(keywords_data)
    mood = pipeline.pick_visual_mood(niche)
    slot_label = "A (11am Malta)" if os.environ.get("POST_HOUR_UTC")=="9" else "B (3pm Malta)"
    print(f"\n  MindCore AI -- Male Cinematic Pipeline v8.0")
    print(f"  Run #{pipeline.GITHUB_RUN_NUMBER} | Mode: {mode.upper()} | Slot {slot_label}")
    print(f"  Pexels B-roll | Voice only | Fixed word flashes | Soft ad CTA")
    print(f"  Upload: {'ENABLED' if upload_enabled else 'DISABLED'}")
    print("="*60)
    print("\n  Generating script...")
    if mode=="ad": script = pipeline.generate_ad_script(pipeline.load_app_facts(),niche,client)
    else:
        topic = pipeline.fetch_trending_topic(client,niche)
        script = pipeline.generate_content_script(topic,niche,client)
        pipeline.save_topic_history(pipeline.load_topic_history(),topic.get("keyword",topic.get("topic","")))
    script = pipeline.sanitize_script(script); (OUTPUT_DIR/"script.json").write_text(json.dumps(script,indent=2))
    tw = sum(len(script[s]["voiceover"].split()) for s in pipeline.SCENE_ORDER); ed = round(tw/130*60)
    print(f"\n  ~{ed}s | Hook: {script.get('hook_formula','?')}")
    for s in pipeline.SCENE_ORDER: print(f"  [{s:15s}] {script[s]['voiceover'][:85]}...")
    final_path = pipeline.render_cinematic_video(pipeline.build_full_script(script),mood,niche,script=script)
    gt = pipeline.generate_upload_guide(script,mode,niche,client)
    pipeline.save_upload_guide(gt,script,mode,pipeline.GITHUB_RUN_NUMBER,niche)
    um = pipeline.generate_upload_metadata(script,mode,niche,client)
    (OUTPUT_DIR/"upload_metadata.json").write_text(json.dumps(um,indent=2))
    if upload_enabled:
        sd = get_scheduled_post_time()
        ur = pipeline.upload_to_platforms(final_path,um,cfg,scheduled_date=sd)
        (OUTPUT_DIR/"upload_result.json").write_text(json.dumps(ur,indent=2))
        if ur.get("status_code")==200: print(f"  Scheduled OK -- fires at {sd}")
    else: (OUTPUT_DIR/"upload_result.json").write_text(json.dumps({"skipped":True},indent=2))
    print(f"\n  DONE | ~{ed}s | {niche['name']}")

if __name__=="__main__":
    try: main()
    except Exception as exc: print(f"\n  FAILED: {exc}",file=sys.stderr); raise SystemExit(1)
