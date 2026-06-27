#!/usr/bin/env python3
"""One-shot script to inject anti-AI writing rules into all pipeline prompts."""
import re
import os

ANTI_AI_BLOCK = """
WRITING STYLE (MANDATORY):
- NEVER use em dashes. Use commas, periods, or separate sentences instead.
- NEVER use these AI-tell words: "delve", "tapestry", "landscape", "realm", "navigate", "leverage", "foster", "cultivate", "embark", "comprehensive", "multifaceted", "ever-evolving", "game-changer", "unlock", "unleash", "empower", "supercharge", "revolutionize", "it's important to note", "it's worth noting", "in today's world", "in today's fast-paced world", "harness", "pivotal", "seasoned", "cutting-edge", "spearhead".
- Write like a real person. Vary sentence length. No corporate jargon or motivational-poster tone.
- Prefer simple words: "help" not "facilitate", "use" not "utilize", "start" not "commence".
"""

FILES = [
    "scripts/affiliate_carousel_pipeline.py",
    "scripts/relax_audio_blog.py",
    "scripts/affiliate_blog_automation.py",
    "scripts/facebook_automation.py",
    "scripts/instagram_automation.py",
    "scripts/carousel_pipeline.py",
    "scripts/blog_automation.py",
    "video_pipeline/male_pipeline.py",
    "video_pipeline/female_pipeline.py",
]

INJECT_BEFORE = [
    "Return ONLY", "Respond ONLY", "Output ONLY", "Return EXACTLY",
    "Return only", "Respond only",
    "Write ONLY the script",
]

def process_file(filepath):
    if not os.path.exists(filepath):
        print(f"  SKIP {filepath} (not found)")
        return False
    
    with open(filepath) as f:
        content = f.read()
    
    if "WRITING STYLE (MANDATORY)" in content:
        print(f"  SKIP {filepath} (already has anti-AI rules)")
        return False
    
    modified = content
    injected = 0
    
    for pattern in INJECT_BEFORE:
        positions = list(re.finditer(re.escape(pattern), modified))
        offset = 0
        for m in positions:
            pos = m.start() + offset
            nearby = modified[max(0, pos-200):pos]
            if "WRITING STYLE (MANDATORY)" in nearby:
                continue
            modified = modified[:pos] + ANTI_AI_BLOCK + "\n" + modified[pos:]
            offset += len(ANTI_AI_BLOCK) + 1
            injected += 1
    
    # Special case: relax_audio_blog.py - inject before FORMAT:
    if "relax_audio_blog" in filepath and injected == 0:
        modified = modified.replace(
            "FORMAT:\n  - Clean WordPress HTML:",
            ANTI_AI_BLOCK + "\nFORMAT:\n  - Clean WordPress HTML:",
            1
        )
        injected += 1
    
    # Replace em dashes (protect the rule mention)
    modified = modified.replace("em dashes (\u2014)", "EM_DASH_PLACEHOLDER")
    modified = modified.replace("\u2014", " -")
    modified = modified.replace("EM_DASH_PLACEHOLDER", "em dashes (\u2014)")
    
    with open(filepath, "w") as f:
        f.write(modified)
    
    print(f"  OK   {filepath} ({injected} prompt(s) injected)")
    return True

def main():
    print("== Applying anti-AI writing rules ==")
    changed = 0
    for filepath in FILES:
        if process_file(filepath):
            changed += 1
    print(f"\n== Done: {changed}/{len(FILES)} files modified ==")

if __name__ == "__main__":
    main()
