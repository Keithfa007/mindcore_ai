#!/usr/bin/env python3
"""
MindCore AI -- Male Pipeline Patch v3.1
=======================================
v3.1: Pexels-only + xfade crossfade transitions (matching female v5.8).
v3.0: WaveSpeed with automatic Pexels fallback.
v2.9: WaveSpeed API only (RunPod removed).
v2.7: Removed word flash overlays.
v2.4: ElevenLabs TTS.
v2.3: SERP targets GB.
"""
import json, os, sys, random, subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
import requests
import video_pipeline.male_pipeline as pipeline
from video_pipeline.word_flash import pick_power_word as fixed_pick_power_word
from video_pipeline.word_flash import WORD_FLASH_STOPWORDS as FIXED_STOPWORDS
from video_pipeline.word_flash import POWER_WORDS as FIXED_POWER_WORDS
from video_pipeline.tts import generate_elevenlabs_tts, MALE_VOICE_ID

pipeline.pick_power_word = fixed_pick_power_word
pipeline.WORD_FLASH_STOPWORDS = FIXED_STOPWORDS
pipeline.POWER_WORDS = FIXED_POWER_WORDS

def _elevenlabs_tts(script_text, output_path):
    return generate_elevenlabs_tts(script_text, output_path, MALE_VOICE_ID)
pipeline.generate_fish_audio_tts = _elevenlabs_tts

_kd = pipeline.load_keywords_data()
SERP_COUNTRY = _kd.get("serp_country", "gb")
print(f"  SERP country: {SERP_COUNTRY}")

def _improved_ass_subtitles(words, output_path):
    if not words: return False
    def ts(s): h=int(s//3600);m=int((s%3600)//60);s=s%60; return f"{h}:{m:02d}:{s:05.2f}"
    header = (
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "ScaledBorderAndShadow: yes\nWrapStyle: 1\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        "Style: Default,Arial,85,"
        "&H00FFFFFF,&H000000FF,&H00000000,&H00000000,"
        "-1,0,0,0,100,100,2,0,1,5,2,2,60,60,500,1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    chunks=[]; i=0; chunk_size=2
    while i<len(words):
        chunk=words[i:i+chunk_size]
        text=" ".join(w["word"].upper() for w in chunk)
        start=chunk[0]["start"]; end=chunk[-1]["end"]
        if not chunks: start=0.0
        elif start<chunks[-1]["end"]: start=chunks[-1]["end"]
        chunks.append({"text":text,"start":start,"end":end})
        i+=chunk_size
    events=""
    for c in chunks:
        events+=f"Dialogue: 0,{ts(c['start'])},{ts(c['end'])},Default,,0,0,0,,{{\\fad(150,100)}}{c['text']}\n"
    content_out = (header+events).encode("utf-8", errors="ignore").decode("utf-8")
    Path(output_path).write_text(content_out, encoding="utf-8")
    print(f"  Subtitles: {len(chunks)} groups (no word flashes)")
    return True

pipeline.generate_ass_subtitles = _improved_ass_subtitles

def _patched_serp_google_query(seed):
    r = requests.get(pipeline.SERP_API_URL, params={"engine":"google","q":seed,"api_key":pipeline.SERP_API_KEY,"num":10,"hl":"en","gl":SERP_COUNTRY}, timeout=30)
    r.raise_for_status(); return r.json()
def _patched_serp_autocomplete_query(seed):
    try:
        r = requests.get(pipeline.SERP_API_URL, params={"engine":"google_autocomplete","q":seed,"api_key":pipeline.SERP_API_KEY,"hl":"en","gl":SERP_COUNTRY}, timeout=30)
        r.raise_for_status(); return [s.get("value","").strip() for s in r.json().get("suggestions",[]) if s.get("value")]
    except Exception as e: print(f"  Autocomplete failed: {e}"); return []
pipeline._serp_google_query = _patched_serp_google_query
pipeline._serp_autocomplete_query = _patched_serp_autocomplete_query

def get_scheduled_post_time():
    env_hour = os.environ.get("POST_HOUR_UTC")
    if not env_hour: raise RuntimeError("POST_HOUR_UTC env variable not set.")
    post_hour = int(env_hour); now = datetime.now(timezone.utc)
    target = now.replace(hour=post_hour, minute=0, second=0, microsecond=0)
    if now >= target: target += timedelta(days=1)
    scheduled = target.strftime("%Y-%m-%dT%H:%M:%SZ")
    slot = "MORNING (11am Malta)" if post_hour == 9 else "EVENING (7pm Malta)"
    print(f"  {slot} | {post_hour:02d}:00 UTC = {post_hour+2:02d}:00 Malta | Fires: {scheduled}")
    return scheduled

# ── xfade assembly -- replaces hard concat with smooth dissolve transitions ──
def _patched_assemble_cinematic_video(clip_paths, audio_path, output_path, music_path=None, ass_path=None, scene_types=None):
    XFADE_DUR = 0.6
    ad = pipeline.get_audio_duration(audio_path); n = len(clip_paths)
    total_xfade = XFADE_DUR * (n - 1) if n > 1 else 0
    cd = (ad + total_xfade) / n
    print(f"  Assembling: {n} clips x {cd:.1f}s = {ad:.1f}s (with {XFADE_DUR}s crossfades)")
    clips_dir = pipeline.OUTPUT_DIR / "clips"; clips_dir.mkdir(exist_ok=True); processed = []
    for i, rp in enumerate(clip_paths):
        st = scene_types[i] if scene_types and i < len(scene_types) else "problem"
        grade = pipeline.COLOR_GRADE_WARM if st in pipeline.WARM_SCENES else pipeline.COLOR_GRADE_COLD
        d = pipeline.KB_DIRECTIONS[i % len(pipeline.KB_DIRECTIONS)]
        out = str(clips_dir / f"clip_{i}_processed.mp4")
        try:
            pipeline.process_clip_to_portrait(rp, out, cd, d, grade)
            processed.append(out)
            print(f"    Clip {i+1}/{n}: {d} | {'WARM' if grade == pipeline.COLOR_GRADE_WARM else 'COLD'}")
        except Exception as e:
            print(f"  Clip {i+1} failed ({e}) -- skipping")
    if not processed: raise RuntimeError("No clips processed")
    if len(processed) == 1:
        cv = processed[0]
    else:
        inputs = []
        for p in processed: inputs.extend(["-i", p])
        clip_durs = []
        for p in processed:
            dur_out = subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",p], capture_output=True, text=True)
            clip_durs.append(float(dur_out.stdout.strip()) if dur_out.returncode == 0 else cd)
        filters = []; offset = clip_durs[0] - XFADE_DUR; prev = "0:v"
        for i in range(1, len(processed)):
            out_label = f"v{i}" if i < len(processed) - 1 else "outv"
            filters.append(f"[{prev}][{i}:v]xfade=transition=fade:duration={XFADE_DUR}:offset={offset:.3f}[{out_label}]")
            prev = out_label
            if i < len(processed) - 1: offset += clip_durs[i] - XFADE_DUR
        cv = str(pipeline.OUTPUT_DIR / "xfade_video.mp4")
        xfade_cmd = ["ffmpeg","-y"] + inputs + ["-filter_complex",";".join(filters),"-map","[outv]","-c:v","libx264","-crf","18","-preset","slow","-pix_fmt","yuv420p",cv]
        print(f"  [xfade] {len(processed)} clips with {XFADE_DUR}s dissolve transitions...")
        r = subprocess.run(xfade_cmd, capture_output=True, text=True)
        if r.returncode != 0:
            print(f"  [xfade] Failed -- falling back to hard concat: {r.stderr[-300:]}")
            cf = pipeline.OUTPUT_DIR / "concat.txt"
            with open(cf, "w") as f:
                for p in processed: f.write(f"file '{Path(p).resolve()}'\n")
            cv = str(pipeline.OUTPUT_DIR / "concat_video.mp4")
            subprocess.run(["ffmpeg","-f","concat","-safe","0","-i",str(cf),"-c:v","copy","-t",str(ad),"-y",cv], capture_output=True, text=True, check=True)
        else:
            print(f"  [xfade] Smooth transitions applied")
    r = subprocess.run(["ffmpeg","-i",cv,"-i",audio_path,"-map","0:v:0","-map","1:a:0","-c:v","libx264","-crf","18","-preset","slow","-c:a","aac","-b:a","192k","-t",str(ad),"-y",output_path], capture_output=True, text=True)
    if r.returncode != 0: raise RuntimeError(f"Audio mix failed: {r.stderr[-500:]}")
    print(f"  Assembled: {Path(output_path).stat().st_size/(1024*1024):.1f} MB | xfade transitions")
    if ass_path: pipeline.burn_subtitles_into_video(output_path, ass_path)

# ── Pexels-only render -- WaveSpeed removed ──
def _patched_render_cinematic_video(script_text, mood, niche, script=None):
    """Render video: Pexels B-roll with xfade transitions."""
    print("\n  [TTS] Generating voiceover (ElevenLabs)...")
    audio_path = str(pipeline.OUTPUT_DIR / "voiceover.mp3")
    pipeline.generate_fish_audio_tts(script_text, audio_path)

    print("\n  [Subtitles] Transcribing with Whisper...")
    ass_path = str(pipeline.OUTPUT_DIR / "subtitles_cinematic.ass")
    words = pipeline.transcribe_audio_whisper(audio_path)
    if not pipeline.generate_ass_subtitles(words, ass_path): ass_path = None

    clips_dir = pipeline.OUTPUT_DIR / "clips"; clips_dir.mkdir(exist_ok=True)
    raw_clip_paths = []; scene_types = []

    from video_pipeline.pexels_clips import fetch_pexels_clip_for_scene, reset_used_videos
    reset_used_videos()
    for scene_name, count in [("hook",1),("problem",2),("story",1),("solution_cta",1)]:
        for j in range(count):
            clip_path = str(clips_dir / f"raw_{len(raw_clip_paths)}.mp4")
            pexels_path = fetch_pexels_clip_for_scene(scene_name, len(raw_clip_paths), clip_path, pipeline.GITHUB_RUN_NUMBER, gender="man")
            if pexels_path: raw_clip_paths.append(pexels_path); scene_types.append(scene_name)
            else: print(f"  WARNING: {scene_name} clip skipped")

    if not raw_clip_paths: raise RuntimeError("No clips fetched from Pexels")
    print(f"\n  Fetched {len(raw_clip_paths)} clips (Pexels)")
    final_path = str(pipeline.OUTPUT_DIR / "mindcore_ai_video.mp4")
    pipeline.assemble_cinematic_video(raw_clip_paths, audio_path, final_path, None, ass_path, scene_types=scene_types)
    return final_path

def _patched_generate_ad_script(app_facts, niche, client):
    ad_topic = random.choice(pipeline.AD_TOPICS)
    formula = random.choice(pipeline.HOOK_FORMULAS)
    hook_block = pipeline._build_hook_block(formula)
    print(f"  AD: {ad_topic['pain_point'][:65]}...")
    lp,hp = pipeline.WORD_TARGETS_AD["problem"]; ls,hs = pipeline.WORD_TARGETS_AD["story"]; lc,hc = pipeline.WORD_TARGETS_AD["solution_cta"]
    prompt = f"""You are writing a punchy cinematic voiceover ad script for MindCore AI. Target: 25-35 seconds.\n\nVIEWER: {niche['viewer_persona']}\nPAIN POINT: {ad_topic['pain_point']}\nINSIGHT: {ad_topic['insight']}\nFEATURE: {ad_topic['feature']}\n\n{hook_block}\n\nSCENES:\nhook -> problem ({lp}-{hp} words) -> story ({ls}-{hs} words -- mention MindCore AI ONCE as "a space that listens". NEVER say download, play, Google Play.) -> solution_cta ({lc}-{hc} words -- PURE EMOTIONAL RESOLUTION. NEVER say "Play now" or "Google Play".)\nBANNED: "free trial", "download now", "play now", "Google Play"\n\nReturn ONLY valid JSON:\n{{"video_type":"ad","topic":"{ad_topic['pain_point'][:55]}","seo_keyword":"AI mental health companion for men","render_format":"cinematic","hook_formula":"{formula['name']}","hook":{{"voiceover":"..."}},"problem":{{"voiceover":"..."}},"story":{{"voiceover":"..."}},"solution_cta":{{"voiceover":"..."}}}}"""
    return pipeline._call_claude_raw(prompt, client, max_tokens=800)

def _patched_upload(video_path, metadata, cfg, scheduled_date=None):
    if not pipeline.UPLOAD_POST_API_KEY: return {"skipped":True,"reason":"no API key"}
    user = cfg.get("upload_post_user","")
    if not user: return {"skipped":True,"reason":"no user configured"}
    data = [("user",user),("platform[]","tiktok"),("platform[]","youtube"),("title",metadata.get("tiktok_caption","")[:pipeline.TIKTOK_CAPTION_LIMIT]),("facebook_title",metadata.get("facebook_title","")[:255]),("facebook_description",metadata.get("facebook_description","")),("youtube_title",metadata.get("youtube_title","")[:pipeline.YOUTUBE_TITLE_LIMIT]),("youtube_description",metadata.get("youtube_description","")[:pipeline.YOUTUBE_DESCRIPTION_LIMIT]),("youtube_tags",metadata.get("youtube_tags","")),("first_comment",metadata.get("first_comment",""))]
    if scheduled_date: data.append(("scheduled_date",scheduled_date))
    try:
        with open(video_path,"rb") as f:
            resp = requests.post(pipeline.UPLOAD_POST_API_URL,headers={"Authorization":f"Apikey {pipeline.UPLOAD_POST_API_KEY}"},files=[("video",("mindcore_ai_video.mp4",f,"video/mp4"))],data=data,timeout=180)
        result = resp.json() if resp.headers.get("content-type","").startswith("application/json") else {"raw":resp.text}
        result["status_code"] = resp.status_code
        if scheduled_date: result["scheduled_date"] = scheduled_date
        print(f"  Upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}")
        if not resp.ok: print(f"  {resp.text[:300]}")
        return result
    except Exception as e:
        print(f"  Upload failed: {e}"); return {"error": str(e)}

pipeline.assemble_cinematic_video = _patched_assemble_cinematic_video
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
    print(f"\n  MindCore AI -- Male Cinematic Pipeline v8.9")
    print(f"  Run #{pipeline.GITHUB_RUN_NUMBER} | Mode: {mode.upper()} | Daily")
    print(f"  Pexels + xfade | ElevenLabs TTS | SERP: {SERP_COUNTRY.upper()}")
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
