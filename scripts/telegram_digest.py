#!/usr/bin/env python3
"""
MindCore AI — Daily Telegram Digest v2.8
=========================================
v2.8: Auto-fetch Facebook page_id, impressions display fix, removed Instagram.
v2.7: Debug logging for Upload-Post API.
v2.6: Added Upload-Post social media analytics.
v2.5: Switched Firestore query to firebase_admin.

Daily morning summary sent to Telegram:
- Pipeline health (GitHub Actions)
- Today's scheduled pipelines
- App users (Firestore users collection)
- Social media analytics (Upload-Post API)
- Website stats 7-day (Google Analytics GA4)
- Search Console stats (impressions, clicks, avg position)
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
        cron_matches = re.findall(r"cron:\s*['\"](.+?)['\"]", content)
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
        return {"total": total, "new_24h": new_24h}
    except Exception as e:
        print(f"   Firestore users error: {e}")
        return None


def get_social_media_stats():
    if not UPLOAD_POST_API_KEY:
        print("   UPLOAD_POST_API_KEY not set")
        return None
    try:
        url = f"https://api.upload-post.com/api/analytics/{UPLOAD_POST_USER}"
        headers = {"Authorization": f"Apikey {UPLOAD_POST_API_KEY}"}

        # Fetch Facebook page ID first
        fb_page_id = None
        try:
            fb_resp = requests.get(
                "https://api.upload-post.com/api/uploadposts/facebook/pages",
                headers=headers, params={"user": UPLOAD_POST_USER}, timeout=15)
            if fb_resp.status_code == 200:
                pages = fb_resp.json()
                if isinstance(pages, list) and pages:
                    fb_page_id = pages[0].get("id", pages[0].get("page_id"))
                    print(f"   Facebook page ID: {fb_page_id}")
        except Exception as e:
            print(f"   Facebook pages lookup: {e}")

        # Fetch TikTok + YouTube
        resp = requests.get(url, headers=headers, params={"platforms": "tiktok,youtube"}, timeout=30)
        if resp.status_code != 200:
            print(f"   Upload-Post API error: {resp.status_code}")
            return None
        data = resp.json()

        # Fetch Facebook separately with page_id
        if fb_page_id:
            try:
                fb_resp = requests.get(url, headers=headers,
                    params={"platforms": "facebook", "page_id": fb_page_id}, timeout=30)
                if fb_resp.status_code == 200:
                    fb_data = fb_resp.json()
                    data["facebook"] = fb_data.get("facebook", {})
            except Exception as e:
                print(f"   Facebook analytics: {e}")

        results = {}
        for platform in ["tiktok", "facebook", "youtube"]:
            pdata = data.get(platform, {})
            if not isinstance(pdata, dict):
                continue
            if pdata.get("message") or pdata.get("success") is False:
                continue
            results[platform] = {
                "followers": pdata.get("followers", pdata.get("subscribers", 0)),
                "views": pdata.get("views", 0),
                "reach": pdata.get("reach", 0),
                "impressions": pdata.get("impressions", 0),
                "likes": pdata.get("likes", 0),
                "comments": pdata.get("comments", 0),
                "shares": pdata.get("shares", 0),
            }
        return results if results else None
    except Exception as e:
        print(f"   Social media stats error: {e}")
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


def build_message(workflows, failures, todays_schedule, firebase_users, social_stats, analytics, search_console):
    now = datetime.utcnow().strftime("%A, %b %d %Y \u2014 %H:%M UTC")
    lines = ["\U0001f4ca *MindCore AI \u2014 Daily Digest*", f"_{now}_", ""]

    total = len(workflows)
    passed = sum(1 for w in workflows if w["conclusion"] == "success")
    failed = sum(1 for w in workflows if w["conclusion"] == "failure")
    lines.append(f"\U0001f527 *Pipelines:* {passed}/{total} passing")
    if failed > 0:
        for w in workflows:
            if w["conclusion"] == "failure":
                lines.append(f"  \u274c {w['name']}")
    lines.append("")

    if todays_schedule:
        lines.append(f"\U0001f4c5 *Today's Schedule ({len(todays_schedule)} pipelines):*")
        for s in todays_schedule:
            if s.get("all_day"):
                lines.append(f"  \u23f0 {s['name']}")
            else:
                malta_h = (s['hour'] + 2) % 24
                lines.append(f"  \u23f0 {malta_h:02d}:{s['minute']:02d} \u2014 {s['name']}")
        lines.append("")

    if firebase_users:
        new_emoji = "\U0001f389" if firebase_users["new_24h"] > 0 else ""
        lines.append(f"\U0001f465 *App Users:* {firebase_users['total']} total")
        if firebase_users["new_24h"] > 0:
            lines.append(f"  {new_emoji} {firebase_users['new_24h']} new in last 24h")
        else:
            lines.append("  No new signups yesterday")
        lines.append("")

    if social_stats:
        lines.append("\U0001f4f1 *Social Media:*")
        for platform in ["tiktok", "facebook", "youtube"]:
            pdata = social_stats.get(platform)
            if not pdata:
                continue
            name = {"tiktok": "TikTok", "facebook": "Facebook", "youtube": "YouTube"}.get(platform, platform.capitalize())
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
            lines.append(f"  \u274c {f['name']} \u2014 _{format_time(f['updated'])}_")
        lines.append("")

    lines.append("_Have a good day, Keith._ \U0001f4aa")
    return "\n".join(lines)


def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    resp = requests.post(url, json=payload, timeout=30)
    if resp.status_code != 200:
        print(f"Telegram error: {resp.status_code} \u2014 {resp.text}")
        return False
    print("Telegram message sent")
    return True


def main():
    print("== MindCore AI \u2014 Daily Digest v2.8 ==\n")
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: Telegram credentials not set"); return
    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN not set"); return

    print("1. Pipeline health...")
    workflows, error = get_workflow_runs()
    if error:
        send_telegram(f"\u274c *Digest Error:* {error}"); return
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

    print("5. Social media (Upload-Post)...")
    social_stats = get_social_media_stats()
    if social_stats:
        print(f"   OK - {len(social_stats)} platforms")
    else:
        print("   skipped")

    print("6. Google Analytics (7 days)...")
    creds = get_google_credentials()
    analytics = get_analytics_stats(creds) if creds else None
    print(f"   {'OK' if analytics else 'skipped'}")

    print("7. Search Console...")
    search_console = get_search_console_stats(creds) if creds else None
    print(f"   {'OK' if search_console else 'skipped'}")

    print("8. Sending digest...")
    message = build_message(workflows, failures, todays_schedule, firebase_users, social_stats, analytics, search_console)
    send_telegram(message)
    print("\n== Done ==")


if __name__ == "__main__":
    main()
