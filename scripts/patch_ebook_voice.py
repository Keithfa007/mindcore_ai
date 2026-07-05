#!/usr/bin/env python3
"""Patch: Fix ebook promo voice settings + rewrite script generation for variety."""
import sys

with open("scripts/ebook_promo_pipeline.py") as f:
    c = f.read()

changes = 0

# 1. Fix voice settings to match kinetic (emotional dramatic monologue)
old_voice = '{"text": script_text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.50, "similarity_boost": 0.75}}'
new_voice = '{"text": script_text, "model_id": "eleven_multilingual_v2", "voice_settings": {"stability": 0.30, "similarity_boost": 0.75, "style": 0.60, "use_speaker_boost": True}}'
if old_voice in c:
    c = c.replace(old_voice, new_voice)
    changes += 1
    print("Fixed: voice settings (stability 0.30, style 0.60, speaker_boost)")

# 2. Replace voiceover script generation with story-driven approach
old_vo_func = '''def generate_voiceover_script(client):
    angle = random.choice(PROMO_ANGLES)
    hook = random.choice(VOICEOVER_HOOKS)
    closer = random.choice(VOICEOVER_CLOSERS)
    print(f"   Voiceover angle: {angle}")
    print(f"   Hook: {hook[:50]}...")
    print(f"   Closer: {closer}")
    prompt = f"""Write a SHORT voiceover script for a TikTok video promoting an ebook called
"{EBOOK_TITLE}  - {EBOOK_SUBTITLE}" by Keith, Founder of MindCore AI.

The ebook is a deeply personal recovery guide written by someone who spent 20 years in addiction and has been 2 years clean.
7 chapters: rock bottom, willpower, shame, the first 7 days, mental reset toolkit, relapse, rebuilding identity.
Chapter 1 is available to read completely free. The full book is currently 50% off through July.

ANGLE: {angle}
OPENING HOOK (use this as the first line or adapt it): "{hook}"
CLOSING LINE (end with this exactly): "{closer}"

RULES:
- Total 3-5 sentences including hook and closer. 10-18 seconds spoken.
- Speak as Keith (first person)  - raw, honest, direct, no filter
- The middle 1-3 sentences should connect the hook to the closer naturally
- NO emojis, NO hashtags, NO links, NO "Hey", NO "What's up"
- Sound like a man talking to himself at 3am, not a marketer

WRITING STYLE (MANDATORY):
- NEVER use em dashes. Use commas, periods, or separate sentences instead.
- NEVER use these AI-tell words: "delve", "tapestry", "landscape", "realm", "navigate", "leverage", "foster", "cultivate", "embark", "comprehensive", "multifaceted", "ever-evolving", "game-changer", "unlock", "unleash", "empower", "supercharge", "revolutionize", "it's important to note", "it's worth noting", "in today's world", "in today's fast-paced world", "harness", "pivotal", "seasoned", "cutting-edge", "spearhead".
- Write like a real person. Vary sentence length. No corporate jargon or motivational-poster tone.
- Prefer simple words: "help" not "facilitate", "use" not "utilize", "start" not "commence".

Return ONLY the voiceover text, nothing else.\\"\\"\\"
    return client.messages.create(model=ANTHROPIC_MODEL, max_tokens=300, messages=[{"role": "user", "content": prompt}]).content[0].text.strip()'''

new_vo_func = '''def generate_voiceover_script(client):
    angle = random.choice(PROMO_ANGLES)
    print(f"   Voiceover angle: {angle}")

    # Story-driven chapters for specific, non-repetitive scripts
    chapter_stories = [
        "Chapter 3 is about shame. The kind you carry so long it starts to feel like your personality. I wrote it because nobody else was going to say it out loud.",
        "There's a section in Chapter 5 about the mental reset. Not motivational quotes. Actual tools I used when I wanted to quit quitting. The ugly, practical stuff.",
        "Chapter 6 is about relapse. Not the Hollywood version. The version where you hide it from everyone and hate yourself in the shower the next morning.",
        "I wrote Chapter 1 about rock bottom. But here's the thing nobody tells you. Rock bottom has a basement. I found it. Then I found the stairs.",
        "The first seven days clean. Chapter 4. I wrote it like a war diary because that's what it felt like. Hour by hour. Minute by minute.",
        "Chapter 7 is about rebuilding. Not the inspirational kind. The kind where you don't recognise yourself anymore and you have to decide who to become from nothing.",
        "There's a page in Chapter 2 where I wrote down every lie I told myself about willpower. Reading it back still makes my stomach turn.",
    ]
    story = random.choice(chapter_stories)

    prompt = f"""Write a SHORT voiceover script for a TikTok video promoting an ebook called
"{EBOOK_TITLE}  - {EBOOK_SUBTITLE}" by Keith, Founder of MindCore AI.

Keith spent 20 years in addiction. 2 years clean. He wrote everything down. 7 chapters. This is not a self-help book. It's a confession that might save someone's life.

Chapter 1 is completely free to read. Full book is 50% off through July.

ANGLE: {angle}

USE THIS STORY ELEMENT (weave it into the script naturally, don't copy verbatim):
{story}

RULES:
- 4-6 sentences total. 15-22 seconds spoken.
- Speak as Keith (first person). Raw, honest, like talking to yourself at 3am.
- Open with something that makes someone stop scrolling. NOT a generic hook. Something specific and visceral.
- Build tension in the middle. Make the listener feel something uncomfortable.
- End with one line about the book. Mention "Chapter 1 is free" or "half price through July" but make it feel earned, not salesy.
- Every script must feel COMPLETELY DIFFERENT from any other ebook promo. Vary tone: some angry, some quiet, some confessional, some defiant.
- NO emojis, NO hashtags, NO links, NO "Hey", NO "What's up"
- Do NOT start with "I spent twenty years" or "Nobody talks about" or "This isn't a self-help book" as these have been overused.

WRITING STYLE (MANDATORY):
- NEVER use em dashes. Use commas, periods, or separate sentences instead.
- NEVER use these AI-tell words: "delve", "tapestry", "landscape", "realm", "navigate", "leverage", "foster", "cultivate", "embark", "comprehensive", "multifaceted", "ever-evolving", "game-changer", "unlock", "unleash", "empower", "supercharge", "revolutionize", "it's important to note", "it's worth noting", "in today's world", "in today's fast-paced world", "harness", "pivotal", "seasoned", "cutting-edge", "spearhead".
- Write like a real person. Short punchy sentences mixed with longer ones. No corporate jargon.
- Prefer simple words: "help" not "facilitate", "use" not "utilize", "start" not "commence".

Return ONLY the voiceover text, nothing else.\\"\\"\\"
    return client.messages.create(model=ANTHROPIC_MODEL, max_tokens=300, messages=[{"role": "user", "content": prompt}]).content[0].text.strip()'''

if 'OPENING HOOK (use this as the first line or adapt it)' in c:
    c = c.replace(old_vo_func, new_vo_func)
    changes += 1
    print("Replaced: voiceover script generation (story-driven, no recycled hooks)")

if changes == 0:
    print("ERROR: No changes applied")
    sys.exit(1)

with open("scripts/ebook_promo_pipeline.py", "w") as f:
    f.write(c)
print(f"\nDone: {changes} changes")
