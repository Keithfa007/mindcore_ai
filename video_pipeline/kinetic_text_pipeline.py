#!/usr/bin/env python3
"""
MindCore AI — Kinetic Text Video Pipeline v4.3
===============================================
SERP-enriched cinematic word-by-word karaoke.
Supports GENDER env var: "male" (default) or "female".

v4.3: Shorter punchier lines (max 7 words per line) for cleaner on-screen text.
v4.2: Outlined text with warm highlight, brighter scenic backgrounds, brightness floor.
v4.1: Gender support — switches voice, persona, keywords file, SERP seeds.
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
KEYWORDS_PATH = PIPELINE_DIR / ("niche_keywords_female.json" if GENDER == "female" else "niche_keywords.json")
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
    history.append(new_topic); KINETIC_HISTORY_PATH.write_text(json.dumps(history[-TOPIC_HISTORY_SIZE:], indent=2))
def serp_google(seed):
    resp = requests.get(SERP_API_URL, params={"engine":"google","q":seed,"api_key":SERP_API_KEY,"num":10,"hl":"en","gl":"us"}, timeout=30); resp.raise_for_status(); return resp.json()
def serp_autocomplete(seed):
    try:
        resp = requests.get(SERP_API_URL, params={"engine":"google_autocomplete","q":seed,"api_key":SERP_API_KEY,"hl":"en","gl":"us"}, timeout=30); resp.raise_for_status()
        return [s.get("value","").strip() for s in resp.json().get("suggestions",[]) if s.get("value")]
    except: return []
def research_serp_candidates(seeds):
    candidates = []; seen = set(); sample = random.sample(seeds, min(3, len(seeds)))
    for seed in sample:
        try:
            data = serp_google(seed); paa_count = 0
            for q in data.get("related_questions", []): t = q.get("question","").strip(); (seen.add(t.lower()) or candidates.append({"text":t,"source":"paa","seed":seed})) if t and t.lower() not in seen else None; paa_count += 1 if t and t.lower() not in seen else 0
            for r in data.get("related_searches", []): t = r.get("query","").strip(); (seen.add(t.lower()) or candidates.append({"text":t,"source":"related","seed":seed})) if t and t.lower() not in seen else None
            print(f"  [SERP] '{seed[:50]}': {paa_count} PAA"); time.sleep(0.5)
        except Exception as e: print(f"  SERP failed for '{seed}': {e}")
    for seed in random.sample(sample, min(2, len(sample))):
        prefix = " ".join(seed.split()[:3])
        for t in serp_autocomplete(prefix):
            if t and t.lower() not in seen: seen.add(t.lower()); candidates.append({"text":t,"source":"autocomplete","seed":prefix})
        time.sleep(0.5)
    print(f"  SERP candidates: {len(candidates)}"); return candidates
def pick_topic_claude(candidates, client, topic_history, niche):
    if not candidates: return None
    cand_list = "\n".join(f"{i+1}. [{c['source'].upper()}] {c['text']}" for i, c in enumerate(candidates[:40]))
    history_note = ("\nRECENT (DO NOT REPEAT):\n" + "\n".join(f"  - {t}" for t in topic_history) + "\n") if topic_history else ""
    prompt = f"""Select a topic for a raw, emotional TikTok video.\nNICHE: {niche['name']}\nVIEWER: {niche['viewer_persona']}\n{history_note}\nPick the best topic. Favour emotional, specific topics.\n\nCANDIDATES:\n{cand_list}\n\nReturn ONLY valid JSON:\n{{"topic":"short topic","question":"question this person asks at night","keyword":"1-5 word SEO keyword","source":"paa|related|autocomplete","why":"one sentence"}}"""
    for attempt in range(3):
        try:
            result = client.messages.create(model=ANTHROPIC_MODEL, max_tokens=400, messages=[{"role":"user","content":prompt}]).content[0].text.strip()
            if result.startswith("```"): result = result.split("```")[1].lstrip("json").strip()
            parsed = json.loads(result); print(f"  Winner: '{parsed.get('keyword')}' [{parsed.get('source','?')}]"); return parsed
        except: pass
    return None
def get_fallback_topic(topic_history):
    available = [a for a in FALLBACK_ANGLES if a["topic"] not in topic_history] or FALLBACK_ANGLES
    angle = available[GITHUB_RUN_NUMBER % len(available)]; print(f"  Fallback: {angle['topic']}")
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
- Exactly 5-7 short lines. Each line on its own line.
- MAX 7 words per line. Think poetry, not paragraphs.
- Total length: 30-50 words. 12-20 seconds spoken.
- First person OR direct address ("you"). Raw. Honest. No filter.
- Each line must work as standalone text on screen.
- NO emojis, NO hashtags, NO "hey guys", NO motivational cliches.
- Do NOT start with "I" more than twice.
- First line must hit IMMEDIATELY. No setup. Punch first.

WRITING STYLE (MANDATORY):
- NEVER use em dashes. Use commas, periods, or separate sentences.
- NEVER use: "delve", "tapestry", "landscape", "realm", "navigate", "leverage", "foster", "cultivate", "embark", "comprehensive", "multifaceted", "ever-evolving", "game-changer", "unlock", "unleash", "empower", "supercharge", "revolutionize".
- {talk_style}

Return ONLY the script lines."""
    for attempt in range(3):
        try:
            result = client.messages.create(model=ANTHROPIC_MODEL, max_tokens=200, messages=[{"role":"user","content":prompt}]).content[0].text.strip()
            lines = [l.strip() for l in result.split("\n") if l.strip()]
            print(f"  Script ({len(lines)} lines, {sum(len(l.split()) for l in lines)} words):")
            for l in lines: print(f"    > {l}")
            return lines
        except Exception as e:
            if attempt == 2: raise
    raise RuntimeError("Script failed")
def generate_seo_caption(client, script_lines, topic, niche):
    script_text = " ".join(script_lines); keyword = topic.get("keyword","mental health"); niche_tags = " ".join(niche.get("hashtags",[])) if niche else ""
    prompt = f"""Upload metadata for a raw mental health TikTok.\n\nSCRIPT: "{script_text}"\nSEO KEYWORD: {keyword}\nNICHE HASHTAGS: {niche_tags}\n\nGenerate:\n- tiktok_caption: 1-2 raw sentences + 8-10 hashtags incl #mindcoreai. Max 2200.\n- youtube_title: punchy <100 chars with SEO keyword\n- youtube_description: 2 sentences. "Try MindCore AI: https://mindcoreai.eu". 6-8 hashtags #Shorts.\n- x_caption: 1-2 punchy sentences + 2-3 hashtags incl #mindcoreai. Max 250 chars total. No hashtag spam.
- facebook_description: 2 sentences + 4-5 hashtags incl #mindcoreai\n\nNO emojis. Raw tone. No em dashes.\n\nReturn ONLY valid JSON:\n{{"tiktok_caption":"...","youtube_title":"...","youtube_description":"...","x_caption":"...","facebook_description":"..."}}"""
    try:
        result = client.messages.create(model=ANTHROPIC_MODEL, max_tokens=600, messages=[{"role":"user","content":prompt}]).content[0].text.strip()
        if result.startswith("```"): result = result.split("```")[1].lstrip("json").strip()
        return json.loads(result)
    except:
        tags = f"#mindcoreai #mentalhealth #fyp {niche_tags}".strip()
        return {"tiktok_caption":f"Some things need to be said.\n\n{tags}","youtube_title":"Mental Health","youtube_description":f"Try MindCore AI: https://mindcoreai.eu\n\n{tags} #Shorts","facebook_description":f"Some things need to be said.\n\n{tags}"}
def generate_bg_prompt(client, topic):
    question = topic.get("question", topic.get("topic", "mental health"))
    print(f"  BG topic: {question}")
    try: return client.messages.create(model=ANTHROPIC_MODEL, max_tokens=100, messages=[{"role":"user","content":f"""Create an image prompt for a cinematic TikTok background that DIRECTLY illustrates this topic:

TOPIC: "{question}"

RULES:
- The image must visually represent the SPECIFIC emotion or concept in the topic
- Use symbolic or metaphorical imagery: broken objects, empty spaces, silhouettes from behind, hands, shadows, mirrors, clocks, chains, open doors, abandoned places, storms, paths
- Silhouettes and figures seen from behind or far away are OK but must be FULLY CLOTHED (jacket, hoodie, coat, shirt)
- STRICTLY NO nudity, NO bare skin, NO shirtless figures, NO exposed bodies, NO underwear, NO swimwear
- NO close-up faces, NO readable text, NO logos
- Moody, cinematic lighting. Dark enough for white text overlay but NOT pitch black
- High visual impact. This must stop someone scrolling on TikTok.
- SAFE FOR ALL AUDIENCES. Content must pass TikTok community guidelines.
- Max 40 words

EXAMPLES:
- "anger in recovery" -> "silhouette of man in hoodie punching wall in dark hallway, plaster dust in shaft of light, moody blue and amber tones, cinematic"
- "feeling invisible" -> "transparent ghostly figure in winter coat standing in crowded subway station, motion blur of people walking through them, cold blue tones"
- "anxiety at 2am" -> "person in t-shirt sitting on edge of bed in dark room, blue phone glow seen from behind, moonlight through window, insomnia"
- "carrying everything alone" -> "clothed figure carrying enormous bundle on back walking up endless staircase, dramatic overhead light, exhaustion"

Return ONLY the prompt."""}]).content[0].text.strip()
    except: return "lone silhouette in dark jacket standing at end of long corridor, single shaft of warm light ahead, moody cinematic atmosphere, emotional"
def generate_background_image(bg_prompt, output_path):
    if not FAL_KEY: return None
    try:
        resp = requests.post("https://fal.run/fal-ai/flux/schnell", headers={"Authorization":f"Key {FAL_KEY}","Content-Type":"application/json"},
            json={"prompt":bg_prompt,"image_size":{"width":1080,"height":1920},"num_images":1,"num_inference_steps":4,"enable_safety_checker":True}, timeout=120)
        if not resp.ok: return None
        images = resp.json().get("images",[]); url = images[0].get("url") if images else None
        if not url: return None
        img_resp = requests.get(url, timeout=60)
        if img_resp.ok:
            with open(output_path,"wb") as f: f.write(img_resp.content)
            print(f"  Background: {os.path.getsize(output_path)//1024} KB"); return output_path
        return None
    except: return None
def prepare_emotional_text(lines):
    parts = []
    for i, line in enumerate(lines): parts.append(line); parts.append("...") if i < len(lines) - 1 else None
    return " ".join(parts)
def generate_voiceover(script_lines, output_path):
    if not ELEVENLABS_API_KEY: return False
    try:
        resp = requests.post(f"{ELEVENLABS_API_URL}/{ELEVENLABS_VOICE_ID}", headers={"xi-api-key":ELEVENLABS_API_KEY,"Content-Type":"application/json"},
            json={"text":prepare_emotional_text(script_lines),"model_id":"eleven_multilingual_v2","voice_settings":{"stability":0.30,"similarity_boost":0.65,"style":0.60,"use_speaker_boost":True}}, stream=True, timeout=120)
        if not resp.ok: print(f"  ElevenLabs error {resp.status_code}"); return False
        with open(output_path,"wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if chunk: f.write(chunk)
        print(f"  Voiceover: {os.path.getsize(output_path)//1024} KB [{GENDER}]"); return True
    except Exception as e: print(f"  ElevenLabs failed: {e}"); return False
def get_word_timestamps(audio_path):
    try:
        import whisper; model = whisper.load_model("base"); result = model.transcribe(audio_path, word_timestamps=True); words = []
        for seg in result.get("segments",[]): 
            for w in seg.get("words",[]): words.append({"word":w["word"].strip(),"start":w["start"],"end":w["end"]})
        print(f"  Whisper: {len(words)} words"); return words
    except Exception as e: print(f"  Whisper failed: {e}"); return None
def get_audio_duration(p): return float(subprocess.run(["ffprobe","-v","quiet","-show_entries","format=duration","-of","csv=p=0",p],capture_output=True,text=True).stdout.strip())
def build_sentence_word_data(script_lines, wts, dur):
    sentences = []; wi = 0; tw = len(wts) if wts else 0
    for line in script_lines:
        s = {"text":line,"words":[]}
        for word in line.split():
            if wi < tw: wt = wts[wi]; s["words"].append({"text":word,"start":wt["start"],"end":wt["end"]}); wi += 1
            else: last = s["words"][-1]["end"] if s["words"] else 0; s["words"].append({"text":word,"start":last,"end":last+0.3})
        if s["words"]: s["start"] = s["words"][0]["start"]; s["end"] = s["words"][-1]["end"]
        else: s["start"] = s["end"] = 0
        sentences.append(s)
    return sentences
def ease_in_out(t): return t * t * (3 - 2 * t)
def build_word_positions(words, font, max_w, cx, by, lh):
    sw = font.getbbox("n")[2] - font.getbbox("n")[0]; lines = []; cl = []; cw = 0
    for i, w in enumerate(words):
        ww = font.getbbox(w["text"])[2] - font.getbbox(w["text"])[0]; test = cw + (sw if cl else 0) + ww
        if test <= max_w or not cl: cl.append({"idx":i,"text":w["text"],"w":ww}); cw = test
        else: lines.append((cl, cw)); cl = [{"idx":i,"text":w["text"],"w":ww}]; cw = ww
    if cl: lines.append((cl, cw))
    pos = [None] * len(words); y = by
    for lw, lwid in lines:
        x = cx - lwid // 2
        for w in lw: pos[w["idx"]] = {"x":x,"y":y,"w":w["w"]}; x += w["w"] + sw
        y += lh
    return pos, len(lines)
def pick_background_music():
    music_dir = PIPELINE_DIR / "music"
    tracks = [f for f in music_dir.glob("*.mp3") if f.stat().st_size > 10000]
    if not tracks:
        print("  No music tracks found")
        return None
    track = random.choice(tracks)
    print(f"  BG music: {track.name}")
    return str(track)

def create_kinetic_video(audio_path, sentences, output_path, audio_duration, bg_image_path=None):
    from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
    import tempfile, shutil
    FPS=24; tf=int((audio_duration+0.5)*FPS); FI=0.25; FO=0.20; AM=(255,180,80); HL=(255,220,140); DM=(180,180,195); OC=(0,0,0); SW=3
    fm = None
    for p in ["/tmp/fonts/Montserrat-ExtraBold.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf","/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf"]:
        try: fm = ImageFont.truetype(p, 58); print(f"  Font: {os.path.basename(p)}"); break
        except: continue
    if not fm: fm = ImageFont.load_default()
    fw = None
    for p in ["/tmp/fonts/Montserrat-Medium.ttf","/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf","/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"]:
        try: fw = ImageFont.truetype(p, 22); break
        except: continue
    if not fw: fw = ImageFont.load_default()
    mtw=int(WIDTH*0.84); lh=72; cx=WIDTH//2
    for s in sentences:
        est=max(1,len(s["words"])//4); by=(HEIGHT//2)-(est*lh//2)-20
        ps,nl = build_word_positions(s["words"],fm,mtw,cx,by,lh); by=(HEIGHT//2)-(nl*lh//2)-20
        ps,_ = build_word_positions(s["words"],fm,mtw,cx,by,lh); s["positions"]=ps
    bg = None
    if bg_image_path and os.path.exists(bg_image_path):
        try:
            bg=Image.open(bg_image_path).convert("RGB"); bg=bg.resize((int(WIDTH*1.2),int(HEIGHT*1.2)),Image.LANCZOS)
            bg_brightness = sum(bg.resize((1,1)).getpixel((0,0))) / 3
            brightness_factor = 0.55 if bg_brightness > 80 else 0.65
            bg=ImageEnhance.Brightness(bg).enhance(brightness_factor); print(f"  BG: AI image (avg={bg_brightness:.0f}, factor={brightness_factor})")
        except: bg=None
    if bg is None:
        bf=Image.new("RGB",(WIDTH,HEIGHT)); d=ImageDraw.Draw(bf)
        for y in range(HEIGHT): r=y/HEIGHT; e=r*r*(3-2*r); d.line([(0,y),(WIDTH,y)],fill=(int(12+(6-12)*e),int(16+(6-16)*e),int(32+(12-32)*e)))
    vi=Image.new("RGBA",(WIDTH,HEIGHT),(0,0,0,0)); vd=ImageDraw.Draw(vi)
    for y in range(350): vd.line([(0,y),(WIDTH,y)],fill=(0,0,0,int(200*(1.0-y/350))))
    for y in range(HEIGHT-350,HEIGHT): vd.line([(0,y),(WIDTH,y)],fill=(0,0,0,int(200*((y-(HEIGHT-350))/350))))
    wt="MindCore AI"; wb=fw.getbbox(wt); wmx=(WIDTH-(wb[2]-wb[0]))//2; wmy=HEIGHT-85; bary=HEIGHT-38; barh=4; barm=80
    fd=tempfile.mkdtemp(prefix="kinetic_"); print(f"  Rendering {tf} frames at {FPS}fps...")
    for fn in range(tf):
        t=fn/FPS; pr=t/audio_duration if audio_duration>0 else 0
        if bg is not None:
            zm=1.0+0.15*pr; px=0.5+0.1*math.sin(pr*math.pi); py=0.5+0.05*math.cos(pr*math.pi*0.7)
            sw,sh=bg.size; cw,ch=int(WIDTH/zm),int(HEIGHT/zm)
            ccx=max(0,min(int(px*(sw-cw)),sw-cw)); ccy=max(0,min(int(py*(sh-ch)),sh-ch))
            frame=bg.crop((ccx,ccy,ccx+cw,ccy+ch)).resize((WIDTH,HEIGHT),Image.LANCZOS)
            frame=Image.alpha_composite(frame.convert("RGBA"),vi).convert("RGB")
        else: frame=bf.copy()
        draw=ImageDraw.Draw(frame); ai=-1
        for i,s in enumerate(sentences):
            if t>=s["start"]: ai=i
        for si,s in enumerate(sentences):
            ia=(si==ai); io=(si==ai-1) if ai>0 else False
            if not ia and not io: continue
            ps=s.get("positions",[]); 
            if not ps or any(p is None for p in ps): continue
            if io:
                ns=sentences[ai]["start"]; fb=ns-FO
                if t>=ns: continue
                if t<fb: a=1.0; yo=0
                else: raw=(t-fb)/FO; a=1.0-ease_in_out(min(raw,1.0)); yo=-int(30*ease_in_out(min(raw,1.0)))
                if a<0.03: continue
                for wi,w in enumerate(s["words"]): p=ps[wi]; draw.text((p["x"],p["y"]+yo),w["text"],font=fm,fill=(int(DM[0]*a),int(DM[1]*a),int(DM[2]*a)),stroke_width=SW,stroke_fill=(int(OC[0]),int(OC[1]),int(OC[2]),int(255*a)))
            elif ia:
                el=t-s["start"]; sa=ease_in_out(min(el/FI,1.0)) if el<FI else 1.0
                for wi,w in enumerate(s["words"]):
                    p=ps[wi]; wa=w["start"]<=t<w["end"]; ws=t>=w["start"]
                    if wa: c=(int(HL[0]*sa),int(HL[1]*sa),int(HL[2]*sa))
                    elif ws: c=(int(255*sa),)*3
                    else: c=(int(DM[0]*sa),int(DM[1]*sa),int(DM[2]*sa))
                    draw.text((p["x"],p["y"]),w["text"],font=fm,fill=c,stroke_width=SW,stroke_fill=(int(OC[0]),int(OC[1]),int(OC[2]),int(255*sa)))
        draw.text((wmx,wmy),wt,font=fw,fill=(180,180,200))
        if audio_duration>0:
            bp=min(t/audio_duration,1.0); bw=WIDTH-2*barm
            draw.rectangle([(barm,bary),(WIDTH-barm,bary+barh)],fill=(40,40,60))
            fwi=int(bw*bp)
            if fwi>0: draw.rectangle([(barm,bary),(barm+fwi,bary+barh)],fill=AM)
        frame.save(os.path.join(fd,f"frame_{fn:05d}.png"),"PNG")
        if fn%(FPS*5)==0: print(f"    Frame {fn}/{tf} ({t:.1f}s)")
    music_path = pick_background_music()
    print("  Encoding...")
    if music_path:
        fade_out_start = max(0, audio_duration - 2)
        cmd=["ffmpeg","-y","-framerate",str(FPS),"-i",os.path.join(fd,"frame_%05d.png"),"-i",audio_path,"-i",music_path,
            "-filter_complex",f"[2:a]volume=0.12,afade=t=in:d=2,afade=t=out:st={fade_out_start:.1f}:d=2[bg];[1:a][bg]amix=inputs=2:duration=first:dropout_transition=2[aout]",
            "-map","0:v","-map","[aout]","-c:v","libx264","-preset","fast","-crf","20","-c:a","aac","-b:a","128k","-pix_fmt","yuv420p","-shortest",output_path]
    else:
        cmd=["ffmpeg","-y","-framerate",str(FPS),"-i",os.path.join(fd,"frame_%05d.png"),"-i",audio_path,"-c:v","libx264","-preset","fast","-crf","20","-c:a","aac","-b:a","128k","-pix_fmt","yuv420p","-shortest",output_path]
    result=subprocess.run(cmd,capture_output=True,text=True); shutil.rmtree(fd,ignore_errors=True)
    if result.returncode!=0: raise RuntimeError(f"FFmpeg failed: {result.stderr[-500:]}")
    print(f"  Video: {os.path.getsize(output_path)/(1024*1024):.1f} MB, {audio_duration:.1f}s")
def get_scheduled_time(h):
    now=datetime.datetime.utcnow(); t=now.replace(hour=h,minute=0,second=0,microsecond=0)
    if now>=t: t+=datetime.timedelta(days=1)
    return t.strftime("%Y-%m-%dT%H:%M:%SZ")
def upload_video(video_path, metadata, scheduled_date=None):
    if not UPLOAD_POST_API_KEY: return {"skipped":True}
    data=[("user",UPLOAD_POST_USER),("platform[]","tiktok"),("platform[]","facebook"),("platform[]","x"),("title",metadata.get("tiktok_caption","")[:2200]),("facebook_title",metadata.get("facebook_description","")[:255]),("x_title",metadata.get("x_caption",metadata.get("tiktok_caption",""))[:250]),("facebook_description",metadata.get("facebook_description","")),("youtube_title",metadata.get("youtube_title","")[:100]),("youtube_description",metadata.get("youtube_description","")),("youtube_tags","mental health,recovery,mindcore ai,healing")]
    if scheduled_date: data.append(("scheduled_date",scheduled_date))
    try:
        with open(video_path,"rb") as f:
            resp=requests.post("https://api.upload-post.com/api/upload",headers={"Authorization":f"Apikey {UPLOAD_POST_API_KEY}"},files=[("video",("kinetic.mp4",f,"video/mp4"))],data=data,timeout=180)
        r=resp.json() if "json" in resp.headers.get("content-type","") else {"raw":resp.text}; r["status_code"]=resp.status_code; print(f"  Upload {'OK' if resp.ok else 'WARN'}: {resp.status_code}")
        if not resp.ok: print(f"  {resp.text[:400]}")
        return r
    except Exception as e: print(f"  Upload failed: {e}"); return {"error":str(e)}
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    print(f"== MindCore AI - Kinetic Text v4.3 | {GENDER.upper()} ==")
    print(f"  Run #{GITHUB_RUN_NUMBER} | Voice: {ELEVENLABS_VOICE_ID[:8]}... | Post: {POST_HOUR_UTC}:00 UTC")
    if not ANTHROPIC_API_KEY: sys.exit("ERROR: ANTHROPIC_API_KEY not set")
    client = Anthropic(api_key=ANTHROPIC_API_KEY); sd = get_scheduled_time(POST_HOUR_UTC)
    kd = load_keywords_data(); niche = get_niche_for_today(kd) if kd else None; th = load_topic_history()
    if th: print(f"  Avoiding: {th}")
    with tempfile.TemporaryDirectory() as tmp:
        ap=os.path.join(tmp,"vo.mp3"); vp=os.path.join(tmp,"k.mp4"); bp=os.path.join(tmp,"bg.png")
        print("\n1. SERP research..."); topic=fetch_topic(client,niche,th)
        print(f"  Topic: {topic.get('topic')} | Keyword: {topic.get('keyword')} | Source: {topic.get('source')}")
        print("\n2. Script..."); sl=generate_script(client,topic,niche)
        print("\n3. SEO captions..."); md=generate_seo_caption(client,sl,topic,niche); print(f"  YT: {md.get('youtube_title','')[:60]}")
        print("\n4. Background..."); bgp=generate_bg_prompt(client,topic); bgr=generate_background_image(bgp,bp)
        print("\n5. Voiceover...");
        if not generate_voiceover(sl,ap): sys.exit("ERROR: Voiceover failed")
        print("\n6. Whisper..."); wts=get_word_timestamps(ap); dur=get_audio_duration(ap); print(f"  Duration: {dur:.1f}s")
        print("\n7. Word data..."); sents=build_sentence_word_data(sl,wts,dur)
        for s in sents: print(f"  [{s['start']:.1f}-{s['end']:.1f}s] {s['text']}")
        print("\n8. Render..."); create_kinetic_video(ap,sents,vp,dur,bg_image_path=bgr)
        import shutil; shutil.copy2(vp,OUTPUT_DIR/f"kinetic_{GENDER}_{GITHUB_RUN_NUMBER}.mp4")
        if bgr and os.path.exists(bgr): shutil.copy2(bgr,OUTPUT_DIR/f"bg_{GENDER}_{GITHUB_RUN_NUMBER}.png")
        print("\n9. Upload..."); upload_video(vp,md,scheduled_date=sd)
    save_topic_history(th,topic.get("keyword",topic.get("topic","")))
    (OUTPUT_DIR/"kinetic_metadata.json").write_text(json.dumps({"run":GITHUB_RUN_NUMBER,"gender":GENDER,"topic":topic,"niche":niche.get("name") if niche else "fallback","script":sl,"metadata":md,"scheduled":sd,"bg":bool(bgr)},indent=2))
    print(f"\n== Done | {GENDER.upper()} | {topic.get('keyword')} ==")
if __name__ == "__main__": main()
