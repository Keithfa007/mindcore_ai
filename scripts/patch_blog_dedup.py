#!/usr/bin/env python3
"""One-shot: Clean keyword library + add deduplication guard to blog pipeline."""
import json

# ── PART 1: Clean keyword library ──
print("=== Cleaning keyword library ===")
with open("scripts/keyword_library.json") as f:
    library = json.loads(f.read())

# Mark near-duplicates as used so they never generate posts
MARK_AS_USED = [
    "days sober app",
    "sobriety counter",
    "sober buddy app",
    "stay sober app",
    "sobriety tracking app",
    "personal growth apps",
    "wellbeing apps",
    "self improving apps",
    "mood diary app",
    "mood journal app",
    "emotional support app",
    "stress anxiety companion app",
    "bedtime meditation for sleep",
    "meditation to fall asleep",
    "short meditation for anxiety",
    "meditation to calm the mind",
    "guided relaxation meditation",
]

marked = 0
for entry in library:
    if entry["keyword"].lower() in MARK_AS_USED and not entry.get("used"):
        entry["used"] = True
        entry["skip_reason"] = "near-duplicate of existing post"
        marked += 1
        print(f"  Marked as used: {entry['keyword']}")

with open("scripts/keyword_library.json", "w") as f:
    json.dump(library, f, indent=2)

remaining = [k for k in library if not k.get("used")]
print(f"\nMarked {marked} near-duplicates. {len(remaining)} unique keywords remaining:")
for k in remaining:
    print(f"  ✅ {k['keyword']}")

# ── PART 2: Add deduplication guard to blog pipeline ──
print("\n=== Adding deduplication guard to blog_automation.py ===")
with open("scripts/blog_automation.py") as f:
    content = f.read()

DEDUP_GUARD = '''
# ── Deduplication guard: prevent semantically similar posts ──────────────
KEYWORD_SIMILARITY_GROUPS = [
    ["sober", "sobriety", "recovery app", "clean app", "addiction app"],
    ["mood track", "mood diary", "mood journal", "mood log"],
    ["self improvement", "personal growth", "self improving", "wellbeing app"],
    ["anxiety relief", "anxiety app", "emotional support", "stress companion"],
    ["meditation sleep", "bedtime meditation", "sleep meditation", "fall asleep meditation"],
    ["ai companion", "ai chat", "ai mental health", "ai wellness"],
    ["weighted blanket", "anxiety blanket"],
    ["mental health app", "mental wellness app", "wellness app"],
    ["women mental", "perimenopause", "postpartum"],
]

def is_duplicate_keyword(new_keyword, history):
    """Check if new keyword is too similar to any already-published keyword."""
    used_keywords = [e.get("primary_keyword", "").lower() for e in history]
    new_lower = new_keyword.lower()
    
    for group in KEYWORD_SIMILARITY_GROUPS:
        new_matches = any(term in new_lower for term in group)
        if new_matches:
            for used_kw in used_keywords:
                used_matches = any(term in used_kw for term in group)
                if used_matches:
                    print(f"   DEDUP: '{new_keyword}' blocked (similar to '{used_kw}')")
                    return True
    return False

'''

# Insert after imports, before the first function
marker = "def load_history():"
if "is_duplicate_keyword" not in content:
    content = content.replace(marker, DEDUP_GUARD + marker)
    print("Added deduplication guard function")

    # Wire the guard into pick_from_library
    old_pick = "and kw[\"keyword\"].lower() not in used_keywords"
    new_pick = "and kw[\"keyword\"].lower() not in used_keywords\n            and not is_duplicate_keyword(kw[\"keyword\"], history)"
    content = content.replace(old_pick, new_pick, 1)
    print("Wired guard into pick_from_library()")

    with open("scripts/blog_automation.py", "w") as f:
        f.write(content)
    print("Done!")
else:
    print("SKIP: deduplication guard already exists")
