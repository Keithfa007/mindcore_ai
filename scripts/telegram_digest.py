#!/usr/bin/env python3
"""
MindCore AI — Daily Telegram Digest v2.0
=========================================
Daily morning summary sent to Telegram:
- Pipeline health (GitHub Actions)
- Website visitors + bounce rate (Google Analytics GA4)
- Search Console stats (impressions, clicks, avg position)
- OpenAI daily cost
"""

import os
import json
import requests
from datetime import datetime, timedelta

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")
GITHUB_TOKEN       = os.environ.get("GITHUB_TOKEN", "")
OPENAI_API_KEY     = os.environ.get("OPENAI_API_KEY", "")
REPO               = "Keithfa007/mindcore_ai"
GA4_PROPERTY_ID    = "516837337"
SITE_URL           = "https://mindcoreai.eu/"


def get_google_credentials():
    """Load Google service account credentials from env."""
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


# ── Pipeline Health ──────────────────────────────────────────────────────

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


# ── Google Analytics ─────────────────────────────────────────────────────

def get_analytics_stats(creds):
    """Get yesterday's GA4 stats: sessions, users, bounce rate."""
    try:
        from google.analytics.data_v1beta import BetaAnalyticsDataClient
        from google.analytics.data_v1beta.types import RunReportRequest, DateRange, Metric

        client = BetaAnalyticsDataClient(credentials=creds)
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")

        request = RunReportRequest(
            property=f"properties/{GA4_PROPERTY_ID}",
            date_ranges=[DateRange(start_date=yesterday, end_date=yesterday)],
            metrics=[
                Metric(name="sessions"),
                Metric(name="activeUsers"),
                Metric(name="bounceRate"),
                Metric(name="screenPageViews"),
            ],
        )
        response = client.run_report(request)

        if response.rows:
            row = response.rows[0]
            return {
                "sessions": int(row.metric_values[0].value),
                "users": int(row.metric_values[1].value),
                "bounce_rate": round(float(row.metric_values[2].value) * 100, 1),
                "pageviews": int(row.metric_values[3].value),
                "date": yesterday,
            }
    except Exception as e:
        print(f"   Analytics error: {e}")
    return None


# ── Google Search Console ────────────────────────────────────────────────

def get_search_console_stats(creds):
    """Get last 7 days of Search Console stats."""
    try:
        from googleapiclient.discovery import build

        service = build("searchconsole", "v1", credentials=creds)
        end_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        start_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")

        response = service.searchanalytics().query(
            siteUrl=SITE_URL,
            body={
                "startDate": start_date,
                "endDate": end_date,
                "dimensions": [],
            }
        ).execute()

        if response.get("rows"):
            row = response["rows"][0]
            return {
                "clicks": int(row.get("clicks", 0)),
                "impressions": int(row.get("impressions", 0)),
                "ctr": round(row.get("ctr", 0) * 100, 1),
                "position": round(row.get("position", 0), 1),
                "period": f"{start_date} to {end_date}",
            }
    except Exception as e:
        print(f"   Search Console error: {e}")
    return None


# ── OpenAI Daily Cost ────────────────────────────────────────────────────

def get_openai_cost():
    """Get yesterday's OpenAI API cost."""
    if not OPENAI_API_KEY:
        return None
    try:
        yesterday = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}"}
        resp = requests.get(
            "https://api.openai.com/v1/organization/costs",
            headers=headers,
            params={"start_time": f"{yesterday}T00:00:00Z", "end_time": f"{yesterday}T23:59:59Z", "bucket_width": "1d"},
            timeout=30,
        )
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("data", [])
            if results:
                total_cents = sum(r.get("results", [{}])[0].get("amount", {}).get("value", 0) for r in results if r.get("results"))
                return {"cost": round(total_cents / 100, 2), "date": yesterday}
        else:
            print(f"   OpenAI cost API: {resp.status_code}")
    except Exception as e:
        print(f"   OpenAI cost error: {e}")
    return None


# ── Message Builder ──────────────────────────────────────────────────────

def format_time(iso_str):
    if not iso_str:
        return "never"
    try:
        return datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ").strftime("%b %d, %H:%M")
    except Exception:
        return iso_str


def build_message(workflows, failures, analytics, search_console, openai_cost):
    now = datetime.utcnow().strftime("%A, %b %d %Y \u2014 %H:%M UTC")
    lines = ["\U0001f4ca *MindCore AI \u2014 Daily Digest*", f"_{now}_", ""]

    # ── Pipelines ──
    total = len(workflows)
    passed = sum(1 for w in workflows if w["conclusion"] == "success")
    failed = sum(1 for w in workflows if w["conclusion"] == "failure")
    lines.append(f"\U0001f527 *Pipelines:* {passed}/{total} passing")
    if failed > 0:
        lines.append(f"\u274c {failed} failed:")
        for w in workflows:
            if w["conclusion"] == "failure":
                lines.append(f"  \u274c {w['name']}")
    lines.append("")

    # ── Website (Analytics) ──
    if analytics:
        lines.append("\U0001f310 *Website (yesterday):*")
        lines.append(f"  Users: {analytics['users']} | Sessions: {analytics['sessions']}")
        lines.append(f"  Pageviews: {analytics['pageviews']} | Bounce: {analytics['bounce_rate']}%")
        lines.append("")

    # ── Search Console ──
    if search_console:
        lines.append("\U0001f50d *Google Search (7 days):*")
        lines.append(f"  Impressions: {search_console['impressions']} | Clicks: {search_console['clicks']}")
        lines.append(f"  CTR: {search_console['ctr']}% | Avg Position: {search_console['position']}")
        lines.append("")

    # ── OpenAI Cost ──
    if openai_cost:
        emoji = "\u2705" if openai_cost["cost"] < 1 else "\u26a0\ufe0f" if openai_cost["cost"] < 5 else "\U0001f6a8"
        lines.append(f"\U0001f4b0 *OpenAI cost (yesterday):* {emoji} ${openai_cost['cost']:.2f}")
        lines.append("")

    # ── 24h Failures Detail ──
    if failures:
        lines.append(f"*\U0001f6a8 Failed in last 24h:*")
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
    print("== MindCore AI \u2014 Daily Digest v2.0 ==\n")

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

    print("3. Google Analytics...")
    creds = get_google_credentials()
    analytics = get_analytics_stats(creds) if creds else None
    print(f"   {'OK' if analytics else 'skipped'}")

    print("4. Search Console...")
    search_console = get_search_console_stats(creds) if creds else None
    print(f"   {'OK' if search_console else 'skipped'}")

    print("5. OpenAI cost...")
    openai_cost = get_openai_cost()
    print(f"   {'OK' if openai_cost else 'skipped'}")

    print("6. Sending digest...")
    message = build_message(workflows, failures, analytics, search_console, openai_cost)
    send_telegram(message)

    print("\n== Done ==")


if __name__ == "__main__":
    main()
