#!/usr/bin/env python3
"""One-shot: Wire SERP enrichment into library keyword path."""

with open("scripts/blog_automation.py") as f:
    content = f.read()

# Add SERP enrichment to research_from_library
old_func_start = '''def research_from_library(picked, audience, profile, history, library):
    history_txt = format_history_for_prompt(history)
    category    = LIBRARY_CATEGORY_MAP.get(picked["keyword"].lower(), profile["preferred_categories"][0])

    response = _call_anthropic_with_retry(anthropic_client, 
        model="claude-opus-4-5", max_tokens=2000,
        messages=[{"role": "user", "content": f"""You are an expert SEO content strategist for mindcoreai.eu.

VERIFIED KEYWORD: {picked['keyword']}'''

new_func_start = '''def research_from_library(picked, audience, profile, history, library):
    history_txt = format_history_for_prompt(history)
    category    = LIBRARY_CATEGORY_MAP.get(picked["keyword"].lower(), profile["preferred_categories"][0])

    # SERP enrichment: fetch real PAA questions for this keyword
    paa_block = ""
    if SERP_AVAILABLE and SERP_API_KEY:
        try:
            print(f"   [SERP] Enriching library keyword with real search data...")
            serp_candidates = research_topics([picked["keyword"]], SERP_API_KEY, country="gb", num_seeds=1, num_autocomplete=2)
            paa_questions = [c["text"] for c in serp_candidates if c.get("source") == "people_also_ask"][:8]
            related_terms = [c["text"] for c in serp_candidates if c.get("source") in ("autocomplete", "related_searches")][:6]
            if paa_questions:
                paa_block = "\\nREAL GOOGLE 'PEOPLE ALSO ASK' QUESTIONS (use 3-5 of these in the blog FAQ section):\\n"
                paa_block += "\\n".join(f"  - {q}" for q in paa_questions) + "\\n"
                print(f"   [SERP] Found {len(paa_questions)} PAA questions + {len(related_terms)} related terms")
            if related_terms:
                paa_block += "\\nRELATED SEARCH TERMS (weave 2-3 of these naturally into the post):\\n"
                paa_block += "\\n".join(f"  - {t}" for t in related_terms) + "\\n"
        except Exception as e:
            print(f"   [SERP] Enrichment failed (non-fatal): {e}")
    else:
        print("   [SERP] Skipped enrichment (no API key)")

    response = _call_anthropic_with_retry(anthropic_client, 
        model="claude-opus-4-5", max_tokens=2000,
        messages=[{"role": "user", "content": f"""You are an expert SEO content strategist for mindcoreai.eu.

VERIFIED KEYWORD: {picked['keyword']}'''

if old_func_start in content:
    content = content.replace(old_func_start, new_func_start)
    print("Added SERP enrichment call to research_from_library()")
else:
    print("ERROR: Could not find research_from_library function start")

# Now inject the paa_block into the Claude prompt (before ALREADY PUBLISHED)
old_prompt_section = '''ALREADY PUBLISHED (avoid repeating):
{history_txt}

Tasks:'''

new_prompt_section = '''{paa_block}
ALREADY PUBLISHED (avoid repeating):
{history_txt}

Tasks:'''

if "paa_block" not in content.split("research_from_library")[1].split("research_from_claude")[0]:
    # Only replace in research_from_library, not in other functions
    # Find the specific occurrence
    func_start = content.find("def research_from_library")
    func_end = content.find("def research_from_claude")
    func_body = content[func_start:func_end]
    
    if old_prompt_section in func_body:
        new_func_body = func_body.replace(old_prompt_section, new_prompt_section, 1)
        content = content[:func_start] + new_func_body + content[func_end:]
        print("Injected PAA block into Claude prompt")
    else:
        print("WARNING: Could not find prompt injection point")
else:
    print("SKIP: paa_block already in prompt")

with open("scripts/blog_automation.py", "w") as f:
    f.write(content)

print("\nDone! SERP now enriches every library keyword with real PAA questions.")
