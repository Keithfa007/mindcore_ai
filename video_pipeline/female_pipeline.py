#!/usr/bin/env python3
"""
MindCore AI -- Female Cinematic Pipeline v2.1
=============================================
Fish Audio TTS + Pexels B-roll + FFmpeg assembly.
No HeyGen. No avatar. Cinematic only.

CHANGES (v2.1):
  - Day-based niche rotation from niche_keywords_female.json
  - 12-formula hook system injected into every script prompt
  - 25 banned hook openers
  - Viewer persona per niche for precise emotional targeting
  - Pexels: 8-query mood pool, random 5 sampled per run
  - Pexels: random page 1-3 per search query for clip variety
  - Visual mood cycles through 4 moods per niche by run number

SUBTITLES: Whisper 'tiny' -> 75px Arial bold, MarginV 500px
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
FISH_AUDIO_API_KEY  = os.environ.get("FISH_AUDIO_API_KEY", "")
PEXELS_API_KEY      = os.environ.get("PEXELS_API_KEY", "")
SERP_API_KEY        = os.environ.get("SERP_API_KEY", "")
UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
GITHUB_RUN_NUMBER   = int(os.environ.get("GITHUB_RUN_NUMBER", "1"))

FISH_AUDIO_TTS_URL  = "https://api.fish.audio/v1/tts"
PEXELS_VIDEO_URL    = "https://api.pexels.com/videos/search"
SERP_API_URL        = "https://serpapi.com/search"
UPLOAD_POST_API_URL = "https://api.upload-post.com/api/upload"

FISH_AUDIO_VOICE_ID = "5dac3271d0f04c9186efd837e606d133"

OUTPUT_DIR         = Path("video_pipeline/output_female")
PIPELINE_DIR       = Path("video_pipeline")
MUSIC_DIR          = PIPELINE_DIR / "music"
TOPIC_HISTORY_PATH = PIPELINE_DIR / "topic_history_female.json"
KEYWORDS_PATH      = PIPELINE_DIR / "niche_keywords_female.json"
SCENE_ORDER        = ["hook", "problem", "story", "solution_cta"]

KB_SCALE      = 1.10
KB_DIRECTIONS = ["pan_right", "pan_left", "pan_up", "pan_down", "zoom_in", "zoom_out"]

COLOR_GRADE_FILTER = (
    "eq=contrast=1.05:brightness=0.02:saturation=0.85:gamma=0.95,"
    "colorbalance=rs=0.06:gs=0.01:bs=-0.04"
)

MUSIC_VOLUME       = 0.05
WHISPER_MODEL      = "tiny"
SUBTITLE_FONT      = "Arial"
SUBTITLE_FONT_SIZE = 75
SUBTITLE_MARGIN_V  = 500
SUBTITLE_CHUNK     = 3
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

HOOK_FORMULAS = [
    {"name":"pattern_interrupt","instruction":"Open with a statement that contradicts what the viewer expects. No setup.","example":"Nobody talks about what actually happens when you stop people-pleasing.","rule":"The surprising statement IS the hook. No preamble, no context."},
    {"name":"counter_intuitive","instruction":"State something true that feels wrong at first. Flip the obvious assumption.","example":"Anxiety in women doesn't always look like panic. It looks like over-preparing for everything.","rule":"Must feel like a reframe. The viewer should think: I never thought of it that way."},
    {"name":"uncomfortable_admission","instruction":"Say something the viewer has felt but never heard spoken out loud.","example":"I used to apologise for taking up space in my own life.","rule":"First person or universal. Never preachy. Must feel like someone finally said the quiet part."},
    {"name":"specific_moment","instruction":"Drop the viewer into an exact moment in time they recognise from their own life.","example":"It's 11pm and you're still running through the conversation you had this morning.","rule":"Name the time, the place, the detail. Generic moments don't stop scrolls. Specific ones do."},
    {"name":"direct_challenge","instruction":"Challenge a belief the viewer holds without shaming them. Create a gap they need filled.","example":"The reason you can't rest isn't that you're busy. It's something else entirely.","rule":"Must create urgency. The viewer must need the next sentence to feel complete."},
    {"name":"name_the_feeling","instruction":"Name an emotion or experience with precision the viewer has felt but never heard named.","example":"That thing where you're surrounded by people who love you and still feel invisible.","rule":"Specific enough that only the target viewer recognises it. Too broad = no scroll stop."},
    {"name":"reveal","instruction":"Promise something being withheld. The viewer must feel they'll miss something real if they leave.","example":"There's one thing that happens when women finally stop holding everything together.","rule":"The promised reveal MUST actually be delivered in the video. No bait-and-switch."},
    {"name":"bold_reframe","instruction":"Make a bold statement that reframes how the viewer sees themselves.","example":"You're not too sensitive. You've just been in environments that treated sensitivity as a flaw.","rule":"Must feel earned and true. The viewer should feel seen, not given a motivational poster."},
    {"name":"direct_address","instruction":"Speak directly to one specific person in one specific situation.","example":"If you've spent years being the person everyone leans on and you don't remember the last time someone asked how you were -- this is for you.","rule":"Name the situation, not just the feeling. The more specific, the more people it reaches."},
    {"name":"rhetorical_hit","instruction":"Ask a question the viewer has asked themselves but never heard asked back to them.","example":"When was the last time you put yourself on the list?","rule":"Rhetorical -- not a quiz. The question lands and the video answers it."},
    {"name":"contrast","instruction":"Two short sentences. What others see vs what is actually happening.","example":"Everyone thinks you have it together. You know how much that's costing you.","rule":"Two sentences maximum. No explanation. The contrast must be immediately felt."},
    {"name":"unspoken_truth","instruction":"Say the one thing the viewer has felt but never heard anyone articulate.","example":"You're not tired from doing too much. You're tired from disappearing too long.","rule":"Must be viscerally recognisable on first hearing. If it needs explaining, rewrite it."},
]

BANNED_HOOK_OPENERS = [
    "I remember sitting at my kid","I remember sitting at a","I was sitting at",
    "There I was, sitting","Picture this","Let me tell you something",
    "Here's the thing","Great question","That's a great",
    "So today we're talking about","In this video",
    "There's something important","Most people don't realise",
    "Let me ask you something","If you're watching this",
    "Have you ever felt","Today I want to talk about",
    "Something that doesn't get talked about","This is for anyone who",
    "The truth is,","I want to share something",
    "What if I told you","Here's what nobody tells you",
    "We need to talk about","It's time to talk about",
]

WORD_TARGETS_AD      = {"hook":(12,15),"problem":(30,40),"story":(40,55),"solution_cta":(20,30)}
WORD_TARGETS_CONTENT = {"hook":(12,15),"problem":(30,45),"story":(45,65),"solution_cta":(20,35)}

BANNED_PHRASE_REPLACEMENTS = [
    (r"try\s+it\s+for\s+free","try it"),
    (r"download\s+now","find MindCore AI on Google Play"),
    (r"free\s+trial","try MindCore AI"),
]

AD_TOPICS = [
    {"pain_point":"the 3am overthinking spiral that just won't stop","insight":"Most women don't have a place to put their thoughts that isn't someone else's problem.","feature":"MindCore AI gives you a private, calm space to untangle what's going through your head."},
    {"pain_point":"carrying everyone else's emotions while your own go unnoticed","insight":"Women are often the emotional caretakers. And somewhere in all of that, their own needs disappear.","feature":"MindCore AI is a space that's entirely yours. No one else's feelings to manage."},
    {"pain_point":"feeling like you've completely lost yourself","insight":"You spend so long being everything to everyone that one day you don't know what you actually feel anymore.","feature":"MindCore AI helps you reconnect with yourself -- privately, without pressure. It's on Google Play."},
    {"pain_point":"anxiety that gets dismissed as being too emotional","insight":"Women's anxiety often gets minimised. But it's real, and it deserves real support.","feature":"MindCore AI takes what you're feeling seriously. No dismissal. No labels."},
    {"pain_point":"feeling completely alone even when surrounded by people","insight":"You can be in a room full of people who love you and still feel like nobody actually sees you.","feature":"MindCore AI is there for the moments when you need to be heard. Private, available 24/7."},
    {"pain_point":"the guilt that comes with finally putting yourself first","insight":"Women are often conditioned to feel selfish for having needs.","feature":"MindCore AI is a judgment-free space where putting yourself first isn't selfish."},
    {"pain_point":"the pressure to appear like everything is fine","insight":"Most women are experts at looking okay when they're not. The performance becomes exhausting.","feature":"MindCore AI is the place you don't have to perform. Say exactly what's going on, privately."},
    {"pain_point":"emotional exhaustion from years of people pleasing","insight":"People pleasing isn't a personality trait -- it's a survival strategy that stops working.","feature":"MindCore AI helps you find a way back to yourself. Available any time, on Google Play."},
]


def load_topic_history():
    if TOPIC_HISTORY_PATH.exists():
        try: return json.loads(TOPIC_HISTORY_PATH.read_text())
        except: return []
    return []

def save_topic_history(history, new_topic):
    history.append(new_topic)
    TOPIC_HISTORY_PATH.write_text(json.dumps(history[-TOPIC_HISTORY_SIZE:], indent=2))

def pick_music_track():
    if not MUSIC_DIR.exists(): return None
    tracks=[t for t in MUSIC_DIR.glob("*.mp3") if t.stem!=".gitkeep"]
    if not tracks: return None
    chosen=random.choice(tracks); print(f"  Music: {chosen.name} @ {int(MUSIC_VOLUME*100)}%"); return str(chosen)

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
        original=script[scene]["voiceover"]; cleaned=original
        for pattern,replacement in BANNED_PHRASE_REPLACEMENTS: cleaned=re.sub(pattern,replacement,cleaned,flags=re.IGNORECASE)
        if cleaned!=original: print(f"  SANITIZED [{scene}]"); script[scene]["voiceover"]=cleaned
    return script

def _call_claude_raw(prompt, client, max_tokens=1000):
    for attempt in range(1,CLAUDE_MAX_RETRIES+1):
        try:
            msg=client.messages.create(model="claude-sonnet-4-6",max_tokens=max_tokens,messages=[{"role":"user","content":prompt}])
            raw=msg.content[0].text.strip()
            if raw.startswith("```"): parts=raw.split("```"); raw=parts[1].lstrip("json").strip() if len(parts)>1 else raw
            return json.loads(raw)
        except anthropic.APIStatusError as e:
            if e.status_code==529:
                if attempt==CLAUDE_MAX_RETRIES: raise RuntimeError("Anthropic overloaded.")
                wait=CLAUDE_RETRY_BASE*attempt; print(f"  Overloaded -- waiting {wait}s..."); time.sleep(wait)
            else: raise
        except json.JSONDecodeError:
            if attempt==CLAUDE_MAX_RETRIES: raise RuntimeError("Invalid JSON after all retries")
            time.sleep(10)
    raise RuntimeError("Unexpected exit")

def determine_mode(): return "ad" if GITHUB_RUN_NUMBER%10==0 else "content"
def load_app_facts():
    with open(PIPELINE_DIR/"app_facts.json") as f: return json.load(f)

def load_keywords_data():
    if not KEYWORDS_PATH.exists():
        return {"schedule":{},"niches":{"default":{"name":"Women's Mental Health","viewer_persona":"A woman in her 30s carrying everything for everyone.","seed_queries":["women mental health tips"],"visual_moods":[{"name":"default","description":"soft warm","pexels_queries":["woman alone window","woman journaling","soft light woman","woman nature","woman quiet moment"]}]}}}
    with open(KEYWORDS_PATH) as f: return json.load(f)

def get_niche_for_today(keywords_data):
    day_names=["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
    today=day_names[datetime.now(timezone.utc).weekday()]
    schedule=keywords_data.get("schedule",{}); niche_key=schedule.get(today,list(keywords_data["niches"].keys())[0])
    niche=keywords_data["niches"][niche_key]; print(f"  Niche: {niche['name']} ({today.capitalize()})"); return niche

def pick_visual_mood(niche_data):
    moods=niche_data.get("visual_moods",[])
    if not moods: return {"name":"default","description":"warm cinematic","pexels_queries":["woman alone window","woman journaling","soft light","woman nature","woman peaceful"]}
    mood_index=GITHUB_RUN_NUMBER%len(moods); mood=moods[mood_index]
    print(f"  Visual mood: {mood['name']} ({mood_index+1}/{len(moods)})"); return mood

def sample_pexels_queries(mood, n=PEXELS_CLIPS_PER_VIDEO):
    pool=mood.get("pexels_queries",[])
    if len(pool)<=n: return pool[:]
    return random.sample(pool,n)

def _serp_google_query(seed):
    resp=requests.get(SERP_API_URL,params={"engine":"google","q":seed,"api_key":SERP_API_KEY,"num":10,"hl":"en","gl":"us"},timeout=30)
    resp.raise_for_status(); return resp.json()

def _serp_autocomplete_query(seed):
    try:
        resp=requests.get(SERP_API_URL,params={"engine":"google_autocomplete","q":seed,"api_key":SERP_API_KEY,"hl":"en","gl":"us"},timeout=30)
        resp.raise_for_status(); return [s.get("value","").strip() for s in resp.json().get("suggestions",[]) if s.get("value")]
    except Exception as e: print(f"  Autocomplete failed: {e}"); return []

def _word_count(text): return len(text.split())
def _keyword_type(text):
    wc=_word_count(text); return "short_tail" if wc<=3 else ("mid_tail" if wc<=5 else "long_tail")

def research_keyword_candidates_from_serp(seeds):
    candidates=[]; seen=set()
    for seed in random.sample(seeds,min(SERP_SEEDS_PER_RUN,len(seeds))):
        try:
            data=_serp_google_query(seed)
            total=int(str(data.get("search_information",{}).get("total_results","0")).replace(",","").replace(".","") or "0")
            paa=rs=0
            for q in data.get("related_questions",[]):
                t=q.get("question","").strip()
                if t and t.lower() not in seen: seen.add(t.lower()); candidates.append({"text":t,"source":"people_also_ask","tail_type":_keyword_type(t),"word_count":_word_count(t),"seed":seed,"total_results":total}); paa+=1
            for r in data.get("related_searches",[]):
                t=r.get("query","").strip()
                if t and t.lower() not in seen: seen.add(t.lower()); candidates.append({"text":t,"source":"related_search","tail_type":_keyword_type(t),"word_count":_word_count(t),"seed":seed,"total_results":0}); rs+=1
            for org in data.get("organic_results",[])[:3]:
                t=org.get("title","").strip()
                if t and t.lower() not in seen and len(t)<120: seen.add(t.lower()); candidates.append({"text":t,"source":"organic_title","tail_type":_keyword_type(t),"word_count":_word_count(t),"seed":seed,"total_results":total})
            print(f"  [GOOGLE] '{seed[:45]}': {paa} PAA | {rs} related | {total:,} results"); time.sleep(0.5)
        except Exception as e: print(f"  SERP failed for '{seed}': {e}")
    bases=[]
    for s in seeds:
        w=s.split(); bases.extend([" ".join(w[:2])," ".join(w[:3])] if len(w)>=3 else [s])
    for ac in random.sample(list(set(bases)),min(AUTOCOMPLETE_SEEDS_PER_RUN,len(set(bases)))):
        ac_count=0
        for t in _serp_autocomplete_query(ac):
            if t and t.lower() not in seen and _word_count(t)<=6:
                seen.add(t.lower()); candidates.append({"text":t,"source":"autocomplete","tail_type":_keyword_type(t),"word_count":_word_count(t),"seed":ac,"total_results":0}); ac_count+=1
        if ac_count: print(f"  [AUTOCOMPLETE] '{ac}': {ac_count} suggestions")
        time.sleep(0.5)
    s=sum(1 for c in candidates if c["tail_type"]=="short_tail"); m=sum(1 for c in candidates if c["tail_type"]=="mid_tail"); l=sum(1 for c in candidates if c["tail_type"]=="long_tail")
    print(f"  Candidates: {len(candidates)} ({s} short | {m} mid | {l} long)"); return candidates

def rank_and_select_keyword_claude(candidates, client, topic_history, niche):
    if not candidates: raise ValueError("No SERP candidates")
    type_order={"short_tail":0,"mid_tail":1,"long_tail":2}; source_order={"autocomplete":0,"people_also_ask":1,"related_search":2,"organic_title":3}
    sorted_cands=sorted(candidates,key=lambda c:(type_order.get(c["tail_type"],3),source_order.get(c["source"],4)))
    candidate_list="\n".join([f"{i+1}. [{c['tail_type'].upper()} | {c['source'].upper()} | {c['word_count']}w] {c['text']}" for i,c in enumerate(sorted_cands[:50])])
    history_note=""
    if topic_history: history_note="\nRECENT TOPICS (DO NOT REPEAT):\n"+"\n".join(f"  - {t}" for t in topic_history)+"\nChoose something different.\n"
    prompt=f"""Expert in SEO for women's mental health on TikTok and YouTube Shorts.\nNICHE: {niche['name']}\nVIEWER: {niche['viewer_persona']}\n{history_note}\nChoose the SINGLE BEST keyword for a short cinematic video for this viewer today.\nFAVOUR: emotional, specific, something this woman types alone late at night.\n\nCANDIDATES:\n{candidate_list}\n\nReturn ONLY valid JSON:\n{{"topic":"exact candidate text","question":"exact question this woman asks herself","keyword":"1-5 word SEO keyword","tail_type":"short_tail|mid_tail|long_tail","competition_signal":"low|medium|high","why":"one sentence","source":"autocomplete|people_also_ask|related_search|organic_title"}}"""
    result=_call_claude_raw(prompt,client,max_tokens=500); print(f"  Winner: '{result.get('keyword')}' [{result.get('tail_type','?')}]"); return result

def fetch_trending_topic_claude_fallback(seeds, topic_history, niche, client):
    seed=random.choice(seeds); hist=f"AVOID: {', '.join(topic_history)}. " if topic_history else ""
    prompt=f"""SEO expert for women's mental health.\nNICHE: {niche['name']}\nVIEWER: {niche['viewer_persona']}\nGenerate ONE topic for a cinematic short video. Related to: "{seed}"\n{hist}Return ONLY valid JSON:\n{{"topic":"question or keyword","question":"exact question this woman asks herself","keyword":"1-5 word SEO keyword","tail_type":"short_tail|mid_tail|long_tail","competition_signal":"low|medium|high","why":"one sentence","source":"claude_generated"}}"""
    return _call_claude_raw(prompt,client,max_tokens=400)

def fetch_trending_topic(client, niche):
    seeds=niche["seed_queries"]; topic_history=load_topic_history()
    if topic_history: print(f"  Avoiding recent: {topic_history}")
    if SERP_API_KEY:
        try:
            candidates=research_keyword_candidates_from_serp(seeds)
            if candidates:
                topic=rank_and_select_keyword_claude(candidates,client,topic_history,niche)
                topic["source"]=f"serp_{topic.get('source','research')}"
                (OUTPUT_DIR/"keyword_research.json").write_text(json.dumps({"run":GITHUB_RUN_NUMBER,"niche":niche["name"],"candidates":candidates,"winner":topic},indent=2))
                return topic
        except Exception as e: print(f"  SERP failed ({e}) -- falling back to Claude")
    return fetch_trending_topic_claude_fallback(seeds,topic_history,niche,client)

def _build_hook_block(formula):
    banned_str="\n".join(f'  - "{p}..."' for p in BANNED_HOOK_OPENERS)
    return f"""HOOK (12-15 words MAXIMUM -- the most critical sentence in the video):\nFormula to use: "{formula['name']}"\nWhat to do: {formula['instruction']}\nWorked example: "{formula['example']}"\nNon-negotiable rule: {formula['rule']}\nThe hook MUST create a curiosity gap. The viewer must need the next sentence to feel complete.\n\nFORBIDDEN HOOK OPENERS -- never start with any of these or anything similar:\n{banned_str}"""

def generate_content_script(topic, niche, client):
    keyword=topic.get("keyword",topic["topic"]); question=topic.get("question",topic["topic"])
    formula=random.choice(HOOK_FORMULAS); hook_block=_build_hook_block(formula)
    lo_prob,hi_prob=WORD_TARGETS_CONTENT["problem"]; lo_story,hi_story=WORD_TARGETS_CONTENT["story"]; lo_cta,hi_cta=WORD_TARGETS_CONTENT["solution_cta"]
    prompt=f"""You are writing a cinematic voiceover script for a short-form video.\n\nVIEWER: {niche['viewer_persona']}\nNICHE: {niche['name']}\nQUESTION THE VIEWER IS ASKING HERSELF: "{question}"\nSEO KEYWORD: {keyword}\n\nThis is voiceover for atmospheric B-roll footage. Write for the ear only -- no visual cues, no stage directions.\nNo MindCore AI. Pure value. The viewer should feel understood, not sold to.\n\n{hook_block}\n\n4 SCENES (deliver in this order):\nhook (12-15 words) | problem ({lo_prob}-{hi_prob} words) | story ({lo_story}-{hi_story} words) | solution_cta ({lo_cta}-{hi_cta} words)\n\nReturn ONLY valid JSON:\n{{"video_type":"content","topic":"{topic['topic']}","seo_keyword":"{keyword}","render_format":"cinematic","hook_formula":"{formula['name']}","hook":{{"voiceover":"..."}},"problem":{{"voiceover":"..."}},"story":{{"voiceover":"..."}},"solution_cta":{{"voiceover":"..."}}}}"""
    return _call_claude_raw(prompt,client,max_tokens=1200)

def generate_ad_script(app_facts, niche, client):
    ad_topic=random.choice(AD_TOPICS); formula=random.choice(HOOK_FORMULAS); hook_block=_build_hook_block(formula)
    print(f"  AD: pain point: {ad_topic['pain_point'][:65]}...")
    lo_prob,hi_prob=WORD_TARGETS_AD["problem"]; lo_story,hi_story=WORD_TARGETS_AD["story"]; lo_cta,hi_cta=WORD_TARGETS_AD["solution_cta"]
    prompt=f"""You are writing a cinematic voiceover ad script for MindCore AI targeting women.\n\nVIEWER: {niche['viewer_persona']}\nPAIN POINT: {ad_topic['pain_point']}\nINSIGHT: {ad_topic['insight']}\nFEATURE: {ad_topic['feature']} (private, 24/7, Google Play)\n\n{hook_block}\n\nSCENES: hook -> problem -> story (introduce MindCore AI naturally) -> solution_cta ("Find MindCore AI on Google Play.")\nBANNED: "free trial", "first week free", "download now"\nWORD COUNTS: hook 12-15 | problem {lo_prob}-{hi_prob} | story {lo_story}-{hi_story} | cta {lo_cta}-{hi_cta}\n\nReturn ONLY valid JSON:\n{{"video_type":"ad","topic":"{ad_topic['pain_point'][:55]}","seo_keyword":"AI mental health companion for women","render_format":"cinematic","hook_formula":"{formula['name']}","hook":{{"voiceover":"..."}},"problem":{{"voiceover":"..."}},"story":{{"voiceover":"..."}},"solution_cta":{{"voiceover":"..."}}}}"""
    return _call_claude_raw(prompt,client,max_tokens=1200)

def build_full_script(script):
    parts=[]
    for scene in SCENE_ORDER:
        vo=script[scene]["voiceover"].strip()
        if vo and vo[-1] not in ".!?": vo+="."
        parts.append(vo)
    return "  ".join(parts)

def transcribe_audio_whisper(media_path):
    try:
        import whisper
        print(f"  Whisper: loading '{WHISPER_MODEL}' model...")
        model=whisper.load_model(WHISPER_MODEL)
        result=model.transcribe(str(media_path),word_timestamps=True,language="en",fp16=False)
        words=[]
        for seg in result.get("segments",[]):
            for w in seg.get("words",[]):
                word=w.get("word","").strip()
                if word: words.append({"word":word,"start":float(w.get("start",0)),"end":float(w.get("end",0))})
        print(f"  Whisper: {len(words)} words"); return words
    except Exception as e: print(f"  Whisper failed ({e}) -- no subtitles"); return []

def generate_ass_subtitles(words, output_path):
    if not words: return False
    def ts(s): h=int(s//3600);m=int((s%3600)//60);s=s%60; return f"{h}:{m:02d}:{s:05.2f}"
    header=("[Script Info]\nScriptType: v4.00+\nPlayResX: 1080\nPlayResY: 1920\nScaledBorderAndShadow: yes\nWrapStyle: 1\n\n[V4+ Styles]\n"
            "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\n"
            f"Style: Default,{SUBTITLE_FONT},{SUBTITLE_FONT_SIZE},&H00FFFFFF,&H000000FF,&H00000000,&H00000000,-1,0,0,0,100,100,1,0,1,4,0,2,60,60,{SUBTITLE_MARGIN_V},1\n\n"
            "[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n")
    chunks=[]; i=0
    while i<len(words):
        chunk=words[i:i+SUBTITLE_CHUNK]; text=" ".join(w["word"].upper() for w in chunk)
        start=chunk[0]["start"]; end=chunk[-1]["end"]
        if chunks and start<chunks[-1]["end"]: start=chunks[-1]["end"]
        chunks.append({"text":text,"start":start,"end":end}); i+=SUBTITLE_CHUNK
    events="".join(f"Dialogue: 0,{ts(c['start'])},{ts(c['end'])},Default,,0,0,0,,{c['text']}\n" for c in chunks)
    Path(output_path).write_text(header+events,encoding="utf-8")
    print(f"  Subtitles: {len(chunks)} groups | {SUBTITLE_FONT} {SUBTITLE_FONT_SIZE}px | MarginV {SUBTITLE_MARGIN_V}px"); return True

def burn_subtitles_into_video(video_path, ass_path):
    if not ass_path or not Path(ass_path).exists(): return False
    safe_ass=str(Path(ass_path).resolve()).replace("\\","/"); burnt_tmp=video_path.replace(".mp4","_subtitled.mp4")
    cmd=["ffmpeg","-i",video_path,"-vf",f"ass='{safe_ass}'","-c:v","libx264","-crf","16","-preset","slow","-c:a","copy","-y",burnt_tmp]
    result=subprocess.run(cmd,capture_output=True,text=True)
    if result.returncode==0:
        Path(burnt_tmp).replace(Path(video_path)); print(f"  Captions burned: {Path(video_path).stat().st_size/(1024*1024):.1f} MB"); return True
    print("  WARNING: subtitle burn failed")
    if Path(burnt_tmp).exists(): Path(burnt_tmp).unlink(); return False

def ken_burns_vf(clip_duration, direction):
    d=max(clip_duration,0.5); sw=int(1080*KB_SCALE); sh=int(1920*KB_SCALE); ew=sw-1080; eh=sh-1920
    if direction=="pan_right":   x,y=f"min(t/{d:.2f}*{ew},{ew})",str(eh//2)
    elif direction=="pan_left":  x,y=f"max({ew}-t/{d:.2f}*{ew},0)",str(eh//2)
    elif direction=="pan_up":    x,y=str(ew//2),f"min(t/{d:.2f}*{eh},{eh})"
    elif direction=="pan_down":  x,y=str(ew//2),f"max({eh}-t/{d:.2f}*{eh},0)"
    elif direction=="zoom_in":   x,y=f"max({ew}-t/{d:.2f}*{ew//2},{ew//2})",f"max({eh}-t/{d:.2f}*{eh//2},{eh//2})"
    else:                        x,y=f"min(t/{d:.2f}*{ew//2},{ew//2})",f"min(t/{d:.2f}*{eh//2},{eh//2})"
    return f"scale={sw}:{sh},crop=1080:1920:{x}:{y}"

def generate_fish_audio_tts(script_text, output_path):
    if not FISH_AUDIO_API_KEY: raise RuntimeError("FISH_AUDIO_API_KEY not set")
    headers={"Authorization":f"Bearer {FISH_AUDIO_API_KEY}","Content-Type":"application/json"}
    payload={"text":script_text,"reference_id":FISH_AUDIO_VOICE_ID,"format":"mp3","mp3_bitrate":192,"latency":"normal"}
    print(f"  Fish Audio TTS: {FISH_AUDIO_VOICE_ID[:8]}... | {len(script_text)} chars")
    resp=requests.post(FISH_AUDIO_TTS_URL,headers=headers,json=payload,stream=True,timeout=120)
    if not resp.ok: raise RuntimeError(f"Fish Audio TTS failed {resp.status_code}: {resp.text[:300]}")
    with open(output_path,"wb") as f:
        for chunk in resp.iter_content(chunk_size=65_536):
            if chunk: f.write(chunk)
    print(f"  TTS: {Path(output_path).stat().st_size/1024:.0f} KB"); return output_path

def get_audio_duration(audio_path):
    return float(subprocess.run(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",audio_path],capture_output=True,text=True,check=True).stdout.strip())

def search_pexels_clips(queries, num_clips=PEXELS_CLIPS_PER_VIDEO):
    if not PEXELS_API_KEY: raise RuntimeError("PEXELS_API_KEY not set")
    headers={"Authorization":PEXELS_API_KEY}; clips=[]; seen_ids=set()
    for query in queries:
        if len(clips)>=num_clips: break
        for orientation in ("portrait",None):
            if len(clips)>=num_clips: break
            params={"query":query,"per_page":5,"size":"medium","page":random.randint(1,3)}
            if orientation: params["orientation"]=orientation
            try:
                resp=requests.get(PEXELS_VIDEO_URL,headers=headers,params=params,timeout=30)
                if not resp.ok: break
                for video in resp.json().get("videos",[]):
                    vid_id=video["id"]
                    if vid_id in seen_ids: continue
                    seen_ids.add(vid_id); files=video.get("video_files",[])
                    portrait=[f for f in files if f.get("width",1)<f.get("height",1)]
                    chosen=sorted([f for f in (portrait or files) if f.get("height",0)<=1920],key=lambda x:x.get("height",0),reverse=True)
                    if chosen:
                        clips.append({"url":chosen[0]["link"],"query":query,"id":vid_id,"duration":video.get("duration",10)})
                        if len(clips)>=num_clips: break
                time.sleep(0.3)
            except Exception as e: print(f"  Pexels error '{query}': {e}"); break
    print(f"  Pexels: {len(clips)} clips"); return clips[:num_clips]

def download_clip(url, output_path):
    resp=requests.get(url,stream=True,timeout=120); resp.raise_for_status()
    with open(output_path,"wb") as f:
        for chunk in resp.iter_content(chunk_size=65_536):
            if chunk: f.write(chunk)
    print(f"  Clip: {Path(output_path).name} ({Path(output_path).stat().st_size/(1024*1024):.1f} MB)"); return output_path

def process_clip_to_portrait(clip_path, output_path, duration, direction="pan_right"):
    kb_vf=ken_burns_vf(duration,direction); vf_str=f"{kb_vf},{COLOR_GRADE_FILTER},fps=30"
    cmd=["ffmpeg","-stream_loop","-1","-i",clip_path,"-vf",vf_str,"-t",str(duration),"-an","-c:v","libx264","-crf","20","-preset","fast","-y",output_path]
    result=subprocess.run(cmd,capture_output=True,text=True)
    if result.returncode!=0: raise RuntimeError(f"Clip failed: {result.stderr[-300:]}"); return output_path

def assemble_cinematic_video(clip_paths, audio_path, output_path, music_path=None, ass_path=None):
    audio_duration=get_audio_duration(audio_path); n=len(clip_paths); clip_duration=audio_duration/n
    print(f"  Assembling: {n} clips x {clip_duration:.1f}s = {audio_duration:.1f}s")
    clips_dir=OUTPUT_DIR/"clips"; clips_dir.mkdir(exist_ok=True); processed=[]
    for i,raw_path in enumerate(clip_paths):
        direction=KB_DIRECTIONS[i%len(KB_DIRECTIONS)]; out=str(clips_dir/f"clip_{i}_processed.mp4")
        try: process_clip_to_portrait(raw_path,out,clip_duration,direction); processed.append(out); print(f"    Clip {i+1}/{n}: {direction}")
        except Exception as e: print(f"  Clip {i+1} failed ({e}) -- skipping")
    if not processed: raise RuntimeError("No clips processed")
    concat_file=OUTPUT_DIR/"concat.txt"
    with open(concat_file,"w") as f:
        for p in processed: f.write(f"file '{Path(p).resolve()}'\n")
    concat_video=str(OUTPUT_DIR/"concat_video.mp4")
    result=subprocess.run(["ffmpeg","-f","concat","-safe","0","-i",str(concat_file),"-c:v","copy","-t",str(audio_duration),"-y",concat_video],capture_output=True,text=True)
    if result.returncode!=0: raise RuntimeError(f"Concat failed: {result.stderr[-500:]}")
    if music_path:
        cmd=["ffmpeg","-i",concat_video,"-i",audio_path,"-stream_loop","-1","-i",music_path,"-filter_complex",f"[2:a]volume={MUSIC_VOLUME}[music];[1:a][music]amix=inputs=2:duration=first:normalize=0[aout]","-map","0:v","-map","[aout]","-c:v","copy","-c:a","aac","-b:a","192k","-t",str(audio_duration),"-y",output_path]
    else:
        cmd=["ffmpeg","-i",concat_video,"-i",audio_path,"-map","0:v:0","-map","1:a:0","-c:v","copy","-c:a","aac","-b:a","192k","-t",str(audio_duration),"-y",output_path]
    result=subprocess.run(cmd,capture_output=True,text=True)
    if result.returncode!=0:
        if music_path: print("  Music mix failed -- retrying without music"); assemble_cinematic_video(clip_paths,audio_path,output_path,music_path=None,ass_path=ass_path); return
        raise RuntimeError(f"Audio mix failed: {result.stderr[-500:]}")
    size_mb=Path(output_path).stat().st_size/(1024*1024); w,h=get_video_dimensions(output_path)
    print(f"  Assembled: {w}x{h} | {size_mb:.1f} MB")
    if ass_path: burn_subtitles_into_video(output_path,ass_path)

def render_cinematic_video(script_text, mood):
    print("\n  [TTS] Generating voiceover...")
    audio_path=str(OUTPUT_DIR/"voiceover_female.mp3"); generate_fish_audio_tts(script_text,audio_path)
    print("\n  [Subtitles] Transcribing with Whisper...")
    ass_path=str(OUTPUT_DIR/"subtitles_cinematic_female.ass"); words=transcribe_audio_whisper(audio_path)
    if not generate_ass_subtitles(words,ass_path): ass_path=None
    pexels_queries=sample_pexels_queries(mood)
    print(f"\n  [Pexels] Mood: {mood['name']} | Queries: {pexels_queries}")
    clips=search_pexels_clips(pexels_queries)
    if not clips: raise RuntimeError("No Pexels clips found")
    clips_dir=OUTPUT_DIR/"clips"; clips_dir.mkdir(exist_ok=True); raw_clip_paths=[]
    for i,clip in enumerate(clips):
        clip_path=str(clips_dir/f"raw_{i}.mp4")
        try: download_clip(clip["url"],clip_path); raw_clip_paths.append(clip_path)
        except Exception as e: print(f"  Clip {i+1} download failed ({e})")
    if not raw_clip_paths: raise RuntimeError("All clip downloads failed")
    music_path=pick_music_track(); final_path=str(OUTPUT_DIR/"mindcore_female_video.mp4")
    assemble_cinematic_video(raw_clip_paths,audio_path,final_path,music_path,ass_path); return final_path

def get_video_dimensions(path):
    parts=subprocess.run(["ffprobe","-v","error","-select_streams","v:0","-show_entries","stream=width,height","-of","csv=p=0",path],capture_output=True,text=True,check=True).stdout.strip().split(",")
    return int(parts[0]),int(parts[1])

def generate_upload_guide(script, mode, niche, client):
    seo_kw=script.get("seo_keyword",""); hook_vo=script.get("hook",{}).get("voiceover",""); vtype=script.get("video_type",mode).upper()
    prompt=f"""Social media expert for TikTok, Instagram, Facebook, YouTube Shorts. Women's mental health.\nNICHE: {niche['name']} | VIDEO TYPE: {vtype} | SEO KEYWORD: {seo_kw} | HOOK: {hook_vo}\nGenerate upload copy for all 4 platforms. Include {REQUIRED_BRAND_HASHTAG} everywhere.\nCRITICAL: Original sentences only. Never copy the script."""
    for attempt in range(1,CLAUDE_MAX_RETRIES+1):
        try:
            msg=client.messages.create(model="claude-sonnet-4-6",max_tokens=1500,messages=[{"role":"user","content":prompt}])
            return msg.content[0].text.strip()
        except anthropic.APIStatusError as e:
            if e.status_code==529: time.sleep(CLAUDE_RETRY_BASE*attempt)
            else: raise
    raise RuntimeError("Could not generate upload guide")

def generate_upload_metadata(script, mode, niche, client):
    seo_kw=script.get("seo_keyword",""); hook_vo=script.get("hook",{}).get("voiceover",""); vtype=script.get("video_type",mode).upper()
    prompt=f"""Social media expert for women's mental health on TikTok, Instagram, Facebook, YouTube Shorts.\nNICHE: {niche['name']} | VIDEO TYPE: {vtype} | SEO KEYWORD: {seo_kw} | HOOK: {hook_vo}\nCRITICAL: ORIGINAL sentences only. Do NOT copy the script.\n- tiktok_caption: 1-2 sentences + 8-10 hashtags. Max 2200 chars. MUST include {REQUIRED_BRAND_HASHTAG} #womensmentalhealth\n- facebook_title: max 255 chars\n- facebook_description: 2 sentences + 4-5 hashtags. MUST include {REQUIRED_BRAND_HASHTAG}\n- youtube_title: max 100 chars\n- youtube_description: 2 sentences. Blank line. "Try MindCore AI: https://mindcoreai.eu". Blank line. 6-8 hashtags ending #Shorts. MUST include {REQUIRED_BRAND_HASHTAG}\n- youtube_tags: comma-separated 8-12 keywords (no # symbols)\nReturn ONLY valid JSON:\n{{"tiktok_caption":"...","facebook_title":"...","facebook_description":"...","youtube_title":"...","youtube_description":"...","youtube_tags":"..."}}"""
    for attempt in range(1,CLAUDE_MAX_RETRIES+1):
        try:
            msg=client.messages.create(model="claude-sonnet-4-6",max_tokens=700,messages=[{"role":"user","content":prompt}])
            raw=msg.content[0].text.strip()
            if raw.startswith("```"): parts=raw.split("```"); raw=parts[1].lstrip("json").strip() if len(parts)>1 else raw
            metadata=json.loads(raw)
            for key in ("tiktok_caption","facebook_description","youtube_description"): metadata[key]=ensure_brand_hashtag(metadata.get(key,""))
            metadata["youtube_title"]=metadata.get("youtube_title","")[:YOUTUBE_TITLE_LIMIT]
            print(f"  TikTok:  {metadata.get('tiktok_caption','')[:80]}..."); print(f"  YouTube: {metadata.get('youtube_title','')[:60]}...")
            return metadata
        except (anthropic.APIStatusError,json.JSONDecodeError) as e:
            if attempt==CLAUDE_MAX_RETRIES: raise RuntimeError(f"Metadata failed: {e}")
            time.sleep(10)
    raise RuntimeError("Unexpected exit")

def upload_to_platforms(video_path, metadata, cfg):
    if not UPLOAD_POST_API_KEY: return {"skipped":True,"reason":"no API key"}
    user=cfg.get("upload_post_user","")
    if not user: return {"skipped":True,"reason":"no user configured"}
    headers={"Authorization":f"Apikey {UPLOAD_POST_API_KEY}"}
    data=[("user",user),("platform[]","tiktok"),("platform[]","facebook"),("platform[]","instagram"),("platform[]","youtube"),
          ("title",metadata.get("tiktok_caption","")[:TIKTOK_CAPTION_LIMIT]),("facebook_title",metadata.get("facebook_title","")[:255]),
          ("facebook_description",metadata.get("facebook_description","")),("youtube_title",metadata.get("youtube_title","")[:YOUTUBE_TITLE_LIMIT]),
          ("youtube_description",metadata.get("youtube_description","")[:YOUTUBE_DESCRIPTION_LIMIT]),("youtube_tags",metadata.get("youtube_tags",""))]
    try:
        with open(video_path,"rb") as f:
            files=[("video",("mindcore_female_video.mp4",f,"video/mp4"))]
            resp=requests.post(UPLOAD_POST_API_URL,headers=headers,files=files,data=data,timeout=180)
        result=resp.json() if resp.headers.get("content-type","").startswith("application/json") else {"raw":resp.text}
        result["status_code"]=resp.status_code; print(f"  Upload {'OK' if resp.ok else 'WARNING'}: {resp.status_code}")
        if not resp.ok: print(f"  {resp.text[:300]}"); return result
    except Exception as e: print(f"  Upload failed: {e}"); return {"error":str(e)}

def save_upload_guide(guide_text, script, mode, run_number, niche):
    generated_at=datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    total_words=sum(len(script[s]["voiceover"].split()) for s in SCENE_ORDER); est_duration=round(total_words/130*60)
    header=f"MINDCORE AI FEMALE UPLOAD GUIDE -- Run #{run_number} | {generated_at}\nNiche: {niche['name']} | Format: CINEMATIC | ~{est_duration}s | {total_words} words\n\nFULL SCRIPT\n"
    for scene in SCENE_ORDER: header+=f"[{scene.upper()}] {script[scene]['voiceover']}\n\n"
    (OUTPUT_DIR/"upload_guide_female.txt").write_text(header+guide_text,encoding="utf-8"); print("  Upload guide saved")

def main():
    OUTPUT_DIR.mkdir(parents=True,exist_ok=True); (OUTPUT_DIR/"clips").mkdir(exist_ok=True)
    mode=determine_mode(); client=anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    cfg={}; cfg_path=PIPELINE_DIR/"heygen_config_female.json"
    if cfg_path.exists():
        with open(cfg_path) as f: cfg=json.load(f)
    upload_enabled=cfg.get("upload_enabled",False) and bool(UPLOAD_POST_API_KEY)
    music_tracks=list(MUSIC_DIR.glob("*.mp3")) if MUSIC_DIR.exists() else []
    keywords_data=load_keywords_data(); niche=get_niche_for_today(keywords_data); mood=pick_visual_mood(niche)
    print(f"\n  MindCore AI -- Female Cinematic Pipeline v2.1")
    print(f"  Run #{GITHUB_RUN_NUMBER} -- Mode: {mode.upper()}")
    print(f"  Niche: {niche['name']} | Mood: {mood['name']}")
    print(f"  Ken Burns: {len(KB_DIRECTIONS)} directions | Colour grade: FEMALE (warm/soft)")
    print(f"  Subtitles: Whisper '{WHISPER_MODEL}' -> {SUBTITLE_FONT_SIZE}px {SUBTITLE_FONT}, MarginV {SUBTITLE_MARGIN_V}px")
    print(f"  Music: {len(music_tracks)} tracks @ {int(MUSIC_VOLUME*100)}% | Upload: {'ENABLED' if upload_enabled else 'DISABLED'}")
    print("="*60)
    print("\n  Generating script...")
    if mode=="ad": script=generate_ad_script(load_app_facts(),niche,client)
    else:
        topic=fetch_trending_topic(client,niche); script=generate_content_script(topic,niche,client)
        topic_history=load_topic_history(); save_topic_history(topic_history,topic.get("keyword",topic.get("topic","")))
    script=sanitize_script(script); (OUTPUT_DIR/"script_female.json").write_text(json.dumps(script,indent=2))
    total_words=sum(len(script[s]["voiceover"].split()) for s in SCENE_ORDER); est_duration=round(total_words/130*60)
    print(f"\n  ~{est_duration}s | Hook formula: {script.get('hook_formula','?')}")
    for scene in SCENE_ORDER: print(f"  [{scene:15s}] {script[scene]['voiceover'][:85]}...")
    final_path=render_cinematic_video(build_full_script(script),mood)
    guide_text=generate_upload_guide(script,mode,niche,client); save_upload_guide(guide_text,script,mode,GITHUB_RUN_NUMBER,niche)
    upload_metadata=generate_upload_metadata(script,mode,niche,client); (OUTPUT_DIR/"upload_metadata_female.json").write_text(json.dumps(upload_metadata,indent=2))
    if upload_enabled:
        upload_result=upload_to_platforms(final_path,upload_metadata,cfg); (OUTPUT_DIR/"upload_result_female.json").write_text(json.dumps(upload_result,indent=2))
    else: (OUTPUT_DIR/"upload_result_female.json").write_text(json.dumps({"skipped":True},indent=2))
    print(f"\n  DONE | CINEMATIC | ~{est_duration}s | {niche['name']} | {mood['name']}")
    if upload_enabled: print("  Posted: TikTok + Facebook + Instagram + YouTube")

if __name__=="__main__":
    try: main()
    except Exception as exc: print(f"\n  FAILED: {exc}",file=sys.stderr); raise SystemExit(1)
