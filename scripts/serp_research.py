"""
MindCore AI — Shared SERP Research Module v1.0
===============================================
Reusable keyword research functions for all pipelines.
Uses SerpAPI for Google search, People Also Ask, Related Searches,
and Autocomplete data.

Usage:
    from scripts.serp_research import research_topics, pick_best_topic

    candidates = research_topics(seeds, serp_api_key, country="us")
    winner = pick_best_topic(candidates, anthropic_client, history, context)
"""

import os, random, time, requests

SERP_API_URL = "https://serpapi.com/search"


def _serp_google(seed, api_key, country="gb"):
    """Run a Google search via SerpAPI. Returns raw JSON."""
    r = requests.get(SERP_API_URL, params={
        "engine": "google", "q": seed, "api_key": api_key,
        "num": 10, "hl": "en", "gl": country,
    }, timeout=30)
    r.raise_for_status()
    return r.json()


def _serp_autocomplete(seed, api_key, country="gb"):
    """Get Google Autocomplete suggestions."""
    try:
        r = requests.get(SERP_API_URL, params={
            "engine": "google_autocomplete", "q": seed,
            "api_key": api_key, "hl": "en", "gl": country,
        }, timeout=30)
        r.raise_for_status()
        return [s.get("value", "").strip() for s in r.json().get("suggestions", []) if s.get("value")]
    except Exception as e:
        print(f"  Autocomplete failed: {e}")
        return []


def _word_count(t):
    return len(t.split())


def _keyword_type(t):
    wc = _word_count(t)
    return "short_tail" if wc <= 3 else ("mid_tail" if wc <= 5 else "long_tail")


def research_topics(seeds, serp_api_key, country="gb", num_seeds=3, num_autocomplete=2):
    """Research keyword candidates from SERP data.

    Args:
        seeds: List of seed queries to research.
        serp_api_key: SerpAPI key.
        country: Country code for SERP (gb, us, etc).
        num_seeds: How many seeds to search (from the pool).
        num_autocomplete: How many autocomplete queries to run.

    Returns:
        List of candidate dicts with text, source, tail_type, word_count, seed.
    """
    candidates = []
    seen = set()

    # Google search: PAA + Related Searches + Organic titles
    for seed in random.sample(seeds, min(num_seeds, len(seeds))):
        try:
            data = _serp_google(seed, serp_api_key, country)
            total = int(str(data.get("search_information", {}).get("total_results", "0")).replace(",", "").replace(".", "") or "0")
            paa = rs = 0

            for q in data.get("related_questions", []):
                t = q.get("question", "").strip()
                if t and t.lower() not in seen:
                    seen.add(t.lower())
                    candidates.append({"text": t, "source": "people_also_ask", "tail_type": _keyword_type(t), "word_count": _word_count(t), "seed": seed, "total_results": total})
                    paa += 1

            for r in data.get("related_searches", []):
                t = r.get("query", "").strip()
                if t and t.lower() not in seen:
                    seen.add(t.lower())
                    candidates.append({"text": t, "source": "related_search", "tail_type": _keyword_type(t), "word_count": _word_count(t), "seed": seed, "total_results": 0})
                    rs += 1

            for org in data.get("organic_results", [])[:3]:
                t = org.get("title", "").strip()
                if t and t.lower() not in seen and len(t) < 120:
                    seen.add(t.lower())
                    candidates.append({"text": t, "source": "organic_title", "tail_type": _keyword_type(t), "word_count": _word_count(t), "seed": seed, "total_results": total})

            print(f"  [SERP {country.upper()}] '{seed[:45]}': {paa} PAA | {rs} related | {total:,} results")
            time.sleep(0.5)
        except Exception as e:
            print(f"  SERP failed for '{seed}': {e}")

    # Autocomplete suggestions
    bases = []
    for s in seeds:
        w = s.split()
        bases.extend([" ".join(w[:2]), " ".join(w[:3])] if len(w) >= 3 else [s])
    for ac in random.sample(list(set(bases)), min(num_autocomplete, len(set(bases)))):
        ac_count = 0
        for t in _serp_autocomplete(ac, serp_api_key, country):
            if t and t.lower() not in seen and _word_count(t) <= 6:
                seen.add(t.lower())
                candidates.append({"text": t, "source": "autocomplete", "tail_type": _keyword_type(t), "word_count": _word_count(t), "seed": ac, "total_results": 0})
                ac_count += 1
        if ac_count:
            print(f"  [AUTOCOMPLETE {country.upper()}] '{ac}': {ac_count} suggestions")
            time.sleep(0.5)

    s = sum(1 for c in candidates if c["tail_type"] == "short_tail")
    m = sum(1 for c in candidates if c["tail_type"] == "mid_tail")
    l = sum(1 for c in candidates if c["tail_type"] == "long_tail")
    print(f"  Candidates: {len(candidates)} ({s} short | {m} mid | {l} long)")
    return candidates


def pick_best_topic(candidates, client, history=None, context="mental health blog", model="claude-sonnet-4-6"):
    """Use Claude to pick the best keyword from SERP candidates.

    Args:
        candidates: List of candidate dicts from research_topics().
        client: Anthropic client.
        history: List of recently used topics to avoid.
        context: Description of what the content is for.
        model: Claude model to use.

    Returns:
        Dict with topic, keyword, question, tail_type, source, etc.
    """
    if not candidates:
        raise ValueError("No SERP candidates")

    # Sort: prefer mid-tail, then by source quality
    to = {"short_tail": 0, "mid_tail": 1, "long_tail": 2}
    so = {"autocomplete": 0, "people_also_ask": 1, "related_search": 2, "organic_title": 3}
    sc = sorted(candidates, key=lambda c: (to.get(c["tail_type"], 3), so.get(c["source"], 4)))

    cl = "\n".join([f"{i+1}. [{c['tail_type'].upper()} | {c['source'].upper()} | {c['word_count']}w] {c['text']}" for i, c in enumerate(sc[:50])])
    hn = ""
    if history:
        hn = "\nRECENT TOPICS (DO NOT REPEAT):\n" + "\n".join(f"  - {t}" for t in history) + "\nChoose something different.\n"

    prompt = f"""Expert in SEO for {context}.
{hn}
Choose the SINGLE BEST keyword from these SERP candidates.
FAVOUR: emotional, specific, high search intent, something someone types when they need help.

CANDIDATES:
{cl}

Return ONLY valid JSON:
{{"topic":"exact candidate text","question":"rephrase as a question","keyword":"1-5 word SEO keyword","tail_type":"short_tail|mid_tail|long_tail","competition_signal":"low|medium|high","why":"one sentence","source":"autocomplete|people_also_ask|related_search|organic_title"}}"""

    for attempt in range(3):
        try:
            raw = client.messages.create(
                model=model, max_tokens=500,
                messages=[{"role": "user", "content": prompt}]
            ).content[0].text.strip()
            if raw.startswith("```"):
                parts = raw.split("```")
                raw = parts[1].lstrip("json").strip() if len(parts) > 1 else raw
            import json
            result = json.loads(raw)
            print(f"  Winner: '{result.get('keyword')}' [{result.get('tail_type', '?')}] — {result.get('why', '')[:60]}")
            return result
        except Exception as e:
            print(f"  Topic selection attempt {attempt+1} failed: {e}")
            if attempt == 2:
                raise
            time.sleep(10)
    raise RuntimeError("Failed to pick topic")


def check_ranking(keyword, domain, serp_api_key, country="gb"):
    """Check if a domain ranks for a keyword and at what position.

    Returns:
        Dict with position (int or None), url (str or None), found (bool).
    """
    try:
        data = _serp_google(keyword, serp_api_key, country)
        for result in data.get("organic_results", []):
            link = result.get("link", "")
            if domain in link:
                pos = result.get("position", 0)
                print(f"  [RANK] '{keyword}': #{pos} — {link}")
                return {"position": pos, "url": link, "found": True}
        print(f"  [RANK] '{keyword}': not found in top 10")
        return {"position": None, "url": None, "found": False}
    except Exception as e:
        print(f"  [RANK] Check failed: {e}")
        return {"position": None, "url": None, "found": False, "error": str(e)}
