#!/usr/bin/env python3
"""
MindCore AI — Daily Telegram Digest v1.0
=========================================
Checks all GitHub Actions workflows and sends a daily summary to Telegram.
Runs at 07:00 UTC (09:00 Malta time).
"""

import os
import json
import requests
from datetime import datetime, timedelta

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")
GITHUB_TOKEN       = os.environ.get("GITHUB_TOKEN", "")
REPO               = "Keithfa007/mindcore_ai"


def get_workflow_runs():
    """Fetch the latest run for each workflow in the repo."""
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}

    resp = requests.get(f"https://api.github.com/repos/{REPO}/actions/workflows", headers=headers, timeout=30)
    if resp.status_code != 200:
        return None, f"GitHub API error: {resp.status_code}"

    workflows = resp.json().get("workflows", [])
    results = []

    for wf in workflows:
        if wf.get("state") != "active":
            continue

        runs_resp = requests.get(
            f"https://api.github.com/repos/{REPO}/actions/workflows/{wf['id']}/runs",
            headers=headers,
            params={"per_page": 1, "status": "completed"},
            timeout=30,
        )

        if runs_resp.status_code != 200:
            continue

        runs = runs_resp.json().get("workflow_runs", [])
        if not runs:
            results.append({
                "name": wf["name"],
                "status": "no_runs",
                "conclusion": None,
                "updated": None,
            })
            continue

        latest = runs[0]
        results.append({
            "name": wf["name"],
            "status": latest.get("status"),
            "conclusion": latest.get("conclusion"),
            "updated": latest.get("updated_at"),
        })

    return results, None


def get_recent_failures():
    """Get workflows that failed in the last 24 hours."""
    headers = {"Authorization": f"token {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"}
    since = (datetime.utcnow() - timedelta(hours=24)).strftime("%Y-%m-%dT%H:%M:%SZ")

    resp = requests.get(
        f"https://api.github.com/repos/{REPO}/actions/runs",
        headers=headers,
        params={"status": "failure", "created": f">{since}", "per_page": 20},
        timeout=30,
    )

    if resp.status_code != 200:
        return []

    return [
        {"name": r["name"], "updated": r["updated_at"], "url": r["html_url"]}
        for r in resp.json().get("workflow_runs", [])
    ]


def format_status_icon(conclusion):
    if conclusion == "success":
        return "\u2705"
    elif conclusion == "failure":
        return "\u274c"
    elif conclusion == "cancelled":
        return "\u26a0\ufe0f"
    elif conclusion is None:
        return "\u23f3"
    return "\u2753"


def format_time(iso_str):
    if not iso_str:
        return "never"
    try:
        dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ")
        return dt.strftime("%b %d, %H:%M UTC")
    except Exception:
        return iso_str


def build_message(workflows, failures):
    now = datetime.utcnow().strftime("%A, %b %d %Y \u2014 %H:%M UTC")
    lines = ["\U0001f4ca *MindCore AI \u2014 Daily Digest*", f"_{now}_", ""]

    total = len(workflows)
    passed = sum(1 for w in workflows if w["conclusion"] == "success")
    failed = sum(1 for w in workflows if w["conclusion"] == "failure")

    lines.append(f"\U0001f527 *Pipeline Health:* {passed}/{total} passing")
    if failed > 0:
        lines.append(f"\u274c *{failed} failed in last run*")
    lines.append("")

    failures_list = [w for w in workflows if w["conclusion"] == "failure"]
    success_list = [w for w in workflows if w["conclusion"] == "success"]
    other_list = [w for w in workflows if w["conclusion"] not in ("success", "failure")]

    if failures_list:
        lines.append("*\u274c Failed:*")
        for w in failures_list:
            lines.append(f"  \u274c {w['name']}")
            lines.append(f"      _{format_time(w['updated'])}_")
        lines.append("")

    if success_list:
        lines.append("*\u2705 Passing:*")
        for w in success_list:
            lines.append(f"  \u2705 {w['name']}")
        lines.append("")

    if other_list:
        lines.append("*\u23f3 Other:*")
        for w in other_list:
            lines.append(f"  {format_status_icon(w['conclusion'])} {w['name']} \u2014 {w['conclusion'] or 'no runs'}")
        lines.append("")

    if failures:
        lines.append("*\U0001f6a8 Failures in last 24h:*")
        for f in failures[:5]:
            lines.append(f"  \u274c {f['name']}")
            lines.append(f"      _{format_time(f['updated'])}_")
        lines.append("")

    lines.append("_Have a good day, Keith._ \U0001f4aa")

    return "\n".join(lines)


def send_telegram(message):
    """Send a message via Telegram bot."""
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    resp = requests.post(url, json=payload, timeout=30)
    if resp.status_code != 200:
        print(f"Telegram error: {resp.status_code} \u2014 {resp.text}")
        return False
    print("Telegram message sent successfully")
    return True


def main():
    print("== MindCore AI \u2014 Daily Digest ==\n")

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        return

    if not GITHUB_TOKEN:
        print("ERROR: GITHUB_TOKEN not set")
        return

    print("1. Fetching workflow statuses...")
    workflows, error = get_workflow_runs()
    if error:
        print(f"   Error: {error}")
        send_telegram(f"\u274c *Digest Error*\n\nCould not fetch pipeline data: {error}")
        return

    print(f"   Found {len(workflows)} workflows")

    print("2. Checking recent failures...")
    failures = get_recent_failures()
    print(f"   {len(failures)} failures in last 24h")

    print("3. Building message...")
    message = build_message(workflows, failures)

    print("4. Sending to Telegram...")
    send_telegram(message)

    print("\n== Done ==")


if __name__ == "__main__":
    main()
