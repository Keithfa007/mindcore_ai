#!/usr/bin/env python3
"""
MindCore AI Video Pipeline v5.16
=================================

CHANGES (v5.16):
  Remove `dimension` param from HeyGen v3 payload -- API no longer accepts it.
  `aspect_ratio: 9:16` handles format; `dimension` caused 400 invalid_parameter.

CHANGES (v5.15):
  Whisper subtitles on cinematic videos.

CHANGES (v5.14):
  cropdetect limit raised 30->200 to strip white letterbox.

CHANGES (v5.13):
  Descriptions no longer copy the script.

CHANGES (v5.12):
  Word-by-word subtitles for avatar videos.

CHANGES (v5.11):
  Interview response script format.
"""

import json
import os
import random
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import requests

ANTHROPIC_API_KEY   = os.environ["ANTHROPIC_API_KEY"]
HEYGEN_API_KEY      = os.environ["HEYGEN_API_KEY"]
FISH_AUDIO_API_KEY  = os.environ.get("FISH_AUDIO_API_KEY", "")
PEXELS_API_KEY      = os.environ.get("PEXELS_API_KEY", "")
SERP_API_KEY        = os.environ.get("SERP_API_KEY", "")
UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
FORCE_FORMAT        = os.environ.get("FORCE_FORMAT", "").strip().lower()
GITHUB_RUN_NUMBER   = int(os.environ.get("GITHUB_RUN_NUMBER", "1"))

HEYGEN_V3_URL       = "https://api.heygen.com/v3/videos"
HEYGEN_STATUS_URL   = "https://api.heygen.com/v1/video_status.get"
FISH_AUDIO_TTS_URL  = "https://api.fish.audio/v1/tts"
PEXELS_VIDEO_URL    = "https://api.pexels.com/videos/search"
SERP_API_URL        = "https://serpapi.com/search"
UPLOAD_POST_API_URL = "https://api.upload-post.com/api/upload"

FISH_AUDIO_VOICE_ID = "4ea1bbc944004fa89ea67021d86129ef"

OUTPUT_DIR         = Path("video_pipeline/output")
PIPELINE_DIR       = Path("video_pipeline")
MUSIC_DIR          = PIPELINE_DIR / "music"
TOPIC_HISTORY_PATH = PIPELINE_DIR / "topic_history.json"
LOOK_QUEUE_PATH    = PIPELINE_DIR / "look_queue.json"
SCENE_ORDER        = ["hook", "problem", "story", "solution_cta"]

MUSIC_VOLUME       = 0.05
WHISPER_MODEL      = "tiny"
SUBTITLE_FONT      = "Arial"
SUBTITLE_FONT_SIZE = 75
SUBTITLE_MARGIN_V  = 500
SUBTITLE_CHUNK     = 3
POLL_INTERVAL      = 15
VIDEO_TIMEOUT      = 1200
CLAUDE_MAX_RETRIES = 10
CLAUDE_RETRY_BASE  = 30
SERP_SEEDS_PER_RUN         = 3
AUTOCOMPLETE_SEEDS_PER_RUN = 2
TIKTOK_CAPTION_LIMIT      = 2200
YOUTUBE_TITLE_LIMIT       = 100
YOUTUBE_DESCRIPTION_LIMIT = 5000
PEXELS_CLIPS_PER_VIDEO    = 5
TOPIC_HISTORY_SIZE        = 5
REQUIRED_BRAND_HASHTAG    = "#mindcoreai"

INTERVIEW_HOOKS = ["direct_answer","reframe_first","counter_intuitive","personal_truth","hard_fact","challenge_premise"]

BANNED_OPENINGS = [
    "I remember sitting at my kid","I remember sitting at a","I was sitting at",
    "There I was, sitting","Picture this","Let me tell you something",
    "Here's the thing","Great question","That's a great",
    "So today we're talking about","In this video",
]

AD_TOPICS = [
    {"pain_point":"talking to yourself at 3am trying to figure out why you can't sleep",
     "insight":"Most men don't have a safe space to process what's going on in their head -- without judgment, without advice they didn't ask for.",
     "feature":"MindCore AI gives you a private, calm space to talk through whatever's keeping you up. It's built for men, available 24/7, and it actually listens."},
    {"pain_point":"the anger that comes out of nowhere in recovery",
     "insight":"Sobriety doesn't remove your emotions. It removes the thing you were using to numb them. And suddenly all that feeling has nowhere to go.",
     "feature":"MindCore AI helps men in recovery understand and process what's underneath the anger -- without judgment, without a waiting list."},
    {"pain_point":"feeling like no one around you actually gets what you're going through",
     "insight":"Men are wired to solve problems, not talk about them. Which means the pain just builds. And eventually it comes out sideways.",
     "feature":"MindCore AI is built specifically for men's mental health. No small talk. No generic advice. Just honest, private conversations whenever you need them."},
    {"pain_point":"the emotional numbness that creeps in after years of staying strong",
     "insight":"Emotional shutdown isn't weakness. It's your brain protecting you from overwhelm. But over time, it cuts you off from everything -- the good stuff too.",
     "feature":"MindCore AI helps men reconnect with what they're actually feeling, one conversation at a time. It's on Google Play."},
    {"pain_point":"anxiety that shows up as irritability and short fuses, not panic attacks",
     "insight":"Most men with anxiety don't recognise it as anxiety. It looks like anger, withdrawal, or just constantly feeling on edge for no obvious reason.",
     "feature":"MindCore AI understands how anxiety actually shows up in men -- and helps you work through it in a way that actually fits how you think."},
    {"pain_point":"lying awake wondering if what you're feeling is normal",
     "insight":"The number of men silently asking that question every night is staggering. And most of them never ask anyone out loud.",
     "feature":"MindCore AI exists for exactly that moment. A private AI mental health companion for men -- honest, non-judgmental, available any time."},
    {"pain_point":"going through the motions every day but feeling completely disconnected from your own life",
     "insight":"That disconnect has a name. And it's more common in men over 35 than almost any other mental health experience. But nobody talks about it.",
     "feature":"MindCore AI was built to help men name what they're feeling and start actually dealing with it -- privately, on their own terms."},
    {"pain_point":"not wanting to burden your family with what's going on in your head",
     "insight":"That instinct to protect the people you love can become its own trap. You end up carrying everything alone, and they can tell something's off anyway.",
     "feature":"MindCore AI gives you somewhere to put it that isn't your partner, your kids, or your mates. Just you, and a tool that was built for this."},
]

WORD_TARGETS_AD      = {"hook":(10,15),"problem":(30,40),"story":(40,55),"solution_cta":(20,30)}
WORD_TARGETS_CONTENT = {"hook":(10,18),"problem":(30,45),"story":(45,65),"solution_cta":(20,35)}

BANNED_PHRASE_REPLACEMENTS = [
    (r"try\s+it\s+for\s+free","try it"),
    (r"download\s+now","find MindCore AI on Google Play"),
    (r"free\s+trial","try MindCore AI"),
]


def load_topic_history():
    if TOPIC_HISTORY_PATH.exists():
        try: return json.loads(TOPIC_HISTORY_PATH.read_text())
        except: return []
    return []

def save_topic_history(history,new_topic):
    history.append(new_topic)
    TOPIC_HISTORY_PATH.write_text(json.dumps(history[-TOPIC_HISTORY_SIZE:],indent=2))

def load_look_queue(all_looks):
    if LOOK_QUEUE_PATH.exists():
        try:
            q=[l for l in json.loads(LOOK_QUEUE_PATH.read_text()) if l in all_looks]
            if q: return q
        except: pass
    deck=all_looks[:]; random.shuffle(deck)
    print(f"  Look queue: new shuffled deck of {len(deck)} looks")
    return deck

def save_look_queue(queue): LOOK_QUEUE_PATH.write_text(json.dumps(queue,indent=2))

def pick_music_track():
    if not MUSIC_DIR.exists(): return None
    tracks=[t for t in MUSIC_DIR.glob("*.mp3") if t.stem!=".gitkeep"]
    if not tracks: return None
    chosen=random.choice(tracks)
    print(f"  Background music: {chosen.name} @ {int(MUSIC_VOLUME*100)}% volume")
    return str(chosen)


def transcribe_audio_whisper(media_path):
    try:
        import whisper
        print(f"  Whisper: loading '{WHISPER_MODEL}' model (CPU)...")
        model=whisper.load_model(WHISPER_MODEL)
        result=model.transcribe(str(media_path),word_timestamps=True,language="en",fp16=False)
        words=[]
        for seg in result.get("segments",[]):
            for w in seg.get("words",[]):
                word=w.get("word","").strip()
                if word: words.append({"word":word,"start":float(w.get("start",0)),"end":float(w.get("end",0))})
        print(f"  Whisper: {len(words)} words transcribed")
        return words
    except Exception as e:
        print(f"  Whisper failed ({e}) -- continuing without subtitles"); return []


def generate_ass_subtitles(words,output_path):
    if not words: return False
    def ts(s):
        h=int(s//3600);m=int((s%3600)//60);s=s%60
        return f"{h}:{m:02d}:{s:05.2f}"
    header=(
        "[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\n"
        "ScaledBorderAndShadow: yes\nWrapStyle: 1\n\n[V4+ Styles]\n"
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding\n"
        f"Style: Default,{SUBTITLE_FONT},{SUBTITLE_FONT_SIZE},"
        "&H00FFFFFF,&H000000FF,&H00000000,&H00000000,"
        f"-1,0,0,0,100,100,1,0,1,4,0,2,60,60,{SUBTITLE_MARGIN_V},1\n\n"
        "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n"
    )
    chunks=[];i=0
    while i<len(words):
        chunk=words[i:i+SUBTITLE_CHUNK]
        text=" ".join(w["word"].upper() for w in chunk)
        start=chunk[0]["start"];end=chunk[-1]["end"]
        if chunks and start<chunks[-1]["end"]: start=chunks[-1]["end"]
        chunks.append({"text":text,"start":start,"end":end})
        i+=SUBTITLE_CHUNK
    events="".join(f"Dialogue: 0,{ts(c['start'])},{ts(c['end'])},Default,,0,0,0,,{c['text']}\n" for c in chunks)
    Path(output_path).write_text(header+events,encoding="utf-8")
    print(f"  Subtitles: {len(chunks)} groups | {SUBTITLE_FONT} {SUBTITLE_FONT_SIZE}px | MarginV {SUBTITLE_MARGIN_V}px")
    return True


def burn_subtitles_into_video(video_path,ass_path):
    if not ass_path or not Path(ass_path).exists(): return False
    safe_ass=str(Path(ass_path).resolve()).replace("\\","/")
    burnt_tmp=video_path.replace(".mp4","_subtitled.mp4")
    cmd=["ffmpeg","-i",video_path,"-vf",f"ass='{safe_ass}'","-c:v","libx264","-crf","16","-preset","slow","-c:a","copy","-y",burnt_tmp]
    result=subprocess.run(cmd,capture_output=True,text=True)
    if result.returncode==0:
        Path(burnt_tmp).replace(Path(video_path))
        print(f"  Cinematic captions burned: {Path(video_path).stat().st_size/(1024*1024):.1f} MB")
        return True
    print(f"  WARNING: cinematic subtitle burn failed")
    if Path(burnt_tmp).exists(): Path(burnt_tmp).unlink()
    return False


def determine_mode(): return "ad" if GITHUB_RUN_NUMBER%10==0 else "content"
def load_config():
    with open(PIPELINE_DIR/"heygen_config.json") as f: return json.load(f)
def pick_avatar_look(cfg):
    all_looks=cfg.get("avatar_look_ids",[])
    if not all_looks: raise RuntimeError("No avatar_look_ids")
    queue=load_look_queue(all_looks);chosen=queue.pop(0);save_look_queue(queue)
    remaining=len(queue)
    if remaining==0: print(f"  Avatar look: {chosen[:8]}... (deck exhausted | {len(all_looks)} total)")
    else: print(f"  Avatar look: {chosen[:8]}... ({remaining} remaining | {len(all_looks)} total)")
    return chosen
def load_app_facts():
    with open(PIPELINE_DIR/"app_facts.json") as f: return json.load(f)
def load_niche_keywords():
    path=PIPELINE_DIR/"niche_keywords.json"
    if not path.exists(): return {"seed_queries":["men mental health tips"],"content_angles":["real talk"],"visual_styles":[]}
    with open(path) as f: return json.load(f)
def pick_visual_style(keywords):
    styles=keywords.get("visual_styles",[])
    if not styles: return {"name":"atmospheric_solitude","query_templates":["lonely man window","empty room","man thinking alone"]}
    return random.choice(styles)
def ensure_brand_hashtag(text):
    if not text: return REQUIRED_BRAND_HASHTAG
    if REQUIRED_BRAND_HASHTAG.lower() in text.lower(): return text
    lines=text.rstrip().split("\n")
    for i in range(len(lines)-1,-1,-1):
        if "#" in lines[i]: lines[i]=lines[i].rstrip()+f" {REQUIRED_BRAND_HASHTAG}"; return "\n".join(lines)
    return text.rstrip()+f"\n{REQUIRED_BRAND_HASHTAG}"
def sanitize_script(script):
    for scene in SCENE_ORDER:
        if scene not in script: continue
        original=script[scene]["voiceover"];cleaned=original
        for pattern,replacement in BANNED_PHRASE_REPLACEMENTS:
            cleaned=re.sub(pattern,replacement,cleaned,flags=re.IGNORECASE)
        if cleaned!=original:
            print(f"  SANITIZED [{scene}]")
            script[scene]["voiceover"]=cleaned
    return script
def _call_claude_raw(prompt,client,max_tokens=1000):
    for attempt in range(1,CLAUDE_MAX_RETRIES+1):
        try:
            message=client.messages.create(model="claude-sonnet-4-6",max_tokens=max_tokens,messages=[{"role":"user","content":prompt}])
            raw=message.content[0].text.strip()
            if raw.startswith("```"): parts=raw.split("```");raw=parts[1].lstrip("json").strip() if len(parts)>1 else raw
            return json.loads(raw)
        except anthropic.APIStatusError as e:
            if e.status_code==529:
                if attempt==CLAUDE_MAX_RETRIES: raise RuntimeError("Anthropic API overloaded.")
                wait=CLAUDE_RETRY_BASE*attempt;print(f"  Overloaded -- waiting {wait}s...");time.sleep(wait)
            else: raise
        except json.JSONDecodeError:
            if attempt==CLAUDE_MAX_RETRIES: raise RuntimeError("Invalid JSON after all retries")
            time.sleep(10)
    raise RuntimeError("Unexpected exit")


def _serp_google_query(seed):
    resp=requests.get(SERP_API_URL,params={"engine":"google","q":seed,"api_key":SERP_API_KEY,"num":10,"hl":"en","gl":"us"},timeout=30)
    resp.raise_for_status();return resp.json()
def _serp_autocomplete_query(seed):
    try:
        resp=requests.get(SERP_API_URL,params={"engine":"google_autocomplete","q":seed,"api_key":SERP_API_KEY,"hl":"en","gl":"us"},timeout=30)
        resp.raise_for_status()
        return [s.get("value","").strip() for s in resp.json().get("suggestions",[]) if s.get("value")]
    except Exception as e: print(f"  Autocomplete failed for '{seed}': {e}");return []
def _word_count(text): return len(text.split())
def _keyword_type(text):
    wc=_word_count(text)
    if wc<=3: return "short_tail"
    elif wc<=5: return "mid_tail"
    else: return "long_tail"

def research_keyword_candidates_from_serp(seeds):
    candidates=[];seen=set()
    for seed in random.sample(seeds,min(SERP_SEEDS_PER_RUN,len(seeds))):
        try:
            data=_serp_google_query(seed)
            total=int(str(data.get("search_information",{}).get("total_results","0")).replace(",","").replace(".","") or "0")
            paa=rs=0
            for q in data.get("related_questions",[]):
                t=q.get("question","").strip()
                if t and t.lower() not in seen: seen.add(t.lower());candidates.append({"text":t,"source":"people_also_ask","tail_type":_keyword_type(t),"word_count":_word_count(t),"seed":seed,"total_results":total});paa+=1
            for r in data.get("related_searches",[]):
                t=r.get("query","").strip()
                if t and t.lower() not in seen: seen.add(t.lower());candidates.append({"text":t,"source":"related_search","tail_type":_keyword_type(t),"word_count":_word_count(t),"seed":seed,"total_results":0});rs+=1
            for org in data.get("organic_results",[])[:3]:
                t=org.get("title","").strip()
                if t and t.lower() not in seen and len(t)<120: seen.add(t.lower());candidates.append({"text":t,"source":"organic_title","tail_type":_keyword_type(t),"word_count":_word_count(t),"seed":seed,"total_results":total})
            print(f"  [GOOGLE] '{seed[:45]}': {paa} PAA | {rs} related | {total:,} results");time.sleep(0.5)
        except Exception as e: print(f"  Google search failed for '{seed}': {e}")
    bases=[]
    for s in seeds:
        w=s.split()
        if len(w)>=3: bases.extend([" ".join(w[:2])," ".join(w[:3])])
        else: bases.append(s)
    for ac in random.sample(list(set(bases)),min(AUTOCOMPLETE_SEEDS_PER_RUN,len(set(bases)))):
        ac_count=0
        for t in _serp_autocomplete_query(ac):
            if t and t.lower() not in seen and _word_count(t)<=6: seen.add(t.lower());candidates.append({"text":t,"source":"autocomplete","tail_type":_keyword_type(t),"word_count":_word_count(t),"seed":ac,"total_results":0});ac_count+=1
        if ac_count: print(f"  [AUTOCOMPLETE] '{ac}': {ac_count} suggestions")
        time.sleep(0.5)
    s=sum(1 for c in candidates if c["tail_type"]=="short_tail")
    m=sum(1 for c in candidates if c["tail_type"]=="mid_tail")
    l=sum(1 for c in candidates if c["tail_type"]=="long_tail")
    print(f"  Total candidates: {len(candidates)} ({s} short | {m} mid | {l} long tail)")
    return candidates

def rank_and_select_keyword_claude(candidates,client,topic_history,visual_style):
    if not candidates: raise ValueError("No SERP candidates to rank")
    type_order={"short_tail":0,"mid_tail":1,"long_tail":2}
    source_order={"autocomplete":0,"people_also_ask":1,"related_search":2,"organic_title":3}
    sorted_cands=sorted(candidates,key=lambda c:(type_order.get(c["tail_type"],3),source_order.get(c["source"],4)))
    candidate_list="\n".join([f"{i+1}. [{c['tail_type'].upper()} | {c['source'].upper()} | {c['word_count']}w] {c['text']}" for i,c in enumerate(sorted_cands[:50])])
    history_note=""
    if topic_history: history_note=f"\nRECENT TOPICS (DO NOT REPEAT):\n"+"\n".join(f"  - {t}" for t in topic_history)+"\nPick something DIFFERENT.\n"
    sn=visual_style.get("name","atmospheric_solitude");sd=visual_style.get("description","moody atmospheric")
    st=visual_style.get("query_templates",["lonely man window","empty road","man thinking"])
    prompt=f"""Expert in SEO for men's mental health, recovery, sobriety on TikTok/Reels/YouTube Shorts.\n\nBelow are REAL Google search queries. Choose the SINGLE BEST keyword for a short video today.\n{history_note}\nFAVOUR: questions men actually ask. Short emotional phrases.\n\nSCORING:\n1. Would a man ask this out loud?\n2. Emotional resonance for men 35-55 struggling silently\n3. Low competition: under big-brand radar?\n4. Niche fit: men's mental health, sobriety, recovery\n\nFORMAT: \"avatar\" (interview) or \"cinematic\" (atmospheric)\nVISUAL STYLE: {sn} ({sd}) | If cinematic, 4 Pexels queries: {st}\n\nCANDIDATES (short-tail first):\n{candidate_list}\n\nReturn ONLY valid JSON:\n{{\n  \"topic\": \"exact candidate text\",\n  \"question\": \"exact question a man would ask\",\n  \"keyword\": \"primary 1-5 word SEO keyword\",\n  \"tail_type\": \"short_tail|mid_tail|long_tail\",\n  \"competition_signal\": \"low|medium|high\",\n  \"why\": \"one sentence\",\n  \"source\": \"autocomplete|people_also_ask|related_search|organic_title\",\n  \"format\": \"avatar|cinematic\",\n  \"visual_style\": \"{sn}\",\n  \"pexels_queries\": [\"q1\",\"q2\",\"q3\",\"q4\"]\n}}"""
    result=_call_claude_raw(prompt,client,max_tokens=700)
    if FORCE_FORMAT in ("avatar","cinematic"): result["format"]=FORCE_FORMAT;print(f"  Format: FORCED to {FORCE_FORMAT.upper()}")
    else: print(f"  Format: {result.get('format','avatar').upper()} (Claude's choice)")
    print(f"  Winner: '{result.get('keyword')}' [{result.get('tail_type','?')} | {result.get('competition_signal','?')} competition]")
    print(f"  Question: {result.get('question','')}")
    return result

def fetch_trending_topic_claude_fallback(seeds,topic_history,visual_style,client):
    seed=random.choice(seeds);hist=f"AVOID: {', '.join(topic_history)}. " if topic_history else ""
    sn=visual_style.get("name","atmospheric_solitude")
    prompt=f"""SEO expert for men's mental health.\nGenerate ONE question for a short interview video. Related to: \"{seed}\"\n{hist}Return ONLY valid JSON:\n{{\n  \"topic\": \"question or keyword\",\n  \"question\": \"exact question a man would ask\",\n  \"keyword\": \"1-5 word SEO keyword\",\n  \"tail_type\": \"short_tail|mid_tail|long_tail\",\n  \"competition_signal\": \"low|medium|high\",\n  \"why\": \"one sentence\",\n  \"source\": \"claude_generated\",\n  \"format\": \"avatar\",\n  \"visual_style\": \"{sn}\",\n  \"pexels_queries\": [\"lonely man window\",\"man thinking dark room\",\"empty street night\",\"person silhouette fog\"]\n}}"""
    result=_call_claude_raw(prompt,client,max_tokens=400)
    if FORCE_FORMAT in ("avatar","cinematic"): result["format"]=FORCE_FORMAT
    return result

def fetch_trending_topic(client):
    keywords=load_niche_keywords();seeds=keywords["seed_queries"]
    topic_history=load_topic_history();visual_style=pick_visual_style(keywords)
    print(f"  Visual style: {visual_style.get('name')} ({visual_style.get('description')})")
    if topic_history: print(f"  Avoiding recent topics: {topic_history}")
    if SERP_API_KEY:
        print(f"  Keyword research: {SERP_SEEDS_PER_RUN} Google + {AUTOCOMPLETE_SEEDS_PER_RUN} autocomplete...")
        try:
            candidates=research_keyword_candidates_from_serp(seeds)
            if candidates:
                topic=rank_and_select_keyword_claude(candidates,client,topic_history,visual_style)
                topic["source"]=f"serp_{topic.get('source','research')}"
                (OUTPUT_DIR/"keyword_research.json").write_text(json.dumps({"run":GITHUB_RUN_NUMBER,"candidates":candidates,"winner":topic},indent=2))
                return topic
            print("  No candidates -- falling back to Claude")
        except Exception as e: print(f"  SERP research failed ({e}) -- falling back to Claude")
    print("  Generating topic with Claude (no SERP)...")
    topic=fetch_trending_topic_claude_fallback(seeds,topic_history,visual_style,client)
    print(f"  Topic: {topic.get('topic')} [{topic.get('tail_type','?')} | {topic.get('competition_signal','?')}]")
    return topic


def generate_content_script(topic,client):
    print(f"  Generating INTERVIEW RESPONSE script for: {topic['topic']}")
    keyword=topic.get("keyword",topic["topic"]);question=topic.get("question",topic["topic"])
    fmt=topic.get("format","avatar");hook_style=random.choice(INTERVIEW_HOOKS)
    lo_hook,hi_hook=WORD_TARGETS_CONTENT["hook"]
    lo_prob,hi_prob=WORD_TARGETS_CONTENT["problem"]
    lo_story,hi_story=WORD_TARGETS_CONTENT["story"]
    lo_cta,hi_cta=WORD_TARGETS_CONTENT["solution_cta"]
    cinematic_note="\nNOTE: Voiceover for cinematic B-roll. Write for the ear only." if fmt=="cinematic" else ""
    banned_str="\n".join(f'  - "{p}..."' for p in BANNED_OPENINGS)
    hook_instructions={"direct_answer":"Start mid-answer, launched straight in.","reframe_first":"Reframe what the question is really about.","counter_intuitive":"Start with what most people get wrong.","personal_truth":"Raw, honest admission. First person.","hard_fact":"Uncomfortable truth nobody says out loud.","challenge_premise":"Push back on how this is usually framed."}
    prompt=f"""You are a credible man in his 40s being interviewed on a podcast about men's mental health.\nThe interviewer just asked you: \"{question}\"\n\nANSWER IT.{cinematic_note}\n\nHOOK STYLE: {hook_style} -- {hook_instructions[hook_style]}\n\n4 SCENES:\n1. hook: First thing out of your mouth.\n2. problem: Why this is the way it is.\n3. story: Truth most men relate to but nobody says.\n4. solution_cta: Genuine takeaway.\n\nAUDIENCE: Men 35+. SEO KEYWORD: {keyword}. TONE: Direct, warm, trusted older brother.\nNo MindCore AI. Pure value.\n\nBANNED OPENINGS:\n{banned_str}\n\nWORD COUNTS: hook {lo_hook}-{hi_hook} | problem {lo_prob}-{hi_prob} | story {lo_story}-{hi_story} | cta {lo_cta}-{hi_cta}\n\nReturn ONLY valid JSON:\n{{\n  \"video_type\": \"content\",\n  \"topic\": \"{topic['topic']}\",\n  \"seo_keyword\": \"{keyword}\",\n  \"render_format\": \"{fmt}\",\n  \"interview_question\": \"{question}\",\n  \"hook_style\": \"{hook_style}\",\n  \"hook\": {{\"voiceover\": \"...\"}},\n  \"problem\": {{\"voiceover\": \"...\"}},\n  \"story\": {{\"voiceover\": \"...\"}},\n  \"solution_cta\": {{\"voiceover\": \"...\"}}\n}}"""
    return _call_claude_raw(prompt,client,max_tokens=1200)

def generate_ad_script(app_facts,client):
    ad_topic=random.choice(AD_TOPICS);hook_style=random.choice(INTERVIEW_HOOKS)
    print(f"  Generating AD script... pain point: {ad_topic['pain_point'][:65]}...")
    lo_hook,hi_hook=WORD_TARGETS_AD["hook"];lo_prob,hi_prob=WORD_TARGETS_AD["problem"]
    lo_story,hi_story=WORD_TARGETS_AD["story"];lo_cta,hi_cta=WORD_TARGETS_AD["solution_cta"]
    banned_str="\n".join(f'  - "{p}..."' for p in BANNED_OPENINGS)
    prompt=f"""Expert men's mental health content creator.\nWrite an informational video script for MindCore AI. Must feel like content for first two scenes.\nPAIN POINT: {ad_topic['pain_point']}\nINSIGHT: {ad_topic['insight']}\nFEATURE: {ad_topic['feature']} (private, 24/7, built for men, Google Play)\nSCENES: hook (no MindCore AI) -> problem (no MindCore AI) -> story (introduce MindCore AI) -> solution_cta (\"Find MindCore AI on Google Play.\")\nBANNED: \"free trial\", \"first week free\", \"download now\"\nBANNED OPENINGS:\n{banned_str}\nWORD COUNTS: hook {lo_hook}-{hi_hook} | problem {lo_prob}-{hi_prob} | story {lo_story}-{hi_story} | cta {lo_cta}-{hi_cta}\nReturn ONLY valid JSON:\n{{\n  \"video_type\": \"ad\",\n  \"topic\": \"{ad_topic['pain_point'][:55]}\",\n  \"seo_keyword\": \"AI mental health coach for men\",\n  \"render_format\": \"avatar\",\n  \"hook_style\": \"{hook_style}\",\n  \"hook\": {{\"voiceover\": \"...\"}},\n  \"problem\": {{\"voiceover\": \"...\"}},\n  \"story\": {{\"voiceover\": \"...\"}},\n  \"solution_cta\": {{\"voiceover\": \"...\"}}\n}}"""
    return _call_claude_raw(prompt,client,max_tokens=1200)

def build_full_script(script):
    parts=[]
    for scene in SCENE_ORDER:
        vo=script[scene]["voiceover"].strip()
        if vo and vo[-1] not in ".!?": vo+="."
        parts.append(vo)
    return "  ".join(parts)


# ---------------------------------------------------------------------------
# AVATAR PATH  (dimension param removed -- HeyGen v3 no longer accepts it)
# ---------------------------------------------------------------------------

def submit_heygen_video(script_text,avatar_id,voice_id):
    headers={"X-Api-Key":HEYGEN_API_KEY,"Content-Type":"application/json"}
    payload={
        "type":"avatar","avatar_id":avatar_id,"voice_id":voice_id,"script":script_text,
        "motion_prompt":"Gesturing naturally with hands while presenting. Warm eye contact. Nodding gently on emotional points. Open palm gestures when sharing insights. Grounded upper body movement throughout.",
        "expressiveness":"high","aspect_ratio":"9:16",
        "use_avatar_iv_model":True,"super_resolution":True,"talking_style":"expressive",
    }
    print(f"  HeyGen: POST /v3/videos | avatar={avatar_id[:8]}...")
    resp=requests.post(HEYGEN_V3_URL,headers=headers,json=payload,timeout=30)
    print(f"  Response [{resp.status_code}]: {resp.text[:200]}")
    if not resp.ok: raise RuntimeError(f"HeyGen v3/videos failed {resp.status_code}: {resp.text}")
    data=resp.json()
    video_id=data.get("data",{}).get("video_id") or data.get("video_id") or data.get("data",{}).get("id") or data.get("id")
    if not video_id: raise RuntimeError(f"No video_id in HeyGen response: {data}")
    print(f"  Submitted -- video_id: {video_id}")
    return video_id

def poll_heygen_video(video_id):
    headers={"X-Api-Key":HEYGEN_API_KEY};deadline=time.time()+VIDEO_TIMEOUT
    while time.time()<deadline:
        resp=requests.get(HEYGEN_STATUS_URL,headers=headers,params={"video_id":video_id},timeout=30)
        resp.raise_for_status();data=resp.json().get("data",{});status=data.get("status","unknown")
        if status=="completed":
            url=data.get("video_url")
            if not url: raise RuntimeError(f"Completed but no video_url: {data}")
            print("  HeyGen render complete!");return url
        if status in ("failed","error"): raise RuntimeError(f"HeyGen render failed: {data}")
        elapsed=int(time.time()-(deadline-VIDEO_TIMEOUT))
        print(f"    waiting... status={status} ({elapsed}s elapsed)");time.sleep(POLL_INTERVAL)
    raise TimeoutError(f"HeyGen timed out after {VIDEO_TIMEOUT}s")

def render_avatar_video(script_text,cfg):
    avatar_id=pick_avatar_look(cfg);voice_id=cfg.get("voice_id","")
    video_id=submit_heygen_video(script_text,avatar_id,voice_id)
    video_url=poll_heygen_video(video_id)
    raw_path=str(OUTPUT_DIR/"mindcore_ai_raw.mp4");final_path=str(OUTPUT_DIR/"mindcore_ai_video.mp4")
    download_video(video_url,raw_path)
    print("\n  [Subtitles] Transcribing audio with Whisper...")
    ass_path=str(OUTPUT_DIR/"subtitles_avatar.ass")
    words=transcribe_audio_whisper(raw_path)
    if not generate_ass_subtitles(words,ass_path): ass_path=None
    crop_to_portrait(raw_path,final_path,ass_path=ass_path)
    return final_path


# ---------------------------------------------------------------------------
# CINEMATIC PATH
# ---------------------------------------------------------------------------

def generate_fish_audio_tts(script_text,output_path):
    if not FISH_AUDIO_API_KEY: raise RuntimeError("FISH_AUDIO_API_KEY not set")
    headers={"Authorization":f"Bearer {FISH_AUDIO_API_KEY}","Content-Type":"application/json"}
    payload={"text":script_text,"reference_id":FISH_AUDIO_VOICE_ID,"format":"mp3","mp3_bitrate":192,"latency":"normal"}
    print(f"  Fish Audio TTS: {FISH_AUDIO_VOICE_ID[:8]}... | {len(script_text)} chars")
    resp=requests.post(FISH_AUDIO_TTS_URL,headers=headers,json=payload,stream=True,timeout=120)
    if not resp.ok: raise RuntimeError(f"Fish Audio TTS failed {resp.status_code}: {resp.text[:300]}")
    with open(output_path,"wb") as f:
        for chunk in resp.iter_content(chunk_size=65_536):
            if chunk: f.write(chunk)
    print(f"  TTS saved: {output_path} ({Path(output_path).stat().st_size/1024:.0f} KB)")
    return output_path

def get_audio_duration(audio_path):
    return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",audio_path],capture_output=True,text=True,check=True).stdout.strip())

def search_pexels_clips(queries,num_clips=PEXELS_CLIPS_PER_VIDEO):
    if not PEXELS_API_KEY: raise RuntimeError("PEXELS_API_KEY not set")
    headers={"Authorization":PEXELS_API_KEY};clips=[];seen_ids=set()
    for query in queries:
        if len(clips)>=num_clips: break
        for orientation in ("portrait",None):
            if len(clips)>=num_clips: break
            params={"query":query,"per_page":5,"size":"medium"}
            if orientation: params["orientation"]=orientation
            try:
                resp=requests.get(PEXELS_VIDEO_URL,headers=headers,params=params,timeout=30)
                if not resp.ok: break
                for video in resp.json().get("videos",[]):
                    vid_id=video["id"]
                    if vid_id in seen_ids: continue
                    seen_ids.add(vid_id)
                    files=video.get("video_files",[])
                    portrait=[f for f in files if f.get("width",1)<f.get("height",1)]
                    chosen=sorted([f for f in (portrait or files) if f.get("height",0)<=1920],key=lambda x:x.get("height",0),reverse=True)
                    if chosen:
                        clips.append({"url":chosen[0]["link"],"query":query,"id":vid_id,"duration":video.get("duration",10)})
                        if len(clips)>=num_clips: break
                time.sleep(0.3)
            except Exception as e: print(f"  Pexels error for '{query}': {e}");break
    print(f"  Pexels: {len(clips)} clips from {len(queries)} queries")
    return clips[:num_clips]

def download_clip(url,output_path):
    resp=requests.get(url,stream=True,timeout=120);resp.raise_for_status()
    with open(output_path,"wb") as f:
        for chunk in resp.iter_content(chunk_size=65_536):
            if chunk: f.write(chunk)
    print(f"  Downloaded: {Path(output_path).name} ({Path(output_path).stat().st_size/(1024*1024):.1f} MB)")
    return output_path

def process_clip_to_portrait(clip_path,output_path,duration):
    cmd=["ffmpeg","-stream_loop","-1","-i",clip_path,
         "-vf","scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,fps=30",
         "-t",str(duration),"-an","-c:v","libx264","-crf","20","-preset","fast","-y",output_path]
    result=subprocess.run(cmd,capture_output=True,text=True)
    if result.returncode!=0: raise RuntimeError(f"Clip processing failed: {result.stderr[-300:]}")
    return output_path

def assemble_cinematic_video(clip_paths,audio_path,output_path,music_path=None,ass_path=None):
    audio_duration=get_audio_duration(audio_path)
    n=len(clip_paths);clip_duration=audio_duration/n
    print(f"  Assembling: {n} clips x {clip_duration:.1f}s = {audio_duration:.1f}s")
    clips_dir=OUTPUT_DIR/"clips";clips_dir.mkdir(exist_ok=True)
    processed=[]
    for i,raw_path in enumerate(clip_paths):
        out=str(clips_dir/f"clip_{i}_processed.mp4")
        try: process_clip_to_portrait(raw_path,out,clip_duration);processed.append(out)
        except Exception as e: print(f"  Clip {i+1} failed ({e}) -- skipping")
    if not processed: raise RuntimeError("No clips processed")
    concat_file=OUTPUT_DIR/"concat.txt"
    with open(concat_file,"w") as f:
        for p in processed: f.write(f"file '{Path(p).resolve()}'\n")
    concat_video=str(OUTPUT_DIR/"concat_video.mp4")
    result=subprocess.run(["ffmpeg","-f","concat","-safe","0","-i",str(concat_file),"-c:v","libx264","-crf","16","-preset","slow","-t",str(audio_duration),"-y",concat_video],capture_output=True,text=True)
    if result.returncode!=0: raise RuntimeError(f"Concat failed: {result.stderr[-500:]}")
    if music_path:
        cmd=["ffmpeg","-i",concat_video,"-i",audio_path,"-stream_loop","-1","-i",music_path,
             "-filter_complex",f"[2:a]volume={MUSIC_VOLUME}[music];[1:a][music]amix=inputs=2:duration=first:normalize=0[aout]",
             "-map","0:v","-map","[aout]","-c:v","copy","-c:a","aac","-b:a","192k","-t",str(audio_duration),"-y",output_path]
    else:
        cmd=["ffmpeg","-i",concat_video,"-i",audio_path,"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k","-t",str(audio_duration),"-y",output_path]
    result=subprocess.run(cmd,capture_output=True,text=True)
    if result.returncode!=0:
        if music_path: print("  WARNING: music mix failed -- retrying without music");assemble_cinematic_video(clip_paths,audio_path,output_path,music_path=None,ass_path=ass_path);return
        raise RuntimeError(f"Audio mix failed: {result.stderr[-500:]}")
    size_mb=Path(output_path).stat().st_size/(1024*1024);w,h=get_video_dimensions(output_path)
    print(f"  Cinematic assembled: {output_path} ({w}x{h} | {size_mb:.1f} MB)")
    if ass_path: burn_subtitles_into_video(output_path,ass_path)

def render_cinematic_video(script_text,pexels_queries):
    print("\n  [Cinematic] Generating voiceover via Fish Audio...")
    audio_path=str(OUTPUT_DIR/"voiceover.mp3")
    generate_fish_audio_tts(script_text,audio_path)
    print("\n  [Cinematic Subtitles] Transcribing TTS audio with Whisper...")
    ass_path=str(OUTPUT_DIR/"subtitles_cinematic.ass")
    words=transcribe_audio_whisper(audio_path)
    if not generate_ass_subtitles(words,ass_path): ass_path=None
    print(f"\n  [Cinematic] Searching Pexels B-roll: {pexels_queries}")
    clips=search_pexels_clips(pexels_queries,num_clips=PEXELS_CLIPS_PER_VIDEO)
    if not clips: raise RuntimeError("No Pexels clips found")
    print(f"\n  [Cinematic] Downloading {len(clips)} clips...")
    clips_dir=OUTPUT_DIR/"clips";clips_dir.mkdir(exist_ok=True)
    raw_clip_paths=[]
    for i,clip in enumerate(clips):
        clip_path=str(clips_dir/f"raw_{i}.mp4")
        try: download_clip(clip["url"],clip_path);raw_clip_paths.append(clip_path)
        except Exception as e: print(f"  Clip {i+1} download failed ({e}) -- skipping")
    if not raw_clip_paths: raise RuntimeError("All clip downloads failed")
    music_path=pick_music_track()
    print(f"\n  [Cinematic] Assembling video ({len(raw_clip_paths)} clips)...")
    final_path=str(OUTPUT_DIR/"mindcore_ai_video.mp4")
    assemble_cinematic_video(raw_clip_paths,audio_path,final_path,music_path,ass_path=ass_path)
    return final_path


def download_video(url,output_path):
    resp=requests.get(url,stream=True,timeout=120);resp.raise_for_status()
    with open(output_path,"wb") as f:
        for chunk in resp.iter_content(chunk_size=65_536):
            if chunk: f.write(chunk)
    print(f"  Downloaded: {output_path} ({Path(output_path).stat().st_size/(1024*1024):.1f} MB)")

def get_video_dimensions(path):
    parts=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","csv=p=0",path],capture_output=True,text=True,check=True).stdout.strip().split(",")
    return int(parts[0]),int(parts[1])

def detect_content_crop(video_path):
    cmd=["ffmpeg","-i",video_path,"-vf","cropdetect=limit=200:round=2:reset=0","-frames:v","90","-f","null","-"]
    result=subprocess.run(cmd,capture_output=True,text=True)
    matches=re.findall(r"crop=(\d+):(\d+):(\d+):(\d+)",result.stderr)
    if not matches: return None
    cw,ch,cx,cy=map(int,matches[-1])
    print(f"  cropdetect: {cw}x{ch} at x={cx}, y={cy}")
    return cw,ch,cx,cy

def make_portrait_filter(cw,ch,cx,cy):
    return (f"crop={cw}:{ch}:{cx}:{cy},"
            f"scale=1080:1920:force_original_aspect_ratio=increase:flags=lanczos,"
            f"crop=1080:1920:(iw-1080)/2:(ih-1920)/2,fps=30")

def crop_to_portrait(raw_path,final_path,ass_path=None):
    w,h=get_video_dimensions(raw_path);print(f"  Raw dimensions: {w}x{h}")
    crop_result=detect_content_crop(raw_path)
    filter_str=make_portrait_filter(*crop_result) if crop_result else make_portrait_filter(w,h,0,0)
    if ass_path and Path(ass_path).exists():
        safe_ass=str(Path(ass_path).resolve()).replace("\\","/")
        filter_str+=f",ass='{safe_ass}'"
        print(f"  Burning subtitles: {Path(ass_path).name} ({SUBTITLE_FONT_SIZE}px {SUBTITLE_FONT} | MarginV {SUBTITLE_MARGIN_V}px)")
    else: print("  No subtitle file -- rendering without captions")
    cmd=["ffmpeg","-i",raw_path,"-vf",filter_str,"-c:v","libx264","-crf","16","-preset","slow","-b:v","4M","-maxrate","6M","-bufsize","8M","-c:a","copy","-y",final_path]
    result=subprocess.run(cmd,capture_output=True,text=True)
    if result.returncode!=0:
        if ass_path and Path(ass_path).exists():
            print("  WARNING: subtitle burn failed -- retrying without captions")
            crop_to_portrait(raw_path,final_path,ass_path=None);return
        raise RuntimeError(f"ffmpeg failed: {result.stderr[-1000:]}")
    size_mb=Path(final_path).stat().st_size/(1024*1024);w2,h2=get_video_dimensions(final_path)
    sub_note=" + captions" if (ass_path and Path(ass_path).exists()) else ""
    print(f"  Final: {final_path} ({w2}x{h2} | {size_mb:.1f} MB{sub_note})")


def generate_upload_guide(script,mode,render_fmt,client):
    print("  Generating upload guide...")
    topic=script.get("topic","");seo_kw=script.get("seo_keyword","")
    question=script.get("interview_question",topic);hook_vo=script.get("hook",{}).get("voiceover","")
    video_type=script.get("video_type",mode)
    prompt=f"""Social media expert for TikTok, Instagram, Facebook, YouTube Shorts. Men's mental health niche.\nVIDEO TYPE: {video_type.upper()} | FORMAT: {render_fmt.upper()}\nQUESTION ANSWERED: {question} | SEO KEYWORD: {seo_kw} | HOOK LINE: {hook_vo}\nGenerate upload copy for all 4 platforms. Include {REQUIRED_BRAND_HASHTAG} everywhere.\nCRITICAL: Write ALL descriptions in your own words. Do NOT copy the video script."""
    for attempt in range(1,CLAUDE_MAX_RETRIES+1):
        try:
            msg=client.messages.create(model="claude-sonnet-4-6",max_tokens=1500,messages=[{"role":"user","content":prompt}])
            return msg.content[0].text.strip()
        except anthropic.APIStatusError as e:
            if e.status_code==529: time.sleep(CLAUDE_RETRY_BASE*attempt)
            else: raise
    raise RuntimeError("Could not generate upload guide")

def generate_upload_metadata(script,mode,client):
    print("  Generating platform metadata...")
    topic=script.get("topic","");seo_kw=script.get("seo_keyword","")
    question=script.get("interview_question",topic);hook_vo=script.get("hook",{}).get("voiceover","")
    video_type=script.get("video_type",mode).upper()
    prompt=f"""Social media expert for men's mental health on TikTok, Instagram, Facebook, YouTube Shorts.\nVIDEO TYPE: {video_type} | QUESTION: {question} | SEO KEYWORD: {seo_kw} | OPENING LINE: {hook_vo}\nCRITICAL: ALL descriptions must be ORIGINAL sentences. Do NOT copy the video script.\n- tiktok_caption: 1-2 punchy sentences + 8-10 hashtags. Max 2200 chars. MUST include {REQUIRED_BRAND_HASHTAG} #mensmentalhealth\n- facebook_title: max 255 chars\n- facebook_description: 2 original sentences + 4-5 hashtags. MUST include {REQUIRED_BRAND_HASHTAG}\n- youtube_title: max 100 chars\n- youtube_description: 2 sentences. Blank line. \"Try MindCore AI: https://mindcoreai.eu\". Blank line. 6-8 hashtags ending #Shorts. MUST include {REQUIRED_BRAND_HASHTAG}\n- youtube_tags: comma-separated 8-12 keywords (no # symbols)\nReturn ONLY valid JSON:\n{{\n  \"tiktok_caption\": \"...\",\n  \"facebook_title\": \"...\",\n  \"facebook_description\": \"...\",\n  \"youtube_title\": \"...\",\n  \"youtube_description\": \"S1. S2.\\n\\nTry MindCore AI: https://mindcoreai.eu\\n\\n{REQUIRED_BRAND_HASHTAG} #mentalhealth #Shorts\",\n  \"youtube_tags\": \"keyword1, keyword2\"\n}}"""
    for attempt in range(1,CLAUDE_MAX_RETRIES+1):
        try:
            msg=client.messages.create(model="claude-sonnet-4-6",max_tokens=700,messages=[{"role":"user","content":prompt}])
            raw=msg.content[0].text.strip()
            if raw.startswith("```"): parts=raw.split("```");raw=parts[1].lstrip("json").strip() if len(parts)>1 else raw
            metadata=json.loads(raw)
            for key in ("tiktok_caption","facebook_description","youtube_description"):
                metadata[key]=ensure_brand_hashtag(metadata.get(key,""))
            metadata["youtube_title"]=metadata.get("youtube_title","")[:YOUTUBE_TITLE_LIMIT]
            print(f"  TikTok+IG: {metadata.get('tiktok_caption','')[:80]}...")
            print(f"  Facebook:  {metadata.get('facebook_title','')[:60]}...")
            print(f"  YouTube:   {metadata.get('youtube_title','')[:60]}...")
            return metadata
        except (anthropic.APIStatusError,json.JSONDecodeError) as e:
            if attempt==CLAUDE_MAX_RETRIES: raise RuntimeError(f"Could not generate metadata: {e}")
            time.sleep(10)
    raise RuntimeError("Unexpected exit")

def upload_to_platforms(video_path,metadata,cfg):
    if not UPLOAD_POST_API_KEY: return {"skipped":True,"reason":"no API key"}
    user=cfg.get("upload_post_user","")
    if not user: return {"skipped":True,"reason":"no user configured"}
    caption=metadata.get("tiktok_caption","")[:TIKTOK_CAPTION_LIMIT]
    fb_title=metadata.get("facebook_title","")[:255]
    fb_desc=metadata.get("facebook_description","")
    yt_title=metadata.get("youtube_title","")[:YOUTUBE_TITLE_LIMIT]
    yt_desc=metadata.get("youtube_description","")[:YOUTUBE_DESCRIPTION_LIMIT]
    yt_tags=metadata.get("youtube_tags","")
    print(f"  Uploading to TikTok + Facebook + Instagram + YouTube as '{user}'...")
    headers={"Authorization":f"Apikey {UPLOAD_POST_API_KEY}"}
    data=[("user",user),("platform[]","tiktok"),("platform[]","facebook"),("platform[]","instagram"),("platform[]","youtube"),
          ("title",caption),("facebook_title",fb_title),("facebook_description",fb_desc),
          ("youtube_title",yt_title),("youtube_description",yt_desc),("youtube_tags",yt_tags)]
    try:
        with open(video_path,"rb") as f:
            files=[("video",("mindcore_ai_video.mp4",f,"video/mp4"))]
            resp=requests.post(UPLOAD_POST_API_URL,headers=headers,files=files,data=data,timeout=180)
        result=resp.json() if resp.headers.get("content-type","").startswith("application/json") else {"raw":resp.text}
        result["status_code"]=resp.status_code
        print(f"  Upload {'successful' if resp.ok else 'WARNING'}: {resp.status_code}")
        if not resp.ok: print(f"  {resp.text[:300]}")
        return result
    except Exception as e: print(f"  Upload failed: {e}");return {"error":str(e)}

def save_upload_guide(guide_text,script,mode,run_number,render_fmt):
    generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    topic=script.get("topic","N/A");seo_kw=script.get("seo_keyword","N/A")
    question=script.get("interview_question",topic);video_type=script.get("video_type",mode).upper()
    hook_style=script.get("hook_style","unknown")
    total_words=sum(len(script[s]["voiceover"].split()) for s in SCENE_ORDER)
    est_duration=round(total_words/130*60)
    music_tracks=list(MUSIC_DIR.glob("*.mp3")) if MUSIC_DIR.exists() else []
    music_note=f"{len(music_tracks)} tracks @ {int(MUSIC_VOLUME*100)}% volume" if music_tracks else "none"
    header=f"""================================================================================
  MINDCORE AI -- VIDEO UPLOAD GUIDE  (Run #{run_number} | {generated_at})
================================================================================
  Video type : {video_type} | Format: {render_fmt.upper()} | Hook: {hook_style}
  Question   : {question}
  Topic      : {topic} | SEO kw: {seo_kw}
  Subtitles  : {SUBTITLE_FONT_SIZE}px {SUBTITLE_FONT} bold white | {SUBTITLE_CHUNK} words/group (AVATAR + CINEMATIC)
  Duration   : ~{est_duration}s ({total_words} words) | Music: {music_note}
================================================================================

FULL SCRIPT\n-----------\n"""
    for scene in SCENE_ORDER:
        wc=len(script[scene]["voiceover"].split())
        header+=f"[{scene.upper()}]  ({wc} words)\n{script[scene]['voiceover']}\n\n"
    header+="================================================================================\n  PLATFORM UPLOAD DETAILS\n================================================================================\n\n"
    (OUTPUT_DIR/"upload_guide.txt").write_text(header+guide_text+"\n\n================================================================================\n",encoding="utf-8")
    print(f"  Upload guide saved")


def main():
    OUTPUT_DIR.mkdir(parents=True,exist_ok=True)
    (OUTPUT_DIR/"clips").mkdir(exist_ok=True)
    mode=determine_mode();cfg=load_config()
    client=anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    upload_enabled=cfg.get("upload_enabled",False) and bool(UPLOAD_POST_API_KEY)
    topic_history=load_topic_history()
    music_tracks=list(MUSIC_DIR.glob("*.mp3")) if MUSIC_DIR.exists() else []
    all_looks=cfg.get("avatar_look_ids",[])
    print(f"\n  MindCore AI Video Pipeline v5.16")
    print(f"  Run #{GITHUB_RUN_NUMBER} -- Mode: {mode.upper()}")
    print(f"  Avatar looks: {len(all_looks)} | shuffled deck rotation")
    print(f"  Subtitles: Whisper '{WHISPER_MODEL}' -> {SUBTITLE_FONT_SIZE}px {SUBTITLE_FONT} bold | AVATAR + CINEMATIC")
    print(f"  Crop: cropdetect limit=200 | HeyGen: dimension param removed (v3 API change)")
    print(f"  Music: {len(music_tracks)} tracks @ {int(MUSIC_VOLUME*100)}%")
    print(f"  Auto-upload: {'ENABLED' if upload_enabled else 'DISABLED'}")
    if FORCE_FORMAT: print(f"  Format override: {FORCE_FORMAT.upper()}")
    print("="*60)
    print("\n  Generating script...")
    if mode=="ad":
        script=generate_ad_script(load_app_facts(),client)
        script=sanitize_script(script);render_fmt="avatar";pexels_queries=[]
    else:
        topic=fetch_trending_topic(client)
        script=generate_content_script(topic,client)
        script=sanitize_script(script)
        render_fmt=topic.get("format","avatar")
        pexels_queries=topic.get("pexels_queries",["man thinking","empty road","lonely man"])
        save_topic_history(topic_history,topic.get("keyword",topic.get("topic","")))
    script["render_format"]=render_fmt
    (OUTPUT_DIR/"script.json").write_text(json.dumps(script,indent=2))
    total_words=sum(len(script[s]["voiceover"].split()) for s in SCENE_ORDER)
    est_duration=round(total_words/130*60)
    print(f"\n  Video type:        {script.get('video_type',mode)}")
    print(f"  Question answered: {script.get('interview_question',script.get('topic','N/A'))}")
    print(f"  Hook style:        {script.get('hook_style','N/A')}")
    print(f"  SEO kw:            {script.get('seo_keyword','N/A')}")
    print(f"  Render format:     {render_fmt.upper()} | ~{est_duration}s ({total_words} words)")
    if est_duration>60: print(f"  NOTE: >{est_duration}s -- YouTube will post as regular video, not Short.")
    print()
    for scene in SCENE_ORDER:
        wc=len(script[scene]["voiceover"].split())
        print(f"  [{scene:15s}]  {wc:2d} words  |  {script[scene]['voiceover']}")
    print(f"\n  Full script:\n  {build_full_script(script)}")
    final_path=None
    if render_fmt=="cinematic":
        print(f"\n  Rendering CINEMATIC video (with Whisper captions)...")
        try: final_path=render_cinematic_video(build_full_script(script),pexels_queries)
        except Exception as e:
            print(f"\n  CINEMATIC RENDER FAILED: {e}\n  Falling back to AVATAR render...")
            render_fmt="avatar";script["render_format"]="avatar"
    if render_fmt=="avatar" or final_path is None:
        print(f"\n  Rendering AVATAR video (HeyGen + Whisper captions)...")
        final_path=render_avatar_video(build_full_script(script),cfg)
    print("\n  Generating upload guide...")
    guide_text=generate_upload_guide(script,mode,render_fmt,client)
    save_upload_guide(guide_text,script,mode,GITHUB_RUN_NUMBER,render_fmt)
    upload_metadata=generate_upload_metadata(script,mode,client)
    (OUTPUT_DIR/"upload_metadata.json").write_text(json.dumps(upload_metadata,indent=2))
    if upload_enabled:
        print("\n  Uploading to all platforms...")
        upload_result=upload_to_platforms(final_path,upload_metadata,cfg)
        (OUTPUT_DIR/"upload_result.json").write_text(json.dumps(upload_result,indent=2))
    else:
        print("\n  Auto-upload disabled")
        (OUTPUT_DIR/"upload_result.json").write_text(json.dumps({"skipped":True},indent=2))
    print(f"\n  DONE | Format: {render_fmt.upper()} | ~{est_duration}s")
    print(f"  Video: {final_path}")
    if upload_enabled: print("  Posted: TikTok + Facebook + Instagram + YouTube")
    print("\n  Pipeline complete!")


if __name__=="__main__":
    try: main()
    except Exception as exc: print(f"\n  FAILED: {exc}",file=sys.stderr);raise SystemExit(1)
