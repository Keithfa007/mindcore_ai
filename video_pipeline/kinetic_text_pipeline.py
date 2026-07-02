#!/usr/bin/env python3
"""
MindCore AI — Kinetic Text Video Pipeline v4.1
===============================================
SERP-enriched cinematic word-by-word karaoke.
Supports GENDER env var: "male" (default) or "female".

v4.1: Gender support — switches ElevenLabs voice, script persona, viewer fallback.
v4.0: SERP research, dynamic backgrounds, SEO captions, topic history.
v3.1: Word-by-word karaoke, Montserrat font, Ken Burns AI background.
"""

import os, sys, json, random, subprocess, tempfile, datetime, time, math
from pathlib import Path
from anthropic import Anthropic
import requests

ANTHROPIC_API_KEY   = os.environ.get("ANTHROPIC_API_KEY", "")
ELEVENLABS_API_KEY  = os.environ.get("ELEVENLABS_API_KEY", "")
UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
UPLOAD_POST_USER    = os.environ.get("UPLOAD_POST_USER", "MindCoreAI")
FAL_KEY             = os.environ.get("FAL_KEY", "")
SERP_API_KEY        = os.environ.get("SERP_API_KEY", "")
GENDER              = os.environ.get("GENDER", "male").lower()
MALE_VOICE_ID       = "jfIS2w2yJi0grJZPyEsk"
FEMALE_VOICE_ID     = "uIZsnBL0YK1S5j69bAih"
ELEVENLABS_VOICE_ID = FEMALE_VOICE_ID if GENDER == "female" else MALE_VOICE_ID
ELEVENLABS_API_URL  = "https://api.elevenlabs.io/v1/text-to-speech"
SERP_API_URL        = "https://serpapi.com/search"
ANTHROPIC_MODEL     = "claude-sonnet-4-6"
GITHUB_RUN_NUMBER   = int(os.environ.get("GITHUB_RUN_NUMBER", "1"))
POST_HOUR_UTC       = int(os.environ.get("POST_HOUR_UTC", "15"))

OUTPUT_DIR = Path("video_pipeline/output_kinetic")
PIPELINE_DIR = Path("video_pipeline")
KEYWORDS_PATH = PIPELINE_DIR / "niche_keywords.json"
KINETIC_HISTORY_PATH = PIPELINE_DIR / "kinetic_topic_history.json"
WIDTH = 1080
HEIGHT = 1920
TOPIC_HISTORY_SIZE = 8

FALLBACK_ANGLES = [
    {"topic": "the mask we wear at work", "question": "Why do I pretend to be fine at work?", "instruction": "About hiding behind a performance of being okay. The exhaustion of pretending."},
    {"topic": "overthinking at 3am", "question": "Why can't I stop overthinking at night?", "instruction": "About the loop of thoughts that won't stop at night."},
    {"topic": "emotional numbness", "question": "Why do I feel numb and empty inside?", "instruction": "About going through the motions. Functioning but feeling nothing."},
    {"topic": "burnout nobody sees", "question": "Am I burned out or just lazy?", "instruction": "About the kind of exhaustion sleep doesn't fix."},
    {"topic": "loneliness in a room full of people", "question": "Why do I feel alone even around friends?", "instruction": "About the specific loneliness of being surrounded by people who don't really know you."},
    {"topic": "carrying everyone else", "question": "Who takes care of the person who takes care of everyone?", "instruction": "About being the strong one for so long you forgot what it feels like to ask for help."},
    {"topic": "sunday night dread", "question": "Why do I dread Mondays so much?", "instruction": "About that specific heavy feeling on Sunday evenings."},
    {"topic": "feeling disconnected from your own life", "question": "Why does nothing feel real anymore?", "instruction": "About watching your own life like you're behind glass."},
]

def load_keywords_data():
    if not KEYWORDS_PATH.exists(): return None
    with open(KEYWORDS_PATH) as f: return json.load(f)

def get_niche_for_today(keywords_data):
    if not keywords_data: return None
    days = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    today = days[datetime.datetime.utcnow().weekday()]
    niche_key = keywords_data.get("schedule", {}).get(today, list(keywords_data["niches"].keys())[0])
    niche = keywords_data["niches"].get(niche_key)
    if niche: print(f"  Niche: {niche['name']} ({today.capitalize()})")
    return niche

def load_topic_history():
    if KINETIC_HISTORY_PATH.exists():
        try: return json.loads(KINETIC_HISTORY_PATH.read_text())
        except: return []
    return []

def save_topic_history(history, new_topic):
    history.append(new_topic)
    KINETIC_HISTORY_PATH.write_text(json.dumps(history[-TOPIC_HISTORY_SIZE:], indent=2))

def serp_google(seed):
    resp = requests.get(SERP_API_URL, params={"engine":"google","q":seed,"api_key":SERP_API_KEY,"num":10,"hl":"en","gl":"us"}, timeout=30)
    resp.raise_for_status(); return resp.json()

def serp_autocomplete(seed):
    try:
        resp = requests.get(SERP_API_URL, params={"engine":"google_autocomplete","q":seed,"api_key":SERP_API_KEY,"hl":"en","gl":"us"}, timeout=30)
        resp.raise_for_status(); return [s.get("value","").strip() for s in resp.json().get("suggestions",[]) if s.get("value")]
    except: return []

def research_serp_candidates(seeds):
    candidates = []; seen = set(); sample = random.sample(seeds, min(3, len(seeds)))
    for seed in sample:
        try:
            data = serp_google(seed); paa_count = 0
            for q in data.get("related_questions", []):
                t = q.get("question","").strip()
                if t and t.lower() not in seen: seen.add(t.lower()); candidates.append({"text":t,"source":"paa","seed":seed}); paa_count += 1
            for r in data.get("related_searches", []):
                t = r.get("query","").strip()
                if t and t.lower() not in seen: seen.add(t.lower()); candidates.append({"text":t,"source":"related","seed":seed})
            print(f"  [SERP] '{seed[:50]}': {paa_count} PAA"); time.sleep(0.5)
        except Exception as e: print(f"  SERP failed for '{seed}': {e}")
    for seed in random.sample(sample, min(2, len(sample))):
        prefix = " ".join(seed.split()[:3])
        for t in serp_autocomplete(prefix):
            if t and t.lower() not in seen: seen.add(t.lower()); candidates.append({"text":t,"source":"autocomplete","seed":prefix})
        time.sleep(0.5)
    print(f"  Total SERP candidates: {len(candidates)}"); return candidates

def pick_topic_claude(candidates, client, topic_history, niche):
    if not candidates: return None
    cand_list = "\n".join(f"{i+1}. [{c['source'].upper()}] {c['text']}" for i, c in enumerate(candidates[:40]))
    history_note = ("\nRECENT TOPICS (DO NOT REPEAT):\n" + "\n".join(f"  - {t}" for t in topic_history) + "\n") if topic_history else ""
    prompt = f"""Select a topic for a raw, emotional TikTok video.\nNICHE: {niche['name']}\nVIEWER: {niche['viewer_persona']}\n{history_note}\nPick the single best topic. Favour emotional, specific topics.\n\nCANDIDATES:\n{cand_list}\n\nReturn ONLY valid JSON:\n{{"topic":"short topic","question":"question this person asks at night","keyword":"1-5 word SEO keyword","source":"paa|related|autocomplete","why":"one sentence"}}"""
    for attempt in range(3):
        try:
            result = client.messages.create(model=ANTHROPIC_MODEL, max_tokens=400, messages=[{"role":"user","content":prompt}]).content[0].text.strip()
            if result.startswith("```"): result = result.split("```")[1].lstrip("json").strip()
            parsed = json.loads(result); print(f"  Winner: '{parsed.get('keyword')}' [{parsed.get('source','?')}]"); return parsed
        except Exception as e:
            if attempt == 2: return None
    return None

def get_fallback_topic(topic_history):
    available = [a for a in FALLBACK_ANGLES if a["topic"] not in topic_history] or FALLBACK_ANGLES
    angle = available[GITHUB_RUN_NUMBER % len(available)]
    print(f"  Fallback: {angle['topic']}")
    return {"topic":angle["topic"],"question":angle["question"],"keyword":angle["topic"],"source":"fallback","instruction":angle.get("instruction","")}

def fetch_topic(client, niche, topic_history):
    if SERP_API_KEY and niche:
        try:
            candidates = research_serp_candidates(niche["seed_queries"])
            if candidates:
                topic = pick_topic_claude(candidates, client, topic_history, niche)
                if topic: topic["niche"] = niche["name"]; return topic
        except Exception as e: print(f"  SERP failed: {e}")
    return get_fallback_topic(topic_history)

def generate_script(client, topic, niche):
    question = topic.get("question", topic.get("topic", "")); keyword = topic.get("keyword", ""); instruction = topic.get("instruction", "")
    if niche: viewer = niche["viewer_persona"]
    elif GENDER == "female": viewer = "A woman in her late 30s who has been the strong one for everyone else. She is exhausted in a way nobody sees."
    else: viewer = "A man in his 40s who holds it together for everyone but is falling apart inside."
    angle_block = f"SPECIFIC DIRECTION: {instruction}" if instruction else f'The viewer is silently asking: "{question}"'
    if GENDER == "female":
        persona = "You are a woman speaking from real experience about mental health. You know what it feels like to hold everything together while falling apart inside. You are not a therapist. You are someone who has been through it."
        talk_style = "Write like a woman talking to her closest friend at midnight. Vulnerable, honest, no performance."
    else:
        persona = "You are Keith, founder of MindCore AI. 2 years clean after 15 years of hidden addiction."
        talk_style = "Write like a real person talking to himself at 2am. Vary sentence length. No corporate jargon."
    prompt = f"""{persona}
Write a short voiceover script for a TikTok video.

TOPIC: {topic.get('topic', keyword)}
{angle_block}
VIEWER: {viewer}

RULES:
- Exactly 4-5 sentences. Each sentence on its own line.
- Total length: 40-70 words. This will be spoken in 15-25 seconds.
- First person OR direct address ("you"). Raw. Honest. No filter.
- Each sentence should work as a standalone line of text on screen.
- NO emojis, NO hashtags, NO "hey guys", NO motivational cliches.
- Do NOT start with "I" more than twice.
- The first sentence must hit IMMEDIATELY. No setup. Punch first.

WRITING STYLE (MANDATORY):
- NEVER use em dashes. Use commas, periods, or separate sentences instead.
- NEVER use these AI-tell words: "delve", "tapestry", "landscape", "realm", "navigate", "leverage", "foster", "cultivate", "embark", "comprehensive", "multifaceted", "ever-evolving", "game-changer", "unlock", "unleash", "empower", "supercharge", "revolutionize".
- {talk_style}

Return ONLY the script lines. Nothing else."""
    for attempt in range(3):
        try:
            result = client.messages.create(model=ANTHROPIC_MODEL, max_tokens=200, messages=[{"role":"user","content":prompt}]).content[0].text.strip()
            lines = [l.strip() for l in result.split("\n") if l.strip()]
            print(f"  Script ({len(lines)} lines, {sum(len(l.split()) for l in lines)} words):")
            for l in lines: print(f"    > {l}")
            return lines
        except Exception as e:
            if attempt == 2: raise
    raise RuntimeError("Script generation failed")

def generate_seo_caption(client, script_lines, topic, niche):
    script_text = " ".join(script_lines); keyword = topic.get("keyword","mental health")
    niche_tags = " ".join(niche.get("hashtags",[])) if niche else ""
    prompt = f"""Write upload metadata for a raw mental health TikTok video.\n\nSCRIPT: "{script_text}"\nSEO KEYWORD: {keyword}\nNICHE HASHTAGS: {niche_tags}\n\nGenerate:\n- tiktok_caption: 1-2 raw sentences + 8-10 hashtags including #mindcoreai. Max 2200 chars.\n- youtube_title: punchy title under 100 chars with SEO keyword\n- youtube_description: 2 sentences. Blank line. "Try MindCore AI: https://mindcoreai.eu". 6-8 hashtags ending #Shorts.\n- facebook_description: 2 sentences + 4-5 hashtags including #mindcoreai\n\nNO emojis. Raw tone. NEVER use em dashes.\n\nReturn ONLY valid JSON:\n{{"tiktok_caption":"...","youtube_title":"...","youtube_description":"...","facebook_description":"..."}}"""
    try:
        result = client.messages.create(model=ANTHROPIC_MODEL, max_tokens=600, messages=[{"role":"user","content":prompt}]).content[0].text.strip()
        if result.startswith("```"): result = result.split("```")[1].lstrip("json").strip()
        return json.loads(result)
    except:
        tags = f"#mindcoreai #mentalhealth #fyp {niche_tags}".strip()
        return {"tiktok_caption":f"Some things need to be said.\n\n{tags}","youtube_title":"Mental Health","youtube_description":f"Try MindCore AI: https://mindcoreai.eu\n\n{tags} #Shorts","facebook_description":f"Some things need to be said.\n\n{tags}"}

def generate_bg_prompt(client, topic):
    question = topic.get("question", topic.get("topic", "mental health"))
    prompt = f"""Generate a short image prompt for a moody, cinematic background image.\n\nVIDEO TOPIC: "{question}"\n\nRequirements: atmospheric, cinematic, dark/moody, NO people, NO text, NO faces. Include lighting, colour palette, objects. Max 40 words.\n\nReturn ONLY the prompt."""
    try: return client.messages.create(model=ANTHROPIC_MODEL, max_tokens=100, messages=[{"role":"user","content":prompt}]).content[0].text.strip()
    except: return "dark moody atmospheric scene, cinematic film grain, melancholic, no people, no text"

def generate_background_image(bg_prompt, output_path):
    if not FAL_KEY: return None
    try:
        resp = requests.post("https://fal.run/fal-ai/flux/schnell", headers={"Authorization":f"Key {FAL_KEY}","Content-Type":"application/json"},
            json={"prompt":bg_prompt,"image_size":{"width":1080,"height":1920},"num_images":1,"num_inference_steps":4,"enable_safety_checker":False}, timeout=120)
        if not resp.ok: return None
        images = resp.json().get("images",[]); url = images[0].get("url") if images else None
        if not url: return None
        img_resp = requests.get(url, timeout=60)
        if img_resp.ok:
            with open(output_path,"wb") as f: f.write(img_resp.content)
            print(f"  Background: {os.path.getsize(output_path)//1024} KB"); return output_path
        return None
    except: return None

def prepare_emotional_text(script_lines):
    parts = []
    for i, line in enumerate(script_lines):
        parts.append(line)
        if i < len(script_lines) - 1: parts.append("...")
    return " ".join(parts)

def generate_voiceover(script_lines, output_path):
    if not ELEVENLABS_API_KEY: return False
    script_text = prepare_emotional_text(script_lines)
    try:
        resp = requests.post(f"{ELEVENLABS_API_URL}/{ELEVENLABS_VOICE_ID}",
            headers={"xi-api-key":ELEVENLABS_API_KEY,"Content-Type":"application/json"},
            json={"text":script_text,"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.30,"similarity_boost":0.65,"style":0.60,"use_speaker_boost":True}},
            stream=True, timeout=120)
        if not resp.ok: print(f"  ElevenLabs error {resp.status_code}"); return False
        with open(output_path,"wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk: f.write(chunk)
        print(f"  Voiceover: {os.path.getsize(output_path)//1024} KB [{GENDER}] [emotional]"); return True
    except Exception as e: print(f"  ElevenLabs failed: {e}"); return False

def get_word_timestamps(audio_path):
    try:
        import whisper; model = whisper.load_model("base")
        result = model.transcribe(audio_path, word_timestamps=True); words = []
        for seg in result.get("segments",[]): 
            for w in seg.get("words",[]): words.append({"word":w["word"].strip(),"start":w["start"],"end":w["end"]})
        print(f"  Whisper: {len(words)} words"); return words
    except Exception as e: print(f"  Whisper failed: {e}"); return None

def get_audio_duration(audio_path):
    return float(subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",audio_path],capture_output=True,text=True).stdout.strip())

def build_sentence_word_data(script_lines, word_timestamps, audio_duration):
    sentences = []; w_idx = 0; total_w = len(word_timestamps) if word_timestamps else 0
    for line in script_lines:
        sent = {"text":line,"words":[]}
        for word in line.split():
            if w_idx < total_w: wt = word_timestamps[w_idx]; sent["words"].append({"text":word,"start":wt["start"],"end":wt["end"]}); w_idx += 1
            else: last = sent["words"][-1]["end"] if sent["words"] else 0; sent["words"].append({"text":word,"start":last,"end":last+0.3})
        if sent["words"]: sent["start"] = sent["words"][0]["start"]; sent["end"] = sent["words"][-1]["end"]
        else: sent["start"] = sent["end"] = 0
        sentences.append(sent)
    return sentences

def ease_in_out(t): return t * t * (3 - 2 * t)

def build_word_positions(words, font, max_width, center_x, base_y, line_h):
    space_w = font.getbbox("n")[2] - font.getbbox("n")[0]
    lines = []; cur_line = []; cur_w = 0
    for i, word in enumerate(words):
        ww = font.getbbox(word["text"])[2] - font.getbbox(word["text"])[0]
        test = cur_w + (space_w if cur_line else 0) + ww
        if test <= max_width or not cur_line: cur_line.append({"idx":i,"text":word["text"],"w":ww}); cur_w = test
        else: lines.append((cur_line, cur_w)); cur_line = [{"idx":i,"text":word["text"],"w":ww}]; cur_w = ww
    if cur_line: lines.append((cur_line, cur_w))
    positions = [None] * len(words); y = base_y
    for line_words, line_width in lines:
        x = center_x - line_width // 2
        for lw in line_words: positions[lw["idx"]] = {"x":x,"y":y,"w":lw["w"]}; x += lw["w"] + space_w
        y += line_h
    return positions, len(lines)

def create_kinetic_video(audio_path, sentences, output_path, audio_duration, bg_image_path=None):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    import tempfile, shutil
    FPS = 24; total_frames = int((audio_duration + 0.5) * FPS); SENT_FADE_IN = 0.25; SENT_FADE_OUT = 0.20
    AMBER = (212,165,116); DIM = (90,90,110)
    font_main = None
    for p in ["/tmp/fonts/Montserrat-ExtraBold.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf","/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        try: font_main = ImageFont.truetype(p, 54); print(f"  Font: {os.path.basename(p)}"); break
        except: continue
    if not font_main: font_main = ImageFont.load_default()
    font_wm = None
    for p in ["/tmp/fonts/Montserrat-Medium.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf","/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]:
        try: font_wm = ImageFont.truetype(p, 22); break
        except: continue
    if not font_wm: font_wm = ImageFont.load_default()
    max_text_w = int(WIDTH * 0.84); line_h = 72; center_x = WIDTH // 2
    for sent in sentences:
        est = max(1, len(sent["words"]) // 4); base_y = (HEIGHT // 2) - (est * line_h // 2) - 20
        positions, n_lines = build_word_positions(sent["words"], font_main, max_text_w, center_x, base_y, line_h)
        base_y = (HEIGHT // 2) - (n_lines * line_h // 2) - 20
        positions, _ = build_word_positions(sent["words"], font_main, max_text_w, center_x, base_y, line_h)
        sent["positions"] = positions
    bg_source = None
    if bg_image_path and os.path.exists(bg_image_path):
        try: bg_source = Image.open(bg_image_path).convert("RGB"); bg_source = bg_source.resize((int(WIDTH*1.20),int(HEIGHT*1.20)),Image.LANCZOS); bg_source = ImageEnhance.Brightness(bg_source).enhance(0.32); print(f"  BG: AI image")
        except: bg_source = None
    if bg_source is None:
        bg_fallback = Image.new("RGB",(WIDTH,HEIGHT)); d = ImageDraw.Draw(bg_fallback)
        for y in range(HEIGHT): r=y/HEIGHT; e=r*r*(3-2*r); d.line([(0,y),(WIDTH,y)],fill=(int(12+(6-12)*e),int(16+(6-16)*e),int(32+(12-32)*e)))
    vignette = Image.new("RGBA",(WIDTH,HEIGHT),(0,0,0,0)); vd = ImageDraw.Draw(vignette)
    for y in range(350): vd.line([(0,y),(WIDTH,y)],fill=(0,0,0,int(200*(1.0-y/350))))
    for y in range(HEIGHT-350,HEIGHT): vd.line([(0,y),(WIDTH,y)],fill=(0,0,0,int(200*((y-(HEIGHT-350))/350))))
    wt="MindCore AI"; wb=font_wm.getbbox(wt); wm_x=(WIDTH-(wb[2]-wb[0]))//2; wm_y=HEIGHT-85
    bar_y=HEIGHT-38; bar_h=4; bar_m=80
    frames_dir = tempfile.mkdtemp(prefix="kinetic_"); print(f"  Rendering {total_frames} frames at {FPS}fps...")
    for fn in range(total_frames):
        t=fn/FPS; progress=t/audio_duration if audio_duration>0 else 0
        if bg_source is not None:
            zoom=1.0+0.15*progress; px=0.5+0.1*math.sin(progress*math.pi); py=0.5+0.05*math.cos(progress*math.pi*0.7)
            sw,sh=bg_source.size; cw,ch=int(WIDTH/zoom),int(HEIGHT/zoom)
            cx=max(0,min(int(px*(sw-cw)),sw-cw)); cy=max(0,min(int(py*(sh-ch)),sh-ch))
            frame=bg_source.crop((cx,cy,cx+cw,cy+ch)).resize((WIDTH,HEIGHT),Image.LANCZOS)
            frame=Image.alpha_composite(frame.convert("RGBA"),vignette).convert("RGB")
        else: frame=bg_fallback.copy()
        draw=ImageDraw.Draw(frame); active_idx=-1
        for i,s in enumerate(sentences):
            if t>=s["start"]: active_idx=i
        for si,sent in enumerate(sentences):
            is_active=(si==active_idx); is_outgoing=(si==active_idx-1) if active_idx>0 else False
            if not is_active and not is_outgoing: continue
            positions=sent.get("positions",[])
            if not positions or any(p is None for p in positions): continue
            if is_outgoing:
                next_s=sentences[active_idx]["start"]; fade_begin=next_s-SENT_FADE_OUT
                if t>=next_s: continue
                if t<fade_begin: alpha=1.0; y_off=0
                else: raw=(t-fade_begin)/SENT_FADE_OUT; alpha=1.0-ease_in_out(min(raw,1.0)); y_off=-int(30*ease_in_out(min(raw,1.0)))
                if alpha<0.03: continue
                for wi,w in enumerate(sent["words"]): pos=positions[wi]; draw.text((pos["x"],pos["y"]+y_off),w["text"],font=font_main,fill=(int(DIM[0]*alpha),int(DIM[1]*alpha),int(DIM[2]*alpha)))
            elif is_active:
                elapsed=t-sent["start"]; sent_alpha=ease_in_out(min(elapsed/SENT_FADE_IN,1.0)) if elapsed<SENT_FADE_IN else 1.0
                for wi,w in enumerate(sent["words"]):
                    if w["start"]<=t<w["end"]:
                        pos=positions[wi]; glow=Image.new("RGBA",(WIDTH,HEIGHT),(0,0,0,0)); gd=ImageDraw.Draw(glow)
                        gd.text((pos["x"],pos["y"]),w["text"],font=font_main,fill=(AMBER[0],AMBER[1],AMBER[2],int(100*sent_alpha)))
                        glow=glow.filter(ImageFilter.GaussianBlur(radius=14)); frame=Image.alpha_composite(frame.convert("RGBA"),glow).convert("RGB"); draw=ImageDraw.Draw(frame); break
                for wi,w in enumerate(sent["words"]):
                    pos=positions[wi]; word_active=w["start"]<=t<w["end"]; word_started=t>=w["start"]
                    if word_active: c=(int(255*sent_alpha),)*3
                    elif word_started: c=(int(240*sent_alpha),)*3
                    else: c=(int(DIM[0]*sent_alpha),int(DIM[1]*sent_alpha),int(DIM[2]*sent_alpha))
                    draw.text((pos["x"]+2,pos["y"]+2),w["text"],font=font_main,fill=(int(20*sent_alpha),)*3)
                    draw.text((pos["x"],pos["y"]),w["text"],font=font_main,fill=c)
        draw.text((wm_x,wm_y),wt,font=font_wm,fill=(180,180,200))
        if audio_duration>0:
            bp=min(t/audio_duration,1.0); bw=WIDTH-2*bar_m
            draw.rectangle([(bar_m,bar_y),(WIDTH-bar_m,bar_y+bar_h)],fill=(40,40,60))
            fw=int(bw*bp)
            if fw>0: draw.rectangle([(bar_m,bar_y),(bar_m+fw,bar_y+bar_h)],fill=AMBER)
        frame.save(os.path.join(frames_dir,f"frame_{fn:05d}.png"),"PNG")
        if fn%(FPS*5)==0: print(f"    Frame {fn}/{total_frames} ({t:.1f}s)")
    print("  Encoding..."); cmd=["ffmpeg","-y","-framerate",str(FPS),"-i",os.path.join(frames_dir,"frame_%05d.png"),"-i",audio_path,"-c:v","libx264","-preset","fast","-crf","20","-c:a","aac","-b:a","128k","-pix_fmt","yuv420p","-shortest",output_path]
    result=subprocess.run(cmd,capture_output=True,text=True); shutil.rmtree(frames_dir,ignore_errors=True)
    if result.returncode!=0: raise RuntimeError(f"FFmpeg failed: {result.stderr[-500:]}")
    print(f"  Video: {os.path.getsize(output_path)/(1024*1024):.1f} MB, {audio_duration:.1f}s")

def get_scheduled_time(hour_utc):
    now=datetime.datetime.utcnow(); target=now.replace(hour=hour_utc,minute=0,second=0,microsecond=0)
    if now>=target: target+=datetime.timedelta(days=1)
    return target.strftime("%Y-%m-%dT%H:%M:%SZ")

def upload_video(video_path, metadata, scheduled_date=None):
    if not UPLOAD_POST_API_KEY: return {"skipped":True}
    data=[("user",UPLOAD_POST_USER),("platform[]","tiktok"),("platform[]","facebook"),("platform[]","youtube"),
        ("title",metadata.get("tiktok_caption","")[:2200]),("facebook_title",metadata.get("facebook_description","")[:255]),
        ("facebook_description",metadata.get("facebook_description","")),("youtube_title",metadata.get("youtube_title","")[:100]),
        ("youtube_description",metadata.get("youtube_description","")),("youtube_tags","mental health,recovery,mindcore ai,healing")]
    if scheduled_date: data.append(("scheduled_date",scheduled_date))
    try:
        with open(video_path,"rb") as f:
            resp=requests.post("https://api.upload-post.com/api/upload",headers={"Authorization":f"Apikey {UPLOAD_POST_API_KEY}"},
                files=[("video",("kinetic.mp4",f,"video/mp4"))],data=data,timeout=180)
        result=resp.json() if "json" in resp.headers.get("content-type","") else {"raw":resp.text}
        result["status_code"]=resp.status_code; print(f"  Upload {'OK' if resp.ok else 'WARN'}: {resp.status_code}"); return result
    except Exception as e: print(f"  Upload failed: {e}"); return {"error":str(e)}

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"== MindCore AI - Kinetic Text v4.1 | {GENDER.upper()} ==")
    print(f"  Run #{GITHUB_RUN_NUMBER} | Voice: {ELEVENLABS_VOICE_ID[:8]}... | Post: {POST_HOUR_UTC}:00 UTC")
    if not ANTHROPIC_API_KEY: sys.exit("ERROR: ANTHROPIC_API_KEY not set")
    client = Anthropic(api_key=ANTHROPIC_API_KEY); scheduled_date = get_scheduled_time(POST_HOUR_UTC)
    keywords_data = load_keywords_data(); niche = get_niche_for_today(keywords_data) if keywords_data else None
    topic_history = load_topic_history()
    if topic_history: print(f"  Avoiding: {topic_history}")
    with tempfile.TemporaryDirectory() as tmp:
        audio_path=os.path.join(tmp,"voiceover.mp3"); video_path=os.path.join(tmp,"kinetic.mp4"); bg_path=os.path.join(tmp,"bg.png")
        print("\n1. SERP research..."); topic=fetch_topic(client,niche,topic_history)
        print(f"  Topic: {topic.get('topic')} | Keyword: {topic.get('keyword')} | Source: {topic.get('source')}")
        print("\n2. Script..."); script_lines=generate_script(client,topic,niche)
        print("\n3. SEO captions..."); metadata=generate_seo_caption(client,script_lines,topic,niche)
        print(f"  YT: {metadata.get('youtube_title','')[:60]}")
        print("\n4. Background..."); bg_prompt=generate_bg_prompt(client,topic); bg_result=generate_background_image(bg_prompt,bg_path)
        print("\n5. Voiceover..."); 
        if not generate_voiceover(script_lines,audio_path): sys.exit("ERROR: Voiceover failed")
        print("\n6. Whisper..."); word_timestamps=get_word_timestamps(audio_path); audio_duration=get_audio_duration(audio_path); print(f"  Duration: {audio_duration:.1f}s")
        print("\n7. Word data..."); sentences=build_sentence_word_data(script_lines,word_timestamps,audio_duration)
        for s in sentences: print(f"  [{s['start']:.1f}-{s['end']:.1f}s] {s['text']}")
        print("\n8. Render..."); create_kinetic_video(audio_path,sentences,video_path,audio_duration,bg_image_path=bg_result)
        import shutil; shutil.copy2(video_path,OUTPUT_DIR/f"kinetic_{GENDER}_{GITHUB_RUN_NUMBER}.mp4")
        if bg_result and os.path.exists(bg_result): shutil.copy2(bg_result,OUTPUT_DIR/f"bg_{GENDER}_{GITHUB_RUN_NUMBER}.png")
        print("\n9. Upload..."); result=upload_video(video_path,metadata,scheduled_date=scheduled_date)
    save_topic_history(topic_history,topic.get("keyword",topic.get("topic","")))
    (OUTPUT_DIR/"kinetic_metadata.json").write_text(json.dumps({"run":GITHUB_RUN_NUMBER,"gender":GENDER,"topic":topic,"niche":niche.get("name") if niche else "fallback","script":script_lines,"metadata":metadata,"scheduled":scheduled_date,"bg":bool(bg_result)},indent=2))
    print(f"\n== Done | {GENDER.upper()} | {topic.get('keyword')} ==")

if __name__ == "__main__": main()
