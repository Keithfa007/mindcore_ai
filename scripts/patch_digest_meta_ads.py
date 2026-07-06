#!/usr/bin/env python3
"""One-shot patch: telegram_digest.py v3.4 -> v3.5
Adds Meta Ads campaign report to daily Telegram digest.
Shows: spend, impressions, reach, clicks, installs, CPI, CTR.
"""

filepath = "scripts/telegram_digest.py"

with open(filepath, "r") as f:
    content = f.read()

# 1. Update version
content = content.replace(
    "Daily Telegram Digest v3.4",
    "Daily Telegram Digest v3.5"
)
content = content.replace(
    "v3.4: Fixed Facebook page lookup to handle dict response from Upload-Post API.",
    "v3.5: Added Meta Ads campaign report (spend, impressions, clicks, installs).\nv3.4: Fixed Facebook page lookup to handle dict response from Upload-Post API."
)
content = content.replace(
    "Daily Digest v3.4 ==",
    "Daily Digest v3.5 =="
)

# 2. Add META env vars after UPLOAD_POST_USER_US
old_vars = 'UPLOAD_POST_USER_US = "MindCoreAI_US"'
new_vars = '''UPLOAD_POST_USER_US = "MindCoreAI_US"
META_ACCESS_TOKEN   = os.environ.get("META_ACCESS_TOKEN", "")
META_AD_ACCOUNT_ID  = "1662262447260384"'''

assert old_vars in content, "UPLOAD_POST_USER_US not found!"
content = content.replace(old_vars, new_vars)

# 3. Add get_meta_ads_stats function before get_analytics_stats
meta_ads_func = '''

def get_meta_ads_stats():
    """Fetch Meta Ads campaign performance for last 7 days."""
    if not META_ACCESS_TOKEN:
        print("   META_ACCESS_TOKEN not set")
        return None
    try:
        url = f"https://graph.facebook.com/v21.0/act_{META_AD_ACCOUNT_ID}/insights"
        params = {
            "access_token": META_ACCESS_TOKEN,
            "date_preset": "last_7d",
            "fields": "spend,impressions,reach,clicks,actions,cost_per_action_type,ctr,cpm",
            "level": "account",
        }
        resp = requests.get(url, params=params, timeout=30)
        if resp.status_code != 200:
            print(f"   Meta Ads API error: {resp.status_code} - {resp.text[:200]}")
            return None
        data = resp.json().get("data", [])
        if not data:
            print("   Meta Ads: no data returned (campaigns may be paused)")
            return None
        row = data[0]
        spend = float(row.get("spend", 0))
        impressions = int(row.get("impressions", 0))
        reach = int(row.get("reach", 0))
        clicks = int(row.get("clicks", 0))
        ctr = float(row.get("ctr", 0))
        cpm = float(row.get("cpm", 0))
        # Extract app installs from actions
        installs = 0
        actions = row.get("actions", [])
        for action in actions:
            if action.get("action_type") in ("mobile_app_install", "app_install", "omni_app_install"):
                installs += int(action.get("value", 0))
        # Extract cost per install
        cpi = 0
        cost_actions = row.get("cost_per_action_type", [])
        for ca in cost_actions:
            if ca.get("action_type") in ("mobile_app_install", "app_install", "omni_app_install"):
                cpi = float(ca.get("value", 0))
        return {
            "spend": spend,
            "impressions": impressions,
            "reach": reach,
            "clicks": clicks,
            "installs": installs,
            "ctr": round(ctr, 2),
            "cpm": round(cpm, 2),
            "cpi": round(cpi, 2),
        }
    except Exception as e:
        print(f"   Meta Ads error: {e}")
        return None


'''

old_analytics_def = "def get_analytics_stats(creds):"
assert old_analytics_def in content, "get_analytics_stats not found!"
content = content.replace(old_analytics_def, meta_ads_func + old_analytics_def)

# 4. Add Meta Ads section to build_message (after social stats, before website)
old_build_sig = "def build_message(workflows, failures, todays_schedule, firebase_users, social_stats, analytics, search_console):"
new_build_sig = "def build_message(workflows, failures, todays_schedule, firebase_users, social_stats, meta_ads, analytics, search_console):"

assert old_build_sig in content, "build_message signature not found!"
content = content.replace(old_build_sig, new_build_sig)

# Insert Meta Ads display block before website section
old_website_section = '''    if analytics:
        lines.append("\\U0001f310 *Website (7 days):*")'''

meta_ads_display = '''    if meta_ads:
        lines.append("\\U0001f4b0 *Meta Ads (7 days):*")
        lines.append(f"  Spend: \\u20ac{meta_ads['spend']:.2f} | Impressions: {format_number(meta_ads['impressions'])}")
        lines.append(f"  Reach: {format_number(meta_ads['reach'])} | Clicks: {meta_ads['clicks']}")
        if meta_ads['installs'] > 0:
            lines.append(f"  \\U0001f4f2 Installs: {meta_ads['installs']} | CPI: \\u20ac{meta_ads['cpi']:.2f}")
        else:
            lines.append(f"  Installs: 0 | CTR: {meta_ads['ctr']}%")
        lines.append("")

'''

assert old_website_section in content, "Website section not found!"
content = content.replace(old_website_section, meta_ads_display + old_website_section)

# 5. Add Meta Ads step to main() and update build_message call
old_step_6 = '''    print("6. Google Analytics (7 days)...")'''
new_step_6 = '''    print("6. Meta Ads...")
    meta_ads = get_meta_ads_stats()
    if meta_ads:
        print(f"   OK - \\u20ac{meta_ads['spend']:.2f} spent, {meta_ads['installs']} installs")
    else:
        print("   skipped")

    print("7. Google Analytics (7 days)...")'''

assert old_step_6 in content, "Step 6 not found!"
content = content.replace(old_step_6, new_step_6)

# Renumber remaining steps
content = content.replace(
    '    print("7. Search Console...")',
    '    print("8. Search Console...")'
)
content = content.replace(
    '    print("8. Sending digest...")',
    '    print("9. Sending digest...")'
)

# Update build_message call to include meta_ads
old_call = "    message = build_message(workflows, failures, todays_schedule, firebase_users, social_stats, analytics, search_console)"
new_call = "    message = build_message(workflows, failures, todays_schedule, firebase_users, social_stats, meta_ads, analytics, search_console)"

assert old_call in content, "build_message call not found!"
content = content.replace(old_call, new_call)

# 6. Update docstring
content = content.replace(
    "- Search Console stats (impressions, clicks, avg position)",
    "- Search Console stats (impressions, clicks, avg position)\n- Meta Ads campaign report (spend, impressions, clicks, installs)"
)

with open(filepath, "w") as f:
    f.write(content)

print("Patch applied!")

with open(filepath, "r") as f:
    patched = f.read()

assert "v3.5" in patched, "Version not updated"
assert "META_ACCESS_TOKEN" in patched, "Meta env var not added"
assert "get_meta_ads_stats" in patched, "Meta function not added"
assert "meta_ads" in patched, "meta_ads not in build_message"
assert "Meta Ads (7 days)" in patched, "Meta display not added"
assert "graph.facebook.com" in patched, "Meta API URL not found"
print("All assertions passed!")
