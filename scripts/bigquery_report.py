#!/usr/bin/env python3
"""
MindCore AI — BigQuery Analytics Report v1.3
=============================================
On-demand deep analytics from GA4 raw data in BigQuery.
Queries last 7 days of event data and sends formatted report to Telegram.

Covers: top pages, traffic sources, device split, country breakdown, engagement.

v1.3: Fixed page paths grouping — normalize URL in SQL before grouping.
v1.2: Fixed auth scope (bigquery.readonly -> bigquery).
v1.1: Error surfacing in Telegram.
"""

import os
import json
import requests
from datetime import datetime, timedelta

TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID   = os.environ.get("TELEGRAM_CHAT_ID", "")
PROJECT            = "mindcore-ai"
DATASET            = "analytics_516837337"


def get_client():
    from google.oauth2 import service_account
    from google.cloud import bigquery
    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
    if not sa_json:
        raise RuntimeError("GOOGLE_SERVICE_ACCOUNT_JSON not set")
    creds = service_account.Credentials.from_service_account_info(
        json.loads(sa_json),
        scopes=["https://www.googleapis.com/auth/bigquery"]
    )
    return bigquery.Client(credentials=creds, project=PROJECT)


def get_available_dates(client):
    """Find which event tables exist."""
    tables = list(client.list_tables(f"{PROJECT}.{DATASET}"))
    dates = sorted([t.table_id.replace("events_", "") for t in tables if t.table_id.startswith("events_")])
    return dates


def run_query(client, sql, errors=None):
    """Run a BigQuery SQL query and return rows as list of dicts."""
    try:
        result = client.query(sql).result()
        rows = [dict(row) for row in result]
        print(f"   Query returned {len(rows)} rows")
        return rows
    except Exception as e:
        msg = str(e)[:200]
        print(f"   Query error: {msg}")
        if errors is not None:
            errors.append(msg)
        return []


def format_number(n):
    if not n or n == 0:
        return "0"
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n/1_000:.1f}K"
    return str(int(n))


def build_report(client, dates):
    """Build analytics report from available dates."""
    if not dates:
        return "No GA4 data available in BigQuery yet."

    # Use last 7 days of available data
    recent = dates[-7:]
    tables = " UNION ALL ".join(
        [f"SELECT * FROM `{PROJECT}.{DATASET}.events_{d}`" for d in recent]
    )
    date_range = f"{recent[0][:4]}-{recent[0][4:6]}-{recent[0][6:]} to {recent[-1][:4]}-{recent[-1][4:6]}-{recent[-1][6:]}"

    print(f"   Querying {len(recent)} days: {date_range}")

    errors = []
    lines = []
    lines.append("\U0001f4ca *BigQuery Analytics Report*")
    lines.append(f"_{date_range} ({len(recent)} days)_")
    lines.append("")

    # 0. Diagnostic: test basic table access
    print("   [0/5] Diagnostic test...")
    test_table = f"`{PROJECT}.{DATASET}.events_{recent[-1]}`"
    diag = run_query(client, f"SELECT COUNT(*) as cnt FROM {test_table}", errors)
    if diag:
        lines.append(f"_Diagnostic: {diag[0].get('cnt', 0)} events in latest table_")
        lines.append("")
    elif errors:
        lines.append(f"_Diagnostic FAILED: {errors[-1]}_")
        lines.append("")

    # 1. Overview
    print("   [1/5] Overview...")
    rows = run_query(client, f"""
        SELECT
            COUNT(DISTINCT user_pseudo_id) as users,
            COUNT(*) as total_events,
            COUNTIF(event_name = 'page_view') as page_views,
            COUNTIF(event_name = 'session_start') as sessions,
            COUNTIF(event_name = 'first_visit') as new_users
        FROM ({tables})
    """, errors)
    if rows:
        r = rows[0]
        lines.append("\U0001f310 *Overview:*")
        lines.append(f"  Users: {format_number(r.get('users', 0))} | Sessions: {format_number(r.get('sessions', 0))}")
        lines.append(f"  Page views: {format_number(r.get('page_views', 0))} | New users: {format_number(r.get('new_users', 0))}")
        lines.append("")

    # 2. Top pages — normalize URL in SQL before grouping
    print("   [2/5] Top pages...")
    rows = run_query(client, f"""
        SELECT
            IFNULL(
                NULLIF(
                    REGEXP_REPLACE(
                        SPLIT(
                            SPLIT(
                                REPLACE(
                                    (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location'),
                                    'https://mindcoreai.eu', ''
                                ),
                                '?'
                            )[SAFE_OFFSET(0)],
                            '#'
                        )[SAFE_OFFSET(0)],
                        r'/$', ''
                    ),
                    ''
                ),
                '/'
            ) as page,
            COUNT(*) as views
        FROM ({tables})
        WHERE event_name = 'page_view'
        GROUP BY page
        ORDER BY views DESC
        LIMIT 8
    """, errors)
    if rows:
        lines.append("\U0001f4c4 *Top Pages:*")
        for r in rows:
            page = r.get('page', '/') or '/'
            lines.append(f"  {page} \u2014 {r.get('views', 0)} views")
        lines.append("")

    # 3. Traffic sources
    print("   [3/5] Traffic sources...")
    rows = run_query(client, f"""
        SELECT
            traffic_source.source as source,
            traffic_source.medium as medium,
            COUNT(DISTINCT user_pseudo_id) as users
        FROM ({tables})
        WHERE event_name = 'session_start'
        GROUP BY source, medium
        ORDER BY users DESC
        LIMIT 8
    """, errors)
    if rows:
        lines.append("\U0001f517 *Traffic Sources:*")
        for r in rows:
            source = r.get('source', '(direct)')
            medium = r.get('medium', '(none)')
            label = f"{source} / {medium}"
            lines.append(f"  {label} \u2014 {r.get('users', 0)} users")
        lines.append("")

    # 4. Countries
    print("   [4/5] Countries...")
    rows = run_query(client, f"""
        SELECT
            geo.country as country,
            COUNT(DISTINCT user_pseudo_id) as users
        FROM ({tables})
        WHERE event_name = 'session_start'
        GROUP BY country
        ORDER BY users DESC
        LIMIT 8
    """, errors)
    if rows:
        lines.append("\U0001f30d *Countries:*")
        for r in rows:
            country = r.get('country', 'Unknown')
            lines.append(f"  {country} \u2014 {r.get('users', 0)} users")
        lines.append("")

    # 5. Devices
    print("   [5/5] Devices...")
    rows = run_query(client, f"""
        SELECT
            device.category as device,
            COUNT(DISTINCT user_pseudo_id) as users
        FROM ({tables})
        WHERE event_name = 'session_start'
        GROUP BY device
        ORDER BY users DESC
    """, errors)
    if rows:
        lines.append("\U0001f4f1 *Devices:*")
        for r in rows:
            lines.append(f"  {r.get('device', 'unknown').capitalize()} \u2014 {r.get('users', 0)} users")
        lines.append("")

    # Error summary
    if errors:
        lines.append("\u26a0\ufe0f *Query Errors:*")
        for i, err in enumerate(errors[:5], 1):
            lines.append(f"  {i}. {err[:150]}")
        lines.append("")

    return "\n".join(lines)


def send_telegram(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram credentials not set, printing to console:")
        print(message)
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown", "disable_web_page_preview": True}
    resp = requests.post(url, json=payload, timeout=30)
    if resp.status_code != 200:
        print(f"Telegram error: {resp.status_code} \u2014 {resp.text}")
    else:
        print("Report sent to Telegram")


def main():
    print("== MindCore AI \u2014 BigQuery Analytics Report ==\n")

    print("1. Connecting to BigQuery...")
    client = get_client()

    print("2. Checking available data...")
    dates = get_available_dates(client)
    print(f"   {len(dates)} days of data available")

    if not dates:
        print("   No data yet. GA4 export needs at least 1 day.")
        return

    print("3. Building report...")
    report = build_report(client, dates)

    print("4. Sending to Telegram...")
    send_telegram(report)

    print("\n== Done ==")


if __name__ == "__main__":
    main()
