#!/usr/bin/env python3
"""
MindCore AI — Daily Telegram Digest v3.6
=========================================
v3.6: Added Subscriptions / Trials section (isPremium counts, tier breakdown,
      new activations in 24h, unlock rate) from the same Firestore users pass.
v3.5: Added Meta Ads campaign report (spend, impressions, clicks, installs).
v3.4: Fixed Facebook page lookup to handle dict response from Upload-Post API.
v3.3: Added Facebook debug diagnostics to Telegram output.
v3.1: Fixed schedule to skip commented-out (paused) cron lines.
v2.9: Added US TikTok analytics, renamed EU TikTok label.
v2.8: Auto-fetch Facebook page_id, impressions display fix, removed Instagram.
v2.6: Added Upload-Post social media analytics.
v2.5: Switched Firestore query to firebase_admin.

Daily morning summary sent to Telegram:
- Pipeline health (GitHub Actions)
- Today's scheduled pipelines
- App users (Firestore users collection)
- Subscriptions / trials (Firestore isPremium)
- Social media analytics (Upload-Post API) — EU + US TikTok
- Website stats 7-day (Google Analytics GA4)
- Search Console stats (impressions, clicks, avg position)
- Meta Ads campaign report (spend, impressions, clicks, installs)
"""

import os
import json
import re
import base64
import requests
from datetime import datetime, timedelta

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")
GITHUB_TOKEN       = os.environ.get("GITHUB_TOKEN", "")
UPLOAD_POST_API_KEY = os.environ.get("UPLOAD_POST_API_KEY", "")
REPO               = "Keithfa007/mindcore_ai"
GA4_PROPERTY_ID    = "516837337"
SITE_URL           = "https://mindcoreai.eu/"
FIREBASE_PROJECT   = "mindcore-ai"
UPLOAD_POST_USER   = "MindCoreAI"
UPLOAD_POST_USER_US = "MindCoreAI_US"
META_ACCESS_TOKEN   = os.environ.get("META_ACCESS_TOKEN", "")
META_AD_ACCOUNT_ID  = "1662262447260384"


def get_google_credentials():
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not sa_json:
        return None
    try:
        from google.oauth2 import service_account
        info = json.loads(sa_json)
        return service_account.Credentials.from_service_account_info(
            info, scopes=[
                "https://www.googleapis.com/auth/analytics.readonly",
                "https://www.googleapis.com/auth/webmasters.readonly",
            ]
        )
    except Exception as e:
        print(f"   Google auth error: {e}")
        return None


def get_workflow_runs():
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    resp = requests.get(f"https://api.github.com/repos/{REPO}/actions/workflows", headers=headers, timeout=30)
    if resp.status_code != 200:
        return None, f"GitHub API error: {resp.status_code}"
    results = []
    for wf in resp.json().get("workflows", []):
        if wf.get("state") != "active":
            continue
        runs_resp = requests.get(
            f"https://api.github.com/repos/{REPO}/actions/workflows/{wf['id']}/runs",
            headers=headers, params={"per_page": 1, "status": "completed"}, timeout=30)
        if runs_resp.status_code != 200:
            continue
        runs = runs_resp.json().get("workflow_runs", [])
        if not runs:
            results.append({"name": wf["name"], "conclusion": None, "updated": None})
            continue
        latest = runs[0]
        results.append({"name": wf["name"], "conclusion": latest.get("conclusion"), "updated": latest.get("updated_at")})
    return results, None


def get_recent_failures():
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    since = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")
    resp = requests.get(f"https://api.github.com/repos/{REPO}/actions/runs", headers=headers,
                        params={"status": "failure", "created": f">{since}", "per_page": 20}, timeout=30)
    if resp.status_code != 200:
        return []
    return [{"name": r["name"], "updated": r["updated_at"]} for r in resp.json().get("workflow_runs", [])]


def cron_matches_today(cron_expr):
    parts = cron_expr.strip().split()
    if len(parts) < 5:
        return None
    minute, hour, dom, month, dow = parts[:5]
    today = datetime.utcnow()
    today_dow = today.weekday()
    today_dom = today.day
    cron_to_python_dow = {0: 6, 1: 0, 2: 1, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6}
    dow_match = False
    if dow == "*":
        dow_match = True
    else:
        for part in dow.split(","):
            if "-" in part:
                start, end = part.split("-")
                for d in range(int(start), int(end) + 1):
                    if cron_to_python_dow.get(d) == today_dow:
                        dow_match = True
            else:
                if cron_to_python_dow.get(int(part)) == today_dow:
                    dow_match = True
    dom_match = False
    if dom == "*":
        dom_match = True
    else:
        for part in dom.split(","):
            if int(part) == today_dom:
                dom_match = True
    if not (dow_match and dom_match):
        return None
    if hour == "*":
        return "all day"
    hours = []
    for part in hour.split(","):
        hours.append(int(part))
    return hours


def get_todays_schedule():
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    resp = requests.get(f"https://api.github.com/repos/{REPO}/contents/.github/workflows",
                        headers=headers, timeout=30)
    if resp.status_code != 200:
        return []
    schedule = []
    for f in resp.json():
        if not f["name"].endswith(".yml") and not f["name"].endswith(".yaml"):
            continue
        file_resp = requests.get(f["url"], headers=headers, timeout=30)
        if file_resp.status_code != 200:
            continue
        content = base64.b64decode(file_resp.json().get("content", "")).decode("utf-8", errors="ignore")
        name_match = re.search(r'^name:\s*(.+)$', content, re.MULTILINE)
        wf_name = name_match.group(1).strip().strip("'\"") if name_match else f["name"]
        # Only match uncommented cron lines (skip paused pipelines)
        cron_matches = []
        for line in content.splitlines():
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue
            m = re.search(r"cron:\s*['\"](.+?)['\"]", stripped)
            if m:
                cron_matches.append(m.group(1))
        for cron in cron_matches:
            hours = cron_matches_today(cron)
            if hours is not None:
                if isinstance(hours, list):
                    for h in hours:
                        schedule.append({"name": wf_name, "hour": h, "minute": int(cron.split()[0])})
                else:
                    schedule.append({"name": wf_name, "hour": 0, "minute": 0, "all_day": True})
    schedule.sort(key=lambda x: (x.get("hour", 0), x.get("minute", 0)))
    return schedule


def get_firestore_users():
    sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT", "")
    if not sa_json:
        print("   FIREBASE_SERVICE_ACCOUNT not set")
        return None
    try:
        import firebase_admin
        from firebase_admin import credentials, firestore
        if not firebase_admin._apps:
            cred = credentials.Certificate(json.loads(sa_json))
            firebase_admin.initialize_app(cred)
        db = firestore.client()
        docs = db.collection("users").stream()
        total = 0
        new_24h = 0
        premium_total = 0
        premium_new_24h = 0
        tier_premium = 0
        tier_pro = 0
        cutoff = datetime.utcnow() - timedelta(hours=24)
        for doc in docs:
            total += 1
            data = doc.to_dict()
            created = data.get("createdAt")
            if created:
                try:
                    if hasattr(created, "timestamp"):
                        created_dt = datetime.utcfromtimestamp(created.timestamp())
                    else:
                        created_dt = datetime.strptime(str(created)[:19], "%Y-%m-%dT%H:%M:%S")
                    if created_dt > cutoff:
                        new_24h += 1
                except:
                    pass
            # Subscription / trial access (isPremium = active Google Play trial or sub)
            if data.get("isPremium"):
                premium_total += 1
                tier = data.get("tier")
                if tier == "premium":
                    tier_premium += 1
                elif tier == "pro":
                    tier_pro += 1
                activated = data.get("premiumActivatedAt")
                if activated:
                    try:
                        if hasattr(activated, "timestamp"):
                            activated_dt = datetime.utcfromtimestamp(activated.timestamp())
                        else:
                            activated_dt = datetime.strptime(str(activated)[:19], "%Y-%m-%dT%H:%M:%S")
                        if activated_dt > cutoff:
                            premium_new_24h += 1
                    except:
                        pass
        return {
            "total": total,
            "new_24h": new_24h,
            "premium_total": premium_total,
            "premium_new_24h": premium_new_24h,
            "tier_premium": tier_premium,
            "tier_pro": tier_pro,
        }
    except Exception as e:
        print(f"   Firestore users error: {e}")
        return None


def _fetch_platform_stats(url, headers, platforms_param, extra_params=None):
    """Helper to fetch and parse Upload-Post analytics for given platforms."""
    params = {"platforms": platforms_param}
    if extra_params:
        params.update(extra_params)
    resp = requests.get(url, headers=headers, params=params, timeout=30)
    if resp.status_code != 200:
        return {}
    return resp.json()



def _extract_pages_from_response(pages_raw, fb_debug):
    """Extract a list of page objects from the Upload-Post /facebook/pages response.

    The API may return:
    - A list of page dicts (original expected format)
    - A dict wrapping a list under a common key (data, pages, results, items)
    - A dict that IS a single page object (has id or page_id)
    - A dict with some arbitrary key containing a list of page dicts
    """
    fb_debug.append(f"type={type(pages_raw).__name__}")

    if isinstance(pages_raw, list):
        fb_debug.append(f"pages_count={len(pages_raw)}")
        return pages_raw if pages_raw else None

    if isinstance(pages_raw, dict):
        fb_debug.append(f"keys={list(pages_raw.keys())[:8]}")

        for key in ("data", "pages", "results", "items"):
            if key in pages_raw and isinstance(pages_raw[key], list):
                extracted = pages_raw[key]
                fb_debug.append(f"extracted_from={key}")
                fb_debug.append(f"pages_count={len(extracted)}")
                return extracted if extracted else None

        pid = pages_raw.get("id") or pages_raw.get("page_id")
        if pid:
            fb_debug.append("dict_is_single_page")
            fb_debug.append("pages_count=1")
            return [pages_raw]

        for k, v in pages_raw.items():
            if isinstance(v, list) and v and isinstance(v[0], dict):
                if "id" in v[0] or "page_id" in v[0]:
                    fb_debug.append(f"extracted_from={k}")
                    fb_debug.append(f"pages_count={len(v)}")
                    return v

        fb_debug.append("no_page_id_found_in_dict")

    return None


def get_social_media_stats():
    if not UPLOAD_POST_API_KEY:
        print("   UPLOAD_POST_API_KEY not set")
        return None
    try:
        headers = {"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"}
        eu_url = f"https://api.upload-post.com/api/analytics/{UPLOAD_POST_USER}"
        us_url = f"https://api.upload-post.com/api/analytics/{UPLOAD_POST_USER_US}"

        # Fetch Facebook page ID
        fb_page_id = None
        fb_debug = []
        try:
            fb_resp = requests.get(
                "https://api.upload-post.com/api/uploadposts/facebook/pages",
                headers=headers, params={"user": UPLOAD_POST_USER}, timeout=15)
            fb_debug.append(f"pages_status={fb_resp.status_code}")
            if fb_resp.status_code == 200:
                pages_raw = fb_resp.json()
                pages = _extract_pages_from_response(pages_raw, fb_debug)
                if pages:
                    fb_page_id = pages[0].get("id") or pages[0].get("page_id")
                    fb_debug.append(f"page_id={fb_page_id}")
                else:
                    fb_debug.append("no_pages_found")
            else:
                fb_debug.append(f"pages_body={fb_resp.text[:200]}")
        except Exception as e:
            fb_debug.append(f"pages_error={e}")
            print(f"   Facebook pages lookup failed: {e}")

        # EU: TikTok + YouTube
        eu_data = _fetch_platform_stats(eu_url, headers, "tiktok,youtube,x,pinterest")

        # EU: Facebook (needs page_id)
        if fb_page_id:
            fb_resp_raw = requests.get(eu_url, headers=headers,
                                        params={"platforms": "facebook", "page_id": fb_page_id}, timeout=30)
            fb_debug.append(f"analytics_status={fb_resp_raw.status_code}")
            if fb_resp_raw.status_code == 200:
                fb_data = fb_resp_raw.json()
                fb_entry = fb_data.get("facebook", {})
                fb_debug.append(f"has_data={bool(fb_entry)}")
                if isinstance(fb_entry, dict):
                    fb_debug.append(f"keys={list(fb_entry.keys())[:8]}")
                    if fb_entry.get("message"):
                        fb_debug.append(f"msg={fb_entry['message'][:100]}")
                eu_data["facebook"] = fb_entry
            else:
                fb_debug.append(f"analytics_body={fb_resp_raw.text[:200]}")
        else:
            fb_debug.append("skipped_no_page_id")
        print(f"   Facebook debug: {' | '.join(fb_debug)}")

        # US: TikTok
        us_data = _fetch_platform_stats(us_url, headers, "tiktok")

        results = {}
        platform_map = {
            "tiktok": ("TikTok (EU)", eu_data),
            "facebook": ("Facebook", eu_data),
            "youtube": ("YouTube", eu_data),
            "x": ("X", eu_data),
            "pinterest": ("Pinterest", eu_data),
        }

        for key, (label, source) in platform_map.items():
            pdata = source.get(key, {})
            if not isinstance(pdata, dict):
                continue
            if pdata.get("message") or pdata.get("success") is False:
                continue
            results[key] = {
                "followers": pdata.get("followers", pdata.get("subscribers", 0)),
                "views": pdata.get("views", 0),
                "impressions": pdata.get("impressions", 0),
                "reach": pdata.get("reach", 0),
                "likes": pdata.get("likes", 0),
                "comments": pdata.get("comments", 0),
                "shares": pdata.get("shares", 0),
            }

        # US TikTok
        us_tk = us_data.get("tiktok", {})
        if isinstance(us_tk, dict) and not us_tk.get("message") and us_tk.get("success") is not False:
            results["tiktok_us"] = {
                "followers": us_tk.get("followers", 0),
                "views": us_tk.get("views", 0),
                "impressions": us_tk.get("impressions", 0),
                "reach": us_tk.get("reach", 0),
                "likes": us_tk.get("likes", 0),
                "comments": us_tk.get("comments", 0),
                "shares": us_tk.get("shares", 0),
            }

        return results if results else None
    except Exception as e:
        print(f"   Social media stats error: {e}")
        return None




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


def get_analytics_stats(creds):
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric
        client = BetaAnalyticsDataClient(credentials=creds)
        end_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        start_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        request = RunReportRequest(
            property=f"properties/{GA4_PROPERTY_ID}",
            date_ranges=[DateRange(start_date=start_date, end_date=end_date)],
            metrics=[Metric(name="sessions"), Metric(name="activeUsers"),
                     Metric(name="bounceRate"), Metric(name="screenPageViews")],
        )
        response = client.run_report(request)
        if response.rows:
            row = response.rows[0]
            return {
                "sessions": int(row.metric_values[0].value),
                "users": int(row.metric_values[1].value),
                "bounce_rate": round(float(row.metric_values[2].value) * 100, 1),
                "pageviews": int(row.metric_values[3].value),
            }
    except Exception as e:
        print(f"   Analytics error: {e}")
    return None


def get_search_console_stats(creds):
    try:
        from googleapiclient.discovery import build
        service = build("searchconsole", "v1", credentials=creds)
        end_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        start_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
        response = service.searchanalytics().query(
            siteUrl=SITE_URL,
            body={"startDate": start_date, "endDate": end_date, "dimensions": []},
        ).execute()
        if response.get("rows"):
            row = response["rows"][0]
            return {
                "clicks": int(row.get("clicks", 0)),
                "impressions": int(row.get("impressions", 0)),
                "ctr": round(row.get("ctr", 0) * 100, 1),
                "position": round(row.get("position", 0), 1),
            }
    except Exception as e:
        print(f"   Search Console error: {e}")
    return None


def format_time(iso_str):
    if not iso_str:
        return "never"
    try:
        return datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ").strftime("%b %d, %H:%M")
    except Exception:
        return iso_str


def format_number(n):
    if not n or n == 0:
        return "0"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(n)


def build_message(workflows, failures, todays_schedule, firebase_users, social_stats, meta_ads, analytics, search_console):
    now = datetime.utcnow().strftime("%A, %b %d %Y — %H:%M UTC")
    lines = ["\U0001f4ca *MindCore AI — Daily Digest*", f"_{now}_", ""]

    total = len(workflows)
    passed = sum(1 for w in workflows if w["conclusion"] == "success")
    failed = sum(1 for w in workflows if w["conclusion"] == "failure")
    lines.append(f"\U0001f527 *Pipelines:* {passed}/{total} passing")
    if failed > 0:
        for w in workflows:
            if w["conclusion"] == "failure":
                lines.append(f"  ❌ {w['name']}")
    lines.append("")

    if todays_schedule:
        lines.append(f"\U0001f4c5 *Today's Schedule ({len(todays_schedule)} pipelines):*")
        for s in todays_schedule:
            if s.get("all_day"):
                lines.append(f"  ⏰ {s['name']}")
            else:
                malta_h = (s['hour'] + 2) % 24
                lines.append(f"  ⏰ {malta_h:02d}:{s['minute']:02d} — {s['name']}")
        lines.append("")

    if firebase_users:
        new_emoji = "\U0001f389" if firebase_users["new_24h"] > 0 else ""
        lines.append(f"\U0001f465 *App Users:* {firebase_users['total']} total")
        if firebase_users["new_24h"] > 0:
            lines.append(f"  {new_emoji} {firebase_users['new_24h']} new in last 24h")
        else:
            lines.append("  No new signups yesterday")
        lines.append("")

        # Subscriptions / trials (isPremium = active Google Play trial or subscription)
        prem_total = firebase_users.get("premium_total", 0)
        prem_new = firebase_users.get("premium_new_24h", 0)
        total_users = firebase_users.get("total", 0)
        conv = round(prem_total / total_users * 100, 1) if total_users else 0
        sub_emoji = "\U0001f389" if prem_new > 0 else "\U0001f4b3"
        lines.append(f"{sub_emoji} *Subscriptions / Trials:* {prem_total} active")
        lines.append(f"  Premium: {firebase_users.get('tier_premium', 0)} | Pro: {firebase_users.get('tier_pro', 0)}")
        if prem_new > 0:
            lines.append(f"  \U0001f195 {prem_new} new trial/sub in last 24h")
        else:
            lines.append("  No new trials/subs in last 24h")
        lines.append(f"  Unlock rate: {conv}% of users")
        lines.append("")

    if social_stats:
        lines.append("\U0001f4f1 *Social Media:*")
        for platform in ["tiktok", "tiktok_us", "x", "facebook", "youtube", "pinterest"]:
            pdata = social_stats.get(platform)
            if not pdata:
                continue
            name = {"tiktok": "TikTok (EU)", "tiktok_us": "TikTok (US)", "x": "X", "facebook": "Facebook", "youtube": "YouTube", "pinterest": "Pinterest"}.get(platform, platform.capitalize())
            parts = []
            views = pdata.get("views", 0)
            impressions = pdata.get("impressions", 0)
            reach = pdata.get("reach", 0)
            if views:
                parts.append(f"{format_number(views)} views")
            elif impressions:
                parts.append(f"{format_number(impressions)} impressions")
            elif reach:
                parts.append(f"{format_number(reach)} reach")
            if pdata.get("likes"):
                parts.append(f"{format_number(pdata['likes'])} likes")
            if pdata.get("followers"):
                parts.append(f"{format_number(pdata['followers'])} followers")
            if parts:
                lines.append(f"  {name}: {' | '.join(parts)}")
            else:
                if platform == "facebook":
                    lines.append(f"  {name}: no 30-day data (reconnect in Upload-Post)")
                else:
                    lines.append(f"  {name}: no 30-day data")
        lines.append("")

    if meta_ads:
        lines.append("\U0001f4b0 *Meta Ads (7 days):*")
        lines.append(f"  Spend: €{meta_ads['spend']:.2f} | Impressions: {format_number(meta_ads['impressions'])}")
        lines.append(f"  Reach: {format_number(meta_ads['reach'])} | Clicks: {meta_ads['clicks']}")
        if meta_ads['installs'] > 0:
            lines.append(f"  \U0001f4f2 Installs: {meta_ads['installs']} | CPI: €{meta_ads['cpi']:.2f}")
        else:
            lines.append(f"  Installs: 0 | CTR: {meta_ads['ctr']}%")
        lines.append("")

    if analytics:
        lines.append("\U0001f310 *Website (7 days):*")
        lines.append(f"  Users: {analytics['users']} | Sessions: {analytics['sessions']}")
        lines.append(f"  Pageviews: {analytics['pageviews']} | Bounce: {analytics['bounce_rate']}%")
        lines.append("")

    if search_console:
        lines.append("\U0001f50d *Google Search (7 days):*")
        lines.append(f"  Impressions: {search_console['impressions']} | Clicks: {search_console['clicks']}")
        lines.append(f"  CTR: {search_console['ctr']}% | Avg Position: {search_console['position']}")
        lines.append("")

    if failures:
        lines.append("*\U0001f6a8 Failed in last 24h:*")
        for f in failures[:5]:
            lines.append(f"  ❌ {f['name']} — _{format_time(f['updated'])}_")
        lines.append("")

    lines.append("_Have a good day, Keith._ \U0001f4aa")
    return "\n".join(lines)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    resp = requests.post(url, json=payload, timeout=30)
    if resp.status_code != 200:
        print(f"Telegram error: {resp.status_code} — {resp.text}")
        return False
    print("Telegram message sent")
    return True


def main():
    print("== MindCore AI — Daily Digest v3.6 ==\n")
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: Telegram credentials not set"); return
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN not set"); return

    print("1. Pipeline health...")
    workflows, error = get_workflow_runs()
    if error:
        send_telegram(f"❌ *Digest Error:* {error}"); return
    print(f"   {len(workflows)} workflows")

    print("2. Recent failures...")
    failures = get_recent_failures()
    print(f"   {len(failures)} in last 24h")

    print("3. Today's schedule...")
    todays_schedule = get_todays_schedule()
    print(f"   {len(todays_schedule)} pipelines scheduled today")

    print("4. App users (Firestore)...")
    firebase_users = get_firestore_users()
    print(f"   {'OK - ' + str(firebase_users['total']) + ' users' if firebase_users else 'skipped'}")

    print("5. Social media (Upload-Post EU + US)...")
    social_stats = get_social_media_stats()
    if social_stats:
        print(f"   OK - {len(social_stats)} platforms")
    else:
        print("   skipped")

    print("6. Meta Ads...")
    meta_ads = get_meta_ads_stats()
    if meta_ads:
        print(f"   OK - €{meta_ads['spend']:.2f} spent, {meta_ads['installs']} installs")
    else:
        print("   skipped")

    print("7. Google Analytics (7 days)...")
    creds = get_google_credentials()
    analytics = get_analytics_stats(creds) if creds else None
    print(f"   {'OK' if analytics else 'skipped'}")

    print("8. Search Console...")
    search_console = get_search_console_stats(creds) if creds else None
    print(f"   {'OK' if search_console else 'skipped'}")

    print("9. Sending digest...")
    message = build_message(workflows, failures, todays_schedule, firebase_users, social_stats, meta_ads, analytics, search_console)
    send_telegram(message)
    print("\n== Done ==")


if __name__ == "__main__":
    main()
