#!/usr/bin/env python3
"""Quick test: query BigQuery GA4 data using service account."""
import os, json

sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "")
if not sa_json:
    print("ERROR: GOOGLE_SERVICE_ACCOUNT_JSON not set")
    exit(1)

from google.oauth2 import service_account
from google.cloud import bigquery

creds = service_account.Credentials.from_service_account_info(
    json.loads(sa_json),
    scopes=["https://www.googleapis.com/auth/bigquery.readonly"]
)

client = bigquery.Client(credentials=creds, project="mindcore-ai")

# List tables in the analytics dataset
print("=== BigQuery GA4 Tables ===")
tables = list(client.list_tables("mindcore-ai.analytics_516837337"))
for t in tables[-5:]:
    print(f"  {t.table_id}")

# Run a simple query on the latest events table
latest = tables[-1].table_id if tables else None
if latest and latest.startswith("events_"):
    query = f"""
    SELECT event_name, COUNT(*) as count
    FROM `mindcore-ai.analytics_516837337.{latest}`
    GROUP BY event_name
    ORDER BY count DESC
    LIMIT 10
    """
    print(f"\n=== Top events from {latest} ===")
    for row in client.query(query).result():
        print(f"  {row.event_name}: {row.count}")
else:
    print("No events tables found")
