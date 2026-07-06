#!/usr/bin/env python3
"""One-shot patch: blog_automation.py — fix dedup bypass + add category throttle
1. Add is_duplicate_keyword to neutral fallback in pick_from_library
2. Add category throttle: if last 2 posts same category, skip that category
3. Add is_duplicate_keyword to SERP research path
"""

filepath = "scripts/blog_automation.py"

with open(filepath, "r") as f:
    content = f.read()

# ============================================================
# FIX 1: Add is_duplicate_keyword to neutral fallback
# ============================================================
old_fallback = '''    if not candidates and audience != "neutral":
        candidates = [
            kw for kw in library
            if not kw["used"]
            and kw["keyword"].lower() not in used_keywords
            and kw["audience"] == "neutral"
        ]'''

new_fallback = '''    if not candidates and audience != "neutral":
        candidates = [
            kw for kw in library
            if not kw["used"]
            and kw["keyword"].lower() not in used_keywords
            and not is_duplicate_keyword(kw["keyword"], history)
            and kw["audience"] == "neutral"
        ]'''

assert old_fallback in content, "Neutral fallback block not found!"
content = content.replace(old_fallback, new_fallback)

# ============================================================
# FIX 2: Add category throttle to pick_from_library
# ============================================================
old_pick_start = '''def pick_from_library(library, audience, history):
    used_keywords = {e["primary_keyword"].lower() for e in history}
    candidates = ['''

new_pick_start = '''def pick_from_library(library, audience, history):
    used_keywords = {e["primary_keyword"].lower() for e in history}
    # Category throttle: if last 2 posts share the same category, skip it
    throttled_category = None
    if len(history) >= 2:
        last_cats = [h.get("category", "") for h in history[-2:]]
        if last_cats[0] and last_cats[0] == last_cats[1]:
            throttled_category = last_cats[0]
            print(f"   THROTTLE: Skipping category '{throttled_category}' (last 2 posts)")
    candidates = ['''

assert old_pick_start in content, "pick_from_library start not found!"
content = content.replace(old_pick_start, new_pick_start)

# Now add category throttle filter to the primary candidate list
old_primary_filter = '''    candidates = [
        kw for kw in library
        if not kw["used"]
        and kw["keyword"].lower() not in used_keywords
            and not is_duplicate_keyword(kw["keyword"], history)
        and kw["audience"] == audience
    ]'''

new_primary_filter = '''    candidates = [
        kw for kw in library
        if not kw["used"]
        and kw["keyword"].lower() not in used_keywords
        and not is_duplicate_keyword(kw["keyword"], history)
        and kw["audience"] == audience
        and (throttled_category is None or LIBRARY_CATEGORY_MAP.get(kw["keyword"].lower(), "") != throttled_category)
    ]'''

assert old_primary_filter in content, "Primary filter block not found!"
content = content.replace(old_primary_filter, new_primary_filter)

# Also add throttle to the neutral fallback we just fixed
old_fixed_fallback = '''    if not candidates and audience != "neutral":
        candidates = [
            kw for kw in library
            if not kw["used"]
            and kw["keyword"].lower() not in used_keywords
            and not is_duplicate_keyword(kw["keyword"], history)
            and kw["audience"] == "neutral"
        ]'''

new_fixed_fallback = '''    if not candidates and audience != "neutral":
        candidates = [
            kw for kw in library
            if not kw["used"]
            and kw["keyword"].lower() not in used_keywords
            and not is_duplicate_keyword(kw["keyword"], history)
            and kw["audience"] == "neutral"
            and (throttled_category is None or LIBRARY_CATEGORY_MAP.get(kw["keyword"].lower(), "") != throttled_category)
        ]'''

assert old_fixed_fallback in content, "Fixed neutral fallback not found!"
content = content.replace(old_fixed_fallback, new_fixed_fallback)

# ============================================================
# FIX 3: Add category throttle to SERP and Claude research paths
# ============================================================
old_research_serp_call = '''    # Try SERP research before falling back to Claude
    if SERP_AVAILABLE and SERP_API_KEY:
        try:
            result = research_from_serp(audience, profile, history)'''

new_research_serp_call = '''    # Category throttle for SERP/Claude paths too
    throttled_category = None
    if len(history) >= 2:
        last_cats = [h.get("category", "") for h in history[-2:]]
        if last_cats[0] and last_cats[0] == last_cats[1]:
            throttled_category = last_cats[0]

    # Try SERP research before falling back to Claude
    if SERP_AVAILABLE and SERP_API_KEY:
        try:
            result = research_from_serp(audience, profile, history)'''

assert old_research_serp_call in content, "SERP research call not found!"
content = content.replace(old_research_serp_call, new_research_serp_call)

# Add throttle instruction to SERP Claude prompt
old_serp_already_published = '''ALREADY PUBLISHED (avoid repeating):
{history_txt}

PREFERRED CATEGORIES:
{pref_cats}

ALL CATEGORIES:
{all_cats}

Tasks:
1. Use the SERP keyword as primary keyword or refine to 2-5 words'''

new_serp_already_published = '''ALREADY PUBLISHED (avoid repeating):
{history_txt}

CATEGORY RULE: {"IMPORTANT: Do NOT choose category " + throttled_category + " - the last 2 posts were already in this category. Pick a DIFFERENT category." if throttled_category else "No restriction."}

PREFERRED CATEGORIES:
{pref_cats}

ALL CATEGORIES:
{all_cats}

Tasks:
1. Use the SERP keyword as primary keyword or refine to 2-5 words'''

assert old_serp_already_published in content, "SERP already published block not found!"
content = content.replace(old_serp_already_published, new_serp_already_published)

# Add throttle instruction to Claude research prompt
old_claude_already_published = '''ALREADY PUBLISHED:
{history_txt}

PREFERRED CATEGORIES:
{pref_cats}

ALL CATEGORIES:
{all_cats}


WRITING STYLE (MANDATORY):
- NEVER use em dashes. Use commas, periods, or separate sentences instead.
- NEVER use these AI-tell words: "delve"'''

new_claude_already_published = '''ALREADY PUBLISHED:
{history_txt}

CATEGORY RULE: {"IMPORTANT: Do NOT choose category " + throttled_category + " - the last 2 posts were already in this category. Pick a DIFFERENT category." if throttled_category else "No restriction."}

PREFERRED CATEGORIES:
{pref_cats}

ALL CATEGORIES:
{all_cats}


WRITING STYLE (MANDATORY):
- NEVER use em dashes. Use commas, periods, or separate sentences instead.
- NEVER use these AI-tell words: "delve"'''

assert old_claude_already_published in content, "Claude already published block not found!"
content = content.replace(old_claude_already_published, new_claude_already_published)

# ============================================================
# WRITE AND VERIFY
# ============================================================
with open(filepath, "w") as f:
    f.write(content)

print("Patch applied successfully!")

# Verify
with open(filepath, "r") as f:
    patched = f.read()

dedup_count = patched.count("is_duplicate_keyword")
assert dedup_count >= 3, f"Expected 3+ dedup refs, found {dedup_count}"
assert "throttled_category" in patched, "Category throttle not added"
assert "THROTTLE: Skipping category" in patched, "Throttle print not added"
assert "CATEGORY RULE:" in patched, "Category rule not in prompts"
print(f"is_duplicate_keyword appears {dedup_count} times (def + primary + fallback)")
print("All assertions passed!")
