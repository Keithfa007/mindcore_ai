#!/usr/bin/env python3
"""
MindCore AI -- Female Cinematic Pipeline v5.7
=============================================
v5.7: WaveSpeed with automatic Pexels fallback.
v5.6: WaveSpeed API (RunPod removed).
v5.5: Removed word flash overlays, enhanced subtitle styling.
v5.4: RunPod AI drone footage with Pexels fallback.
v5.3: ElevenLabs TTS (replaces Fish Audio for voiceover).
v5.2: SERP targets GB.
v5.1: Fixed power word flashes + softened ad CTA.
v5.0: Pexels B-roll, no background music.
"""

import json, os, random, re, subprocess, sys, time
from datetime import datetime, timedelta, timezone
from pathlib import Path
import anthropic, requests
from video_pipeline.word_flash import pick_power_word, WORD_FLASH_STOPWORDS, POWER_WORDS
from video_pipeline.tts import generate_elevenlabs_tts, FEMALE_VOICE_ID

ANTHROPIC_API_KEY=os.environ["ANTHROPIC_API_KEY"]
PEXELS_API_KEY=os.environ.get("PEXELS_API_KEY","")
SERP_API_KEY=os.environ.get("SERP_API_KEY","")
UPLOAD_POST_API_KEY=os.environ.get("UPLOAD_POST_API_KEY","")
GITHUB_RUN_NUMBER=int(os.environ.get("GITHUB_RUN_NUMBER","1"))
SERP_API_URL="https://serpapi.com/search"
UPLOAD_POST_API_URL="https://api.upload-post.com/api/upload"
OUTPUT_DIR=Path("video_pipeline/output_female")
PIPELINE_DIR=Path("video_pipeline")
MUSIC_DIR=PIPELINE_DIR/"music"
TOPIC_HISTORY_PATH=PIPELINE_DIR/"topic_history_female.json"
KEYWORDS_PATH=PIPELINE_DIR/"niche_keywords_female.json"
SCENE_ORDER=["hook","problem","story","solution_cta"]
KB_SCALE=1.10;KB_DIRECTIONS=["pan_right","pan_left","pan_up","pan_down","zoom_in","zoom_out"]
COLOR_GRADE_COLD="eq=contrast=1.10:brightness=-0.02:saturation=0.75:gamma=1.00,colorbalance=rs=0.02:gs=0:bs=0.03"
COLOR_GRADE_WARM="eq=contrast=1.00:brightness=0.06:saturation=0.95:gamma=0.93,colorbalance=rs=0.10:gs=0.03:bs=-0.06"
WARM_SCENES={"story","cta","solution_cta"}
WHISPER_MODEL="tiny";SUBTITLE_FONT="Arial";SUBTITLE_FONT_SIZE=75
SUBTITLE_MARGIN_V=500;SUBTITLE_CHUNK=2;WORD_FLASH_FONT_SIZE=110;FLASH_EVERY_N_CHUNKS=3
CLAUDE_MAX_RETRIES=10;CLAUDE_RETRY_BASE=30;SERP_SEEDS_PER_RUN=3;AUTOCOMPLETE_SEEDS_PER_RUN=2
TIKTOK_CAPTION_LIMIT=2200;YOUTUBE_TITLE_LIMIT=100;YOUTUBE_DESCRIPTION_LIMIT=5000
TOPIC_HISTORY_SIZE=5;REQUIRED_BRAND_HASHTAG="#mindcoreai"
GLOBAL_HASHTAGS="#mentalhealth #fyp #foryou #mentalhealthawareness #selfcare #healing"
def _get_serp_country():
    try:
        with open(KEYWORDS_PATH) as f: return json.load(f).get("serp_country","gb")
    except: return "gb"
SERP_COUNTRY=_get_serp_country()

HOOK_FORMULAS=[{"name":"confession_ladder","instruction":"Open at the emotional floor with a 3-4 beat escalating confession.","example":"Emotionally, I'm completely empty. Mentally, I can't hold one more thought. And physically? I'm so tired I can't even cry anymore.","rule":"Each beat must name a different dimension. The ladder MUST escalate. Open as if mid-confession."},{"name":"pattern_interrupt","instruction":"Open with a statement that contradicts what the viewer expects.","example":"Nobody talks about what actually happens when you stop people-pleasing.","rule":"The surprising statement IS the hook."},{"name":"counter_intuitive","instruction":"State something true that feels wrong at first.","example":"Anxiety in women doesn't always look like panic. It looks like over-preparing for everything.","rule":"Must feel like a reframe."},{"name":"uncomfortable_admission","instruction":"Say something the viewer has felt but never heard spoken out loud.","example":"I used to apologise for taking up space in my own life.","rule":"First person or universal. Never preachy."},{"name":"specific_moment","instruction":"Drop the viewer into an exact moment they recognise.","example":"It's 11pm and you're still running through the conversation you had this morning.","rule":"Name the time, place, detail."},{"name":"direct_challenge","instruction":"Challenge a belief without shaming. Create a gap.","example":"The reason you can't rest isn't that you're busy. It's something else entirely.","rule":"Must create urgency."},{"name":"name_the_feeling","instruction":"Name an emotion with precision the viewer has never heard named.","example":"That thing where you're surrounded by people who love you and still feel invisible.","rule":"Specific enough that only the target viewer recognises it."},{"name":"reveal","instruction":"Promise something being withheld.","example":"There's one thing that happens when women finally stop holding everything together.","rule":"The promised reveal MUST actually be delivered."},{"name":"bold_reframe","instruction":"Bold statement that reframes how the viewer sees themselves.","example":"You're not too sensitive. You've just been in environments that treated sensitivity as a flaw.","rule":"Must feel earned and true."},{"name":"direct_address","instruction":"Speak directly to one specific person in one specific situation.","example":"If you've spent years being the person everyone leans on and you don't remember the last time someone asked how you were -- this is for you.","rule":"Name the situation, not just the feeling."},{"name":"rhetorical_hit","instruction":"Ask a question the viewer has asked themselves.","example":"When was the last time you put yourself on the list?","rule":"Rhetorical -- not a quiz."},{"name":"contrast","instruction":"Two short sentences. What others see vs what's happening.","example":"Everyone thinks you have it together. You know how much that's costing you.","rule":"Two sentences maximum."},{"name":"unspoken_truth","instruction":"Say the one thing the viewer has felt but never heard articulated.","example":"You're not tired from doing too much. You're tired from disappearing too long.","rule":"Must be viscerally recognisable on first hearing."},{"name":"specific_number","instruction":"Open with a specific unexpected statistic.","example":"7 in 10 women feel like they're performing a version of themselves every single day.","rule":"Use odd, specific numbers."}]
BANNED_HOOK_OPENERS=["I remember sitting at my kid","I remember sitting at a","I was sitting at","There I was, sitting","Picture this","Let me tell you something","Here's the thing","Great question","That's a great","So today we're talking about","In this video","There's something important","Most people don't realise","Let me ask you something","If you're watching this","Have you ever felt","Today I want to talk about","Something that doesn't get talked about","This is for anyone who","The truth is,","I want to share something","What if I told you","Here's what nobody tells you","We need to talk about","It's time to talk about"]
WORD_TARGETS_AD={"hook":(8,12),"problem":(15,22),"story":(18,25),"solution_cta":(7,10)}
WORD_TARGETS_CONTENT={"hook":(8,12),"problem":(18,25),"story":(20,28),"solution_cta":(7,10)}
BANNED_PHRASE_REPLACEMENTS=[(r"try\s+it\s+for\s+free","try it"),(r"download\s+now","find MindCore AI on Google Play"),(r"free\s+trial","try MindCore AI")]
POST_HOUR_UTC=int(os.environ.get("POST_HOUR_UTC","17"))
def get_scheduled_post_time():
    now=datetime.now(timezone.utc);target=now.replace(hour=POST_HOUR_UTC,minute=0,second=0,microsecond=0)
    if now>=target:target+=timedelta(days=1)
    s=target.strftime("%Y-%m-%dT%H:%M:%SZ");print(f"  Scheduled: {s} ({POST_HOUR_UTC:02d}:00 UTC = {POST_HOUR_UTC+2:02d}:00 Malta)");return s

AD_TOPICS=[{"pain_point":"the 3am overthinking spiral that just won't stop","insight":"Most women don't have a place to put their thoughts that isn't someone else's problem.","feature":"MindCore AI gives you a private, calm space to untangle what's going through your head."},{"pain_point":"carrying everyone else's emotions while your own go unnoticed","insight":"Women are often the emotional caretakers. And somewhere in all of that, their own needs disappear.","feature":"MindCore AI is a space that's entirely yours. No one else's feelings to manage."},{"pain_point":"feeling like you've completely lost yourself","insight":"You spend so long being everything to everyone that one day you don't know what you actually feel anymore.","feature":"MindCore AI helps you reconnect with yourself -- privately, without pressure."},{"pain_point":"anxiety that gets dismissed as being too emotional","insight":"Women's anxiety often gets minimised. But it's real, and it deserves real support.","feature":"MindCore AI takes what you're feeling seriously. No dismissal. No labels."},{"pain_point":"feeling completely alone even when surrounded by people","insight":"You can be in a room full of people who love you and still feel like nobody actually sees you.","feature":"MindCore AI is there for the moments when you need to be heard. Private, available 24/7."},{"pain_point":"the guilt that comes with finally putting yourself first","insight":"Women are often conditioned to feel selfish for having needs.","feature":"MindCore AI is a judgment-free space where putting yourself first isn't selfish."},{"pain_point":"the pressure to appear like everything is fine","insight":"Most women are experts at looking okay when they're not. The performance becomes exhausting.","feature":"MindCore AI is the place you don't have to perform. Say exactly what's going on, privately."},{"pain_point":"emotional exhaustion from years of people pleasing","insight":"People pleasing isn't a personality trait -- it's a survival strategy that stops working.","feature":"MindCore AI helps you find a way back to yourself. Available any time."}]

def load_topic_history():
    if TOPIC_HISTORY_PATH.exists():
        try:return json.loads(TOPIC_HISTORY_PATH.read_text())
        except:return[]
    return[]
def save_topic_history(h,t):h.append(t);TOPIC_HISTORY_PATH.write_text(json.dumps(h[-TOPIC_HISTORY_SIZE:],indent=2))
def ensure_brand_hashtag(text):
    if not text:return REQUIRED_BRAND_HASHTAG
    if REQUIRED_BRAND_HASHTAG.lower() in text.lower():return text
    lines=text.rstrip().split("\n")
    for i in range(len(lines)-1,-1,-1):
        if "#" in lines[i]:lines[i]=lines[i].rstrip()+f" {REQUIRED_BRAND_HASHTAG}";return"\n".join(lines)
    return text.rstrip()+f"\n{REQUIRED_BRAND_HASHTAG}"
def sanitize_script(script):
    for scene in SCENE_ORDER:
        if scene not in script:continue
        o=script[scene]["voiceover"];c=o
        for p,r in BANNED_PHRASE_REPLACEMENTS:c=re.sub(p,r,c,flags=re.IGNORECASE)
        if c!=o:print(f"  SANITIZED [{scene}]");script[scene]["voiceover"]=c
    return script
def _call_claude_raw(prompt,client,max_tokens=1000):
    for a in range(1,CLAUDE_MAX_RETRIES+1):
        try:
            raw=client.messages.create(model="claude-sonnet-4-6",max_tokens=max_tokens,messages=[{"role":"user","content":prompt}]).content[0].text.strip()
            if raw.startswith("```"):parts=raw.split("```");raw=parts[1].lstrip("json").strip() if len(parts)>1 else raw
            return json.loads(raw)
        except anthropic.APIStatusError as e:
            if e.status_code==529:
                if a==CLAUDE_MAX_RETRIES:raise RuntimeError("Overloaded")
                time.sleep(CLAUDE_RETRY_BASE*a)
            else:raise
        except json.JSONDecodeError:
            if a==CLAUDE_MAX_RETRIES:raise RuntimeError("Invalid JSON");time.sleep(10)
    raise RuntimeError("Unexpected")
def determine_mode():return"ad"if GITHUB_RUN_NUMBER%10==0 else"content"
def load_app_facts():
    with open(PIPELINE_DIR/"app_facts.json") as f:return json.load(f)
def load_keywords_data():
    if not KEYWORDS_PATH.exists():return{"schedule":{},"niches":{"default":{"name":"Women's Mental Health","viewer_persona":"A woman in her 30s.","seed_queries":["women mental health tips"],"hashtags":[]}}}
    with open(KEYWORDS_PATH) as f:return json.load(f)
def get_niche_for_today(kd):
    days=["monday","tuesday","wednesday","thursday","friday","saturday","sunday"];today=days[datetime.now(timezone.utc).weekday()]
    s=kd.get("schedule",{});nk=s.get(today,list(kd["niches"].keys())[0]);n=kd["niches"][nk];print(f"  Niche: {n['name']} ({today.capitalize()})");return n
def pick_visual_mood(nd):
    moods=nd.get("visual_moods",[])
    if not moods:return{"name":"default","description":"warm cinematic","pexels_queries":[]}
    mi=GITHUB_RUN_NUMBER%len(moods);m=moods[mi];print(f"  Visual mood: {m['name']} ({mi+1}/{len(moods)})");return m
def _serp_google_query(seed):r=requests.get(SERP_API_URL,params={"engine":"google","q":seed,"api_key":SERP_API_KEY,"num":10,"hl":"en","gl":SERP_COUNTRY},timeout=30);r.raise_for_status();return r.json()
def _serp_autocomplete_query(seed):
    try:r=requests.get(SERP_API_URL,params={"engine":"google_autocomplete","q":seed,"api_key":SERP_API_KEY,"hl":"en","gl":SERP_COUNTRY},timeout=30);r.raise_for_status();return[s.get("value","").strip() for s in r.json().get("suggestions",[]) if s.get("value")]
    except Exception as e:print(f"  Autocomplete failed: {e}");return[]
def _word_count(t):return len(t.split())
def _keyword_type(t):wc=_word_count(t);return"short_tail"if wc<=3 else("mid_tail"if wc<=5 else"long_tail")
def research_keyword_candidates_from_serp(seeds):
    candidates=[];seen=set()
    for seed in random.sample(seeds,min(SERP_SEEDS_PER_RUN,len(seeds))):
        try:
            data=_serp_google_query(seed);total=int(str(data.get("search_information",{}).get("total_results","0")).replace(",","").replace(".","") or"0");paa=rs=0
            for q in data.get("related_questions",[]):
                t=q.get("question","").strip()
                if t and t.lower() not in seen:seen.add(t.lower());candidates.append({"text":t,"source":"people_also_ask","tail_type":_keyword_type(t),"word_count":_word_count(t),"seed":seed,"total_results":total});paa+=1
            for r in data.get("related_searches",[]):
                t=r.get("query","").strip()
                if t and t.lower() not in seen:seen.add(t.lower());candidates.append({"text":t,"source":"related_search","tail_type":_keyword_type(t),"word_count":_word_count(t),"seed":seed,"total_results":0});rs+=1
            for org in data.get("organic_results",[])[:3]:
                t=org.get("title","").strip()
                if t and t.lower() not in seen and len(t)<120:seen.add(t.lower());candidates.append({"text":t,"source":"organic_title","tail_type":_keyword_type(t),"word_count":_word_count(t),"seed":seed,"total_results":total})
            print(f"  [GOOGLE {SERP_COUNTRY.upper()}] '{seed[:45]}': {paa} PAA | {rs} related | {total:,} results");time.sleep(0.5)
        except Exception as e:print(f"  SERP failed for '{seed}': {e}")
    bases=[]
    for s in seeds:w=s.split();bases.extend([" ".join(w[:2])," ".join(w[:3])] if len(w)>=3 else[s])
    for ac in random.sample(list(set(bases)),min(AUTOCOMPLETE_SEEDS_PER_RUN,len(set(bases)))):
        ac_count=0
        for t in _serp_autocomplete_query(ac):
            if t and t.lower() not in seen and _word_count(t)<=6:seen.add(t.lower());candidates.append({"text":t,"source":"autocomplete","tail_type":_keyword_type(t),"word_count":_word_count(t),"seed":ac,"total_results":0});ac_count+=1
        if ac_count:print(f"  [AUTOCOMPLETE {SERP_COUNTRY.upper()}] '{ac}': {ac_count} suggestions");time.sleep(0.5)
    s=sum(1 for c in candidates if c["tail_type"]=="short_tail");m=sum(1 for c in candidates if c["tail_type"]=="mid_tail");l=sum(1 for c in candidates if c["tail_type"]=="long_tail")
    print(f"  Candidates: {len(candidates)} ({s} short | {m} mid | {l} long)");return candidates
def rank_and_select_keyword_claude(candidates,client,th,niche):
    if not candidates:raise ValueError("No SERP candidates")
    to={"short_tail":0,"mid_tail":1,"long_tail":2};so={"autocomplete":0,"people_also_ask":1,"related_search":2,"organic_title":3}
    sc=sorted(candidates,key=lambda c:(to.get(c["tail_type"],3),so.get(c["source"],4)))
    cl="\n".join([f"{i+1}. [{c['tail_type'].upper()} | {c['source'].upper()} | {c['word_count']}w] {c['text']}" for i,c in enumerate(sc[:50])])
    hn=""
    if th:hn="\nRECENT TOPICS (DO NOT REPEAT):\n"+"\n".join(f"  - {t}" for t in th)+"\nChoose something different.\n"
    prompt=f"""Expert in SEO for women's mental health on TikTok and YouTube Shorts.\nNICHE: {niche['name']}\nVIEWER: {niche['viewer_persona']}\n{hn}\nChoose the SINGLE BEST keyword.\nFAVOUR: emotional, specific, something this woman types alone late at night.\n\nCANDIDATES:\n{cl}\n\nReturn ONLY valid JSON:\n{{"topic":"exact candidate text","question":"exact question","keyword":"1-5 word SEO keyword","tail_type":"short_tail|mid_tail|long_tail","competition_signal":"low|medium|high","why":"one sentence","source":"autocomplete|people_also_ask|related_search|organic_title"}}"""
    result=_call_claude_raw(prompt,client,max_tokens=500);print(f"  Winner: '{result.get('keyword')}' [{result.get('tail_type','?')}]");return result
def fetch_trending_topic_claude_fallback(seeds,th,niche,client):
    seed=random.choice(seeds);hist=f"AVOID: {', '.join(th)}. " if th else ""
    prompt=f"""SEO expert for women's mental health.\nNICHE: {niche['name']}\nVIEWER: {niche['viewer_persona']}\nGenerate ONE topic. Related to: "{seed}"\n{hist}Return ONLY valid JSON:\n{{"topic":"question or keyword","question":"exact question","keyword":"1-5 word SEO keyword","tail_type":"short_tail|mid_tail|long_tail","competition_signal":"low|medium|high","why":"one sentence","source":"claude_generated"}}"""
    return _call_claude_raw(prompt,client,max_tokens=400)
def fetch_trending_topic(client,niche):
    seeds=niche["seed_queries"];th=load_topic_history()
    if th:print(f"  Avoiding recent: {th}")
    if SERP_API_KEY:
        try:
            cands=research_keyword_candidates_from_serp(seeds)
            if cands:topic=rank_and_select_keyword_claude(cands,client,th,niche);topic["source"]=f"serp_{topic.get('source','research')}";(OUTPUT_DIR/"keyword_research.json").write_text(json.dumps({"run":GITHUB_RUN_NUMBER,"niche":niche["name"],"candidates":cands,"winner":topic},indent=2));return topic
        except Exception as e:print(f"  SERP failed ({e}) -- falling back to Claude")
    return fetch_trending_topic_claude_fallback(seeds,th,niche,client)
def _build_hook_block(formula):
    bs="\n".join(f'  - "{p}..."' for p in BANNED_HOOK_OPENERS)
    ssr="SILENT SCROLL RULE:\nMost TikTok viewers scroll with sound OFF. First 3-4 words must deliver emotional impact.\nWRONG: \"There's one thing nobody tells you...\" -- empty\nRIGHT: \"You stopped feeling things.\" -- punch in 4 words\nLead with the FEELING."
    return f"{ssr}\n\nHOOK (8-12 words):\nFormula: \"{formula['name']}\"\nInstruction: {formula['instruction']}\nExample: \"{formula['example']}\"\nRule: {formula['rule']}\n\nFORBIDDEN OPENERS:\n{bs}"
def generate_content_script(topic,niche,client):
    kw=topic.get("keyword",topic["topic"]);q=topic.get("question",topic["topic"]);f=random.choice(HOOK_FORMULAS);hb=_build_hook_block(f)
    lp,hp=WORD_TARGETS_CONTENT["problem"];ls,hs=WORD_TARGETS_CONTENT["story"];lc,hc=WORD_TARGETS_CONTENT["solution_cta"]
    prompt=f"""Punchy cinematic voiceover script, 25-35 seconds.\n\nVIEWER: {niche['viewer_persona']}\nNICHE: {niche['name']}\nQUESTION: "{q}"\nSEO KEYWORD: {kw}\n\nVoiceover for atmospheric B-roll. No MindCore AI. Pure value.\n\n{hb}\n\n4 SCENES:\nhook (8-12 words) | problem ({lp}-{hp} words) | story ({ls}-{hs} words) | solution_cta ({lc}-{hc} words -- emotional resolution or comment trigger. NO app mentions.)\nReturn ONLY valid JSON:\n{{"video_type":"content","topic":"{topic['topic']}","seo_keyword":"{kw}","render_format":"cinematic","hook_formula":"{f['name']}","hook":{{"voiceover":"..."}},"problem":{{"voiceover":"..."}},"story":{{"voiceover":"..."}},"solution_cta":{{"voiceover":"..."}}}}"""
    return _call_claude_raw(prompt,client,max_tokens=800)
def generate_ad_script(app_facts,niche,client):
    at=random.choice(AD_TOPICS);f=random.choice(HOOK_FORMULAS);hb=_build_hook_block(f);print(f"  AD: {at['pain_point'][:65]}...")
    lp,hp=WORD_TARGETS_AD["problem"];ls,hs=WORD_TARGETS_AD["story"];lc,hc=WORD_TARGETS_AD["solution_cta"]
    prompt=f"""Punchy cinematic voiceover ad script for MindCore AI targeting women. 25-35 seconds.\n\nVIEWER: {niche['viewer_persona']}\nPAIN POINT: {at['pain_point']}\nINSIGHT: {at['insight']}\nFEATURE: {at['feature']}\n\n{hb}\n\nSCENES:\nhook -> problem ({lp}-{hp} words) -> story ({ls}-{hs} words -- mention MindCore AI ONCE as "a space that listens". NEVER say download/play/Google Play.) -> solution_cta ({lc}-{hc} words -- PURE EMOTIONAL RESOLUTION. NEVER say "Play now" or "Google Play".)\nBANNED: "free trial", "download now", "play now", "Google Play"\n\nReturn ONLY valid JSON:\n{{"video_type":"ad","topic":"{at['pain_point'][:55]}","seo_keyword":"AI mental health companion for women","render_format":"cinematic","hook_formula":"{f['name']}","hook":{{"voiceover":"..."}},"problem":{{"voiceover":"..."}},"story":{{"voiceover":"..."}},"solution_cta":{{"voiceover":"..."}}}}"""
    return _call_claude_raw(prompt,client,max_tokens=800)
def build_full_script(script):
    parts=[]
    for s in SCENE_ORDER:
        vo=script[s]["voiceover"].strip()
        if vo and vo[-1] not in ".!?":vo+="."
        parts.append(vo)
    return"  ".join(parts)

# TTS -- ElevenLabs (replaces Fish Audio)
def generate_fish_audio_tts(st,op):
    return generate_elevenlabs_tts(st, op, FEMALE_VOICE_ID)

def transcribe_audio_whisper(mp):
    try:
        import whisper;model=whisper.load_model(WHISPER_MODEL)
        result=model.transcribe(str(mp),word_timestamps=True,language="en",fp16=False);words=[]
        for seg in result.get("segments",[]):
            for w in seg.get("words",[]):
                word=w.get("word","").strip()
                if word:words.append({"word":word,"start":float(w.get("start",0)),"end":float(w.get("end",0))})
        print(f"  Whisper: {len(words)} words");return words
    except Exception as e:print(f"  Whisper failed ({e})");return[]
def generate_ass_subtitles(words,output_path):
    """Enhanced subtitles: bold white, strong outline, fade effect, no word flash overlays."""
    if not words:return False
    def ts(s):h=int(s//3600);m=int((s%3600)//60);s=s%60;return f"{h}:{m:02d}:{s:05.2f}"
    header="[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nScaledBorderAndShadow: yes\nWrapStyle: 1\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,Arial,85,&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,2,0,1,5,2,2,60,60,500,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    chunks=[];i=0;chunk_size=2
    while i<len(words):
        chunk=words[i:i+chunk_size];text=" ".join(w["word"].upper() for w in chunk);start=chunk[0]["start"];end=chunk[-1]["end"]
        if not chunks:start=0.0
        elif start<chunks[-1]["end"]:start=chunks[-1]["end"]
        chunks.append({"text":text,"start":start,"end":end});i+=chunk_size
    events=""
    for c in chunks:
        events+=f"Dialogue: 0,{ts(c['start'])},{ts(c['end'])},Default,,0,0,0,,{{\\fad(150,100)}}{c['text']}\n"
    Path(output_path).write_text((header+events).encode("utf-8",errors="ignore").decode("utf-8"),encoding="utf-8")
    print(f"  Subtitles: {len(chunks)} groups (no word flashes)");return True
def burn_subtitles_into_video(vp,ap):
    if not ap or not Path(ap).exists():return False
    sa=str(Path(ap).resolve()).replace("\\","/");bt=vp.replace(".mp4","_subtitled.mp4")
    r=subprocess.run(["ffmpeg","-i",vp,"-vf",f"ass='{sa}'","-c:v","libx264","-crf","16","-preset","slow","-c:a","copy","-y",bt],capture_output=True,text=True)
    if r.returncode==0:Path(bt).replace(Path(vp));print(f"  Captions burned: {Path(vp).stat().st_size/(1024*1024):.1f} MB");return True
    print("  WARNING: subtitle burn failed");return False
def ken_burns_vf(d,direction):
    d=max(d,0.5);sw=int(1080*KB_SCALE);sh=int(1920*KB_SCALE);ew=sw-1080;eh=sh-1920;cy=str(eh//2);cx=str(ew//2)
    if direction=="pan_right":x,y=f"min(t/{d:.2f}*{ew}\\,{ew})",cy
    elif direction=="pan_left":x,y=f"max({ew}-t/{d:.2f}*{ew}\\,0)",cy
    elif direction=="pan_up":x,y=cx,f"min(t/{d:.2f}*{eh}\\,{eh})"
    elif direction=="pan_down":x,y=cx,f"max({eh}-t/{d:.2f}*{eh}\\,0)"
    elif direction=="zoom_in":x,y=f"max({ew}-t/{d:.2f}*{ew//2}\\,{ew//2})",f"max({eh}-t/{d:.2f}*{eh//2}\\,{eh//2})"
    else:x,y=f"min(t/{d:.2f}*{ew//2}\\,{ew//2})",f"min(t/{d:.2f}*{eh//2}\\,{eh//2})"
    return f"scale={sw}:{sh},crop=1080:1920:{x}:{y}"
def get_audio_duration(ap):return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",ap],capture_output=True,text=True,check=True).stdout.strip())
def process_clip_to_portrait(cp,op,dur,direction="pan_right",cg=None):
    if cg is None:cg=COLOR_GRADE_COLD
    r=subprocess.run(["ffmpeg","-stream_loop","-1","-i",cp,"-vf",f"{ken_burns_vf(dur,direction)},{cg},fps=30","-t",str(dur),"-an","-c:v","libx264","-crf","20","-preset","fast","-y",op],capture_output=True,text=True)
    if r.returncode!=0:raise RuntimeError(f"Clip failed: {r.stderr[-300:]}");return op
def assemble_cinematic_video(clip_paths,audio_path,output_path,music_path=None,ass_path=None,scene_types=None):
    ad=get_audio_duration(audio_path);n=len(clip_paths);cd=ad/n;print(f"  Assembling: {n} clips x {cd:.1f}s = {ad:.1f}s")
    clips_dir=OUTPUT_DIR/"clips";clips_dir.mkdir(exist_ok=True);processed=[]
    for i,rp in enumerate(clip_paths):
        st=scene_types[i] if scene_types and i<len(scene_types) else"problem"
        grade=COLOR_GRADE_WARM if st in WARM_SCENES else COLOR_GRADE_COLD
        d=KB_DIRECTIONS[i%len(KB_DIRECTIONS)];out=str(clips_dir/f"clip_{i}_processed.mp4")
        try:process_clip_to_portrait(rp,out,cd,d,grade);processed.append(out);print(f"    Clip {i+1}/{n}: {d} | {'WARM' if grade==COLOR_GRADE_WARM else 'COLD'}")
        except Exception as e:print(f"  Clip {i+1} failed ({e}) -- skipping")
    if not processed:raise RuntimeError("No clips processed")
    cf=OUTPUT_DIR/"concat.txt"
    with open(cf,"w") as f:
        for p in processed:f.write(f"file '{Path(p).resolve()}'\n")
    cv=str(OUTPUT_DIR/"concat_video.mp4")
    subprocess.run(["ffmpeg","-f","concat","-safe","0","-i",str(cf),"-c:v","copy","-t",str(ad),"-y",cv],capture_output=True,text=True,check=True)
    r=subprocess.run(["ffmpeg","-i",cv,"-i",audio_path,"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k","-t",str(ad),"-y",output_path],capture_output=True,text=True)
    if r.returncode!=0:raise RuntimeError(f"Audio mix failed: {r.stderr[-500:]}")
    print(f"  Assembled: {Path(output_path).stat().st_size/(1024*1024):.1f} MB")
    if ass_path:burn_subtitles_into_video(output_path,ass_path)
def render_cinematic_video(script_text,mood,niche,script=None):
    wavespeed_key = os.environ.get("WAVESPEED_API_KEY", "")
    print("\n  [TTS] Generating voiceover (ElevenLabs)...");audio_path=str(OUTPUT_DIR/"voiceover_female.mp3");generate_fish_audio_tts(script_text,audio_path)
    print("\n  [Subtitles] Transcribing with Whisper...");ass_path=str(OUTPUT_DIR/"subtitles_cinematic_female.ass");words=transcribe_audio_whisper(audio_path)
    if not generate_ass_subtitles(words,ass_path):ass_path=None
    clips_dir=OUTPUT_DIR/"clips";clips_dir.mkdir(exist_ok=True);raw=[];st=[]
    if wavespeed_key:
        try:
            import subprocess as _sp
            _dur_out = _sp.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",audio_path], capture_output=True, text=True)
            audio_dur = int(float(_dur_out.stdout.strip())) if _dur_out.returncode == 0 else 30
            from video_pipeline.wavespeed_clips import fetch_drone_journey_clips, get_theme_for_run
            theme_name = get_theme_for_run(GITHUB_RUN_NUMBER)
            print(f"\n  [WaveSpeed] Drone theme: {theme_name} | Voiceover: {audio_dur}s")
            clips = fetch_drone_journey_clips(theme_name, str(clips_dir), GITHUB_RUN_NUMBER, duration=audio_dur)
            for cp, sn in clips:
                raw.append(cp);st.append(sn)
            source = "WaveSpeed AI"
        except Exception as e:
            print(f"\n  [WaveSpeed] FAILED ({e}) -- falling back to Pexels")
            raw = []; st = []

    if not raw:
        from video_pipeline.pexels_clips import fetch_pexels_clip_for_scene
        for sn,count in [("hook",1),("problem",2),("story",1),("solution_cta",1)]:
            for j in range(count):
                cp=str(clips_dir/f"raw_{len(raw)}.mp4");pp=fetch_pexels_clip_for_scene(sn,len(raw),cp,GITHUB_RUN_NUMBER,gender="woman")
                if pp:raw.append(pp);st.append(sn)
                else:print(f"  WARNING: {sn} clip skipped")
        source = "Pexels"
    if not raw:raise RuntimeError("No clips generated")
    print(f"\n  Fetched {len(raw)} clips ({source})")
    assemble_cinematic_video(raw,audio_path,str(OUTPUT_DIR/"mindcore_female_video.mp4"),None,ass_path,scene_types=st)
    return str(OUTPUT_DIR/"mindcore_female_video.mp4")
def generate_upload_guide(script,mode,niche,client):
    prompt=f"""Social media expert for women's mental health.\nNICHE: {niche['name']} | TYPE: {script.get('video_type',mode).upper()} | KEYWORD: {script.get('seo_keyword','')} | HOOK: {script.get('hook',{}).get('voiceover','')}\nGenerate upload copy for TikTok, Facebook, YouTube. Include {REQUIRED_BRAND_HASHTAG}. Original sentences only."""
    for a in range(1,CLAUDE_MAX_RETRIES+1):
        try:return client.messages.create(model="claude-sonnet-4-6",max_tokens=1500,messages=[{"role":"user","content":prompt}]).content[0].text.strip()
        except anthropic.APIStatusError as e:
            if e.status_code==529:time.sleep(CLAUDE_RETRY_BASE*a)
            else:raise
    raise RuntimeError("Could not generate upload guide")
def generate_upload_metadata(script,mode,niche,client):
    nt=" ".join(niche.get("hashtags",[]))
    prompt=f"""Social media expert for women's mental health.\nNICHE: {niche['name']} | TYPE: {script.get('video_type',mode).upper()} | KEYWORD: {script.get('seo_keyword','')}\nOriginal sentences only.\n- tiktok_caption: 1-2 sentences + 8-10 hashtags. MUST include {REQUIRED_BRAND_HASHTAG} {nt} {GLOBAL_HASHTAGS}\n- facebook_title: max 255 chars\n- facebook_description: 2 sentences + 4-5 hashtags. MUST include {REQUIRED_BRAND_HASHTAG}\n- youtube_title: max 100 chars\n- youtube_description: 2 sentences + "Try MindCore AI: https://mindcoreai.eu" + hashtags ending #Shorts. MUST include {REQUIRED_BRAND_HASHTAG}\n- youtube_tags: 8-12 keywords\n- first_comment: punchy question (max 150 chars).\nReturn ONLY valid JSON:\n{{"tiktok_caption":"...","facebook_title":"...","facebook_description":"...","youtube_title":"...","youtube_description":"...","youtube_tags":"...","first_comment":"..."}}"""
    for a in range(1,CLAUDE_MAX_RETRIES+1):
        try:
            raw=client.messages.create(model="claude-sonnet-4-6",max_tokens=1000,messages=[{"role":"user","content":prompt}]).content[0].text.strip()
            if raw.startswith("```"):parts=raw.split("```");raw=parts[1].lstrip("json").strip() if len(parts)>1 else raw
            md=json.loads(raw)
            for k in("tiktok_caption","facebook_description","youtube_description"):md[k]=ensure_brand_hashtag(md.get(k,""))
            md["youtube_title"]=md.get("youtube_title","")[:YOUTUBE_TITLE_LIMIT];md["first_comment"]=md.get("first_comment","")[:150];return md
        except(anthropic.APIStatusError,json.JSONDecodeError)as e:
            if a==CLAUDE_MAX_RETRIES:raise RuntimeError(f"Metadata failed: {e}");time.sleep(10)
def upload_to_platforms(video_path,metadata,cfg,scheduled_date=None):
    if not UPLOAD_POST_API_KEY:return{"skipped":True,"reason":"no API key"}
    user=cfg.get("upload_post_user","")
    if not user:return{"skipped":True,"reason":"no user configured"}
    data=[("user",user),("platform[]","tiktok"),("platform[]","facebook"),("platform[]","youtube"),("title",metadata.get("tiktok_caption","")[:TIKTOK_CAPTION_LIMIT]),("facebook_title",metadata.get("facebook_title","")[:255]),("facebook_description",metadata.get("facebook_description","")),("youtube_title",metadata.get("youtube_title","")[:YOUTUBE_TITLE_LIMIT]),("youtube_description",metadata.get("youtube_description","")[:YOUTUBE_DESCRIPTION_LIMIT]),("youtube_tags",metadata.get("youtube_tags","")),("first_comment",metadata.get("first_comment",""))]
    if scheduled_date:data.append(("scheduled_date",scheduled_date))
    try:
        with open(video_path,"rb") as f:resp=requests.post(UPLOAD_POST_API_URL,headers={"Authorization":f"Apikey {UPLOAD_POST_API_KEY}"},files=[("video",("mindcore_female_video.mp4",f,"video/mp4"))],data=data,timeout=180)
        result=resp.json() if resp.headers.get("content-type","").startswith("application/json") else{"raw":resp.text}
        result["status_code"]=resp.status_code
        if scheduled_date:result["scheduled_date"]=scheduled_date
        print(f"  Upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}");return result
    except Exception as e:print(f"  Upload failed: {e}");return{"error":str(e)}
def save_upload_guide(gt,script,mode,rn,niche):
    tw=sum(len(script[s]["voiceover"].split()) for s in SCENE_ORDER);ed=round(tw/130*60)
    header=f"MINDCORE AI FEMALE UPLOAD GUIDE -- Run #{rn} | {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}\nNiche: {niche['name']} | ~{ed}s | {tw} words\n\nFULL SCRIPT\n"
    for s in SCENE_ORDER:header+=f"[{s.upper()}] {script[s]['voiceover']}\n\n"
    (OUTPUT_DIR/"upload_guide_female.txt").write_text(header+gt,encoding="utf-8")

def main():
    OUTPUT_DIR.mkdir(parents=True,exist_ok=True);(OUTPUT_DIR/"clips").mkdir(exist_ok=True)
    mode=determine_mode();client=anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    cfg={};cp=PIPELINE_DIR/"heygen_config_female.json"
    if cp.exists():
        with open(cp) as f:cfg=json.load(f)
    upload_enabled=cfg.get("upload_enabled",False) and bool(UPLOAD_POST_API_KEY)
    kd=load_keywords_data();niche=get_niche_for_today(kd);mood=pick_visual_mood(niche)
    print(f"\n  MindCore AI -- Female Cinematic Pipeline v5.7")
    print(f"  Run #{GITHUB_RUN_NUMBER} | Mode: {mode.upper()} | Pexels | ElevenLabs TTS | SERP: {SERP_COUNTRY.upper()}")
    print(f"  Niche: {niche['name']} | Upload: {'ENABLED' if upload_enabled else 'DISABLED'}")
    print("="*60)
    print("\n  Generating script...")
    if mode=="ad":script=generate_ad_script(load_app_facts(),niche,client)
    else:
        topic=fetch_trending_topic(client,niche);script=generate_content_script(topic,niche,client)
        save_topic_history(load_topic_history(),topic.get("keyword",topic.get("topic","")))
    script=sanitize_script(script);(OUTPUT_DIR/"script_female.json").write_text(json.dumps(script,indent=2))
    tw=sum(len(script[s]["voiceover"].split()) for s in SCENE_ORDER);ed=round(tw/130*60)
    print(f"\n  ~{ed}s | Hook: {script.get('hook_formula','?')}")
    for s in SCENE_ORDER:print(f"  [{s:15s}] {script[s]['voiceover'][:85]}...")
    final_path=render_cinematic_video(build_full_script(script),mood,niche,script=script)
    gt=generate_upload_guide(script,mode,niche,client);save_upload_guide(gt,script,mode,GITHUB_RUN_NUMBER,niche)
    um=generate_upload_metadata(script,mode,niche,client);(OUTPUT_DIR/"upload_metadata_female.json").write_text(json.dumps(um,indent=2))
    if upload_enabled:
        sd=get_scheduled_post_time();ur=upload_to_platforms(final_path,um,cfg,scheduled_date=sd)
        (OUTPUT_DIR/"upload_result_female.json").write_text(json.dumps(ur,indent=2))
    else:(OUTPUT_DIR/"upload_result_female.json").write_text(json.dumps({"skipped":True},indent=2))
    print(f"\n  DONE | ~{ed}s | {niche['name']}")

if __name__=="__main__":
    try:main()
    except Exception as exc:print(f"\n  FAILED: {exc}",file=sys.stderr);raise SystemExit(1)
